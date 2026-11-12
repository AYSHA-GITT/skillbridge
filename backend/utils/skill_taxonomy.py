"""
Shared skill taxonomy for SkillBridge.

One vocabulary is used for BOTH resume skill extraction and job-description
skill extraction, so a skill found on a resume and a skill required by a job
are compared under the same canonical name.

Matching rules
--------------
* Aliases are matched on token boundaries, never as raw substrings
  ("java" does not match inside "javascript", "c" does not match every word
  containing the letter c).
* Ambiguous names (C, R, Go) are only accepted in explicit forms such as
  "C programming", "Golang", "R language", or as a standalone item inside a
  comma / pipe / bullet separated list, matched case-sensitively.
"""
import re
from typing import Dict, List, Optional, Tuple

# canonical name -> (category, [aliases])  (aliases are lowercase; the canonical
# name itself is always included automatically)
SKILL_TAXONOMY: Dict[str, Tuple[str, List[str]]] = {
    # ── Programming languages ─────────────────────────────────────────────
    "python": ("Programming", ["python3", "python 3"]),
    "java": ("Programming", ["core java", "java se", "java ee", "j2ee"]),
    "javascript": ("Programming", ["js", "ecmascript", "es6"]),
    "typescript": ("Programming", ["ts"]),
    "c++": ("Programming", ["cpp", "c plus plus"]),
    "c#": ("Programming", ["c sharp", "csharp"]),
    "c": ("Programming", []),            # ambiguous: see AMBIGUOUS_PATTERNS
    "r": ("Programming", []),            # ambiguous
    "go": ("Programming", ["golang"]),   # ambiguous bare form
    "kotlin": ("Programming", []),
    "swift": ("Programming", []),
    "php": ("Programming", []),
    "ruby": ("Programming", []),
    "rust": ("Programming", []),
    "scala": ("Programming", []),
    "matlab": ("Programming", []),
    "bash": ("Programming", ["shell scripting", "bash scripting", "shell script"]),
    "sql": ("Database", ["structured query language", "t-sql", "pl/sql"]),

    # ── Web / frontend ────────────────────────────────────────────────────
    "html": ("Web", ["html5"]),
    "css": ("Web", ["css3"]),
    "react": ("Web", ["react.js", "reactjs", "react js"]),
    "angular": ("Web", ["angularjs", "angular.js"]),
    "vue": ("Web", ["vue.js", "vuejs"]),
    "next.js": ("Web", ["nextjs", "next js"]),
    "redux": ("Web", []),
    "tailwind css": ("Web", ["tailwind", "tailwindcss"]),
    "bootstrap": ("Web", []),

    # ── Backend / frameworks ──────────────────────────────────────────────
    "node.js": ("Backend", ["nodejs", "node js", "node"]),
    "express": ("Backend", ["express.js", "expressjs"]),
    "flask": ("Backend", []),
    "django": ("Backend", []),
    "fastapi": ("Backend", ["fast api"]),
    "spring boot": ("Backend", ["springboot", "spring framework", "spring mvc"]),
    ".net": ("Backend", ["dotnet", "asp.net", ".net core"]),
    "rest api": ("Backend", ["rest apis", "restful", "restful api", "restful apis", "rest"]),
    "graphql": ("Backend", []),
    "microservices": ("Backend", ["microservice"]),

    # ── Databases ─────────────────────────────────────────────────────────
    "mysql": ("Database", []),
    "postgresql": ("Database", ["postgres"]),
    "mongodb": ("Database", ["mongo"]),
    "sqlite": ("Database", []),
    "redis": ("Database", []),
    "oracle": ("Database", ["oracle db", "oracle database"]),
    "nosql": ("Database", []),

    # ── Data / analytics ──────────────────────────────────────────────────
    "excel": ("Data", ["ms excel", "microsoft excel", "advanced excel"]),
    "power bi": ("Data", ["powerbi", "power-bi"]),
    "tableau": ("Data", []),
    "statistics": ("Data", ["statistical analysis", "statistical modeling", "statistical modelling"]),
    "data analysis": ("Data", ["data analytics"]),
    "data visualization": ("Data", ["data visualisation"]),
    "pandas": ("Data", []),
    "numpy": ("Data", []),
    "matplotlib": ("Data", []),
    "seaborn": ("Data", []),
    "spark": ("Data", ["apache spark", "pyspark"]),
    "hadoop": ("Data", []),
    "etl": ("Data", ["data pipelines", "data pipeline"]),
    "airflow": ("Data", ["apache airflow"]),
    "kafka": ("Data", ["apache kafka"]),

    # ── ML / AI ───────────────────────────────────────────────────────────
    "machine learning": ("ML/AI", ["ml"]),
    "deep learning": ("ML/AI", []),
    "scikit-learn": ("ML/AI", ["sklearn", "scikit learn"]),
    "tensorflow": ("ML/AI", []),
    "keras": ("ML/AI", []),
    "pytorch": ("ML/AI", ["torch"]),
    "nlp": ("ML/AI", ["natural language processing"]),
    "computer vision": ("ML/AI", ["opencv"]),
    "generative ai": ("ML/AI", ["genai", "gen ai", "llm", "llms", "large language models"]),

    # ── Cloud / DevOps ────────────────────────────────────────────────────
    "aws": ("Cloud", ["amazon web services"]),
    "azure": ("Cloud", ["microsoft azure"]),
    "gcp": ("Cloud", ["google cloud", "google cloud platform"]),
    "docker": ("DevOps", []),
    "kubernetes": ("DevOps", ["k8s"]),
    "terraform": ("DevOps", []),
    "ansible": ("DevOps", []),
    "jenkins": ("DevOps", []),
    "ci/cd": ("DevOps", ["cicd", "ci cd", "continuous integration", "continuous deployment",
                          "continuous delivery", "github actions", "gitlab ci"]),
    "linux": ("DevOps", ["unix", "ubuntu"]),
    "monitoring": ("DevOps", ["prometheus", "grafana", "observability"]),
    "git": ("Tools", []),
    "github": ("Tools", []),
    "jira": ("Tools", []),

    # ── CS fundamentals ───────────────────────────────────────────────────
    "data structures": ("Fundamentals", ["dsa", "data structure"]),
    "algorithms": ("Fundamentals", ["algorithm"]),
    "oop": ("Fundamentals", ["object oriented programming", "object-oriented programming", "oops"]),
    "dbms": ("Fundamentals", ["database management systems"]),
    "operating systems": ("Fundamentals", []),
    "computer networks": ("Fundamentals", ["networking"]),
    "system design": ("Fundamentals", []),

    # ── Security ──────────────────────────────────────────────────────────
    "cybersecurity": ("Security", ["cyber security", "information security", "infosec"]),
    "network security": ("Security", []),
    "penetration testing": ("Security", ["pentesting", "pen testing", "ethical hacking"]),
    "siem": ("Security", ["splunk"]),

    # ── Testing / mobile ──────────────────────────────────────────────────
    "unit testing": ("Testing", ["pytest", "junit", "jest"]),
    "selenium": ("Testing", []),
    "android": ("Mobile", []),
    "flutter": ("Mobile", []),
    "react native": ("Mobile", []),

    # ── Professional ──────────────────────────────────────────────────────
    "communication": ("Professional", ["communication skills"]),
    "teamwork": ("Professional", ["team work", "team player"]),
    "leadership": ("Professional", []),
    "problem solving": ("Professional", ["problem-solving"]),
    "agile": ("Professional", ["scrum"]),
}

