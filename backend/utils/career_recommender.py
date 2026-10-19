from data.career_requirements import CAREER_REQUIREMENTS
from utils.skill_gap_analyzer import get_career_requirements
from ml.salary_model import salary_predictor


def evaluate_career_match(verified_skills, career_name):
    """
    Computes deterministic match percentage, gap analysis, and explainability
    for a specific career against a student's verified skills.
    """
    reqs = get_career_requirements(career_name)
    if not reqs:
        return None

    user_skills = set(s.lower().strip() for s in verified_skills)
    required = reqs.get("required", [])
    nice_to_have = reqs.get("nice_to_have", [])

    matched_required = [s for s in required if s in user_skills]
    missing_required = [s for s in required if s not in user_skills]

    matched_nice = [s for s in nice_to_have if s in user_skills]
    missing_nice = [s for s in nice_to_have if s not in user_skills]

    total_req = len(required)
    total_nice = len(nice_to_have)

    req_coverage = (len(matched_required) / total_req) if total_req > 0 else 1.0
    nice_coverage = (len(matched_nice) / total_nice) if total_nice > 0 else 1.0

    # 75% weight on core required skills, 25% on optional skills
    overall_coverage = round((req_coverage * 0.75) + (nice_coverage * 0.25), 4)
    match_percentage = round(overall_coverage * 100, 1)

    # Calculate exact readiness improvement if top missing skill is verified
    target_skill_for_boost = None
    readiness_improvement = 0.0
    projected_match = match_percentage

    if missing_required:
        target_skill_for_boost = missing_required[0]
        boosted_req_cov = (len(matched_required) + 1) / total_req if total_req > 0 else 1.0
        boosted_overall = round((boosted_req_cov * 0.75) + (nice_coverage * 0.25), 4)
        projected_match = round(boosted_overall * 100, 1)
        readiness_improvement = round(projected_match - match_percentage, 1)
    elif missing_nice:
        target_skill_for_boost = missing_nice[0]
        boosted_nice_cov = (len(matched_nice) + 1) / total_nice if total_nice > 0 else 1.0
        boosted_overall = round((req_coverage * 0.75) + (boosted_nice_cov * 0.25), 4)
        projected_match = round(boosted_overall * 100, 1)
        readiness_improvement = round(projected_match - match_percentage, 1)

    # Deterministic why_recommended reason
    if match_percentage >= 70:
        recommendation_reason = (
            f"Your verified skills strongly match the core technical requirements for {career_name.title()}."
        )
    elif match_percentage >= 40:
        matched_str = ", ".join(s.title() for s in matched_required[:3]) if matched_required else "foundational knowledge"
        recommendation_reason = (
            f"You possess key foundations in {matched_str}, making this an attainable career track."
        )
    elif matched_required:
        matched_str = ", ".join(s.title() for s in matched_required[:2])
        recommendation_reason = (
            f"You have begun establishing relevant competencies ({matched_str}) for {career_name.title()}."
        )
    else:
        recommendation_reason = (
            f"High-demand industry track. Verifying beginner skills will quickly raise your match."
        )

    # Structured explainability bullet points
    highlights = [
        f"{len(matched_required)}/{total_req} required core skills verified",
    ]
    if matched_required:
        highlights.append(f"Strong foundation in {', '.join(s.title() for s in matched_required[:3])}")
    else:
        highlights.append("No required skills currently verified for this track")

    if missing_required:
        highlights.append(f"Main remaining gap: {missing_required[0].title()}")
    elif missing_nice:
        highlights.append(f"Core satisfied; recommended optional: {missing_nice[0].title()}")
    else:
        highlights.append("All required competencies verified")

    # Salary estimation
    salary_info = salary_predictor.predict_salary(matched_required)
    estimated_days = (len(missing_required) * 7) + (len(missing_nice) * 3)

    return {
        "career": career_name.title(),
        "career_key": career_name.lower().strip(),
        "match_percentage": match_percentage,
        "readiness_score": match_percentage,
        "required_coverage": round(req_coverage * 100, 1),
        "nice_to_have_coverage": round(nice_coverage * 100, 1),
        "matched_required": matched_required,
        "missing_required": missing_required,
        "matched_nice_to_have": matched_nice,
        "missing_nice_to_have": missing_nice,
        "total_required": total_req,
        "total_nice_to_have": total_nice,
        "estimated_days_to_close": estimated_days,
        "estimated_salary_lpa": salary_info.get("estimated_lpa", 6.0),
        "recommendation_reason": recommendation_reason,
        "explanation": {
            "title": f"Why {career_name.title()}?",
            "highlights": highlights,
            "next_target_skill": target_skill_for_boost,
            "expected_readiness_improvement": readiness_improvement,
            "projected_match": projected_match,
            "action_recommendation": (
                f"Learn {target_skill_for_boost.title()} -> Expected readiness improvement: +{readiness_improvement}%"
                if target_skill_for_boost else "All core competencies verified!"
            )
        }
    }


