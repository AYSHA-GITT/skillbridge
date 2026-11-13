"""
Tests added on 2026-11-13 after the audit of the previous day's work:

- scheduler liveness: the two-hour schedule is only useful if a worker, cron
  job or in-process thread is actually driving it; a heartbeat makes that
  visible to admins and students instead of silently going stale
- account deletion removes the student's uploaded resume files (and the CLI
  can prune files orphaned by earlier deletions)
- curated quiz questions: every career-required skill is verifiable without
  an AI provider, has Hard questions, and seeding is idempotent
"""
from tests.base import app, db, reset_db, make_student, login  # must be first

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from models import QuestionBank, Resume, Skill, Student, SchedulerLease
from utils.job_discovery import sync_service as S
from utils.job_discovery import scheduler as SCHED
from utils import question_bank_manager as qbm
from data.curated_questions import CURATED_QUESTIONS
from data.career_requirements import CAREER_REQUIREMENTS

UTC = timezone.utc
T0 = datetime(2026, 11, 13, 8, 0, tzinfo=UTC)


class SchedulerLivenessTests(unittest.TestCase):
    def setUp(self):
        reset_db()
        self.ctx = app.app_context()
        self.ctx.push()

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()

    def test_never_started_is_reported_honestly(self):
        st = S.scheduler_status()
        self.assertFalse(st["alive"])
        self.assertEqual(st["state"], "never_started")
        self.assertFalse(st["healthy"])
        self.assertIn("job_worker.py", st["message"])

    def test_heartbeat_marks_scheduler_alive_then_stale(self):
        with mock.patch.object(S, "_now", lambda: T0):
            S.record_scheduler_heartbeat("worker:test:1")
            st = S.scheduler_status()
        self.assertTrue(st["alive"])
        self.assertEqual(st["state"], "running")
        self.assertEqual(st["worker"], "worker:test:1")
        # 19 minutes later: still within the 20-minute tolerance (covers a */15 cron)
        with mock.patch.object(S, "_now", lambda: T0 + timedelta(minutes=19)):
            self.assertTrue(S.scheduler_status()["alive"])
        # 25 minutes later with no check-in: stopped, and the overdue sync is called out
        with mock.patch.object(S, "_now", lambda: T0 + timedelta(minutes=25)):
            st = S.scheduler_status()
        self.assertFalse(st["alive"])
        self.assertEqual(st["state"], "stopped")
        self.assertFalse(st["healthy"])
        self.assertIn("no scheduler process is running", st["message"].lower())

    def test_overdue_minutes_measured_from_last_run(self):
        from models import JobSyncRun
        db.session.add(JobSyncRun(trigger="scheduled", status="success",
                                  started_at=T0.replace(tzinfo=None), finished_at=T0.replace(tzinfo=None)))
        db.session.commit()
        with mock.patch.object(S, "_now", lambda: T0 + timedelta(hours=5)):
            st = S.scheduler_status()
        self.assertTrue(st["is_due"])
        self.assertEqual(st["overdue_minutes"], 3 * 60)   # due at T0+2h, now T0+5h
        self.assertIn("overdue by 3 h 0 min", st["message"])
        with mock.patch.object(S, "_now", lambda: T0 + timedelta(hours=1)):
            st = S.scheduler_status()
        self.assertFalse(st["is_due"])
        self.assertEqual(st["overdue_minutes"], 0)
        self.assertIn("will not happen automatically", st["message"])

    def test_worker_loop_records_heartbeat_every_iteration(self):
        with mock.patch.object(S, "build_providers", lambda: []):
            SCHED.run_forever(app, owner="worker:loop", max_iterations=2)
        row = db.session.get(SchedulerLease, S.HEARTBEAT_NAME)
        self.assertIsNotNone(row)
        self.assertEqual(row.owner, "worker:loop")
        self.assertTrue(S.scheduler_status()["alive"])

    def test_heartbeat_owner_change_resets_started_at(self):
        with mock.patch.object(S, "_now", lambda: T0):
            S.record_scheduler_heartbeat("worker:a")
        with mock.patch.object(S, "_now", lambda: T0 + timedelta(minutes=5)):
            S.record_scheduler_heartbeat("worker:a")
            self.assertEqual(S.scheduler_status()["worker_started_at"], T0.isoformat())
            S.record_scheduler_heartbeat("worker:b")
            st = S.scheduler_status()
        self.assertEqual(st["worker"], "worker:b")
        self.assertEqual(st["worker_started_at"], (T0 + timedelta(minutes=5)).isoformat())

    def test_cron_sync_if_due_counts_as_heartbeat(self):
        runner = app.test_cli_runner()
        with mock.patch.object(S, "build_providers", lambda: []):
            result = runner.invoke(args=["jobs", "sync-if-due"])
        self.assertEqual(result.exit_code, 0, result.output)
        row = db.session.get(SchedulerLease, S.HEARTBEAT_NAME)
        self.assertTrue(row.owner.startswith("cron:"))

    def test_status_exposed_to_admin_and_students(self):
        make_student("admin@x.edu", role="admin")
        make_student("stu@x.edu")
        client = app.test_client()
        login(client, "admin@x.edu")
        sched = client.get("/api/admin/jobs/overview").get_json()["schedule"]["scheduler"]
        self.assertIn("alive", sched)
        self.assertIn("message", sched)
        client.post("/api/auth/logout")
        login(client, "stu@x.edu")
        qm = client.get("/api/student/jobs/quality_metrics").get_json()
        self.assertIn("scheduler", qm)
        self.assertFalse(qm["scheduler"]["healthy"])


