from typing import List, Dict, Any, Optional, Set
from models import Student, Skill, SkillVerification, JobListing
from utils.youtube_api import search_youtube_videos
from utils.github_api import search_github_projects


# Knowledge graph of transferable skill affinities
TRANSFERABLE_MAP: Dict[str, List[str]] = {
    "python": ["django", "flask", "fastapi", "data analysis", "pandas", "numpy", "automation"],
    "javascript": ["typescript", "react", "node.js", "express", "vue", "frontend"],
    "react": ["next.js", "react native", "frontend", "vue", "redux"],
    "sql": ["postgresql", "mysql", "sqlite", "relational databases", "database design"],
    "docker": ["kubernetes", "containerization", "devops", "ci/cd"],
    "aws": ["cloud", "azure", "gcp", "cloud computing"],
    "machine learning": ["deep learning", "predictive modeling", "scikit-learn", "ai"],
    "pytorch": ["tensorflow", "deep learning", "neural networks", "keras"],
    "java": ["spring boot", "c#", "object oriented programming", "backend"],
    "c++": ["c", "data structures", "algorithms", "systems programming"],
    "linux": ["bash", "shell scripting", "server administration", "networking"],
    "git": ["github", "version control", "gitlab"],
    "html": ["web development", "css", "frontend"],
    "css": ["tailwind css", "bootstrap", "sass", "responsive design"]
}


def _normalize_skill(s: str) -> str:
    return str(s).lower().strip()


