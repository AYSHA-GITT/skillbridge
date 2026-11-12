"""
Normalization and validation of raw provider jobs.

Principles (the previous implementation violated all of these):
* Never invent data. Missing posting date stays None (it used to become "now",
  which made old jobs look newly posted). Missing URL makes the job invalid
  (it used to become https://careers.google.com). Missing skills stay empty
  (they used to become ["python", "git"]).
* Skills are extracted with the same token-boundary taxonomy used for resumes,
  and split into required vs preferred using the wording of the description.
* Stable identifiers for deduplication: provider id, canonical URL, and a
  title|company|city fingerprint used only to FLAG likely cross-provider
  duplicates (never to merge distinct vacancies silently).
"""
import hashlib
import html
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from utils.skill_taxonomy import find_skill_mentions, normalize_skill_name, is_known_skill
from utils.job_discovery.location_prioritizer import INDIA_KEYWORDS

# Query parameters that never identify a vacancy (tracking / session noise)
_TRACKING_PARAMS = re.compile(
    r"^(utm_.*|ref|referrer|source|src|campaign|gclid|fbclid|mc_[a-z]+|trk|tracking.*|sessionid|sid|from)$",
    re.I)

PREFERRED_MARKERS = re.compile(
    r"nice[\s-]to[\s-]have|preferred|good[\s-]to[\s-]have|is a plus|are a plus|a plus|bonus|desirable|"
    r"advantageous|would be an advantage|optional|familiarity with",
    re.I)
REQUIRED_HEADER = re.compile(r"(requirements?|qualifications?|must[\s-]have|what you.ll need|"
                             r"you have|skills required|required skills|who you are)\s*:?", re.I)
PREFERRED_HEADER = re.compile(r"(nice[\s-]to[\s-]have|preferred (skills|qualifications)|bonus points|"
                              r"good[\s-]to[\s-]have)\s*:?", re.I)

CAREER_CATEGORY_RULES: List[Tuple[str, List[str]]] = [
    ("Machine Learning & AI", ["machine learning", "ml engineer", "ai engineer", "deep learning",
                               "artificial intelligence", "nlp", "computer vision", "llm", "genai"]),
    ("Data Science", ["data scientist", "data science"]),
    ("Data Engineering", ["data engineer", "etl", "big data"]),
    ("Data Analytics", ["data analyst", "business analyst", "analytics", "bi developer",
                        "power bi", "business intelligence", "mis analyst"]),
    ("Cybersecurity", ["security", "cyber", "soc analyst", "penetration", "infosec"]),
    ("Cloud & DevOps", ["devops", "cloud", "sre", "site reliability", "platform engineer",
                        "infrastructure", "kubernetes", "aws engineer"]),
    ("Frontend Engineering", ["frontend", "front-end", "front end", "ui developer", "react developer",
                              "angular developer", "web designer"]),
    ("Full Stack Development", ["full stack", "full-stack", "fullstack", "mern", "mean stack"]),
    ("Backend Engineering", ["backend", "back-end", "back end", "python developer", "java developer",
                             "node developer", "api developer", "golang developer"]),
    ("Mobile Development", ["android", "ios developer", "flutter", "mobile developer", "react native"]),
    ("QA & Testing", ["qa ", "quality assurance", "test engineer", "sdet", "automation tester", "tester"]),
    ("Software Development", ["software", "developer", "engineer", "programmer", "trainee", "graduate"]),
]

INTERNSHIP_RE = re.compile(r"\b(intern|internship|apprentice|apprenticeship|co-?op|working student)\b", re.I)
TRAINEE_RE = re.compile(r"\b(trainee|graduate engineer|fresher|freshers|entry[\s-]level|junior|jr\.?|"
                        r"campus|new grad|graduate program)\b", re.I)
