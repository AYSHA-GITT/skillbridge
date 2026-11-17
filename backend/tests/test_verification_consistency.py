"""
One definition of "verified" across SkillBridge.

The Skill Passport rule (latest quiz attempt >= 70%, or evidence accepted by a
reviewer) must be the rule used by job matching, the recruiter compatibility
report, career recommendations / skill gaps, the Verified Skill Profile, the
Assessments page and badges. A failed quiz attempt is never "verified".
"""
from tests.base import app, db, reset_db, make_student, login  # must be first

import unittest
from datetime import datetime, timedelta, timezone

from models import Skill, SkillVerification, PassportEvidence, Student
from utils.job_matcher import build_student_profile, evaluate_job_match
from utils.recruiting import _skill_credit
from utils.skill_passport import build_owner_passport, skill_verification_states, verified_skill_names

T0 = datetime.now(timezone.utc) - timedelta(days=10)


class VerificationConsistencyTest(unittest.TestCase):
    def setUp(self):
        reset_db()
        self.sid = make_student("vera@test.com", name="Vera", target_career="Cloud Engineer")
        with app.app_context():
            def skill(name, strength='applied', source='resume'):
                s = Skill(student_id=self.sid, skill_name=name, source=source, evidence_strength=strength)
                db.session.add(s)
                db.session.flush()
                return s

            def attempt(sk, pct, days):
                db.session.add(SkillVerification(student_id=self.sid, skill_id=sk.id, quiz_question_count=10,
                                                 quiz_correct_count=int(pct // 10), quiz_score_percent=pct,
                                                 verification_score=pct / 100,
                                                 verified_on=T0 + timedelta(days=days)))

            py, docker, aws = skill('python'), skill('docker'), skill('aws')
            sql, git, react = skill('sql', 'listed_only'), skill('git'), skill('react')
            attempt(py, 80.0, 1)                          # passed
            attempt(docker, 20.0, 1)                      # failed
            attempt(aws, 90.0, 1)
            attempt(aws, 30.0, 2)                         # latest attempt failed -> not verified
            attempt(react, 65.0, 1)                       # 60-69%: old Assessments page called it passed
            ev = PassportEvidence(student_id=self.sid, kind='project', title='ETL pipeline',
                                  review_status='verified', reviewed_at=T0 + timedelta(days=3))
            ev.skills.append(sql)                         # verified through reviewed evidence, no quiz
            db.session.add(ev)
            db.session.commit()
        self.client = app.test_client()
        login(self.client, "vera@test.com")

    def test_states_follow_passport_rule(self):
        with app.app_context():
            st = skill_verification_states(self.sid)
            self.assertEqual(st['python']['status'], 'verified')
            self.assertEqual(st['sql']['status'], 'verified')
            self.assertEqual(st['sql']['verified_via'], ['reviewed_evidence'])
            self.assertEqual(st['docker']['status'], 'assessment_completed')
            self.assertEqual(st['aws']['status'], 'assessment_completed')
            self.assertEqual(st['aws']['latest_score'], 30.0)
            self.assertEqual(st['git']['status'], 'ai_extracted')
            self.assertEqual(sorted(verified_skill_names(self.sid)), ['python', 'sql'])

    def test_job_match_does_not_call_failed_attempts_verified(self):
        with app.app_context():
            student = db.session.get(Student, self.sid)
            res = evaluate_job_match(student=student, include_resources=False, job_data={
                'title': 'Cloud Engineer', 'required_skills': ['Python', 'Docker', 'SQL', 'Git']})
            self.assertEqual(sorted(res['matched_skills']['verified']), ['python', 'sql'])
            self.assertEqual(sorted(res['matched_skills']['unverified']), ['docker', 'git'])
            self.assertEqual(res['skill_status']['docker'], 'assessment_completed')
            self.assertTrue(any('below the pass mark' in r for r in res['match_reasons']))
            self.assertTrue(any(u['skill'] == 'docker' and '70%' in u['reason'] for u in res['uncertain_skills']))
            self.assertTrue(any(u['skill'] == 'git' for u in res['uncertain_skills']))
            self.assertIn("Retake the quiz for 'docker'", ' '.join(res['suggested_next_steps']))
            # the Jobs page labels each skill from skill_status and links it to /verify-skill/<id>
            ids = {s.skill_name: s.id for s in Skill.query.filter_by(student_id=self.sid)}
            self.assertEqual(res['skill_ids'], {k: ids[k] for k in ('python', 'docker', 'sql', 'git')})

    def test_match_endpoint_gives_the_page_status_and_quiz_link_per_skill(self):
        # The Jobs page reads this endpoint's matched_skills array (not evaluate_job_match directly)
        import json as _json
        from models import JobListing
        with app.app_context():
            job = JobListing(title='Cloud Engineer', company='Acme', status='active',
                             required_skills=_json.dumps(['Python', 'Docker', 'Git']),
                             preferred_skills=_json.dumps(['SQL']))
            db.session.add(job)
            db.session.commit()
            job_id = job.id
            ids = {s.skill_name: s.id for s in Skill.query.filter_by(student_id=self.sid)}
        body = self.client.get(f'/api/student/jobs/{job_id}/match').get_json()
        matched = body.get('match', body)['matched_skills']
        by = {m['skill']: m for m in matched}
        self.assertEqual({k: (v['status'], v['skill_id'], v['is_verified']) for k, v in by.items()}, {
            'python': ('verified', ids['python'], True),
            'docker': ('assessment_completed', ids['docker'], False),   # shown "Below pass mark" + Retake quiz
            'git': ('ai_extracted', ids['git'], False),                 # shown "Resume only" + Verify
            'sql': ('verified', ids['sql'], True),                      # preferred, verified by reviewed evidence
        })

    def test_preferred_skills_report_their_real_status(self):
        with app.app_context():
            student = db.session.get(Student, self.sid)
            res = evaluate_job_match(student=student, include_resources=False, job_data={
                'title': 'Platform Engineer', 'required_skills': ['Python'], 'preferred_skills': ['Git', 'AWS']})
            self.assertEqual(res['matched_skills']['preferred'], ['git', 'aws'])
            # preferred skills used to be shown as "Verified Quiz" whatever their status
            self.assertEqual(res['skill_status']['git'], 'ai_extracted')
            self.assertEqual(res['skill_status']['aws'], 'assessment_completed')

    def test_student_and_recruiter_credit_each_skill_the_same(self):
        with app.app_context():
            student = db.session.get(Student, self.sid)
            profile = build_student_profile(student=student)['skills']
            passport = build_owner_passport(student)
            for s in passport['skills']:
                self.assertAlmostEqual(_skill_credit(s), profile[s['skill_name']]['credit'], places=6,
                                       msg=s['skill_name'])
            self.assertEqual(profile['python']['credit'], 1.0)
            self.assertEqual(profile['sql']['credit'], 1.0)      # reviewed evidence now counts
            self.assertEqual(profile['docker']['credit'], 0.2)   # failed attempt, latest score
            self.assertEqual(profile['aws']['credit'], 0.2)      # latest (30%), not best (90%)

    def test_skill_gap_counts_only_verified_skills(self):
        body = self.client.post('/api/student/analyze_skill_gap').get_json()
        self.assertEqual(body['matched_required'], ['python'])
        self.assertIn('docker', body['missing_required'])
        self.assertIn('aws', body['missing_required'])
        self.assertIn('sql', body['matched_nice_to_have'])

    def test_career_recommendations_use_verified_skills(self):
        res = self.client.get('/api/student/career_recommendations')
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertEqual(body['verified_skills_count'], 2)
        cloud = next(r for r in body['recommendations'] if r['career_key'] == 'cloud engineer')
        self.assertEqual(cloud['matched_required'], ['python'])
        self.assertIn('docker', cloud['missing_required'])
        self.assertIn('aws', cloud['missing_required'])

    def test_verified_skill_profile(self):
        body = self.client.get('/api/student/verified_skill_profile').get_json()
        verified = {v['skill_name']: v for v in body['verified_skills']}
        self.assertEqual(set(verified), {'python', 'sql'})
        self.assertEqual(verified['sql']['verified_via'], ['reviewed_evidence'])
        self.assertEqual({v['skill_name'] for v in body['needs_improvement']}, {'docker', 'aws', 'react'})
        self.assertEqual({v['skill_name'] for v in body['needs_verification']}, {'git'})
        self.assertEqual(body['summary']['total_detected'], 6)

    def test_assessments_pass_mark_is_70(self):
        body = self.client.get('/api/student/assessments').get_json()
        done = {c['skill_name']: c for c in body['completed']}
        self.assertFalse(done['react']['passed'])     # 65%
        self.assertTrue(done['python']['passed'])

    def test_core_competent_badge_needs_three_verified_skills(self):
        body = self.client.get('/api/student/badges').get_json()
        badges = body.get('badges', body)
        three = next(b for b in badges if b['id'] == 'three_skills')
        self.assertFalse(three['unlocked'])            # 5 attempts, only 2 verified skills
        first = next(b for b in badges if b['id'] == 'first_quiz')
        self.assertTrue(first['unlocked'])


if __name__ == '__main__':
    unittest.main()