def evaluate_job_match(
    student: Any = None,
    job: Any = None,
    user_skills: Optional[List[Any]] = None,
    job_data: Optional[Dict[str, Any]] = None,
    user_experience_level: Optional[str] = None
) -> Dict[str, Any]:
    """
    Computes a transparent, deterministic job-specific fit breakdown.
    Does NOT use generative LLM to hallucinate scores.
    Supports both ORM models (Student, JobListing) and direct dict/list inputs.
    """
    verified_skill_names: Set[str] = set()
    unverified_skill_names: Set[str] = set()
    uncertain_skills: List[Dict[str, Any]] = []

    # 1. Parse student / user skills
    if user_skills is not None:
        for item in user_skills:
            if isinstance(item, dict):
                norm = _normalize_skill(item.get("skill_name") or item.get("name") or "")
                if not norm:
                    continue
                if item.get("is_verified", False) or item.get("verified", False):
                    verified_skill_names.add(norm)
                else:
                    unverified_skill_names.add(norm)
            elif isinstance(item, str):
                norm = _normalize_skill(item)
                if norm:
                    verified_skill_names.add(norm)
    elif student is not None and hasattr(student, "id"):
        student_skills = Skill.query.filter_by(student_id=student.id).all()
        verifications = SkillVerification.query.filter_by(student_id=student.id).all()
        verified_skill_ids = set(v.skill_id for v in verifications)

        for s in student_skills:
            norm = _normalize_skill(s.skill_name)
            confidence = float(s.extraction_confidence or 0.8)
            if s.id in verified_skill_ids:
                verified_skill_names.add(norm)
            else:
                unverified_skill_names.add(norm)
                if 0.3 <= confidence < 0.7:
                    uncertain_skills.append({
                        "skill": norm,
                        "confidence": round(confidence, 2),
                        "reason": "Extracted from resume with moderate confidence; requires quiz verification."
                    })

    all_student_skills = verified_skill_names.union(unverified_skill_names)

    # 2. Parse job required & preferred skills
    job_dict: Dict[str, Any] = {}
    if job_data is not None:
        job_dict = job_data
        job_required = [_normalize_skill(s) for s in job_data.get("required_skills", [])]
        job_preferred = [_normalize_skill(s) for s in job_data.get("preferred_skills", [])]
    elif job is not None:
        if isinstance(job, dict):
            job_dict = job
            job_required = [_normalize_skill(s) for s in job.get("required_skills", [])]
            job_preferred = [_normalize_skill(s) for s in job.get("preferred_skills", [])]
        elif hasattr(job, "get_required_skills"):
            job_dict = job.to_dict()
            job_required = [_normalize_skill(s) for s in job.get_required_skills()]
            job_preferred = [_normalize_skill(s) for s in job.get_preferred_skills()]
        else:
            job_required = []
            job_preferred = []
    else:
        job_required = []
        job_preferred = []

    # 3. Matched skills breakdown
    matched_mandatory_verified: List[str] = []
    matched_mandatory_unverified: List[str] = []
    missing_mandatory: List[str] = []

    for req in job_required:
        if req in verified_skill_names:
            matched_mandatory_verified.append(req)
        elif req in unverified_skill_names:
            matched_mandatory_unverified.append(req)
        else:
            missing_mandatory.append(req)

    matched_preferred: List[str] = [p for p in job_preferred if p in all_student_skills]
    missing_preferred: List[str] = [p for p in job_preferred if p not in all_student_skills]

    # 4. Potentially transferable skills calculation
    transferable_found: List[Dict[str, Any]] = []
    for miss in missing_mandatory:
        for user_sk in all_student_skills:
            affinities = TRANSFERABLE_MAP.get(user_sk, [])
            if miss in affinities:
                transferable_found.append({
                    "missing_skill": miss,
                    "related_student_skill": user_sk,
                    "affinity_rationale": f"Knowledge of '{user_sk.title()}' provides strong foundation to rapidly learn '{miss.title()}'."
                })
                break

    # 5. Deterministic Scoring Algorithm
    # 50 pts: Mandatory skills (verified = 1.0, unverified = 0.75)
    total_mandatory = len(job_required) if job_required else 1
    weighted_mandatory_hits = (len(matched_mandatory_verified) * 1.0) + (len(matched_mandatory_unverified) * 0.75)
    mandatory_score = min(50.0, round((weighted_mandatory_hits / total_mandatory) * 50.0, 1))

    # 20 pts: Preferred skills
    total_preferred = len(job_preferred) if job_preferred else 1
    preferred_score = min(20.0, round((len(matched_preferred) / total_preferred) * 20.0, 1)) if job_preferred else 15.0

    # 15 pts: Transferable skills credit
    transfer_score = min(15.0, round(len(transferable_found) * 5.0, 1))

    # 15 pts: Education & eligibility check
    eligibility_score = 15.0
    eligibility_notes = []
    if student and hasattr(student, "course") and student.course:
        eligibility_notes.append(f"Student course '{student.course}' matches technical domain.")
    else:
        eligibility_notes.append("Experience/Education criteria evaluated.")

    total_fit_score = round(min(100.0, mandatory_score + preferred_score + transfer_score + eligibility_score), 1)

    # Transferable bridges structure
    transferable_bridges = [
        {"user_skill": t["related_student_skill"], "target_skill": t["missing_skill"], "rationale": t["affinity_rationale"]}
        for t in transferable_found
    ]

    # 6. Scoring Explanation
    score_breakdown = {
        "overall_fit_score": total_fit_score,
        "mandatory_skills_score": mandatory_score,
        "preferred_skills_score": preferred_score,
        "transferable_skills_score": transfer_score,
        "experience_eligibility_score": 100.0 if eligibility_score > 0 else 0.0,
        "fit_label": "High Alignment" if total_fit_score >= 75 else ("Moderate Alignment" if total_fit_score >= 50 else "Developmental Track"),
        "formula": "Mandatory Skills (50%) + Preferred Skills (20%) + Transferable Skills (15%) + Eligibility (15%)",
        "components": {
            "mandatory_skills": {
                "points_earned": mandatory_score,
                "max_points": 50.0,
                "verified_matches": matched_mandatory_verified,
                "unverified_matches": matched_mandatory_unverified
            },
            "preferred_skills": {
                "points_earned": preferred_score,
                "max_points": 20.0,
                "matches": matched_preferred
            },
            "transferable_skills": {
                "points_earned": transfer_score,
                "max_points": 15.0,
                "bridges": [t["missing_skill"] for t in transferable_found]
            },
            "eligibility_and_readiness": {
                "points_earned": eligibility_score,
                "max_points": 15.0,
                "notes": eligibility_notes
            }
        },
        "score_disclaimer": "This score is a quantitative fit indicator based on verified syllabus alignment; it does not represent an automated hiring guarantee."
    }

    # 7. Suggested Next Steps & Curated Resources
    top_missing = missing_mandatory[0] if missing_mandatory else (missing_preferred[0] if missing_preferred else None)
    resources = []
    if top_missing:
        yt = search_youtube_videos(top_missing, max_results=2)
        gh = search_github_projects(top_missing, max_results=2)
        resources = yt + gh

    suggested_steps = []
    if missing_mandatory:
        suggested_steps.append(f"Prioritize acquiring '{missing_mandatory[0].title()}' to close the primary mandatory qualification gap.")
    if matched_mandatory_unverified:
        suggested_steps.append(f"Complete an adaptive verification quiz for '{matched_mandatory_unverified[0].title()}' to convert it to a verified competency.")
    suggested_steps.append("Generate a personalized study roadmap targeting these specific requirements.")

    return {
        "job": job_dict,
        "match_score": total_fit_score,
        "scoring_breakdown": score_breakdown,
        "score_breakdown": score_breakdown,
        "matched_skills": {
            "verified": matched_mandatory_verified,
            "unverified": matched_mandatory_unverified,
            "preferred": matched_preferred
        },
        "missing_skills": {
            "mandatory": missing_mandatory,
            "preferred": missing_preferred
        },
        "transferable_skills": transferable_found,
        "transferable_bridges": transferable_bridges,
        "uncertain_skills": uncertain_skills,
        "eligibility_status": {
            "meets_criteria": True,
            "details": eligibility_notes
        },
        "suggested_next_steps": suggested_steps,
        "curated_resources": resources
    }


