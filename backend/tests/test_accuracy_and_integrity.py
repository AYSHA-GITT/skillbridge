"""
Accuracy & integrity tests: resume skill extraction, quiz verification rules,
salary-estimate labelling/evaluation, federated-learning honesty, embedding
determinism and migrations on a fresh database.
"""
from tests.base import app, db, reset_db, make_student, login  # must be first

import os
import subprocess
import sys
import tempfile
import unittest

from models import Skill, QuestionBank, SkillVerification, FLTrainingRound
from utils.skill_extractor import extract_skills, split_into_sections
from utils.skill_taxonomy import extract_skill_names, normalize_skill_name


def names(text):
    return [s["skill_name"] for s in extract_skills(text)]


class SkillExtractionTests(unittest.TestCase):
    def test_no_substring_false_positives(self):
        # Old extractor returned java, c and r for this resume
        self.assertEqual(names("SKILLS\nJavaScript, React\nPROJECTS\nBuilt a weather dashboard."),
                         ["javascript", "react"])
        self.assertEqual(extract_skill_names("Completed PG-DAC at C-DAC Bangalore. Grade: B"), [])
        self.assertEqual(extract_skill_names("John C. Smith, rest of the team"), [])
        self.assertEqual(extract_skill_names("Spring 2024 semester"), [])

    def test_ambiguous_names_from_list_context(self):
        self.assertEqual(extract_skill_names("Languages: C, C++, Python | R"), ["c", "c++", "python", "r"])
        self.assertIn("go", extract_skill_names("Backend services written in Golang"))

    def test_career_skills_are_recognised(self):
        found = extract_skill_names("Dashboards in Power BI and Tableau, statistical analysis, AWS, k8s, "
                                    "CI/CD via GitHub Actions, DSA")
        for s in ("power bi", "tableau", "statistics", "aws", "kubernetes", "ci/cd", "data structures"):
            self.assertIn(s, found)

    def test_alias_normalization_and_no_duplicates(self):
        self.assertEqual(normalize_skill_name("ReactJS"), "react")
        self.assertEqual(normalize_skill_name("Postgres"), "postgresql")
        self.assertEqual(names("SKILLS\nReact, ReactJS, React.js"), ["react"])

    def test_evidence_strength_and_explanations(self):
        resume = ("PROFILE\nAspiring engineer.\n"
                  "TECHNICAL SKILLS\nPython, Docker, Tableau\n"
                  "PROJECTS\nBuilt a REST API in Python with Flask and deployed it.\n"
                  "CERTIFICATIONS\nAWS Cloud Practitioner\n")
        by = {s["skill_name"]: s for s in extract_skills(resume)}
        self.assertEqual(by["python"]["evidence_strength"], "applied")
        self.assertEqual(by["flask"]["evidence_strength"], "applied")
        self.assertEqual(by["docker"]["evidence_strength"], "listed_only")
        self.assertEqual(by["aws"]["evidence_strength"], "supporting")
        self.assertTrue(by["python"]["evidence"])
        self.assertIn("projects", by["python"]["explanation"])
        self.assertEqual(by["python"]["extraction_confidence"], 1.0)

    def test_section_headers(self):
        secs = split_into_sections("Work Experience\nIntern at X\nAcademic Projects:\nChatbot\nSkills: Python")
        self.assertIn("experience", secs)
        self.assertIn("projects", secs)
        self.assertIn("Python", secs["skills"])