SENIOR_RE = re.compile(r"\b(senior|sr\.?|lead|principal|staff|architect|head of|manager|director|vp)\b", re.I)
YEARS_RANGE_RE = re.compile(r"(\d{1,2})\s*(?:\+|plus)?\s*(?:-|–|to)\s*(\d{1,2})\s*\+?\s*(?:years?|yrs?)", re.I)
YEARS_MIN_RE = re.compile(r"(\d{1,2})\s*\+?\s*(?:years?|yrs?)(?:\s+of)?\s+(?:experience|exp\b|relevant|hands)", re.I)
MIN_YEARS_ALT_RE = re.compile(r"(?:minimum|min\.?|at least)\s+(?:of\s+)?(\d{1,2})\s*(?:years?|yrs?)", re.I)


def clean_html(raw: Optional[str], limit: int = 6000) -> str:
    if not raw:
        return ""
    text = html.unescape(raw)
    text = re.sub(r"<\s*(br|/p|/li|/div|/h\d)\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<\s*li[^>]*>", "\n• ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text).strip()
    return text[:limit]


def canonicalize_url(url: Optional[str]) -> Optional[str]:
    """Lower-case scheme/host, drop fragments and tracking params, sort the rest."""
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    if not re.match(r"^https?://", url, re.I):
        return None
    parts = urlsplit(url)
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=False)
             if not _TRACKING_PARAMS.match(k)]
    query.sort()
    path = re.sub(r"/+$", "", parts.path) or "/"
    return urlunsplit(("https", host, path, urlencode(query), ""))


