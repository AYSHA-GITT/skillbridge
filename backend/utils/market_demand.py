"""
Measured market demand for career skills, computed from the job postings
SkillBridge has collected (active, non-sample listings).

For each career, postings are selected by job title and we count the share of
postings whose extracted required/preferred skills include each skill. The
result is stored in data/market_demand.json with the sample size and date, and
recomputed after every successful job sync.

Caveats (reported alongside the numbers):
* postings are dominated by the employers the system can read (large tech
  companies, mostly mid/senior roles), so basics that employers assume
  (Git, data structures, HTML/CSS) are under-reported;
* careers with fewer than MIN_POSTINGS postings are reported but not used for
  weighting (equal weights are used instead).
"""
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, Optional

MIN_POSTINGS = 20
DEMAND_PATH = os.getenv("MARKET_DEMAND_PATH") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "market_demand.json")

CAREER_TITLE_PATTERNS = {
    "data analyst": r"\b(data|business|product|bi|reporting|mis)\s+analyst\b|\banalytics\b",
    "data scientist": r"data scien|applied scientist",
    "software engineer": r"software (engineer|developer)|\bsde\b|backend|member of technical staff|\bmts\b",
    "web developer": r"front[\s-]?end|web developer|ui engineer|ui developer",
    "full stack developer": r"full[\s-]?stack",
    "devops engineer": r"devops|site reliability|\bsre\b|platform engineer|infrastructure engineer",
    "cloud engineer": r"\bcloud\b",
    "ai engineer": r"machine learning|\bml\b|\bai\b|artificial intelligence|deep learning|\bllm\b|genai",
}

_cache: Dict[str, Any] = {"mtime": None, "data": None}


def compute_market_demand(save: bool = True) -> Dict[str, Any]:
    from models import JobListing
    from utils.skill_taxonomy import normalize_skill_name

    jobs = (JobListing.query
            .filter(JobListing.status == "active", JobListing.is_sample.is_(False),
                    JobListing.duplicate_of_id.is_(None))
            .all())
    careers: Dict[str, Any] = {}
    for career, pattern in CAREER_TITLE_PATTERNS.items():
        rx = re.compile(pattern, re.I)
        matched = [j for j in jobs if rx.search(j.title or "")]
        counts: Counter = Counter()
        for j in matched:
            counts.update({normalize_skill_name(s) for s in j.get_required_skills() + j.get_preferred_skills()})
        n = len(matched)
        careers[career] = {
            "postings": n,
            "entry_level_postings": sum(1 for j in matched if j.is_entry_level or j.job_type == "Internship"),
            "usable_for_weighting": n >= MIN_POSTINGS,
            "skill_share": {s: round(c / n, 3) for s, c in counts.most_common()} if n else {},
        }
    result = {
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "total_active_postings": len(jobs),
        "min_postings_for_weighting": MIN_POSTINGS,
        "caveat": ("Shares come from the postings SkillBridge currently collects (mostly large employers and "
                   "mid/senior roles). Skills employers assume, such as Git or data structures, are under-reported."),
        "careers": careers,
    }
    if save:
        os.makedirs(os.path.dirname(DEMAND_PATH), exist_ok=True)
        with open(DEMAND_PATH, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=1)
        _cache["mtime"] = None
    return result


def load_market_demand() -> Optional[Dict[str, Any]]:
    try:
        mtime = os.path.getmtime(DEMAND_PATH)
    except OSError:
        return None
    if _cache["mtime"] != mtime:
        with open(DEMAND_PATH, encoding="utf-8") as f:
            _cache["data"] = json.load(f)
        _cache["mtime"] = mtime
    return _cache["data"]


def career_demand(career: str) -> Optional[Dict[str, Any]]:
    data = load_market_demand()
    if not data:
        return None
    entry = data["careers"].get((career or "").strip().lower())
    if not entry:
        return None
    return {**entry, "computed_at": data["computed_at"], "caveat": data["caveat"]}


def skill_demand_notes(career: str, skills) -> Dict[str, str]:
    """Plain-language evidence for each skill, e.g. 'In 61% of 36 current data analyst postings'."""
    d = career_demand(career)
    if not d or not d["postings"]:
        return {}
    notes = {}
    for s in skills:
        share = d["skill_share"].get(s.lower(), 0.0)
        notes[s] = (f"Mentioned in {round(share * 100)}% of {d['postings']} current {career} postings"
                    + ("" if d["usable_for_weighting"] else " (small sample)"))
    return notes
