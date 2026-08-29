import os
import pickle
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge


class SalaryPredictor:
    def __init__(self):
        self.model = None
        self.model_path = os.path.join(os.path.dirname(__file__), 'models', 'salary.pkl')
        self.data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'salary_data.csv')
        self._initialized = False

    def train_or_load(self):
        if self._initialized:
            return
        self._initialized = True
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
                return

            if os.path.exists(self.data_path) and os.path.getsize(self.data_path) > 0:
                df = pd.read_csv(self.data_path)
                X = df[['years_experience', 'skill_count', 'has_ml', 'has_cloud', 'has_backend', 'has_db']].values
                y = df['avg_salary_lpa'].values
                self.model = Ridge(alpha=1.0)
                self.model.fit(X, y)
                with open(self.model_path, 'wb') as f:
                    pickle.dump(self.model, f)
        except Exception:
            self.model = None

    def _extract_features(self, skills, years_experience=0):
        skill_set = set(s.lower().strip() for s in skills)
        skill_count = len(skill_set)

        has_ml = 1 if any(s in skill_set for s in ['machine learning', 'deep learning', 'pytorch', 'tensorflow', 'nlp']) else 0
        has_cloud = 1 if any(s in skill_set for s in ['aws', 'docker', 'cloud', 'linux']) else 0
        has_backend = 1 if any(s in skill_set for s in ['flask', 'django', 'node.js', 'rest api']) else 0
        has_db = 1 if any(s in skill_set for s in ['sql', 'mysql', 'postgresql', 'mongodb']) else 0

        return [years_experience, skill_count, has_ml, has_cloud, has_backend, has_db]

    def predict_salary(self, verified_skills, years_experience=0):
        """
        Predicts base LPA based on verified skills.
        """
        self.train_or_load()
        features = self._extract_features(verified_skills, years_experience)
        if self.model:
            pred = float(self.model.predict([features])[0])
        else:
            base = 4.0 + (features[1] * 0.7) + (features[2] * 2.0) + (features[3] * 1.5) + (features[4] * 1.0) + (features[5] * 0.8)
            pred = base

        pred = max(3.5, round(pred, 2))
        return {
            'estimated_lpa': pred,
            'range_min': round(pred * 0.88, 1),
            'range_max': round(pred * 1.20, 1),
            'currency': 'LPA (₹)',
            'skill_count': len(verified_skills)
        }

    def simulate_future_salary(self, current_skills, additional_skills, years_experience=0):
        """
        Simulates the incremental value of acquiring target skills.
        """
        current_res = self.predict_salary(current_skills, years_experience)
        combined_skills = list(set(current_skills + additional_skills))
        projected_res = self.predict_salary(combined_skills, years_experience)

        boost = round(projected_res['estimated_lpa'] - current_res['estimated_lpa'], 2)
        pct_increase = round((boost / current_res['estimated_lpa']) * 100, 1) if current_res['estimated_lpa'] > 0 else 0

        return {
            'current_salary': current_res['estimated_lpa'],
            'projected_salary': projected_res['estimated_lpa'],
            'projected_boost': max(0.0, boost),
            'percentage_increase': max(0.0, pct_increase),
            'additional_skills_count': len(additional_skills)
        }


salary_predictor = SalaryPredictor()
