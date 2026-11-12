"""
Arbeitnow public job board API adapter (https://www.arbeitnow.com/api/job-board-api).

No credentials required. Note: Arbeitnow lists mostly Europe-based roles
(many in Germany) plus remote roles; it is NOT a source of Indian listings.
It is kept as an optional source of remote opportunities and can be disabled
with JOB_PROVIDERS. Results are not keyword-searchable server-side, so
filtering by the search plan happens locally.
"""
import re
from typing import Any, Dict, Iterable, List

from utils.job_discovery.base_adapter import JobSourceAdapter, ProviderBadResponse, RequestBudgetExceeded


class RemoteJobApiAdapter(JobSourceAdapter):
    provider_key = "arbeitnow"
    default_request_budget = 3
    API_URL = "https://www.arbeitnow.com/api/job-board-api"

    def __init__(self, remote_only=None, **kwargs):
        super().__init__(**kwargs)
        import os
        self.remote_only = (remote_only if remote_only is not None
                            else os.getenv("ARBEITNOW_REMOTE_ONLY", "1").lower() in ("1", "true", "yes"))

    @property
    def source_name(self) -> str:
        return "Arbeitnow"

    def is_configured(self) -> bool:
        return True

    def fetch_jobs(self, searches: Iterable[Dict[str, str]]) -> List[Dict[str, Any]]:
        terms = [s.get("what", "").lower() for s in searches if s.get("what")]
        jobs: List[Dict[str, Any]] = []
        for page in range(1, self.max_requests_per_run + 1):
            try:
                data = self._request("GET", self.API_URL, params={"page": page})
            except RequestBudgetExceeded:
                break
            if not isinstance(data, dict) or not isinstance(data.get("data"), list):
                raise ProviderBadResponse("Arbeitnow: unexpected response shape")
            items = data["data"]
            for item in items:
                if not isinstance(item, dict):
                    continue
                title = item.get("title") or ""
                if self.remote_only and not item.get("remote"):
                    continue  # onsite roles in Europe are not reachable for most SkillBridge users
                if terms and not any(_term_matches(t, title) for t in terms):
                    continue
                jobs.append({
                    "source_provider": self.provider_key,
                    "source_name": self.source_name,
                    "source_job_id": item.get("slug"),
                    "title": title,
                    "company": item.get("company_name"),
                    "description": item.get("description"),
                    "location": item.get("location"),
                    "remote": item.get("remote"),
                    "url": item.get("url"),
                    "posted_at": item.get("created_at"),
                    "tags": item.get("tags") or [],
                    "contract_type": " ".join(item.get("job_types") or []),
                })
            if not items or not (data.get("links") or {}).get("next"):
                break
        return jobs


_GENERIC_WORDS = {"remote", "developer", "engineer", "software", "intern", "trainee", "fresher", "junior", ""}


def _term_matches(term: str, title: str) -> bool:
    """True when every role-specific word of the search term appears as a whole
    word in the title. Generic words (remote, developer, ...) are ignored, and a
    term made only of generic words matches titles containing 'software'/'developer'."""
    words = [w for w in re.split(r"[^a-z0-9+#]+", term.lower()) if w not in _GENERIC_WORDS]
    t = title.lower()
    if not words:
        return bool(re.search(r"\b(software|developer|programmer)\b", t))
    return all(re.search(rf"(?<![a-z0-9]){re.escape(w)}(?![a-z0-9])", t) for w in words)
