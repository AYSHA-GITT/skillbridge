"""
Jooble REST API adapter.

Request:  POST https://{JOOBLE_API_HOST}/api/{JOOBLE_API_KEY}
          JSON body: {"keywords", "location", "page", "ResultOnPage", "companysearch": false}
Response: {"totalCount", "jobs": [{id, title, location, snippet, salary, source,
          type, link, company, updated}]}

Important (from Jooble's API documentation):
* The free plan allows 100 requests per day per key, reset at midnight UTC.
  With 12 syncs/day keep JOOBLE_MAX_REQUESTS_PER_RUN <= 8.
* Keys are country-domain specific - a jooble.org key only returns US jobs.
  For Indian jobs request a key for the Indian domain and set
  JOOBLE_API_HOST accordingly (default: in.jooble.org).
* `updated` is the time Jooble last updated the listing, NOT the original
  posting date, so it is not stored as posting_date.
"""
import os
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from utils.job_discovery.base_adapter import (
    JobSourceAdapter, ProviderBadResponse, ProviderNotConfigured, RequestBudgetExceeded,
)

def parse_jooble_salary(text: Optional[str]) -> Tuple[Optional[float], Optional[float], Optional[str], Optional[str]]:
    """Parse strings like '₹30,000 - ₹45,000 per month' or '6 - 9 lakh per year'.
    Returns (min, max, currency, period); all None when it cannot be parsed reliably."""
    if not text or not isinstance(text, str):
        return None, None, None, None
    t = text.replace(" ", " ")
    currency = "INR" if ("₹" in t or "inr" in t.lower() or "lakh" in t.lower() or "lpa" in t.lower()) else \
        "USD" if "$" in t else "EUR" if "€" in t else "GBP" if "£" in t else None
    tl = t.lower()
    period = ("year" if re.search(r"year|annum|annual|lpa|p\.a", tl) else
              "month" if "month" in tl else "week" if "week" in tl else
              "day" if re.search(r"\bday\b|daily", tl) else "hour" if "hour" in tl else None)
    if "lpa" in tl:
        tl = tl.replace("lpa", " lakh")
    nums = re.findall(r"(\d[\d,]*\.?\d*)\s*(k|lakh|lac|l\b)?", tl)[:2]
    # "6 - 9 lakh": a unit written once applies to both ends of the range
    units = [u for _, u in nums if u]
    shared_unit = units[-1] if len(units) == 1 else None
    values: List[float] = []
    for num, unit in nums:
        try:
            v = float(num.replace(",", ""))
        except ValueError:
            continue
        unit = unit or shared_unit
        if unit == "k":
            v *= 1_000
        elif unit in ("lakh", "lac", "l"):
            v *= 100_000
        values.append(v)
    if not values or currency is None or period is None:
        return None, None, None, None
    lo, hi = (values[0], values[1]) if len(values) > 1 else (values[0], values[0])
    return min(lo, hi), max(lo, hi), currency, period


class JoobleAdapter(JobSourceAdapter):
    provider_key = "jooble"
    default_request_budget = 8

    def __init__(self, api_key=None, host=None, results_per_page=None, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key if api_key is not None else os.getenv("JOOBLE_API_KEY", "")
        self.host = (host or os.getenv("JOOBLE_API_HOST", "in.jooble.org")).strip().rstrip("/")
        self.results_per_page = int(results_per_page or os.getenv("JOOBLE_RESULTS_PER_PAGE", "30"))

    @property
    def source_name(self) -> str:
        return "Jooble"

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def fetch_jobs(self, searches: Iterable[Dict[str, str]]) -> List[Dict[str, Any]]:
        if not self.is_configured():
            raise ProviderNotConfigured("Jooble: JOOBLE_API_KEY not set")
        url = f"https://{self.host}/api/{self.api_key}"
        jobs: List[Dict[str, Any]] = []
        for search in searches:
            body = {
                "keywords": search.get("what", ""),
                "location": search.get("where") or "India",
                "page": 1,
                "ResultOnPage": self.results_per_page,
                "companysearch": False,
            }
            try:
                data = self._request("POST", url, json=body, headers={"Content-Type": "application/json"})
            except RequestBudgetExceeded:
                break
            if not isinstance(data, dict) or not isinstance(data.get("jobs", []), list):
                raise ProviderBadResponse("Jooble: unexpected response shape")
            for item in data.get("jobs", []):
                if not isinstance(item, dict):
                    continue
                smin, smax, cur, period = parse_jooble_salary(item.get("salary"))
                jobs.append({
                    "source_provider": self.provider_key,
                    "source_name": f"Jooble (via {item.get('source')})" if item.get("source") else "Jooble",
                    "source_job_id": item.get("id"),
                    "title": item.get("title"),
                    "company": item.get("company"),
                    "description": item.get("snippet"),
                    "location": item.get("location"),
                    "url": item.get("link"),
                    "posted_at": None,               # Jooble exposes only 'updated', not a posting date
                    "provider_updated_at": item.get("updated"),
                    "salary_min": smin,
                    "salary_max": smax,
                    "salary_currency": cur,
                    "salary_period": period,
                    "salary_is_estimated": False if smin is not None else None,
                    "contract_type": item.get("type"),
                    "search_query": search,
                })
        return jobs