# Bare tokens that are too ambiguous to accept anywhere in free text.
# They are only matched through the explicit patterns below.
AMBIGUOUS_SKILLS = {"c", "r", "go"}

# Aliases that are ordinary English words / too generic when lowercase.
# They are only accepted case-sensitively in their technical spelling.
CASE_SENSITIVE_ALIASES = {
    "node": "Node",
    "rest": "REST",
    "ml": "ML",
    "ts": "TS",
    "js": "JS",
    "torch": "Torch",
    "mongo": "Mongo",
    # "you excel at..." is a verb; only the capitalised product name counts
    "excel": "Excel",
}

# characters that may PRECEDE a list item ("Languages: C, ..." / "• C")
_LIST_SEP = r"[,|/•·;:●▪\-\(\[\t]"
# characters that may FOLLOW a list item; no hyphen, so "C-DAC" is not read as C
_LIST_END = r"[,|/•·;●▪\)\]\t]"

AMBIGUOUS_PATTERNS: Dict[str, List[re.Pattern]] = {
    "c": [
        re.compile(r"\bC\s+(?:programming|language|lang)\b", re.I),
        re.compile(r"\bANSI\s+C\b"),
        re.compile(r"\bC/C\+\+"),
        re.compile(rf"(?:^|{_LIST_SEP})\s*C\s*(?={_LIST_END}|$)", re.M),
    ],
    "r": [
        re.compile(r"\bR\s+(?:programming|language|lang)\b", re.I),
        re.compile(r"\bRStudio\b|\bR Studio\b|\bShiny\b|\btidyverse\b|\bggplot2\b"),
        re.compile(rf"(?:^|{_LIST_SEP})\s*R\s*(?={_LIST_END}|$)", re.M),
    ],
    "go": [
        re.compile(r"\bgolang\b", re.I),
        re.compile(r"\bGo\s+(?:programming|language|lang)\b"),
        re.compile(rf"(?:^|{_LIST_SEP})\s*Go\s*(?={_LIST_END}|$)", re.M),
    ],
}