class QuizIntegrityTests(unittest.TestCase):
    def setUp(self):
        reset_db()
        self.sid = make_student("quiz@x.edu")
        with app.app_context():
            self.skill_id = self._skill("python", "applied")
            self.other_skill_id = self._skill("sql", "applied")
            for i in range(6):
                db.session.add(QuestionBank(skill_name="python", question=f"Py Q{i}", option_a="a", option_b="b",
                                            option_c="c", option_d="d", correct_answer="A",
                                            difficulty=["Easy", "Medium", "Hard"][i % 3]))
            db.session.add(QuestionBank(skill_name="sql", question="SQL Q", option_a="a", option_b="b",
                                        option_c="c", option_d="d", correct_answer="B", difficulty="Easy"))
            db.session.commit()
            self.py_ids = [q.id for q in QuestionBank.query.filter_by(skill_name="python").all()]
            self.sql_id = QuestionBank.query.filter_by(skill_name="sql").first().id
        self.client = app.test_client()
        login(self.client, "quiz@x.edu")

    def _skill(self, name, evidence):
        s = Skill(student_id=self.sid, skill_name=name, extraction_confidence=1.0, evidence_strength=evidence)
        db.session.add(s)
        db.session.commit()
        return s.id

    def test_cannot_use_other_skills_questions(self):
        answers = {str(i): "A" for i in self.py_ids[:4]}
        answers[str(self.sql_id)] = "B"
        res = self.client.post(f"/api/student/submit_quiz/{self.skill_id}", json={"answers": answers})
        self.assertEqual(res.status_code, 400)

    def test_partial_quiz_rejected(self):
        res = self.client.post(f"/api/student/submit_quiz/{self.skill_id}", json={"answers": {str(self.py_ids[0]): "A"}})
        self.assertEqual(res.status_code, 400)
        self.assertIn("answer all", res.get_json()["error"])

    def test_full_quiz_scored_with_review(self):
        answers = {str(i): ("A" if n < 4 else "C") for n, i in enumerate(self.py_ids[:5])}
        res = self.client.post(f"/api/student/submit_quiz/{self.skill_id}", json={"answers": answers})
        self.assertEqual(res.status_code, 201, res.get_json())
        body = res.get_json()
        self.assertEqual((body["correct_count"], body["total_questions"]), (4, 5))
        self.assertEqual(len([r for r in body["review"] if not r["is_correct"]]), 1)
        self.assertEqual(body["proficiency"], "Intermediate")
        # quiz (75%) dominates; evidence 'applied' contributes 25%
        self.assertAlmostEqual(body["verification_score"], round(0.25 * 1.0 + 0.75 * 0.8, 2))

    def test_quiz_mixes_difficulty(self):
        with app.app_context():
            QuestionBank.query.filter_by(skill_name="python").count()
        from unittest import mock
        with mock.patch("routes.student.ensure_minimum_questions", lambda *_: None):
            data = self.client.get(f"/api/student/get_quiz/{self.skill_id}").get_json()
        levels = {q["difficulty"] for q in data["questions"]}
        self.assertEqual(levels, {"Easy", "Medium", "Hard"})
        self.assertNotIn("correct_answer", data["questions"][0])


class SalaryHonestyTests(unittest.TestCase):
    def test_prediction_is_labelled_estimate(self):
        from ml.salary_model import salary_predictor
        res = salary_predictor.predict_salary(["python", "sql", "flask"], 0)
        self.assertTrue(res["is_estimate"])
        self.assertEqual(res["currency_code"], "INR")
        self.assertEqual(res["salary_period"], "year")
        self.assertIn("Illustrative", res["disclaimer"])
        self.assertTrue(salary_predictor.predict_salary(["python"] * 1, 10)["extrapolated"])

    def test_evaluation_compares_against_baseline(self):
        from ml.salary_model import SalaryPredictor
        ev = SalaryPredictor().evaluation(n_splits=3, n_repeats=2)
        self.assertEqual(ev["data_audit"]["rows"], 24)
        self.assertIn("baseline_mean", ev["cv_results"])
        deployed = ev["cv_results"]["ridge_alpha_1 (deployed)"]
        self.assertLess(deployed["mae_lpa"], ev["cv_results"]["baseline_mean"]["mae_lpa"])
        self.assertIn("illustrative", ev["data_audit"]["provenance"].lower())


