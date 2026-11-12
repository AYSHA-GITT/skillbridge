"""
Salary estimate model.

DATA WARNING: data/salary_data.csv has 24 rows with no documented source;
the values form smooth hand-constructed progressions. Predictions are an
ILLUSTRATIVE estimate of how skills relate to pay in that table - they are not
market salaries and must not be shown as guaranteed or advertised pay.
Real advertised salaries come from job listings (JobListing.salary_*), which
are labelled 'Advertised by employer' vs 'Estimated by provider'.

`evaluation()` reports a reproducible data audit and repeated K-fold
cross-validation (MAE / RMSE / R^2) against a predict-the-mean baseline, so
any future model change can be compared on the same footing.
"""
import os
import pickle
from typing import Any, Dict, cast

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

FEATURES = ['years_experience', 'skill_count', 'has_ml', 'has_cloud', 'has_backend', 'has_db']
TARGET = 'avg_salary_lpa'
RANDOM_STATE = 42
MODEL_VERSION = 'ridge-v1-a1.0'

DATA_DISCLAIMER = ('Illustrative estimate from a small (24-row) reference table of undocumented origin. '
                   'Not a market salary and not a guarantee. Compare with salaries advertised in real job listings.')


class SalaryPredictor:
    def __init__(self):
        self.model = None
        self.model_path = os.path.join(os.path.dirname(__file__), 'models', 'salary.pkl')
        self.data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'salary_data.csv')
        self._initialized = False
        self._evaluation = None

    def _load_data(self) -> pd.DataFrame:
        return pd.read_csv(self.data_path)

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
                df = self._load_data()
                X = np.asarray(df[FEATURES].values, dtype=np.float64)
                y = np.asarray(df[TARGET].values, dtype=np.float64)
                self.model = Ridge(alpha=1.0)
                self.model.fit(cast(Any, X), cast(Any, y))
                with open(self.model_path, 'wb') as f:
                    pickle.dump(self.model, f)
        except Exception:
            self.model = None

    # ── Evaluation ──────────────────────────────────────────────────────
    def evaluation(self, n_splits: int = 5, n_repeats: int = 10) -> Dict[str, Any]:
        """Reproducible data audit + cross-validated model comparison."""
        if self._evaluation is not None:
            return self._evaluation
        from sklearn.dummy import DummyRegressor
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.linear_model import LinearRegression
        from sklearn.model_selection import RepeatedKFold, cross_validate

        df = self._load_data()
        audit = {
            'rows': int(len(df)),
            'duplicate_rows': int(df.duplicated().sum()),
            'missing_values': int(df.isna().sum().sum()),
            'target_min': float(df[TARGET].min()),
            'target_max': float(df[TARGET].max()),
            'target_unit': 'LPA (lakhs INR per year)',
            'careers': sorted(df['career'].unique().tolist()) if 'career' in df else [],
            'out_of_range_rows': int(((df[TARGET] <= 0) | (df[TARGET] > 200)).sum()),
            'provenance': 'Undocumented; values appear hand-constructed. Treat as illustrative only.',
        }
        X = df[FEATURES].astype(float).values
        y = df[TARGET].astype(float).values
        cv = RepeatedKFold(n_splits=n_splits, n_repeats=n_repeats, random_state=RANDOM_STATE)
        candidates = {
            'baseline_mean': DummyRegressor(strategy='mean'),
            'linear_regression': LinearRegression(),
            'ridge_alpha_1 (deployed)': Ridge(alpha=1.0),
            'ridge_alpha_10': Ridge(alpha=10.0),
            'random_forest': RandomForestRegressor(n_estimators=200, max_depth=4, random_state=RANDOM_STATE),
        }
        results = {}
        for name, est in candidates.items():
            scores = cross_validate(est, X, y, cv=cv,
                                    scoring=('neg_mean_absolute_error', 'neg_root_mean_squared_error', 'r2'))
            results[name] = {
                'mae_lpa': round(float(-scores['test_neg_mean_absolute_error'].mean()), 3),
                'rmse_lpa': round(float(-scores['test_neg_root_mean_squared_error'].mean()), 3),
                'r2': round(float(scores['test_r2'].mean()), 3),
                'r2_std': round(float(scores['test_r2'].std()), 3),
            }
        self._evaluation = {
            'model_version': MODEL_VERSION,
            'features': FEATURES,
            'protocol': f'RepeatedKFold(n_splits={n_splits}, n_repeats={n_repeats}, random_state={RANDOM_STATE})',
            'data_audit': audit,
            'cv_results': results,
            'caveat': ('With 24 rows, cross-validation estimates are noisy and only describe fit to this '
                       'table, not accuracy on real salaries. A real salary dataset is required before '
                       'any accuracy claim can be made.'),
        }
        return self._evaluation

    # ── Inference ───────────────────────────────────────────────────────
    def _extract_features(self, skills, years_experience=0):
        skill_set = set(s.lower().strip() for s in skills)
        skill_count = len(skill_set)

        has_ml = 1 if any(s in skill_set for s in ['machine learning', 'deep learning', 'pytorch', 'tensorflow', 'nlp']) else 0
        has_cloud = 1 if any(s in skill_set for s in ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'linux']) else 0
        has_backend = 1 if any(s in skill_set for s in ['flask', 'django', 'fastapi', 'node.js', 'rest api', 'spring boot']) else 0
        has_db = 1 if any(s in skill_set for s in ['sql', 'mysql', 'postgresql', 'mongodb']) else 0

        return [years_experience, skill_count, has_ml, has_cloud, has_backend, has_db]

    def predict_salary(self, verified_skills, years_experience=0):
        """Illustrative LPA estimate from verified skills (see module docstring)."""
        self.train_or_load()
        features = self._extract_features(verified_skills, years_experience)
        if self.model:
            pred = float(self.model.predict([features])[0])
            method = f'Ridge regression ({MODEL_VERSION})'
        else:
            base = 4.0 + (features[1] * 0.7) + (features[2] * 2.0) + (features[3] * 1.5) + (features[4] * 1.0) + (features[5] * 0.8)
            pred = base
            method = 'Fallback heuristic (model unavailable)'

        pred = max(3.5, round(pred, 2))
        # Training data only covers 3-11 skills and 0-3 years: flag extrapolation
        extrapolated = not (3 <= features[1] <= 11) or not (0 <= years_experience <= 3)
        return {
            'estimated_lpa': pred,
            'range_min': round(pred * 0.88, 1),
            'range_max': round(pred * 1.20, 1),
            'currency': 'LPA (₹)',
            'currency_code': 'INR',
            'salary_period': 'year',
            'is_estimate': True,
            'method': method,
            'extrapolated': extrapolated,
            'disclaimer': DATA_DISCLAIMER,
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
            'additional_skills_count': len(additional_skills),
            'is_estimate': True,
            'disclaimer': DATA_DISCLAIMER,
        }


salary_predictor = SalaryPredictor()
