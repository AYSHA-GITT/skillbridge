"""
Company job boards via the official, public, key-less ATS APIs.

Greenhouse:  GET https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true
             ("Job Board data is publicly available, so authentication is not
             required for any GET endpoints" - Greenhouse Job Board API docs)
Lever:       GET https://api.lever.co/v0/postings/{site}?mode=json
             (public postings API; a key is only needed to submit applications)

These are AUTHORIZED feeds: each company publishes these postings itself.
Every request returns the company's COMPLETE list of open postings, so when a
previously seen posting disappears from a board that was fetched successfully,
that is direct evidence from the source that it is no longer open
(see `completed_scopes`, used by the sync service to expire such listings).

Filtering (keeps the catalogue relevant to SkillBridge users):
* location in India, or remote explicitly open to India / APAC / anywhere;
* job title in a technology / data / analytics career category (finance,
  sales, legal, HR roles are skipped).

Default boards were verified on 2026-11-13 to respond and list India-based
openings. Override with JOB_GREENHOUSE_BOARDS / JOB_LEVER_SITES.
"""
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Set

from utils.job_discovery.base_adapter import JobSourceAdapter, ProviderError, RequestBudgetExceeded

INDIA_RE = re.compile(
    r"\b(india|bengaluru|bangalore|mumbai|pune|hyderabad|chennai|gurgaon|gurugram|noida|new delhi|delhi|"
    r"kolkata|ahmedabad|kochi|mangalore|mangaluru|mysore|mysuru|udupi|jaipur|coimbatore|karnataka|"
    r"maharashtra|telangana|tamil nadu|kerala)\b", re.I)
OPEN_REMOTE_RE = re.compile(r"(remote|anywhere).*\b(apac|asia|anywhere|worldwide|global)\b|"
                            r"\b(apac|asia|worldwide|global)\b.*(remote)", re.I)
RELEVANT_TITLE_RE = re.compile(
    r"\b(engineer|engineering|developer|programmer|software|sde|sdet|devops|sre|site reliability|cloud|"
    r"platform|infrastructure|backend|back-end|frontend|front-end|full[\s-]?stack|mobile|android|ios|"
    r"data|analyst|analytics|scientist|machine learning|ml|ai|artificial intelligence|deep learning|nlp|"
    r"security|cyber|qa|quality assurance|test|automation|architect|database|dba|bi\b|business intelligence|"
    r"intern|internship|trainee|graduate|fresher|technical|tech)\b", re.I)
EXCLUDED_TITLE_RE = re.compile(r"\b(sales|account executive|recruit\w*|talent acquisition|legal|counsel|payable|"
                               r"receivable|accountant|audit|payroll|finance|financial|tax|treasury|"
                               r"expenses?|procurement|benefits|accounting|credit|risk|fraud|deal desk|"
                               r"real estate|talent|sourc(er|ing)|collections?|fp&a|renewals|processing cost|"
                               r"monetization|alliances|rmg|people|provisioning|"
                               r"(ar|ap)\s+analyst|account manager|success manager|"
                               r"marketing manager|customer success manager)\b", re.I)

DEFAULT_GREENHOUSE = ["databricks", "okta", "zscaler", "mongodb", "highradius", "stripe", "gitlab", "rubrik",
                      "toast", "elastic", "netskope", "hackerrank", "twilio", "airbnb", "agoda", "druva",
                      "coinbase", "groww"]
DEFAULT_LEVER = ["paytm", "meesho", "zeta", "fampay", "mindtickle", "cred", "nium"]
LEVER_DISPLAY_NAMES = {"paytm": "Paytm", "meesho": "Meesho", "zeta": "Zeta", "fampay": "FamPay",
                       "mindtickle": "Mindtickle", "cred": "CRED", "nium": "Nium"}


def _env_boards(name: str, default: List[str]) -> List[str]:
    raw = os.getenv(name)
    if raw is None:
        return list(default)
    return [b.strip().lower() for b in raw.split(",") if b.strip()]


STRONG_TECH_TITLE_RE = re.compile(r"\b(engineer|engineering|developer|programmer|scientist|sde|sdet|devops|sre|"
                                  r"site reliability|architect|data analyst|machine learning|ml engineer)\b", re.I)
NON_TECH_ENGINEER_RE = re.compile(r"\b(sales engineer|account engineer)\b", re.I)


def is_relevant_title(title: str) -> bool:
    """Clearly technical titles always qualify ("Software Engineer - Credit Platform");
    ambiguous ones ("Analyst", "Technical ...") must not hit the non-tech exclusions."""
    if not title:
        return False
    if STRONG_TECH_TITLE_RE.search(title) and not NON_TECH_ENGINEER_RE.search(title):
        return True
    return bool(RELEVANT_TITLE_RE.search(title)) and not EXCLUDED_TITLE_RE.search(title)


def is_india_or_open_remote(location_text: str, country: Optional[str] = None) -> bool:
    if (country or "").upper() == "IN":
        return True
    return bool(INDIA_RE.search(location_text or "")) or bool(OPEN_REMOTE_RE.search(location_text or ""))


