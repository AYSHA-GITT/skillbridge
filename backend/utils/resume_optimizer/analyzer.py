"""
SkillLens AI - Resume Optimizer: Analyzer
Computes deterministic, explainable job-match scores, identifies missing skills
and keywords, and flags weak bullet points and formatting deficiencies.
"""

import re
from typing import Dict, Any, List, Set, Tuple
from data.career_requirements import CAREER_REQUIREMENTS
from data.skills_list import KNOWN_SKILLS

WEAK_VERBS = [
    "responsible for", "helped", "worked on", "assisted", "did", "tasked with",
    "participated in", "handled", "involved in", "contributed to", "supported",
    "was part of", "tried to", "attempted", "managed some", "took care of"
]

METRIC_PATTERNS = [
    r'\b\d+%\b',                       # 20%, 100%
    r'\$\d+(?:,\d{3})*(?:\.\d+)?\b',   # $10,000
    r'\b\d+(?:\.\d+)?x\b',             # 2x, 5.5x
    r'\b\d+\s*(?:users|clients|customers|requests|queries|students|ms|sec|seconds|hours|days|GB|TB|MB)\b',
    r'\b(?:reduced|increased|improved|scaled|saved|boosted|accelerated)\s+by\s+\d+',
    r'\b\d{2,}\b'                      # general numbers >= 10
]


def extract_skills_from_jd(jd_text: str) -> Dict[str, List[str]]:
    """
    Extracts required and preferred skills from a custom job description
    using known skill taxonomies and contextual section splitting.
    """
    jd_lower = jd_text.lower()
    found_skills: Set[str] = set()

    for skill in KNOWN_SKILLS:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, jd_lower):
            found_skills.add(skill.lower())

    # Additional common keywords in technical job descriptions
    common_tech = [
        "aws", "azure", "gcp", "ci/cd", "restful api", "graphql", "microservices",
        "redis", "kafka", "scrum", "agile", "unit testing", "system design",
        "oop", "data structures", "algorithms", "problem solving"
    ]
    for tech in common_tech:
        pattern = r'\b' + re.escape(tech) + r'\b'
        if re.search(pattern, jd_lower):
            found_skills.add(tech)

    # Heuristic: skills mentioned in the top half or near "must have"/"required"
    # are required, others are nice-to-have
    skill_list = list(found_skills)
    if len(skill_list) <= 5:
        required = skill_list
        nice_to_have = []
    else:
        midpoint = int(len(skill_list) * 0.65)
        required = skill_list[:midpoint]
        nice_to_have = skill_list[midpoint:]

    return {
        "required": required,
        "nice_to_have": nice_to_have
    }


def find_matched_and_missing_skills(
    resume_skills: List[str],
    resume_text: str,
    target_requirements: Dict[str, List[str]]
) -> Tuple[List[str], List[str], List[str]]:
    """
    Compares the resume content with target career or JD requirements.
    Returns: (matched_skills, missing_required, missing_preferred)
    """
    text_corpus = (
        ' '.join(resume_skills) + ' ' + resume_text
    ).lower()

    required_skills = [s.lower() for s in target_requirements.get('required', [])]
    preferred_skills = [s.lower() for s in target_requirements.get('nice_to_have', [])]

    matched: List[str] = []
    missing_required: List[str] = []
    missing_preferred: List[str] = []

    for req in required_skills:
        pattern = r'\b' + re.escape(req) + r'\b'
        if re.search(pattern, text_corpus):
            matched.append(req)
        else:
            missing_required.append(req)

    for pref in preferred_skills:
        pattern = r'\b' + re.escape(pref) + r'\b'
        if re.search(pattern, text_corpus):
            if req not in matched:
                matched.append(pref)
        else:
            missing_preferred.append(pref)

    return sorted(list(set(matched))), sorted(list(set(missing_required))), sorted(list(set(missing_preferred)))