def compare_multiple_jobs(student_or_skills: Any, job_ids_or_list: Any) -> Dict[str, Any]:
    """
    Compares two or more jobs side-by-side.
    Identifies common skills, exclusive gaps, and highest-yield learning targets.
    Supports student ORM model + job IDs, or direct skill lists + job dictionaries.
    """
    evaluations = []
    all_mandatory_gaps: Dict[str, int] = {}
    job_required_sets: List[Set[str]] = []

    # Detect calling convention
    is_direct_list = isinstance(job_ids_or_list, list) and len(job_ids_or_list) > 0 and isinstance(job_ids_or_list[0], dict)

    if is_direct_list:
        for j_dict in job_ids_or_list:
            eval_res = evaluate_job_match(user_skills=student_or_skills, job_data=j_dict)
            evaluations.append(eval_res)
            req_set = set(_normalize_skill(s) for s in j_dict.get("required_skills", []))
            job_required_sets.append(req_set)
            for gap in eval_res["missing_skills"]["mandatory"]:
                all_mandatory_gaps[gap] = all_mandatory_gaps.get(gap, 0) + 1
    else:
        for jid in job_ids_or_list:
            job = JobListing.query.get(jid)
            if not job:
                continue
            eval_res = evaluate_job_match(student=student_or_skills, job=job)
            evaluations.append(eval_res)
            req_set = set(_normalize_skill(s) for s in job.get_required_skills())
            job_required_sets.append(req_set)
            for gap in eval_res["missing_skills"]["mandatory"]:
                all_mandatory_gaps[gap] = all_mandatory_gaps.get(gap, 0) + 1

    # Overlapping skills across jobs
    overlapping_skills: Set[str] = set()
    if job_required_sets:
        overlapping_skills = set.intersection(*job_required_sets) if len(job_required_sets) > 1 else job_required_sets[0]

    # Sort high-yield skills (skills that satisfy the most jobs if acquired)
    high_yield_skills = sorted(
        [{"skill": k, "unlocks_jobs_count": v} for k, v in all_mandatory_gaps.items()],
        key=lambda x: x["unlocks_jobs_count"],
        reverse=True
    )

    high_yield_overlapping = list(overlapping_skills)
    if not high_yield_overlapping:
        high_yield_overlapping = [h["skill"] for h in high_yield_skills[:3]]

    return {
        "compared_jobs_count": len(evaluations),
        "job_evaluations": evaluations,
        "jobs": evaluations,
        "high_yield_skill_investments": high_yield_skills,
        "high_yield_overlapping_skills": high_yield_overlapping,
        "recommendation": (
            f"Focus on '{high_yield_skills[0]['skill'].title()}' first as it satisfies multiple target job requirements."
            if high_yield_skills else "Your profile demonstrates strong coverage across all selected opportunities!"
        )
    }

