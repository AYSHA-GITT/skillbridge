"""
Skill-gap evaluation for readiness and career insights.

Single source of truth: data/career_requirements.py (the same definitions used
by gap analysis, roadmaps and the resume optimizer). The previous version read
a separate job_skills.csv whose skill lists differed and whose "demand
weights" had no documented source.

Weighting: when at least MIN_POSTINGS current postings exist for the career,
each skill is weighted by its MEASURED share of those postings (floor 0.1, so
assumed basics such as Git still count). Otherwise all skills weigh equally.
The response states which weighting was used and the evidence per skill.
"""
from utils.market_demand import career_demand, skill_demand_notes

WEIGHT_FLOOR = 0.1


class SkillGapMLModel:
    def evaluate_gaps(self, verified_skills, target_career):
        from utils.skill_gap_analyzer import get_career_requirements

        target = (target_career or "").lower().strip()
        user_skills = set(s.lower().strip() for s in verified_skills)
        reqs = get_career_requirements(target) or {"required": [], "nice_to_have": []}
        required = [s.lower() for s in reqs.get("required", [])]
        nice = [s.lower() for s in reqs.get("nice_to_have", [])]

        demand = career_demand(target)
        if demand and demand["usable_for_weighting"]:
            share = demand["skill_share"]
            weight = {s: max(WEIGHT_FLOOR, share.get(s, 0.0)) for s in required + nice}
            weighting = (f"Weighted by measured demand in {demand['postings']} current postings "
                         f"(computed {demand['computed_at'][:10]})")
        else:
            weight = {s: 1.0 for s in required + nice}
            weighting = "Equal weights (fewer than 20 current postings for this career)"

        def coverage(skills):
            total = sum(weight[s] for s in skills)
            got = sum(weight[s] for s in skills if s in user_skills)
            return (got / total) if total else 1.0

        req_cov, nice_cov = coverage(required), coverage(nice)
        missing_req = [s for s in required if s not in user_skills]
        missing_nice = [s for s in nice if s not in user_skills]
        # most in-demand gaps first
        missing_req.sort(key=lambda s: -weight[s])
        missing_nice.sort(key=lambda s: -weight[s])

        return {
            'career': target,
            'overall_coverage': round(min(1.0, req_cov * 0.75 + nice_cov * 0.25), 2),
            'required_coverage': round(req_cov, 2),
            'nice_to_have_coverage': round(nice_cov, 2),
            'matched_required': [s for s in required if s in user_skills],
            'missing_required': missing_req,
            'matched_nice_to_have': [s for s in nice if s in user_skills],
            'missing_nice_to_have': missing_nice,
            'estimated_days_to_close': (len(missing_req) * 7) + (len(missing_nice) * 3),
            'weighting': weighting,
            'skill_evidence': skill_demand_notes(target, required + nice),
            'market_caveat': demand["caveat"] if demand else None,
        }


skill_gap_model = SkillGapMLModel()