def _norm_token(s: Optional[str]) -> str:
    s = (s or "").lower()
    s = re.sub(r"\b(pvt|private|ltd|limited|inc|llc|llp|gmbh|corp|corporation|co|company|technologies|"
               r"technology|solutions|services|india)\b\.?", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def make_fingerprint(title: str, company: str, city: Optional[str]) -> str:
    raw = f"{_norm_token(title)}|{_norm_token(company)}|{_norm_token(city)}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


# Bump when normalization rules change, so the next sync re-applies them to stored listings.
NORMALIZER_VERSION = 3


def content_hash(job: Dict[str, Any]) -> str:
    keys = ["title", "company", "location", "description", "job_type", "work_arrangement",
            "salary_min", "salary_max", "application_url", "deadline", "city", "required_skills",
            "preferred_skills", "experience_level"]
    payload = {k: (job.get(k).isoformat() if isinstance(job.get(k), datetime) else job.get(k)) for k in keys}
    payload["_normalizer_version"] = NORMALIZER_VERSION
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def parse_datetime(value: Any) -> Optional[datetime]:
    """Parse ISO strings / epoch seconds into aware UTC datetimes. Returns None if unknown."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        v = value.strip().replace("Z", "+00:00")
        # trim fractional seconds beyond microseconds (e.g. Jooble "2026-11-12T10:00:00.0000000")
        v = re.sub(r"(\.\d{6})\d+", r"\1", v)
        try:
            dt = datetime.fromisoformat(v)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


# Old and new official names of Indian cities refer to the same place.
CITY_ALIASES = {
    "bangalore": "Bengaluru", "bengaluru": "Bengaluru", "blr": "Bengaluru",
    "gurgaon": "Gurugram", "gurugram": "Gurugram",
    "bombay": "Mumbai", "mumbai": "Mumbai", "navi mumbai": "Navi Mumbai",
    "mangalore": "Mangaluru", "mangaluru": "Mangaluru",
    "mysore": "Mysuru", "mysuru": "Mysuru",
    "madras": "Chennai", "chennai": "Chennai",
    "calcutta": "Kolkata", "kolkata": "Kolkata",
    "trivandrum": "Thiruvananthapuram", "thiruvananthapuram": "Thiruvananthapuram",
    "cochin": "Kochi", "kochi": "Kochi",
    "poona": "Pune", "pune": "Pune", "hyderabad": "Hyderabad", "noida": "Noida",
    "new delhi": "New Delhi", "delhi": "Delhi", "udupi": "Udupi", "bhatkal": "Bhatkal",
}
_CITY_RE = re.compile(r"\b(" + "|".join(sorted((re.escape(k) for k in CITY_ALIASES), key=len, reverse=True)) + r")\b",
                      re.I)


def canonical_city(text: Optional[str]) -> Optional[str]:
    """First known Indian city mentioned in text, under its current official name."""
    m = _CITY_RE.search(text or "")
    return CITY_ALIASES[m.group(1).lower()] if m else None


def location_search_terms(query: str) -> List[str]:
    """All spellings that refer to the same city (search 'Bengaluru' also finds 'Bangalore')."""
    q = (query or "").strip().lower()
    canon = CITY_ALIASES.get(q)
    if not canon:
        return [query.strip()]
    return sorted({alias for alias, c in CITY_ALIASES.items() if c == canon} | {canon.lower()})


def split_location(location: str, country_hint: Optional[str] = None) -> Dict[str, Optional[str]]:
    parts = [p.strip() for p in re.split(r"[,/|]", location or "") if p.strip()]
    lower = (location or "").lower()
    country = country_hint
    if not country:
        if any(re.search(rf"\b{re.escape(k)}\b", lower) for k in INDIA_KEYWORDS):
            country = "India"
    if not country and re.search(r"\bIND\b", location or ""):
        country = "India"
    city = canonical_city(location)
    state = None
    if city is None and parts and not re.search(r"\b(india|remote|anywhere|hybrid)\b", parts[0], re.I):
        city = parts[0]
    if len(parts) >= 2 and parts[1].lower() != (country or "").lower() and not canonical_city(parts[1]) \
            and not re.search(r"\b(india|ind)\b", parts[1], re.I):
        state = parts[1]
    return {"city": city, "state": state, "country": country}


def infer_work_arrangement(title: str, location: str, description: str, remote_flag: Optional[bool]) -> str:
    text = f"{title} {location}".lower()
    if re.search(r"\bhybrid\b", text):
        return "Hybrid"
    if remote_flag is True or re.search(r"\b(remote|work from home|wfh)\b", text):
        return "Remote"
    d = (description or "").lower()[:1500]
    if re.search(r"\bhybrid\b", d):
        return "Hybrid"
    if re.search(r"\b(fully remote|100% remote|remote[- ]first|work from home)\b", d):
        return "Remote"
    if remote_flag is False:
        return "Onsite"
    return "Onsite" if location and "remote" not in location.lower() else "Unspecified"


def infer_job_type(title: str, provider_type: Optional[str], description: str) -> str:
    pt = (provider_type or "").lower()
    if INTERNSHIP_RE.search(title or "") or "intern" in pt:
        return "Internship"
    if "contract" in pt or re.search(r"\bcontract(ual)?\b", (title or "").lower()):
        return "Contract"
    if "part" in pt:
        return "Part-time"
    if "full" in pt or "permanent" in pt:
        return "Full-time"
    return "Full-time" if not INTERNSHIP_RE.search(description[:600] if description else "") else "Internship"


def infer_experience(title: str, description: str) -> Dict[str, Any]:
    text = f"{title}\n{description or ''}"
    min_y: Optional[float] = None
    max_y: Optional[float] = None
    m = YEARS_RANGE_RE.search(text)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        if a <= b <= 30:
            min_y, max_y = a, b
    if min_y is None:
        m = YEARS_MIN_RE.search(text) or MIN_YEARS_ALT_RE.search(text)
        if m and float(m.group(1)) <= 30:
            min_y = float(m.group(1))

    if INTERNSHIP_RE.search(title or ""):
        level, entry = "Internship", True
    elif SENIOR_RE.search(title or ""):
        level, entry = "Senior", False
    elif TRAINEE_RE.search(title or "") or (min_y is not None and min_y <= 1):
        level, entry = "Entry-Level", True
    elif min_y is not None and min_y >= 5:
        level, entry = "Senior", False
    elif min_y is not None and min_y >= 2:
        level, entry = "Mid-Level", False
    else:
        level, entry = "Not specified", None
    if level == "Entry-Level" and min_y is None:
        min_y, max_y = 0.0, max_y if max_y is not None else 2.0
    return {"experience_level": level, "is_entry_level": entry,
            "experience_min_years": min_y, "experience_max_years": max_y}


def infer_career_category(title: str, description: str) -> str:
    t = f" {(title or '').lower()} "
    for category, keywords in CAREER_CATEGORY_RULES:
        if any(k in t for k in keywords):
            return category
    d = (description or "").lower()[:800]
    for category, keywords in CAREER_CATEGORY_RULES[:-1]:
        if any(k in d for k in keywords):
            return category
    return "Other"


_ABOUT_COMPANY_RE = re.compile(r"^\W*(we|we're|we are|our|ours|at [A-Z][\w&.\- ]{1,40}?,|about (us|the company)|"
                               r"join (us|our)|who we are|[A-Z][\w&.\-]+ is (a|an|the)\b)", re.I)
_ABOUT_CANDIDATE_RE = re.compile(r"\b(you|your|candidate|experience (with|in)|proficien\w*|knowledge of|"
                                 r"familiar\w*|hands-on|required|must|should|ability to|skills? in|"
                                 r"expertise|strong understanding|working knowledge)\b", re.I)


def is_company_boilerplate(sentence: str) -> bool:
    """Sentences describing the COMPANY ("We are a leader in AI/ML...") are not
    requirements; sentences describing the candidate or the role are."""
    s = sentence.strip()
    return bool(_ABOUT_COMPANY_RE.search(s)) and not _ABOUT_CANDIDATE_RE.search(s)


def split_required_preferred(description: str, tags: Optional[List[str]] = None) -> Tuple[List[str], List[str], str]:
    """Return (required, preferred, skills_source).

    A skill is 'preferred' when every sentence/bullet mentioning it carries a
    preference marker ("nice to have", "a plus", ...) or sits under a
    preferred-skills header; otherwise it is 'required'."""
    required: Dict[str, None] = {}
    preferred: Dict[str, None] = {}
    if description:
        # A header on its own line ("Nice to have:") sets the mode for the
        # following lines (bulleted sections). Inside prose, a marker only
        # applies to its own sentence.
        mode = None  # None | 'required' | 'preferred'
        for raw_line in description.split("\n"):
            line = raw_line.strip()
            if not line:
                continue
            header_only = len(line) <= 45 and line.rstrip().endswith(":") and not find_skill_mentions(line)
            if header_only and PREFERRED_HEADER.match(line):
                mode = "preferred"
                continue
            if header_only and REQUIRED_HEADER.match(line):
                mode = "required"
                continue
            for sentence in re.split(r"(?<=[.;!?])\s+", line):
                if is_company_boilerplate(sentence):
                    continue
                mentions = find_skill_mentions(sentence)
                if not mentions:
                    continue
                if PREFERRED_MARKERS.search(sentence) or PREFERRED_HEADER.match(sentence):
                    is_pref = True
                elif re.search(r"\b(required|must|mandatory|essential)\b", sentence, re.I):
                    is_pref = False
                else:
                    is_pref = mode == "preferred"
                for skill in mentions:
                    (preferred if is_pref else required)[skill] = None
    source = "description_text" if (required or preferred) else "none"
    for t in tags or []:
        name = normalize_skill_name(t)
        if is_known_skill(name) and name not in required and name not in preferred:
            required[name] = None
            source = "provider_tags" if source == "none" else source
    req = [s for s in required]
    pref = [s for s in preferred if s not in required]
    return req, pref, source


def normalize_job(raw: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Validate and normalize one raw provider job.
    Returns (normalized, None) or (None, rejection_reason)."""
    title = re.sub(r"\s+", " ", clean_html(raw.get("title"), 200)).strip()
    company = re.sub(r"\s+", " ", clean_html(raw.get("company"), 200)).strip()
    description = clean_html(raw.get("description"))
    url = (raw.get("url") or raw.get("application_url") or "").strip()
    provider = raw.get("source_provider")
    source_job_id = str(raw.get("source_job_id") or "").strip()

    if not provider:
        return None, "missing provider"
    if not title:
        return None, "missing title"
    if not company:
        return None, "missing company"
    canonical = canonicalize_url(url)
    if not canonical:
        return None, "missing or invalid job URL"
    if len(description) < 40:
        return None, "description too short to evaluate"
    if not source_job_id:
        source_job_id = hashlib.sha1(canonical.encode()).hexdigest()[:24]

    location = re.sub(r"\s+", " ", clean_html(raw.get("location"), 200)).strip() or "Not specified"
    loc = split_location(location, raw.get("country"))

    required, preferred, skills_source = split_required_preferred(description, raw.get("tags"))
    if raw.get("is_sample") and raw.get("required_skills"):
        required = [normalize_skill_name(s) for s in raw.get("required_skills") or []]
        preferred = [normalize_skill_name(s) for s in raw.get("preferred_skills") or []]
        skills_source = "curated"
    exp = infer_experience(title, description)

    salary_min = raw.get("salary_min")
    salary_max = raw.get("salary_max")
    try:
        salary_min = float(salary_min) if salary_min not in (None, "") else None
        salary_max = float(salary_max) if salary_max not in (None, "") else None
    except (TypeError, ValueError):
        salary_min = salary_max = None
    if salary_min is not None and salary_max is not None and salary_min > salary_max:
        salary_min, salary_max = salary_max, salary_min
    if (salary_min is not None and salary_min <= 0) or (salary_max is not None and salary_max <= 0):
        salary_min = salary_max = None

    normalized = {
        "source_provider": provider,
        "source_job_id": source_job_id[:200],
        "external_id": f"{provider}:{source_job_id}"[:150],
        "title": title[:200],
        "company": company[:200],
        "location": location[:200],
        "city": loc["city"][:120] if loc["city"] else None,
        "state": loc["state"][:120] if loc["state"] else None,
        "country": (loc["country"] or "")[:60] or None,
        "job_type": infer_job_type(title, raw.get("contract_type"), description),
        # a work mode stated explicitly by the source wins over inference
        "work_arrangement": raw.get("work_arrangement") or infer_work_arrangement(title, location, description,
                                                                                 raw.get("remote")),
        "domain": infer_career_category(title, description),
        "career_category": infer_career_category(title, description),
        "experience_level": exp["experience_level"],
        "is_entry_level": exp["is_entry_level"],
        "experience_min_years": exp["experience_min_years"],
        "experience_max_years": exp["experience_max_years"],
        "description": description,
        "required_skills": required,
        "preferred_skills": preferred,
        "skills_source": skills_source,
        "eligibility": (raw.get("eligibility") or None),
        "application_url": url[:500],
        "original_url": url[:1000],
        "canonical_url": canonical[:1000],
        "source": (raw.get("source_name") or provider)[:100],
        "is_sample": bool(raw.get("is_sample", False)),
        "posting_date": parse_datetime(raw.get("posted_at")),
        "deadline": parse_datetime(raw.get("deadline")),
        "salary_min": salary_min,
        "salary_max": salary_max,
        "salary_currency": (raw.get("salary_currency") or None) if (salary_min or salary_max) else None,
        "salary_period": (raw.get("salary_period") or None) if (salary_min or salary_max) else None,
        "salary_is_estimated": (bool(raw.get("salary_is_estimated"))
                                if (salary_min or salary_max) and raw.get("salary_is_estimated") is not None
                                else None),
    }
    # Posting dates in the future are provider errors - drop them rather than trust them
    now = datetime.now(timezone.utc)
    if normalized["posting_date"] and normalized["posting_date"] > now:
        normalized["posting_date"] = None
    normalized["fingerprint"] = make_fingerprint(title, company, normalized["city"])
    normalized["content_hash"] = content_hash(normalized)
    return normalized, None