class FederatedHonestyTests(unittest.TestCase):
    def setUp(self):
        reset_db()

    def test_no_fabricated_accuracy_or_epsilon(self):
        from federated import server
        with app.app_context():
            res = server.run_federated_round()
            self.assertIsNone(res["privacy_guarantee"])
            self.assertIn("no formal", res["privacy_statement"].lower())
            # accuracy is the measured value, reproducible from the stored global model
            X, y = server._test_set()
            self.assertAlmostEqual(res["global_accuracy"], round(server._accuracy(server._load_global(), X, y), 4))
            status = server.get_federated_status()
            self.assertIsNone(status["differential_privacy"]["epsilon"])
            self.assertTrue(status["is_simulation"])
            self.assertTrue(all("Simulated" in n["name"] for n in status["nodes"]))
            history = server.get_federated_history()
            self.assertIsNone(history[-1]["privacy_epsilon"])

    def test_admin_stats_no_default_accuracy(self):
        make_student("adm@x.edu", role="admin")
        c = app.test_client()
        login(c, "adm@x.edu")
        stats = c.get("/api/admin/stats").get_json()
        self.assertIsNone(stats["federated_learning"]["current_global_accuracy"])


class EmbeddingTests(unittest.TestCase):
    def test_fallback_embedding_is_stable_across_processes(self):
        code = ("import sys; sys.path.insert(0, r'%s'); from rag.embedding_engine import EmbeddingEngine;"
                "e=EmbeddingEngine(); print(list(e._fallback_encode(['python flask sql'])[0].nonzero()[0]))") % \
               os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        outs = {subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                               env={**os.environ, "PYTHONHASHSEED": str(seed)}).stdout for seed in (1, 2)}
        self.assertEqual(len(outs), 1, outs)


class RagRetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        from utils.rag_engine import LocalVectorStore
        cls.store = LocalVectorStore()
        cls.store.add_document("pub_da", "Data Analyst Guide", "career_guide",
                               "Data analysts query databases with SQL, build Power BI dashboards and report "
                               "business trends to managers.")
        cls.store.add_document("u1_resume", "User 1 resume", "user_profile",
                               "Private resume of user one: Python, Flask, internship at Acme.", user_id=1)

    def test_tenant_isolation(self):
        other = [r["document_id"] for r in self.store.search("Python Flask internship resume", requesting_user_id=2)]
        own = [r["document_id"] for r in self.store.search("Python Flask internship resume", requesting_user_id=1)]
        self.assertNotIn("u1_resume", other)
        self.assertIn("u1_resume", own)

    def test_off_topic_query_retrieves_nothing(self):
        if self.store.embedder.name != "minilm":
            self.skipTest("MiniLM model not available offline")
        self.assertEqual(self.store.search("best recipe for chocolate cake", requesting_user_id=None), [])
        self.assertTrue(self.store.search("I like making charts about sales for my manager", requesting_user_id=None))

    def test_retrieval_quality_regression(self):
        try:
            from rag.eval_retrieval import load_docs, build_methods, evaluate
            import json as _json
            methods = build_methods(load_docs())
        except Exception as e:
            self.skipTest(f"evaluation dependencies unavailable: {e}")
        if "minilm" not in methods:
            self.skipTest("MiniLM model not available offline")
        queries = _json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                               "rag", "eval_queries.json"), encoding="utf-8"))["queries"]
        res = evaluate(methods["minilm"], queries)["all"]
        self.assertGreaterEqual(res["recall@1"], 0.80)
        self.assertGreaterEqual(res["mrr"], 0.90)


class MigrationTests(unittest.TestCase):
    def test_upgrade_fresh_database_twice(self):
        backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(tempfile.mkdtemp(), "fresh.db").replace("\\", "/")
        env = {**os.environ, "DATABASE_URL": f"sqlite:///{db_path}", "FLASK_APP": "app.py"}
        for _ in range(2):
            r = subprocess.run([sys.executable, "-m", "flask", "db", "upgrade"], cwd=backend, env=env,
                               capture_output=True, text=True, timeout=300)
            self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        import sqlite3
        con = sqlite3.connect(db_path)
        self.assertEqual(con.execute("select version_num from alembic_version").fetchone()[0], "c9f1e2a7b3d4")
        cols = {r[1] for r in con.execute("pragma table_info(job_listings)")}
        self.assertTrue({"canonical_url", "status", "last_verified_at", "salary_is_estimated"} <= cols)


if __name__ == "__main__":
    unittest.main()