class _CompanyBoardsBase(JobSourceAdapter):
    default_request_budget = 40
    uses_search_plan = False

    def __init__(self, boards: Optional[List[str]] = None, **kwargs):
        kwargs.setdefault("max_retries", 2)
        super().__init__(**kwargs)
        self.boards = boards if boards is not None else self._default_boards()
        self.completed_scopes: Dict[str, Set[str]] = {}
        self.kept_ids: Set[str] = set()
        self.run_errors: List[str] = []
        self.filtered_out = 0

    def _default_boards(self) -> List[str]:
        return []

    def is_configured(self) -> bool:
        return bool(self.boards)

    def reset_run_state(self) -> None:
        super().reset_run_state()
        self.completed_scopes = {}
        self.kept_ids = set()
        self.run_errors = []
        self.filtered_out = 0

    def fetch_jobs(self, searches: Iterable[Dict[str, str]] = ()) -> List[Dict[str, Any]]:
        jobs: List[Dict[str, Any]] = []
        for board in self.boards:
            try:
                board_jobs, all_ids = self._fetch_board(board)
            except RequestBudgetExceeded:
                break
            except ProviderError as e:
                # one company's board failing must not stop the others
                self.run_errors.append(f"{board}: {e}")
                continue
            self.completed_scopes[f"{self.provider_key}:{board}:"] = all_ids
            self.kept_ids.update(f"{self.provider_key}:{j['source_job_id']}" for j in board_jobs)
            jobs.extend(board_jobs)
        return jobs

    def _fetch_board(self, board: str):
        raise NotImplementedError


class GreenhouseBoardsAdapter(_CompanyBoardsBase):
    provider_key = "greenhouse"
    API = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs"

    @property
    def source_name(self) -> str:
        return "Company careers (Greenhouse)"

    def _default_boards(self):
        return _env_boards("JOB_GREENHOUSE_BOARDS", DEFAULT_GREENHOUSE)

    def _fetch_board(self, board):
        data = self._request("GET", self.API.format(board=board), params={"content": "true"})
        items = data.get("jobs") if isinstance(data, dict) else None
        if not isinstance(items, list):
            raise ProviderError(f"Greenhouse {board}: unexpected response shape")
        out, ids = [], set()
        for j in items:
            if not isinstance(j, dict) or j.get("id") is None:
                continue
            sid = f"{board}:{j['id']}"
            ids.add(f"{self.provider_key}:{sid}")
            title = j.get("title") or ""
            location = (j.get("location") or {}).get("name") or ""
            if not is_relevant_title(title) or not is_india_or_open_remote(location):
                self.filtered_out += 1
                continue
            emp_type = next((str(m.get("value")) for m in (j.get("metadata") or [])
                             if isinstance(m, dict) and re.search(r"employment|job type|worker type",
                                                                  str(m.get("name")), re.I) and m.get("value")), None)
            lower_loc = location.lower()
            out.append({
                "source_provider": self.provider_key,
                "source_name": f"{j.get('company_name') or board.title()} careers (via Greenhouse)",
                "source_job_id": sid,
                "title": title,
                "company": j.get("company_name") or board.title(),
                "description": j.get("content") or "",
                "location": location,
                "country": "India" if INDIA_RE.search(location) else None,
                "url": j.get("absolute_url"),
                "posted_at": j.get("first_published"),          # not updated_at: that is an edit time
                "deadline": j.get("application_deadline"),
                "remote": True if "remote" in lower_loc else None,
                "work_arrangement": "Hybrid" if "hybrid" in lower_loc else None,
                "contract_type": emp_type,
            })
        return out, ids


class LeverBoardsAdapter(_CompanyBoardsBase):
    provider_key = "lever"
    API = "https://api.lever.co/v0/postings/{site}"
    WORKPLACE = {"remote": "Remote", "hybrid": "Hybrid", "on-site": "Onsite", "onsite": "Onsite"}

    @property
    def source_name(self) -> str:
        return "Company careers (Lever)"

    def _default_boards(self):
        return _env_boards("JOB_LEVER_SITES", DEFAULT_LEVER)

    def _fetch_board(self, site):
        data = self._request("GET", self.API.format(site=site), params={"mode": "json"})
        if not isinstance(data, list):
            raise ProviderError(f"Lever {site}: unexpected response shape")
        company = LEVER_DISPLAY_NAMES.get(site, site.title())
        out, ids = [], set()
        for j in data:
            if not isinstance(j, dict) or not j.get("id"):
                continue
            sid = f"{site}:{j['id']}"
            ids.add(f"{self.provider_key}:{sid}")
            cat = j.get("categories") or {}
            locations = [cat.get("location") or ""] + list(cat.get("allLocations") or [])
            location = ", ".join(dict.fromkeys(l for l in locations if l)) or ""
            title = j.get("text") or ""
            if not is_relevant_title(title) or not is_india_or_open_remote(location, j.get("country")):
                self.filtered_out += 1
                continue
            parts = [j.get("descriptionPlain") or j.get("openingPlain") or ""]
            for lst in j.get("lists") or []:
                if isinstance(lst, dict):
                    parts.append(f"{lst.get('text') or ''}:\n{lst.get('content') or ''}")
            parts.append(j.get("additionalPlain") or "")
            created = j.get("createdAt")
            posted = None
            if isinstance(created, (int, float)) or (isinstance(created, str) and created.isdigit()):
                posted = datetime.fromtimestamp(int(created) / 1000, tz=timezone.utc)
            loc_display = location.title() if location.islower() else location
            if (j.get("country") or "").upper() == "IN" and not INDIA_RE.search(location):
                loc_display = f"{loc_display}, India" if loc_display else "India"
            out.append({
                "source_provider": self.provider_key,
                "source_name": f"{company} careers (via Lever)",
                "source_job_id": sid,
                "title": title,
                "company": company,
                "description": "\n".join(p for p in parts if p),
                "location": loc_display,
                "country": "India" if (j.get("country") or "").upper() == "IN" or INDIA_RE.search(location) else None,
                "url": j.get("hostedUrl"),
                "posted_at": posted,
                "remote": True if (j.get("workplaceType") or "").lower() == "remote" else None,
                "work_arrangement": self.WORKPLACE.get((j.get("workplaceType") or "").lower()),
                "contract_type": cat.get("commitment"),
            })
        return out, ids
