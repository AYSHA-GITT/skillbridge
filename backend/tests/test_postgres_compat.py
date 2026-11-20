"""
Phase 1 regressions: problems that only appeared on PostgreSQL (production) or in a
clean install, never on the SQLite development database.

Run on SQLite (default; foreign keys are enforced by tests/base.py) and on PostgreSQL:
    SKILLBRIDGE_TEST_DATABASE_URL=postgresql://user:pw@host:port/skillbridge_test \
        python -m unittest tests.test_postgres_compat
"""
from tests.base import app, db, reset_db, make_student, login, IS_POSTGRES  # must be first

import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone

import numpy as np

from models import (PassportEvidence, PassportShare, Progress, Resume, Skill, SkillGap, SkillVerification,
                    StudyPlan, Student)

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class AccountDeletionTests(unittest.TestCase):
    """Bug: on PostgreSQL, deleting an account that had uploaded a resume failed with
    skills_resume_id_fkey (resumes deleted before their extracted skills), and with
    skill_verifications_skill_id_fkey (skills deleted before their quiz attempts)."""

    def setUp(self):
        reset_db()
        self.sid = make_student("delete.me@test.com", target_career="data analyst")
        self.keep = make_student("keep.me@test.com")
        with app.app_context():
            # a realistic account: resume -> extracted skills -> quiz attempts, evidence, plan
            for owner in (self.sid, self.keep):
                r = Resume(student_id=owner, file_path="uploads/resumes/does-not-exist-test.pdf",
                           original_filename="cv.pdf", parsed_text="Python SQL")
                db.session.add(r)
                db.session.flush()
                py = Skill(student_id=owner, resume_id=r.id, skill_name="python", source="resume")
                sql = Skill(student_id=owner, resume_id=r.id, skill_name="sql", source="resume")
                db.session.add_all([py, sql])
                db.session.flush()
                db.session.add_all([
                    SkillVerification(student_id=owner, skill_id=py.id, quiz_question_count=5, quiz_correct_count=4,
                                      quiz_score_percent=80.0, verification_score=0.8),
                    SkillVerification(student_id=owner, skill_id=sql.id, quiz_question_count=5, quiz_correct_count=2,
                                      quiz_score_percent=40.0, verification_score=0.4),
                    PassportEvidence(student_id=owner, kind="project", title="Dashboard", skills=[py, sql]),
                    SkillGap(student_id=owner, missing_skill="statistics", importance="High", category="Required"),
                    StudyPlan(student_id=owner, skill_name="statistics", day_number=1, topic="Basics"),
                    Progress(student_id=owner, readiness_score=40.0, skill_count=2, verified_skill_count=1,
                             skill_gap_count=1),
                ])
            db.session.commit()

    def test_account_with_resume_skills_and_attempts_can_be_deleted(self):
        c = app.test_client()
        login(c, "delete.me@test.com")
        res = c.delete("/api/student/account/delete", json={"confirmation": "DELETE_MY_ACCOUNT"})
        self.assertEqual(res.status_code, 200, res.get_json())
        with app.app_context():
            self.assertIsNone(db.session.get(Student, self.sid))
            for model in (Resume, Skill, SkillVerification, PassportEvidence, SkillGap, StudyPlan, Progress):
                self.assertEqual(model.query.filter_by(student_id=self.sid).count(), 0, model.__name__)
            # the other student's data is untouched
            self.assertEqual(Skill.query.filter_by(student_id=self.keep).count(), 2)
            self.assertEqual(SkillVerification.query.filter_by(student_id=self.keep).count(), 2)
            self.assertEqual(Resume.query.filter_by(student_id=self.keep).count(), 1)
        self.assertEqual(c.post("/api/auth/login", json={"email": "delete.me@test.com",
                                                         "password": "password123"}).status_code, 401)

    def test_removing_a_resume_alone_keeps_its_skills(self):
        """The new relationship adds no cascade: a resume deleted on its own leaves the
        skills (and their assessment history) in place, unlinked."""
        with app.app_context():
            r = Resume.query.filter_by(student_id=self.keep).first()
            db.session.delete(r)
            db.session.commit()
            skills = Skill.query.filter_by(student_id=self.keep).all()
            self.assertEqual(len(skills), 2)
            self.assertTrue(all(s.resume_id is None for s in skills))
            self.assertEqual(SkillVerification.query.filter_by(student_id=self.keep).count(), 2)


