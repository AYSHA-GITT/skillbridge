import numpy as np


class ReadinessScorer:
    """
    Computes a transparent, multi-dimensional Career Readiness score
    based on verified skills, assessment quiz scores, and career benchmarks.
    """

    @staticmethod
    def calculate_readiness(gap_analysis, verifications):
        """
        gap_analysis: dict from skill_gap_model or student.py
        verifications: list of SkillVerification instances or dicts
        """
        req_cov = gap_analysis.get('required_coverage', 0.0)
        nth_cov = gap_analysis.get('nice_to_have_coverage', 0.0)

        # Average verification quiz score
        if verifications:
            scores = [
                v.quiz_score_percent if hasattr(v, 'quiz_score_percent') else v.get('quiz_score_percent', 0.0)
                for v in verifications
            ]
            avg_quiz_score = np.mean(scores) / 100.0 if scores else 0.0
        else:
            avg_quiz_score = 0.0

        # Weighted calculation:
        # 50% Required Skill Presence
        # 30% Verified Quiz Competency
        # 20% Nice-to-Have Bonus
        readiness = (req_cov * 0.50) + (avg_quiz_score * 0.30) + (nth_cov * 0.20)
        readiness_pct = min(100.0, max(0.0, round(readiness * 100.0, 1)))

        # Tier calculation
        if readiness_pct >= 85:
            tier = 'Interview Ready'
            badge_color = 'teal'
        elif readiness_pct >= 65:
            tier = 'Proficient Candidate'
            badge_color = 'blue'
        elif readiness_pct >= 40:
            tier = 'Foundational Learner'
            badge_color = 'yellow'
        else:
            tier = 'Early Explorer'
            badge_color = 'gray'

        # Actionable recommendations
        recommendations = []
        missing_req = gap_analysis.get('missing_required', [])
        if missing_req:
            recommendations.append(f"Focus on top missing core skills: {', '.join(missing_req[:3])}.")
        if avg_quiz_score < 0.7 and verifications:
            recommendations.append("Review foundational concepts to increase quiz verification scores above 70%.")
        if not missing_req and gap_analysis.get('missing_nice_to_have'):
            recommendations.append("Strengthen competitive edge with nice-to-have tools like Docker or Cloud.")

        return {
            'readiness_score': readiness_pct,
            'tier': tier,
            'badge_color': badge_color,
            'breakdown': {
                'required_skills_pct': round(req_cov * 100, 1),
                'quiz_proficiency_pct': round(avg_quiz_score * 100, 1),
                'nice_to_have_pct': round(nth_cov * 100, 1)
            },
            'recommendations': recommendations
        }


readiness_scorer = ReadinessScorer()