def _boundary_pattern(alias: str, case_sensitive: bool = False) -> re.Pattern:
    # Token boundaries that also respect symbols used in skill names (c++, c#, .net, node.js)
    escaped = re.escape(alias)
    flags = 0 if case_sensitive else re.I
    return re.compile(rf"(?<![A-Za-z0-9+#.]){escaped}(?![A-Za-z0-9+#]|\.[A-Za-z0-9])", flags)


def _build_patterns() -> Dict[str, List[re.Pattern]]:
    patterns: Dict[str, List[re.Pattern]] = {}
    for canonical, (_cat, aliases) in SKILL_TAXONOMY.items():
        if canonical in AMBIGUOUS_SKILLS:
            plist = list(AMBIGUOUS_PATTERNS.get(canonical, []))
            # unambiguous aliases (e.g. golang) still matched normally
            for a in aliases:
                plist.append(_boundary_pattern(a))
            patterns[canonical] = plist
            continue
        plist = []
        for form in [canonical] + aliases:
            if form in CASE_SENSITIVE_ALIASES:
                plist.append(_boundary_pattern(CASE_SENSITIVE_ALIASES[form], case_sensitive=True))
            else:
                plist.append(_boundary_pattern(form))
        patterns[canonical] = plist
    return patterns


_PATTERNS = _build_patterns()

# alias -> canonical lookup (for normalizing free-form skill strings)
_ALIAS_INDEX: Dict[str, str] = {}
for _canon, (_c, _aliases) in SKILL_TAXONOMY.items():
    _ALIAS_INDEX[_canon] = _canon
    for _a in _aliases:
        _ALIAS_INDEX.setdefault(_a, _canon)


def normalize_skill_name(name: Optional[str]) -> str:
    """Map any alias / casing variant to the canonical skill name.
    Unknown skills are returned lower-cased and whitespace-normalized."""
    if not name:
        return ""
    key = re.sub(r"\s+", " ", str(name).strip().lower())
    return _ALIAS_INDEX.get(key, key)


def skill_category(name: str) -> str:
    entry = SKILL_TAXONOMY.get(normalize_skill_name(name))
    return entry[0] if entry else "Other"


def is_known_skill(name: str) -> bool:
    return normalize_skill_name(name) in SKILL_TAXONOMY


def find_skill_mentions(text: str) -> Dict[str, List[Tuple[int, int]]]:
    """Return {canonical_skill: [(start, end), ...]} for every skill found in text."""
    found: Dict[str, List[Tuple[int, int]]] = {}
    if not text:
        return found
    for canonical, plist in _PATTERNS.items():
        spans: List[Tuple[int, int]] = []
        for p in plist:
            for m in p.finditer(text):
                spans.append((m.start(), m.end()))
        if spans:
            found[canonical] = sorted(set(spans))
    return found


def extract_skill_names(text: str) -> List[str]:
    """Convenience: sorted list of canonical skills mentioned in text."""
    return sorted(find_skill_mentions(text).keys())
