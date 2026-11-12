"""
Resume skill extraction with evidence.

For every skill this module reports three DIFFERENT things, which must not be
confused with each other:

* extraction_confidence - how sure we are that the text really refers to the
  skill (1.0 for an unambiguous name such as "PostgreSQL", lower for names
  that are only recognisable from list context, such as "C" or "R").
  It is a rule-based score, NOT a calibrated probability.
* evidence_strength     - how well the resume SUPPORTS the skill:
    "applied"     mentioned in experience / project / internship text
    "supporting"  mentioned in certifications, education, summary or achievements
    "listed_only" only appears in a skills list
* verified proficiency  - NOT produced here. Only a completed skill quiz
  (SkillVerification) establishes proficiency.

The old implementation used raw substring matching, which reported "java" for
every "javascript" resume and "c"/"r" for almost every resume. Matching now
goes through the shared token-boundary taxonomy in utils.skill_taxonomy.
"""
import re
from typing import Dict, List

from utils.skill_taxonomy import (
    AMBIGUOUS_SKILLS,
    find_skill_mentions,
    skill_category,
)

# canonical section -> header phrases (matched against short, header-like lines)
SECTION_HEADERS: Dict[str, List[str]] = {
    "skills": ["skills", "technical skills", "key skills", "core skills", "skill set", "skillset",
               "technologies", "tech stack", "tools", "tools & technologies", "tools and technologies",
               "core competencies", "competencies", "programming languages", "languages"],
    "experience": ["experience", "work experience", "professional experience", "employment",
                   "employment history", "work history", "internship", "internships",
                   "internship experience", "industrial training", "training"],
    "projects": ["projects", "academic projects", "personal projects", "key projects",
                 "project experience", "major project", "mini project", "capstone project"],
    "education": ["education", "academic background", "academics", "qualifications",
                  "educational qualifications", "academic qualifications"],
    "certifications": ["certifications", "certification", "certificates", "courses",
                       "online courses", "licenses & certifications", "licenses and certifications"],
    "achievements": ["achievements", "awards", "honors", "honours", "accomplishments",
                     "hackathons", "publications"],
    "summary": ["summary", "profile", "objective", "career objective", "professional summary",
                "about me", "profile summary"],
}

APPLIED_SECTIONS = {"experience", "projects"}
SUPPORTING_SECTIONS = {"certifications", "education", "summary", "achievements"}

_HEADER_LOOKUP = {}
for _sec, _phrases in SECTION_HEADERS.items():
    for _p in _phrases:
        _HEADER_LOOKUP[_p] = _sec


def _detect_header(line: str):
    """Return canonical section if `line` looks like a section header."""
    stripped = line.strip().strip(":-–—•*#|").strip()
    if not stripped or len(stripped) > 45:
        return None
    key = re.sub(r"\s+", " ", stripped.lower())
    if key in _HEADER_LOOKUP:
        return _HEADER_LOOKUP[key]
    # "TECHNICAL SKILLS:" / "Skills & Tools" style headers
    for phrase, sec in _HEADER_LOOKUP.items():
        if key.startswith(phrase) and len(key) <= len(phrase) + 15 and not re.search(r"[.,;]", key):
            return sec
    return None


def split_into_sections(text: str) -> Dict[str, str]:
    """Split resume text into canonical sections. Text before the first
    recognised header goes to 'general'."""
    sections: Dict[str, List[str]] = {"general": []}
    current = "general"
    for line in (text or "").splitlines():
        header = _detect_header(line)
        if header:
            current = header
            sections.setdefault(current, [])
            # "Skills: Python, SQL" on the same line as the header
            rest = re.split(r"[:\-–—]", line, maxsplit=1)
            if len(rest) == 2 and rest[1].strip():
                sections[current].append(rest[1])
            continue
        sections.setdefault(current, []).append(line)
    return {name: "\n".join(lines) for name, lines in sections.items()}


def _snippet(text: str, start: int, end: int, width: int = 60) -> str:
    a = max(0, start - width)
    b = min(len(text), end + width)
    snippet = re.sub(r"\s+", " ", text[a:b]).strip()
    return ("…" if a > 0 else "") + snippet + ("…" if b < len(text) else "")


def extract_skills(resume_text: str) -> List[Dict]:
    """
    Returns a list of dicts (one per canonical skill, no duplicates):
      skill_name, category, extraction_confidence, evidence_strength,
      sections, evidence (list of {section, snippet}), explanation
    """
    if not resume_text or not resume_text.strip():
        return []

    sections = split_into_sections(resume_text)
    per_skill: Dict[str, Dict] = {}

    for section_name, section_text in sections.items():
        if not section_text.strip():
            continue
        for skill, spans in find_skill_mentions(section_text).items():
            entry = per_skill.setdefault(skill, {"sections": [], "evidence": []})
            if section_name not in entry["sections"]:
                entry["sections"].append(section_name)
            for (s, e) in spans[:2]:
                if len(entry["evidence"]) < 4:
                    entry["evidence"].append({"section": section_name,
                                              "snippet": _snippet(section_text, s, e)})

    results = []
    for skill, entry in sorted(per_skill.items()):
        secs = set(entry["sections"])
        if secs & APPLIED_SECTIONS:
            strength = "applied"
        elif secs & SUPPORTING_SECTIONS:
            strength = "supporting"
        elif secs == {"skills"}:
            strength = "listed_only"
        else:
            # only in un-sectioned text (resume without recognisable headers)
            strength = "unclassified"

        confidence = 0.7 if skill in AMBIGUOUS_SKILLS else 1.0

        where = ", ".join(sorted(secs))
        if strength == "applied":
            explanation = f"Used in {where} — the resume describes applying this skill."
        elif strength == "supporting":
            explanation = f"Mentioned in {where}, but not in project or work descriptions."
        elif strength == "listed_only":
            explanation = "Only listed in the skills section; no project or work evidence found."
        else:
            explanation = "Mentioned in resume text whose section could not be identified."
        if skill in AMBIGUOUS_SKILLS:
            explanation += " Recognised from list context (short/ambiguous name), so confidence is reduced."

        results.append({
            "skill_name": skill,
            "category": skill_category(skill),
            "extraction_confidence": confidence,
            "evidence_strength": strength,
            "sections": sorted(secs),
            "evidence": entry["evidence"],
            "explanation": explanation,
        })
    return results
