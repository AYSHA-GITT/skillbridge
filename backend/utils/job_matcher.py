"""
Explainable, deterministic job-fit scoring.

Score = 100 x SkillFit x ExperienceFit x LocationFit

SkillFit  = sum(weight x credit) / sum(weight)
            weight: required skill = 3, preferred skill = 1
            credit (how strongly the student demonstrates the skill):
              quiz-verified, best score >= 70%   1.00
              quiz-verified, 40-69%              0.60
              quiz-verified, < 40%               0.20
              resume only, used in projects/work 0.70
              resume only, other sections        0.55
              resume only, skills list only      0.40
              missing but transferable skill     0.25  (required skills only)
              missing                            0.00
ExperienceFit  1.00 if the job's minimum years <= student's years (+0.5),
               0.80 if short by <= 2 years, 0.55 otherwise; seniority title
               mismatch (senior role, student without experience) -> 0.60
LocationFit    1.00 remote / preferred location / no preference set,
               0.90 open to relocation, 0.75 otherwise

What the score deliberately does NOT do (unlike the previous version):
* no free points: eligibility used to add 15/100 to every job and transferable
  skills up to 15/100;
* a matching job TITLE adds nothing - only demonstrated skills count;
* when a job lists no recognisable skills the score is None ("insufficient
  data") rather than a made-up number.
"""
from typing import Any, Dict, List, Optional, Set

from models import Skill, SkillVerification, JobListing
from utils.skill_taxonomy import normalize_skill_name

# Knowledge graph of transferable skill affinities (student skill -> skills it helps with)
TRANSFERABLE_MAP: Dict[str, List[str]] = {
    "python": ["django", "flask", "fastapi", "data analysis", "pandas", "numpy"],
    "javascript": ["typescript", "react", "node.js", "express", "vue", "angular"],
    "react": ["next.js", "react native", "vue", "redux", "angular"],
    "sql": ["postgresql", "mysql", "sqlite", "oracle", "dbms"],
    "postgresql": ["sql", "mysql"],
    "mysql": ["sql", "postgresql"],
    "docker": ["kubernetes", "ci/cd"],
    "aws": ["azure", "gcp"],
    "azure": ["aws", "gcp"],
    "gcp": ["aws", "azure"],
    "machine learning": ["deep learning", "scikit-learn"],
    "pytorch": ["tensorflow", "deep learning", "keras"],
    "tensorflow": ["pytorch", "keras", "deep learning"],
    "java": ["spring boot", "c#", "kotlin", "oop"],
    "c++": ["c", "data structures", "algorithms"],
    "linux": ["bash"],
    "git": ["github"],
    "html": ["css"],
    "css": ["tailwind css", "bootstrap"],
    "excel": ["power bi", "tableau"],
    "power bi": ["tableau"],
    "tableau": ["power bi"],
}

REQUIRED_WEIGHT = 3.0
PREFERRED_WEIGHT = 1.0
TRANSFER_CREDIT = 0.25
EVIDENCE_CREDIT = {"applied": 0.70, "supporting": 0.55, "listed_only": 0.40, "unclassified": 0.40, None: 0.40}

SENIORITY_ORDER = {"internship": 0, "entry-level": 1, "entry": 1, "junior": 1, "beginner": 1,
                   "mid-level": 2, "intermediate": 2, "mid": 2, "senior": 3, "advanced": 3, "lead": 4}


def _normalize_skill(s: str) -> str:
    return normalize_skill_name(s)


def _quiz_credit(pct: Optional[float]) -> float:
    if pct is None:
        return 0.0
    if pct >= 70:
        return 1.0
    if pct >= 40:
        return 0.6
    return 0.2


