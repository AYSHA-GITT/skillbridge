import os
import pandas as pd
import numpy as np


class SkillGapMLModel:
    def __init__(self, data_path=None):
        if data_path is None:
            data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'job_skills.csv')
        self.data_path = data_path
        self.df = None
        self.load_data()

    def load_data(self):
        try:
            if os.path.exists(self.data_path) and os.path.getsize(self.data_path) > 0:
                self.df = pd.read_csv(self.data_path)
            else:
                self.df = pd.DataFrame(columns=['career', 'skill', 'importance', 'category', 'demand_weight'])
        except Exception:
            self.df = pd.DataFrame(columns=['career', 'skill', 'importance', 'category', 'demand_weight'])

    def evaluate_gaps(self, verified_skills, target_career):
        """
        Evaluates missing skills, priority rankings, and estimated completion time.
        """
        target = target_career.lower().strip()
        user_skills = set(s.lower().strip() for s in verified_skills)

        if self.df is not None and not self.df.empty:
            career_rows = self.df[self.df['career'].str.lower() == target]
        else:
            career_rows = pd.DataFrame()

        if career_rows.empty:
            # Fallback to general career requirements if not in csv
            from data.career_requirements import CAREER_REQUIREMENTS
            reqs = CAREER_REQUIREMENTS.get(target, {
                'required': ['python', 'sql', 'git'],
                'nice_to_have': ['docker', 'react']
            })
            matched_req = [s for s in reqs['required'] if s in user_skills]
            missing_req = [s for s in reqs['required'] if s not in user_skills]
            matched_nth = [s for s in reqs['nice_to_have'] if s in user_skills]
            missing_nth = [s for s in reqs['nice_to_have'] if s not in user_skills]

            total_req = len(reqs['required'])
            req_cov = len(matched_req) / total_req if total_req else 1.0
            nth_cov = len(matched_nth) / len(reqs['nice_to_have']) if reqs['nice_to_have'] else 1.0
            overall = round((req_cov * 0.7) + (nth_cov * 0.3), 2)

            return {
                'career': target,
                'overall_coverage': overall,
                'required_coverage': round(req_cov, 2),
                'nice_to_have_coverage': round(nth_cov, 2),
                'matched_required': matched_req,
                'missing_required': missing_req,
                'matched_nice_to_have': matched_nth,
                'missing_nice_to_have': missing_nth,
                'estimated_days_to_close': (len(missing_req) * 7) + (len(missing_nth) * 3)
            }

        required_df = career_rows[career_rows['importance'].str.lower() == 'high']
        nice_df = career_rows[career_rows['importance'].str.lower() != 'high']

        all_req = set(required_df['skill'].str.lower().tolist())
        all_nice = set(nice_df['skill'].str.lower().tolist())

        matched_req = list(all_req.intersection(user_skills))
        missing_req = list(all_req.difference(user_skills))
        matched_nice = list(all_nice.intersection(user_skills))
        missing_nice = list(all_nice.difference(user_skills))

        # Weight-adjusted score
        total_req_weight = required_df['demand_weight'].sum() if not required_df.empty else 1.0
        matched_req_weight = required_df[required_df['skill'].str.lower().isin(user_skills)]['demand_weight'].sum()
        req_coverage = (matched_req_weight / total_req_weight) if total_req_weight > 0 else 1.0

        total_nice_weight = nice_df['demand_weight'].sum() if not nice_df.empty else 1.0
        matched_nice_weight = nice_df[nice_df['skill'].str.lower().isin(user_skills)]['demand_weight'].sum()
        nice_coverage = (matched_nice_weight / total_nice_weight) if total_nice_weight > 0 else 1.0

        overall_cov = round((req_coverage * 0.75) + (nice_coverage * 0.25), 2)
        estimated_days = (len(missing_req) * 7) + (len(missing_nice) * 3)

        return {
            'career': target,
            'overall_coverage': min(1.0, overall_cov),
            'required_coverage': round(req_coverage, 2),
            'nice_to_have_coverage': round(nice_coverage, 2),
            'matched_required': matched_req,
            'missing_required': missing_req,
            'matched_nice_to_have': matched_nice,
            'missing_nice_to_have': missing_nice,
            'estimated_days_to_close': estimated_days
        }


skill_gap_model = SkillGapMLModel()