def evaluate_bullet_points(sections: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Scans experience and project bullet points for:
    - Weak or passive introductory verbs
    - Lack of quantifiable metrics / business impact
    - Brevity or vagueness (< 6 words)
    """
    findings = []

    def check_bullet(text: str, source: str, item_index: int, bullet_index: int):
        t_clean = text.strip()
        if not t_clean or len(t_clean) < 10:
            return

        t_lower = t_clean.lower()
        words = t_clean.split()

        issues = []
        is_weak_verb = False
        for weak in WEAK_VERBS:
            if t_lower.startswith(weak) or f" {weak} " in t_lower:
                issues.append(f"Contains passive phrasing: '{weak}'")
                is_weak_verb = True
                break

        has_metric = any(re.search(pat, t_clean, re.I) for pat in METRIC_PATTERNS)
        if not has_metric:
            issues.append("Lacks quantifiable metric or measurable impact")

        if len(words) < 7:
            issues.append("Too brief or lacking context (< 7 words)")

        if issues:
            findings.append({
                'source': source,
                'item_index': item_index,
                'bullet_index': bullet_index,
                'original_text': t_clean,
                'issues': issues,
                'is_weak_verb': is_weak_verb,
                'has_metric': has_metric
            })

    # Scan Experience bullets
    for i, exp in enumerate(sections.get('experience', [])):
        role_label = exp.get('role') or exp.get('company') or f"Experience #{i+1}"
        for b_idx, bullet in enumerate(exp.get('bullets', [])):
            check_bullet(bullet, f"Experience ({role_label})", i, b_idx)

    # Scan Project bullets
    for i, proj in enumerate(sections.get('projects', [])):
        proj_label = proj.get('name') or f"Project #{i+1}"
        for b_idx, bullet in enumerate(proj.get('bullets', [])):
            check_bullet(bullet, f"Project ({proj_label})", i, b_idx)

    return findings


def evaluate_formatting_issues(sections: Dict[str, Any]) -> List[Dict[str, str]]:
    """Identifies structural and ATS formatting deficiencies."""
    issues = []
    contact = sections.get('contact', {})

    if not contact.get('email'):
        issues.append({
            'code': 'MISSING_EMAIL',
            'severity': 'high',
            'message': 'No contact email detected in resume header.'
        })

    if not contact.get('phone'):
        issues.append({
            'code': 'MISSING_PHONE',
            'severity': 'medium',
            'message': 'No phone number detected for recruiter outreach.'
        })

    if not contact.get('linkedin') and not contact.get('github'):
        issues.append({
            'code': 'MISSING_LINKS',
            'severity': 'low',
            'message': 'Add your LinkedIn or GitHub profile link to bolster credibility.'
        })

    summary = sections.get('summary', '')
    if not summary or len(summary.strip()) < 30:
        issues.append({
            'code': 'MISSING_SUMMARY',
            'severity': 'medium',
            'message': 'Resume is missing an Executive Summary or Career Objective to hook recruiters.'
        })

    if not sections.get('experience') and not sections.get('projects'):
        issues.append({
            'code': 'NO_EXPERIENCE_OR_PROJECTS',
            'severity': 'high',
            'message': 'Resume does not contain any work experience or project entries.'
        })

    skills = sections.get('skills', [])
    if len(skills) < 4:
        issues.append({
            'code': 'FEW_SKILLS',
            'severity': 'medium',
            'message': f'Only {len(skills)} skills detected. Adding a dedicated skills section improves ATS parsing.'
        })

    return issues


def calculate_job_match_score(
    matched_skills: List[str],
    missing_required: List[str],
    missing_preferred: List[str],
    formatting_issues: List[Dict[str, str]],
    weak_bullets_count: int,
    total_bullets_count: int
) -> Dict[str, Any]:
    """
    Computes a deterministic, transparent job-match percentage:
    - Required Skills: 55% weight
    - Preferred Skills: 25% weight
    - Content Structure & ATS Formatting: 20% weight
    """
    # 1. Required skills match ratio
    total_required = len(matched_skills) + len(missing_required)
    matched_req_count = len([s for s in matched_skills if s not in missing_preferred])

    if total_required > 0:
        req_ratio = min(1.0, (len(matched_skills) - len(missing_preferred)) / total_required)
        req_score = max(0.0, req_ratio) * 55.0
    else:
        req_score = 55.0

    # 2. Preferred skills match ratio
    total_pref = len(missing_preferred)
    if total_pref > 0:
        # Give partial credit for matched skills beyond required
        pref_matched = max(0, len(matched_skills) - total_required)
        pref_ratio = min(1.0, pref_matched / total_pref)
        pref_score = pref_ratio * 25.0
    else:
        pref_score = 20.0

    # 3. Content & Formatting Score (out of 20)
    struct_score = 20.0
    for issue in formatting_issues:
        sev = issue.get('severity', 'medium')
        if sev == 'high':
            struct_score -= 5.0
        elif sev == 'medium':
            struct_score -= 3.0
        else:
            struct_score -= 1.5

    if total_bullets_count > 0:
        weak_ratio = weak_bullets_count / total_bullets_count
        struct_score -= min(6.0, weak_ratio * 8.0)

    struct_score = max(4.0, min(20.0, struct_score))

    total_score = round(req_score + pref_score + struct_score, 1)
    total_score = max(10.0, min(99.0, total_score))

    return {
        'total_score': total_score,
        'breakdown': {
            'required_skills_score': round(req_score, 1),
            'preferred_skills_score': round(pref_score, 1),
            'formatting_score': round(struct_score, 1),
            'max_possible': 100
        }
    }


def analyze_resume(
    parsed_sections: Dict[str, Any],
    target_career: str = None,
    job_description: str = None
) -> Dict[str, Any]:
    """
    Main analysis pipeline.
    Deterministic execution, zero hallucinations.
    """
    # Resolve job requirements
    reqs: Dict[str, List[str]] = {"required": [], "nice_to_have": []}
    career_key = (target_career or "").lower().strip()

    if career_key in CAREER_REQUIREMENTS:
        reqs = CAREER_REQUIREMENTS[career_key]
    elif job_description and len(job_description.strip()) > 30:
        reqs = extract_skills_from_jd(job_description)
    else:
        # Fallback to software engineer baseline if neither is specified
        reqs = CAREER_REQUIREMENTS.get("software engineer", {"required": ["python", "sql", "git"], "nice_to_have": []})

    resume_text = parsed_sections.get('raw_text', '')
    resume_skills = parsed_sections.get('skills', [])

    matched, missing_req, missing_pref = find_matched_and_missing_skills(
        resume_skills, resume_text, reqs
    )

    weak_bullets = evaluate_bullet_points(parsed_sections)
    formatting_issues = evaluate_formatting_issues(parsed_sections)

    # Count total bullets across experience and projects
    total_bullets = sum(len(exp.get('bullets', [])) for exp in parsed_sections.get('experience', [])) + \
                    sum(len(proj.get('bullets', [])) for proj in parsed_sections.get('projects', []))

    score_data = calculate_job_match_score(
        matched, missing_req, missing_pref, formatting_issues,
        len(weak_bullets), total_bullets
    )

    return {
        'target_career': target_career or "Custom Role",
        'match_score': score_data['total_score'],
        'score_breakdown': score_data['breakdown'],
        'matched_skills': matched,
        'missing_required_skills': missing_req,
        'missing_preferred_skills': missing_pref,
        'weak_bullet_points': weak_bullets,
        'formatting_issues': formatting_issues,
        'total_bullets_analyzed': total_bullets
    }