def get_all_career_recommendations(verified_skills, current_target_career=None):
    """
    Evaluates all standard career paths against the student's verified skills
    and returns a ranked list with deterministic scores and explanations.
    """
    careers = list(CAREER_REQUIREMENTS.keys())
    results = []

    for c in careers:
        eval_res = evaluate_career_match(verified_skills, c)
        if eval_res:
            eval_res["is_current_target"] = (
                current_target_career.lower().strip() == c.lower().strip()
                if current_target_career else False
            )
            results.append(eval_res)

    # Sort descending by match_percentage, then by number of matched required skills
    results.sort(
        key=lambda x: (x["match_percentage"], len(x["matched_required"])),
        reverse=True
    )

    # Flag the top recommended career
    if results:
        results[0]["is_top_match"] = True
        for r in results[1:]:
            r["is_top_match"] = False

    return results


def compare_career_tracks(verified_skills, career_names):
    """
    Compares 2 or more careers side-by-side using deterministic metrics.
    """
    comparison = []
    for name in career_names:
        clean_name = name.strip().lower()
        res = evaluate_career_match(verified_skills, clean_name)
        if res:
            comparison.append(res)
    return comparison


def simulate_multi_career_paths(verified_skills, career_names, target_career=None):
    """
    Multi-path simulator comparing two or more paths simultaneously.
    Computes overlapping skills, exclusive gaps, shared preparation priorities,
    and transition feasibility without guessing market stats.
    """
    evaluations = compare_career_tracks(verified_skills, career_names)
    if not evaluations:
        return {
            "paths": [],
            "shared_skills": [],
            "preparation_priorities": [],
            "transition_feasibility": {}
        }

    # Extract all required skills per path
    path_reqs = {}
    for e in evaluations:
        c_name = e.get("career") or e.get("career_name") or e.get("career_key", "unknown")
        path_reqs[c_name] = set(e.get("matched_required", []) + e.get("missing_required", []))

    # Intersect to find shared core requirements
    if path_reqs:
        shared_skills = list(set.intersection(*path_reqs.values())) if len(path_reqs) > 1 else list(list(path_reqs.values())[0])
    else:
        shared_skills = []

    # Calculate preparation priorities (skills that help the most paths simultaneously)
    all_missing_counts = {}
    for e in evaluations:
        for m in e.get("missing_required", []):
            all_missing_counts[m] = all_missing_counts.get(m, 0) + 1

    shared_priorities = sorted(
        [{"skill": k, "impact_across_paths": v} for k, v in all_missing_counts.items()],
        key=lambda x: x["impact_across_paths"],
        reverse=True
    )

    # Transition steps between paths
    transitions = []
    if len(evaluations) >= 2:
        for i in range(len(evaluations)):
            for j in range(i + 1, len(evaluations)):
                c1 = evaluations[i].get("career") or evaluations[i].get("career_name", "Path A")
                c2 = evaluations[j].get("career") or evaluations[j].get("career_name", "Path B")
                diff = list(path_reqs.get(c2, set()).difference(path_reqs.get(c1, set())))
                feasibility = max(10, 100 - len(diff) * 15)
                days_needed = len(diff) * 7
                transitions.append({
                    "from_career": c1.title(),
                    "to_career": c2.title(),
                    "from_path": c1.title(),
                    "to_path": c2.title(),
                    "feasibility_score": feasibility,
                    "additional_days_needed": days_needed,
                    "bridge_skills": diff[:4],
                    "additional_skills_needed": diff[:4],
                    "effort_rating": "Low" if len(diff) <= 2 else ("Moderate" if len(diff) <= 4 else "High"),
                    "guidance": f"Moving from {c1.title()} to {c2.title()} requires picking up {len(diff)} distinct technical competencies."
                })

    recommended_sequence = (
        f"Master the shared core skills ({', '.join(shared_skills[:3]) if shared_skills else 'core foundations'}) "
        f"first to establish maximum leverage across your target paths."
    )

    return {
        "paths": evaluations,
        "shared_core_foundation": shared_skills,
        "shared_required_competencies": shared_skills,
        "shared_skills": shared_skills,
        "high_yield_preparation_priorities": shared_priorities[:5],
        "transition_steps": transitions,
        "transitions": transitions,
        "recommended_sequence": recommended_sequence,
        "disclaimer": "Simulations are derived from standard curriculum requirements and current verified competency states."
    }