class ReadinessNumpyTests(unittest.TestCase):
    """Bug: the readiness score came out as numpy.float64 whenever the student had quiz
    attempts; PostgreSQL rejected it with 'schema "np" does not exist'."""

    def setUp(self):
        reset_db()
        self.sid = make_student("ready@test.com", target_career="data analyst")
        with app.app_context():
            sk = Skill(student_id=self.sid, skill_name="sql", source="resume")
            db.session.add(sk)
            db.session.flush()
            db.session.add(SkillVerification(student_id=self.sid, skill_id=sk.id, quiz_question_count=5,
                                             quiz_correct_count=4, quiz_score_percent=80.0, verification_score=0.8))
            db.session.commit()

    def test_model_returns_plain_python_floats(self):
        from ml.readiness_model import readiness_scorer
        out = readiness_scorer.calculate_readiness(
            {"required_coverage": np.float64(0.5), "nice_to_have_coverage": np.float64(0.25)},
            [{"quiz_score_percent": 80.0}, {"quiz_score_percent": 60.0}])
        self.assertIs(type(out["readiness_score"]), float)
        for v in out["breakdown"].values():
            self.assertIs(type(v), float)

    def test_readiness_breakdown_endpoint_stores_the_score(self):
        c = app.test_client()
        login(c, "ready@test.com")
        res = c.get("/api/student/readiness_breakdown")
        self.assertEqual(res.status_code, 200, res.get_json())
        score = res.get_json()["readiness"]["readiness_score"]
        with app.app_context():
            stored = db.session.get(Student, self.sid).readiness_score
            self.assertAlmostEqual(stored, score)
            self.assertGreater(Progress.query.filter_by(student_id=self.sid).count(), 0)

    def test_numpy_values_are_stored_as_numbers(self):
        """Safety net for any other NumPy value reaching the database."""
        with app.app_context():
            st = db.session.get(Student, self.sid)
            st.readiness_score = np.float64(61.5)
            db.session.add(Progress(student_id=self.sid, readiness_score=np.float32(12.5),
                                    skill_count=np.int64(3), verified_skill_count=np.int32(1),
                                    skill_gap_count=np.int64(0)))
            db.session.commit()
            db.session.expire_all()
            self.assertEqual(db.session.get(Student, self.sid).readiness_score, 61.5)
            p = Progress.query.filter_by(student_id=self.sid).order_by(Progress.id.desc()).first()
            self.assertEqual((p.readiness_score, p.skill_count, p.verified_skill_count), (12.5, 3, 1))


@unittest.skipUnless(IS_POSTGRES, "PostgreSQL session time zone")
class PostgresTimeZoneTests(unittest.TestCase):
    """Bug: with a PostgreSQL server in a non-UTC time zone, stored UTC times shifted by
    the zone offset, so expired password-reset tokens and share links stayed valid."""

    def setUp(self):
        reset_db()

    def test_session_time_zone_is_utc(self):
        with app.app_context():
            self.assertEqual(db.session.execute(db.text("SHOW timezone")).scalar(), "UTC")

    def test_aware_utc_datetimes_round_trip_unchanged(self):
        sid = make_student("tz@test.com")
        when = datetime(2026, 1, 15, 10, 30, tzinfo=timezone.utc)
        with app.app_context():
            share = PassportShare(student_id=sid, token_hash="x" * 64, label="tz",
                                  visibility="{}", consent_at=when, expires_at=when)
            db.session.add(share)
            db.session.commit()
            db.session.expire_all()
            stored = db.session.get(PassportShare, share.id).expires_at
            self.assertEqual(stored.replace(tzinfo=None), when.replace(tzinfo=None))


class StartupWithoutGeminiKeyTests(unittest.TestCase):
    """Bug: with GEMINI_API_KEY unset the app could not even start, because one module
    created its Gemini client at import time."""

    def _run(self, code, extra_env):
        tmp = tempfile.mkdtemp(prefix="nokey_")
        env = {**os.environ, "DATABASE_URL": "sqlite:///" + os.path.join(tmp, "x.db").replace("\\", "/"),
               "SECRET_KEY": "test", "RUN_JOB_SCHEDULER_IN_PROCESS": "0", "JOB_PROVIDERS": "",
               "SKILLBRIDGE_TEST_DATABASE_URL": "", **extra_env}
        return subprocess.run([sys.executable, "-c", code], cwd=BACKEND_DIR, env=env,
                              capture_output=True, text=True, timeout=300)

    def test_app_starts_and_uses_the_fallback_without_a_key(self):
        r = self._run("import app\n"
                      "from utils.career_requirements_generator import generate_career_requirements as g\n"
                      "print('RESULT', g('marine biologist')['required'][0])", {"GEMINI_API_KEY": ""})
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])
        self.assertIn("RESULT python", r.stdout)
        self.assertIn("not configured", r.stderr)

    def test_a_configured_key_is_never_printed(self):
        secret = "AIzaSy-phase1-regression-secret-0000"
        r = self._run("import app\n"
                      "from utils.career_requirements_generator import generate_career_requirements as g\n"
                      "g('marine biologist')",
                      {"GEMINI_API_KEY": secret, "GOOGLE_GEMINI_BASE_URL": "http://127.0.0.1:9"})
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])
        self.assertNotIn(secret, r.stdout + r.stderr)


class DependencyPinTests(unittest.TestCase):
    """Bug: backend/requirements.txt pinned SQLAlchemy 2.0.35 while flwr 1.32.1 needs
    >= 2.0.45, so a clean install (Docker, Render, CI) failed."""

    def test_pinned_versions_satisfy_each_others_requirements(self):
        from importlib.metadata import PackageNotFoundError, requires
        from packaging.requirements import Requirement
        from packaging.utils import canonicalize_name
        pins = {}
        with open(os.path.join(BACKEND_DIR, "requirements.txt"), encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines:
            line = line.split("#", 1)[0].strip()
            if "==" in line:
                name, ver = line.split("==", 1)
                pins[canonicalize_name(name)] = ver.strip()
        problems = []
        for pkg in pins:
            try:
                reqs = requires(pkg) or []
            except PackageNotFoundError:
                continue
            for raw in reqs:
                req = Requirement(raw)
                if req.marker and not req.marker.evaluate({"extra": ""}):
                    continue
                dep = canonicalize_name(req.name)
                if dep in pins and not req.specifier.contains(pins[dep], prereleases=True):
                    problems.append(f"{pkg} requires {raw} but requirements.txt pins {dep}=={pins[dep]}")
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