class ResumeFileCleanupTests(unittest.TestCase):
    def setUp(self):
        reset_db()
        self.tmp = tempfile.mkdtemp(prefix="skillbridge_uploads_")
        self._old_folder = app.config.get("UPLOAD_FOLDER")
        app.config["UPLOAD_FOLDER"] = self.tmp
        self.client = app.test_client()

    def tearDown(self):
        app.config["UPLOAD_FOLDER"] = self._old_folder
        with app.app_context():
            db.session.remove()

    def _resume_file(self, name, content=b"%PDF-1.4 test"):
        path = os.path.join(self.tmp, name)
        with open(path, "wb") as f:
            f.write(content)
        return path

    def test_deleting_account_removes_resume_files(self):
        sid = make_student("del@x.edu")
        other = make_student("keep@x.edu")
        mine = self._resume_file("1_mine.pdf")
        theirs = self._resume_file("2_theirs.pdf")
        with app.app_context():
            db.session.add(Resume(student_id=sid, file_path=mine, original_filename="mine.pdf", is_latest=True))
            db.session.add(Resume(student_id=sid, file_path=os.path.join(self.tmp, "1_missing.pdf"),
                                  original_filename="old.pdf", is_latest=False))
            db.session.add(Resume(student_id=other, file_path=theirs, original_filename="theirs.pdf", is_latest=True))
            db.session.commit()
        login(self.client, "del@x.edu")
        res = self.client.delete("/api/student/account/delete", json={"confirmation": "DELETE_MY_ACCOUNT"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["resume_files_removed"], 1)
        self.assertFalse(os.path.exists(mine))
        self.assertTrue(os.path.exists(theirs), "another student's file must not be touched")
        with app.app_context():
            self.assertIsNone(db.session.get(Student, sid))
            self.assertEqual(Resume.query.filter_by(student_id=sid).count(), 0)

    def test_files_outside_uploads_folder_are_never_deleted(self):
        from utils.resume_files import delete_resume_files
        outside = os.path.join(tempfile.mkdtemp(prefix="skillbridge_outside_"), "secret.txt")
        with open(outside, "w") as f:
            f.write("x")
        with app.app_context():
            self.assertEqual(delete_resume_files([outside]), 0)
        self.assertTrue(os.path.exists(outside))

    def test_prune_orphans_cli_dry_run_then_apply(self):
        sid = make_student("owner@x.edu")
        kept = self._resume_file("3_kept.pdf")
        orphan = self._resume_file("9_orphan.docx")
        with app.app_context():
            db.session.add(Resume(student_id=sid, file_path=kept, original_filename="k.pdf", is_latest=True))
            db.session.add(Resume(student_id=sid, file_path=os.path.join(self.tmp, "3_gone.pdf"),
                                  original_filename="gone.pdf", is_latest=False))
            db.session.commit()
        runner = app.test_cli_runner()
        dry = runner.invoke(args=["resumes", "prune-orphans"])
        self.assertEqual(dry.exit_code, 0, dry.output)
        self.assertIn("9_orphan.docx", dry.output)
        self.assertIn("3_gone.pdf", dry.output)        # reported as a DB row whose file is missing
        self.assertTrue(os.path.exists(orphan))      # dry run deletes nothing
        applied = runner.invoke(args=["resumes", "prune-orphans", "--apply"])
        self.assertEqual(applied.exit_code, 0, applied.output)
        self.assertFalse(os.path.exists(orphan))
        self.assertTrue(os.path.exists(kept))


class CuratedQuestionBankTests(unittest.TestCase):
    def setUp(self):
        reset_db()
        self.ctx = app.app_context()
        self.ctx.push()

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()

    def test_every_curated_question_is_valid_and_unique(self):
        from utils.ai_question_generator import normalize_question_text
        seen = set()
        for q in CURATED_QUESTIONS:
            self.assertIsNone(qbm.validate_generated_question(q), q["question"])
            self.assertLessEqual(len(q["question"]), 500)
            for k in "abcd":
                self.assertLessEqual(len(q[f"option_{k}"]), 200)
            key = (q["skill_name"], normalize_question_text(q["question"]))
            self.assertNotIn(key, seen, f"duplicate question: {q['question']}")
            seen.add(key)

    def test_correct_answers_are_not_positionally_biased(self):
        from collections import Counter
        counts = Counter(q["correct_answer"] for q in CURATED_QUESTIONS)
        self.assertEqual(set(counts), {"A", "B", "C", "D"})
        self.assertLess(max(counts.values()) / len(CURATED_QUESTIONS), 0.5)

    def test_every_career_required_skill_is_verifiable_with_hard_questions(self):
        qbm.seed_curated_questions()
        from utils.skill_taxonomy import normalize_skill_name
        for career, req in CAREER_REQUIREMENTS.items():
            for skill in req["required"]:
                skill = normalize_skill_name(skill)
                rows = QuestionBank.query.filter_by(skill_name=skill).all()
                self.assertGreaterEqual(len(rows), qbm.MIN_QUESTIONS_TO_VERIFY, f"{career}: {skill}")
                self.assertIn("Hard", {r.difficulty for r in rows}, f"{career}: {skill} has no Hard question")
        cov = qbm.curated_coverage()
        self.assertTrue(all(v["verifiable"] for v in cov.values()), [k for k, v in cov.items() if not v["verifiable"]])

    def test_seeding_is_idempotent_and_skips_existing_text(self):
        db.session.add(QuestionBank(skill_name="docker", question="Which Docker command shows the containers that are currently running?",
                                    option_a="docker ps", option_b="docker build", option_c="docker pull",
                                    option_d="docker images", correct_answer="A", difficulty="Easy"))
        db.session.commit()
        first = qbm.seed_curated_questions("docker")
        docker_curated = [q for q in CURATED_QUESTIONS if q["skill_name"] == "docker"]
        self.assertEqual(first, len(docker_curated) - 1)        # the pre-existing one was skipped
        self.assertEqual(qbm.seed_curated_questions("docker"), 0)
        self.assertEqual(qbm.seed_curated_questions(), len(CURATED_QUESTIONS) - len(docker_curated))
        self.assertEqual(qbm.seed_curated_questions(), 0)
        self.assertEqual(QuestionBank.query.count(), len(CURATED_QUESTIONS))

    def test_quiz_for_curated_skill_works_without_ai_provider(self):
        sid = make_student("quiz@x.edu")
        skill = Skill(student_id=sid, skill_name="kubernetes", category="DevOps", proficiency="Beginner",
                      extraction_confidence=0.9, evidence_strength="applied")
        db.session.add(skill)
        db.session.commit()
        client = app.test_client()
        login(client, "quiz@x.edu")
        with mock.patch.object(qbm, "generate_questions", lambda *a, **k: None):   # Gemini unavailable
            res = client.get(f"/api/student/get_quiz/{skill.id}")
        self.assertEqual(res.status_code, 200, res.get_json())
        qs = res.get_json()["questions"]
        self.assertEqual(len(qs), 5)
        self.assertTrue(all("correct_answer" not in q for q in qs))
        self.assertEqual({q["difficulty"] for q in qs} & {"Easy", "Medium", "Hard"}, {"Easy", "Medium", "Hard"})

    def test_uncurated_skill_still_gets_nothing_without_provider(self):
        with mock.patch.object(qbm, "generate_questions", lambda *a, **k: None):
            self.assertEqual(qbm.ensure_minimum_questions("cobol"), 0)
        self.assertEqual(QuestionBank.query.filter_by(skill_name="cobol").count(), 0)

    def test_seed_questions_cli(self):
        runner = app.test_cli_runner()
        result = runner.invoke(args=["skills", "seed-questions", "--skill", "react"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn('"added": 6', result.output)
        self.assertEqual(QuestionBank.query.filter_by(skill_name="react").count(), 6)


if __name__ == "__main__":
    unittest.main()