# ──────────────────────────────────────────────────────────────────────────
# Student profile
# ──────────────────────────────────────────────────────────────────────────
def build_student_profile(student: Any = None, user_skills: Optional[List[Any]] = None,
                          user_experience_level: Optional[str] = None) -> Dict[str, Any]:
    """Collect {skill: {credit, status, ...}} plus preferences, once per student."""
    skills: Dict[str, Dict[str, Any]] = {}
    preference: Dict[str, Any] = {}
    experience_years: Optional[float] = None

    if user_skills is not None:
        for item in user_skills:
            if isinstance(item, dict):
                name = _normalize_skill(item.get("skill_name") or item.get("name") or "")
                if not name:
                    continue
                if item.get("is_verified") or item.get("verified"):
                    pct = item.get("quiz_score_percent", 70.0)
                    skills[name] = {"credit": _quiz_credit(pct), "status": "verified", "quiz_score": pct}
                else:
                    ev = item.get("evidence_strength")
                    skills[name] = {"credit": EVIDENCE_CREDIT.get(ev, 0.4), "status": "resume_only",
                                    "evidence_strength": ev}
            elif isinstance(item, str) and _normalize_skill(item):
                # bare strings: treat as claimed (resume-level) skills, not verified ones
                skills[_normalize_skill(item)] = {"credit": EVIDENCE_CREDIT[None], "status": "resume_only",
                                                  "evidence_strength": None}
    elif student is not None and hasattr(student, "id"):
        best_quiz: Dict[int, float] = {}
        for v in SkillVerification.query.filter_by(student_id=student.id).all():
            best_quiz[v.skill_id] = max(best_quiz.get(v.skill_id, 0.0), v.quiz_score_percent or 0.0)
        for s in Skill.query.filter_by(student_id=student.id).all():
            name = _normalize_skill(s.skill_name)
            if s.id in best_quiz:
                entry = {"credit": _quiz_credit(best_quiz[s.id]), "status": "verified",
                         "quiz_score": best_quiz[s.id]}
            else:
                entry = {"credit": EVIDENCE_CREDIT.get(s.evidence_strength, 0.4), "status": "resume_only",
                         "evidence_strength": s.evidence_strength,
                         "extraction_confidence": s.extraction_confidence}
            if name not in skills or entry["credit"] > skills[name]["credit"]:
                skills[name] = entry
        pref = getattr(student, "job_preference", None)
        if pref is not None:
            preference = pref.to_dict()
            experience_years = preference.get("experience_years")

    return {
        "skills": skills,
        "preference": preference,
        "experience_years": experience_years,
        "experience_level": (user_experience_level or "").lower() or None,
        "course": getattr(student, "course", None) if student is not None else None,
    }


