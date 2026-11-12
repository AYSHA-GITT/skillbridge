"""
Adzuna job search API adapter (https://developer.adzuna.com/docs/search).

Request:  GET https://api.adzuna.com/v1/api/jobs/{country}/search/{page}
          ?app_id=..&app_key=..&what=..&where=..&results_per_page=..
Response: results[] with id, title, description (snippet only), created,
          redirect_url, company.display_name, location.display_name/area,
          salary_min, salary_max, salary_is_predicted, contract_type,
          contract_time, category.label

Credentials: ADZUNA_APP_ID, ADZUNA_APP_KEY (server-side env vars only).
Usage limits depend on your Adzuna plan - set JOB_ADZUNA_MAX_REQUESTS_PER_RUN
so that (requests per run x 12 runs/day) stays inside your daily quota.
"""
import os
from typing import Any, Dict, Iterable, List

from utils.job_discovery.base_adapter import (
    JobSourceAdapter, ProviderBadResponse, ProviderNotConfigured, RequestBudgetExceeded,
)

COUNTRY_CURRENCY = {"in": ("INR", "India"), "gb": ("GBP", "United Kingdom"), "us": ("USD", "United States"),
                    "sg": ("SGD", "Singapore"), "au": ("AUD", "Australia"), "ca": ("CAD", "Canada")}


class AdzunaAdapter(JobSourceAdapter):
    provider_key = "adzuna"
    default_request_budget = 12
    API_BASE = "https://api.adzuna.com/v1/api/jobs"

    def __init__(self, app_id=None, app_key=None, country=None, results_per_page=None,
                 max_days_old=None, **kwargs):
        super().__init__(**kwargs)
        self.app_id = app_id if app_id is not None else os.getenv("ADZUNA_APP_ID", "")
        self.app_key = app_key if app_key is not None else os.getenv("ADZUNA_APP_KEY", "")
        self.country = (country or os.getenv("ADZUNA_COUNTRY", "in")).lower()
        self.results_per_page = int(results_per_page or os.getenv("ADZUNA_RESULTS_PER_PAGE", "50"))
        self.max_days_old = int(max_days_old or os.getenv("ADZUNA_MAX_DAYS_OLD", "30"))

    @property
    def source_name(self) -> str:
        return "Adzuna"

    def is_configured(self) -> bool:
        return bool(self.app_id and self.app_key)

    def fetch_jobs(self, searches: Iterable[Dict[str, str]]) -> List[Dict[str, Any]]:
        if not self.is_configured():
            raise ProviderNotConfigured("Adzuna: ADZUNA_APP_ID / ADZUNA_APP_KEY not set")
        currency, country_name = COUNTRY_CURRENCY.get(self.country, (None, None))
        jobs: List[Dict[str, Any]] = []
        for search in searches:
            params = {
                "app_id": self.app_id,
                "app_key": self.app_key,
                "results_per_page": self.results_per_page,
                "what": search.get("what", ""),
                "sort_by": "date",
                "max_days_old": self.max_days_old,
                "content-type": "application/json",
            }
            if search.get("where"):
                params["where"] = search["where"]
            try:
                data = self._request("GET", f"{self.API_BASE}/{self.country}/search/1", params=params)
            except RequestBudgetExceeded:
                break
            if not isinstance(data, dict) or not isinstance(data.get("results", []), list):
                raise ProviderBadResponse("Adzuna: unexpected response shape")
            for item in data.get("results", []):
                if not isinstance(item, dict):
                    continue
                loc = item.get("location") or {}
                area = loc.get("area") or []
                jobs.append({
                    "source_provider": self.provider_key,
                    "source_name": self.source_name,
                    "source_job_id": item.get("id"),
                    "title": item.get("title"),
                    "company": (item.get("company") or {}).get("display_name"),
                    "description": item.get("description"),
                    "location": loc.get("display_name") or ", ".join(reversed(area[1:])) or None,
                    "country": country_name,
                    "url": item.get("redirect_url"),
                    "posted_at": item.get("created"),
                    "salary_min": item.get("salary_min"),
                    "salary_max": item.get("salary_max"),
                    "salary_currency": currency,
                    "salary_period": "year",
                    # Adzuna flags salaries it estimated itself - keep that distinction
                    "salary_is_estimated": str(item.get("salary_is_predicted", "0")) == "1",
                    "contract_type": " ".join(filter(None, [item.get("contract_time"), item.get("contract_type")])),
                    "search_query": search,
                })
        return jobs