# ──────────────────────────────────────────────────────────────────────────
# Fit components
# ──────────────────────────────────────────────────────────────────────────
def _experience_fit(job: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
    notes: List[str] = []
    job_min = job.get("experience_min_years")
    student_years = profile.get("experience_years")
    job_level = (job.get("experience_level") or "").lower()
    student_level = profile.get("experience_level")

    factor = 1.0
    meets: Optional[bool] = True
    if student_level and job_level in SENIORITY_ORDER and student_level in SENIORITY_ORDER:
        gap = SENIORITY_ORDER[job_level] - SENIORITY_ORDER[student_level]
        if gap >= 2:
            factor, meets = 0.55, False
            notes.append(f"Role is {job.get('experience_level')}; your level is {student_level}.")
        elif gap == 1:
            factor, meets = 0.8, False
            notes.append(f"Role expects slightly more seniority ({job.get('experience_level')}).")
        else:
            notes.append(f"Seniority matches ({job.get('experience_level')}).")
    elif job_min is not None:
        years = student_years or 0.0
        short = job_min - years
        if short <= 0.5:
            notes.append(f"Requires {job_min:g}+ years; you have {years:g}.")
        elif short <= 2:
            factor, meets = 0.8, False
            notes.append(f"Requires {job_min:g}+ years of experience; you have {years:g}.")
        else:
            factor, meets = 0.55, False
            notes.append(f"Requires {job_min:g}+ years of experience; you have {years:g} - a significant gap.")
        if student_years is None:
            notes.append("Your experience is not set in job preferences; 0 years assumed.")
    elif job_level == "senior" and not student_years:
        factor, meets = 0.6, False
        notes.append("Senior role; no professional experience recorded in your preferences.")
    else:
        meets = None
        notes.append("The posting does not state an experience requirement.")
    return {"factor": factor, "meets": meets, "notes": notes}


def _location_fit(job: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
    pref = profile.get("preference") or {}
    locations = [l.lower().strip() for l in pref.get("preferred_locations", []) if l and l.strip()]
    modes = [m.lower() for m in pref.get("work_modes", []) if m]
    arrangement = (job.get("work_arrangement") or "").lower()
    job_loc = f"{job.get('location') or ''} {job.get('city') or ''} {job.get('state') or ''}".lower()

    if not locations and not modes:
        return {"factor": 1.0, "compatible": None,
                "notes": ["No location / work-mode preference set - location not scored."]}
    if modes and arrangement and arrangement != "unspecified" and arrangement not in modes:
        if not (arrangement == "remote" and "hybrid" in modes):
            return {"factor": 0.75, "compatible": False,
                    "notes": [f"Work mode is {job.get('work_arrangement')}; you prefer {', '.join(pref.get('work_modes'))}."]}
    if arrangement == "remote":
        return {"factor": 1.0, "compatible": True, "notes": ["Remote role - location compatible."]}
    if not locations or any(l in job_loc for l in locations):
        return {"factor": 1.0, "compatible": True, "notes": [f"Located in {job.get('location')} - matches your preference."]}
    if pref.get("open_to_relocation"):
        return {"factor": 0.9, "compatible": True,
                "notes": [f"Located in {job.get('location')} - outside your preferred locations, but you are open to relocation."]}
    return {"factor": 0.75, "compatible": False,
            "notes": [f"Located in {job.get('location')} - outside your preferred locations."]}


def _job_to_dict(job: Any = None, job_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if job_data is not None:
        return job_data
    if isinstance(job, dict):
        return job
    if job is not None and hasattr(job, "get_required_skills"):
        d = job.to_dict()
        d["required_skills"] = job.get_required_skills()
        d["preferred_skills"] = job.get_preferred_skills()
        return d
    return {}


# ──────────────────────────────────────────────────────────────────────────
# Main scorer
# ──────────────────────────────────────────────────────────────────────────
def evaluate_job_match(
    student: Any = None,
    job: Any = None,
    user_skills: Optional[List[Any]] = None,
    job_data: Optional[Dict[str, Any]] = None,
    user_experience_level: Optional[str] = None,
    profile: Optional[Dict[str, Any]] = None,
    include_resources: bool = True,
) -> Dict[str, Any]:
    profile = profile or build_student_profile(student, user_skills, user_experience_level)
    have = profile["skills"]
    job_dict = _job_to_dict(job, job_data)

    required: List[str] = []
    for s in job_dict.get("required_skills", []) or []:
        n = _normalize_skill(s)
        if n and n not in required:
            required.append(n)
    preferred = []
    for s in job_dict.get("preferred_skills", []) or []:
        n = _normalize_skill(s)
        if n and n not in required and n not in preferred:
            preferred.append(n)

    matched_verified: List[str] = []
    matched_unverified: List[str] = []
    missing_mandatory: List[str] = []
    transferable_found: List[Dict[str, Any]] = []
    uncertain: List[Dict[str, Any]] = []
    req_points = 0.0

    for skill in required:
        info = have.get(skill)
        if info:
            (matched_verified if info["status"] == "verified" else matched_unverified).append(skill)
            req_points += info["credit"]
            if info["status"] == "resume_only":
                uncertain.append({"skill": skill, "evidence_strength": info.get("evidence_strength"),
                                  "reason": "Claimed on resume but not quiz-verified; take the skill quiz to confirm it."})
            continue
        missing_mandatory.append(skill)
        bridge = next((u for u in have if skill in TRANSFERABLE_MAP.get(u, [])), None)
        if bridge:
            req_points += TRANSFER_CREDIT
            transferable_found.append({
                "missing_skill": skill, "related_student_skill": bridge, "transfer_coefficient": TRANSFER_CREDIT,
                "affinity_rationale": f"Your '{bridge}' skill is closely related to '{skill}', which shortens the learning path "
                                      f"(partial credit only - it does not satisfy the requirement)."})

    matched_preferred = [p for p in preferred if p in have]
    missing_preferred = [p for p in preferred if p not in have]
    pref_points = sum(have[p]["credit"] for p in matched_preferred)

    total_weight = REQUIRED_WEIGHT * len(required) + PREFERRED_WEIGHT * len(preferred)
    exp = _experience_fit(job_dict, profile)
    loc = _location_fit(job_dict, profile)

    if total_weight == 0:
        skill_fit = None
        overall = None
        label = "Insufficient data"
    else:
        skill_fit = (REQUIRED_WEIGHT * req_points + PREFERRED_WEIGHT * pref_points) / total_weight
        overall = round(100.0 * skill_fit * exp["factor"] * loc["factor"], 1)
        label = ("Strong match" if overall >= 70 else "Moderate match" if overall >= 45
                 else "Developing match" if overall >= 25 else "Low match")

    req_cov = round(100.0 * (len(matched_verified) + len(matched_unverified)) / len(required), 1) if required else None
    pref_cov = round(100.0 * len(matched_preferred) / len(preferred), 1) if preferred else None
    transfer_pct = round(100.0 * len(transferable_found) / len(missing_mandatory), 1) if missing_mandatory else 0.0

    reasons: List[str] = []
    if overall is None:
        reasons.append("This posting lists no recognisable skills, so a skill match cannot be calculated. "
                       "Read the full description on the source site.")
    else:
        if matched_verified:
            reasons.append(f"You have quiz-verified {len(matched_verified)} of {len(required)} required skills: "
                           f"{', '.join(matched_verified)}.")
        if matched_unverified:
            reasons.append(f"Your resume shows {', '.join(matched_unverified)} (not yet quiz-verified).")
        if missing_mandatory:
            reasons.append(f"Missing required skills: {', '.join(missing_mandatory)}.")
        if matched_preferred:
            reasons.append(f"You also have preferred skills: {', '.join(matched_preferred)}.")
    reasons.extend(exp["notes"])
    reasons.extend(loc["notes"])

    breakdown = {
        "overall_fit_score": overall,
        "skill_fit_score": round(100 * skill_fit, 1) if skill_fit is not None else None,
        # percentages (0-100) - coverage of each skill group
        "mandatory_skills_score": req_cov if req_cov is not None else 0.0,
        "preferred_skills_score": pref_cov if pref_cov is not None else 0.0,
        "transferable_skills_score": transfer_pct,
        "experience_eligibility_score": round(100 * exp["factor"], 1),
        "location_fit_score": round(100 * loc["factor"], 1),
        "fit_label": label,
        "formula": "Overall = 100 x SkillFit x ExperienceFit x LocationFit; SkillFit weights required skills 3x "
                   "preferred, and credits verified skills above resume-only claims.",
        "components": {
            "mandatory_skills": {"coverage_pct": req_cov, "verified_matches": matched_verified,
                                 "unverified_matches": matched_unverified, "weight": REQUIRED_WEIGHT},
            "preferred_skills": {"coverage_pct": pref_cov, "matches": matched_preferred, "weight": PREFERRED_WEIGHT},
            "transferable_skills": {"bridges": [t["missing_skill"] for t in transferable_found],
                                    "credit_per_bridge": TRANSFER_CREDIT},
            "experience": {"factor": exp["factor"], "notes": exp["notes"]},
            "location": {"factor": loc["factor"], "notes": loc["notes"]},
        },
        "score_disclaimer": "A transparent indicator of skill alignment, not a prediction of hiring outcomes.",
    }

    resources: List[Dict[str, Any]] = []
    top_missing = missing_mandatory[0] if missing_mandatory else (missing_preferred[0] if missing_preferred else None)
    if include_resources and top_missing:
        try:
            from utils.youtube_api import search_youtube_videos
            from utils.github_api import search_github_projects
            resources = [dict(r, skill_query=top_missing) for r in
                         (search_youtube_videos(top_missing, max_results=2) + search_github_projects(top_missing, max_results=2))]
        except Exception:
            resources = []

    steps: List[str] = []
    if missing_mandatory:
        steps.append(f"Learn '{missing_mandatory[0]}' first - it is a required skill for this role.")
    if matched_unverified:
        steps.append(f"Take the verification quiz for '{matched_unverified[0]}' to turn a resume claim into a verified skill.")
    if overall is not None and overall >= 70:
        steps.append("Your profile aligns well - tailor your resume to this posting before applying.")

    return {
        "job": job_dict,
        "match_score": overall,
        "scoring_breakdown": breakdown,
        "score_breakdown": breakdown,
        "match_reasons": reasons,
        "matched_skills": {"verified": matched_verified, "unverified": matched_unverified, "preferred": matched_preferred},
        "skill_status": {s: have[s]["status"] for s in matched_verified + matched_unverified + matched_preferred},
        "missing_skills": {"mandatory": missing_mandatory, "preferred": missing_preferred},
        "transferable_skills": transferable_found,
        "transferable_bridges": [
            {"user_skill": t["related_student_skill"], "target_skill": t["missing_skill"],
             "transfer_coefficient": t["transfer_coefficient"], "rationale": t["affinity_rationale"]}
            for t in transferable_found],
        "uncertain_skills": uncertain,
        "eligibility_status": {"meets_criteria": exp["meets"], "details": exp["notes"]},
        "location_compatibility": {"compatible": loc["compatible"], "details": loc["notes"]},
        "suggested_next_steps": steps,
        "curated_resources": resources,
    }


def compare_multiple_jobs(student_or_skills: Any, job_ids_or_list: Any) -> Dict[str, Any]:
    """Side-by-side comparison; identifies shared requirements and highest-yield skills to learn."""
    evaluations = []
    all_mandatory_gaps: Dict[str, int] = {}
    job_required_sets: List[Set[str]] = []
    is_direct_list = isinstance(job_ids_or_list, list) and job_ids_or_list and isinstance(job_ids_or_list[0], dict)

    if is_direct_list:
        profile = build_student_profile(user_skills=student_or_skills)
        jobs = job_ids_or_list
        for j in jobs:
            ev = evaluate_job_match(job_data=j, profile=profile, include_resources=False)
            evaluations.append(ev)
            job_required_sets.append({_normalize_skill(s) for s in j.get("required_skills", [])})
            for gap in ev["missing_skills"]["mandatory"]:
                all_mandatory_gaps[gap] = all_mandatory_gaps.get(gap, 0) + 1
    else:
        profile = build_student_profile(student=student_or_skills)
        for jid in job_ids_or_list:
            job = JobListing.query.get(jid)
            if not job:
                continue
            ev = evaluate_job_match(job=job, profile=profile, include_resources=False)
            evaluations.append(ev)
            job_required_sets.append({_normalize_skill(s) for s in job.get_required_skills()})
            for gap in ev["missing_skills"]["mandatory"]:
                all_mandatory_gaps[gap] = all_mandatory_gaps.get(gap, 0) + 1

    overlapping: Set[str] = set()
    if job_required_sets:
        overlapping = set.intersection(*job_required_sets) if len(job_required_sets) > 1 else job_required_sets[0]
    high_yield = sorted([{"skill": k, "unlocks_jobs_count": v} for k, v in all_mandatory_gaps.items()],
                        key=lambda x: x["unlocks_jobs_count"], reverse=True)
    overlap_list = sorted(overlapping) or [h["skill"] for h in high_yield[:3]]
    return {
        "compared_jobs_count": len(evaluations),
        "job_evaluations": evaluations,
        "comparisons": evaluations,
        "jobs": evaluations,
        "high_yield_skill_investments": high_yield,
        "high_yield_overlapping_skills": overlap_list,
        "recommendation": (
            f"Learn '{high_yield[0]['skill']}' first - it is required by {high_yield[0]['unlocks_jobs_count']} of the compared jobs."
            if high_yield else "You meet the listed required skills of all compared jobs."),
    }
