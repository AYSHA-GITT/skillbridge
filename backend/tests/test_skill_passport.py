"""
Verified Skill Passport: profile, evidence association, verification statuses,
resume import, PDF export, QR generation, share links (consent, visibility,
expiry, revocation, access history) and unauthorized access.
"""
from tests.base import app, db, reset_db, make_student, login  # must be first

import io
import json
import os
import unittest
from datetime import datetime, timedelta, timezone

from models import (Skill, SkillVerification, Resume, PassportEvidence, PassportShare,
                    PassportAccessLog, PassportProfile, Student)
from utils.skill_passport import hash_token

RESUME_TEXT = (
    "Asha Rao\nasha.rao@example.com | +91 9876543210 | linkedin.com/in/asha-rao\n"
    "SUMMARY\nFinal-year CSE student who builds data products.\n"
    "EDUCATION\nB.Tech Computer Science | Test College | 2022 - 2026\n"
    "TECHNICAL SKILLS\nPython, SQL, Docker\n"
    "PROJECTS\nSmart Attendance System | Python, OpenCV\n"
    "- Built a face recognition attendance tool in Python used by 3 classes.\n"
    "CERTIFICATIONS\nAWS Cloud Practitioner\n"
)
PNG_BYTES = b'\x89PNG\r\n\x1a\n' + b'\x00' * 64


def _api(client, method, url, **kw):
    res = getattr(client, method)(url, **kw)
    return res, (res.get_json(silent=True) or {})


class PassportTestBase(unittest.TestCase):
    def setUp(self):
        reset_db()
        self.sid = make_student("asha@test.com", name="Asha Rao", target_career="Data Scientist")
        self.other = make_student("bob@test.com", name="Bob")
        self.admin = make_student("admin@test.com", name="Admin", role="admin")
        with app.app_context():
            r = Resume(student_id=self.sid, file_path="uploads/resumes/none.pdf",
                       original_filename="cv.pdf", parsed_text=RESUME_TEXT, is_latest=True)
            db.session.add(r)
            db.session.commit()
            self.resume_id = r.id
        self.c = app.test_client()
        login(self.c, "asha@test.com")
        # Real extraction pipeline -> AI-extracted skills
        res, body = _api(self.c, 'post', f'/api/student/extract_skills/{self.resume_id}')
        self.assertEqual(res.status_code, 201, body)
        self.skills = {s['skill_name']: s['id'] for s in body['skills']}
        self._files = []

    def tearDown(self):
        with app.app_context():
            from utils.skill_passport import delete_evidence_files
            delete_evidence_files([e.file_path for e in PassportEvidence.query.all() if e.file_path])

    def passport(self, client=None):
        res, body = _api(client or self.c, 'get', '/api/passport/me')
        self.assertEqual(res.status_code, 200, body)
        return body

    def skill(self, name, client=None):
        return next(s for s in self.passport(client)['skills'] if s['skill_name'] == name)

    def add_evidence(self, **kw):
        payload = {'kind': 'project', 'title': 'Churn model', 'description': 'x', 'skill_ids': []}
        payload.update(kw)
        res, body = _api(self.c, 'post', '/api/passport/me/evidence', json=payload)
        self.assertEqual(res.status_code, 201, body)
        return body['evidence']

    def make_share(self, client=None, **kw):
        payload = {'consent': True, 'expires_in_days': 7, 'label': 'Acme'}
        payload.update(kw)
        res, body = _api(client or self.c, 'post', '/api/passport/me/shares', json=payload)
        self.assertEqual(res.status_code, 201, body)
        return body


class ProfileTests(PassportTestBase):
    def test_passport_reuses_existing_student_data(self):
        p = self.passport()
        self.assertEqual(p['student']['name'], 'Asha Rao')
        self.assertEqual(p['education']['current']['institution'], 'Test College')
        self.assertEqual(p['career_interests']['target_career'], 'Data Scientist')
        self.assertIn('python', {s['skill_name'] for s in p['skills']})
        # suggestions come from the parsed resume, nothing is saved automatically
        self.assertFalse(p['profile_saved'])
        self.assertIn('linkedin.com/in/asha-rao', p['suggestions']['linkedin_url'])
        titles = [c['title'] for c in p['resume_import_candidates']['project']]
        self.assertIn('Smart Attendance System', titles)

    def test_create_and_update_profile(self):
        res, body = _api(self.c, 'put', '/api/passport/me/profile',
                         json={'headline': 'Aspiring data scientist', 'summary': 'I build things.',
                               'github_url': 'https://github.com/asha'})
        self.assertEqual(res.status_code, 200, body)
        res, body = _api(self.c, 'put', '/api/passport/me/profile',
                         json={'headline': 'ML engineer in training', 'summary': 'Updated'})
        self.assertEqual(res.status_code, 200)
        p = self.passport()
        self.assertTrue(p['profile_saved'])
        self.assertEqual(p['profile']['headline'], 'ML engineer in training')
        self.assertEqual(p['profile']['github_url'], '')
        with app.app_context():
            self.assertEqual(PassportProfile.query.filter_by(student_id=self.sid).count(), 1)

    def test_profile_validation(self):
        res, _ = _api(self.c, 'put', '/api/passport/me/profile', json={'linkedin_url': 'javascript:alert(1)'})
        self.assertEqual(res.status_code, 400)
        res, _ = _api(self.c, 'put', '/api/passport/me/profile', json={'headline': 'x' * 161})
        self.assertEqual(res.status_code, 400)


class StatusTests(PassportTestBase):
    def test_resume_skill_is_only_ai_extracted(self):
        s = self.skill('python')
        self.assertEqual(s['status'], 'ai_extracted')
        self.assertEqual(s['proficiency'], 'Not assessed')
        self.assertIsNone(s['last_verified_at'])
        self.assertIsNotNone(s['resume_evidence'])
        self.assertIsNotNone(s['confidence']['resume_mention_confidence'])
        self.assertIsNone(s['confidence']['verification_score'])

    def test_self_declared_skill(self):
        res, body = _api(self.c, 'post', '/api/passport/me/skills', json={'skill_name': 'Teamwork'})
        self.assertEqual(res.status_code, 201, body)
        s = self.skill('teamwork')
        self.assertEqual(s['status'], 'self_declared')
        self.assertEqual(s['group'], 'soft_skills')
        self.assertIsNone(s['resume_evidence'])
        # duplicates (incl. aliases) are rejected
        res, _ = _api(self.c, 'post', '/api/passport/me/skills', json={'skill_name': 'Python3'})
        self.assertEqual(res.status_code, 409)
        # self-declared can be removed; resume skills cannot
        res, _ = _api(self.c, 'delete', f"/api/passport/me/skills/{body['skill']['id']}")
        self.assertEqual(res.status_code, 200)
        res, _ = _api(self.c, 'delete', f"/api/passport/me/skills/{self.skills['python']}")
        self.assertEqual(res.status_code, 400)

    def test_evidence_and_certificate_do_not_verify(self):
        ev = self.add_evidence(kind='certificate', title='AWS Cloud Practitioner',
                               url='https://aws.example/cred/1', skill_ids=[self.skills['aws']])
        self.assertEqual(self.skill('aws')['status'], 'evidence_submitted')
        # Uploading a certificate file still does not verify
        res, body = _api(self.c, 'post', f"/api/passport/me/evidence/{ev['id']}/file",
                         data={'file': (io.BytesIO(PNG_BYTES), 'cert.png')}, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 200, body)
        self.assertTrue(body['evidence']['has_file'])
        self.assertEqual(self.skill('aws')['status'], 'evidence_submitted')
        # Requesting review -> pending, still not verified
        res, body = _api(self.c, 'post', f"/api/passport/me/evidence/{ev['id']}/request_review")
        self.assertEqual(res.status_code, 200, body)
        s = self.skill('aws')
        self.assertEqual(s['status'], 'pending_verification')
        self.assertIsNone(s['last_verified_at'])

    def test_admin_review_verifies_and_edit_resets(self):
        ev = self.add_evidence(kind='experience', title='Data intern', organization='Acme',
                               url='https://acme.example/letter', skill_ids=[self.skills['sql']])
        _api(self.c, 'post', f"/api/passport/me/evidence/{ev['id']}/request_review")

        # students cannot review
        res, _ = _api(self.c, 'post', f"/api/passport/admin/evidence/{ev['id']}/review", json={'decision': 'verified'})
        self.assertEqual(res.status_code, 403)

        admin = app.test_client()
        login(admin, "admin@test.com")
        res, body = _api(admin, 'get', '/api/passport/admin/evidence?status=pending')
        self.assertEqual(res.status_code, 200)
        self.assertEqual([e['id'] for e in body['evidence']], [ev['id']])
        res, _ = _api(admin, 'post', f"/api/passport/admin/evidence/{ev['id']}/review", json={'decision': 'rejected'})
        self.assertEqual(res.status_code, 400)  # reason required for rejection
        res, body = _api(admin, 'post', f"/api/passport/admin/evidence/{ev['id']}/review",
                         json={'decision': 'verified', 'note': 'Offer letter checked'})
        self.assertEqual(res.status_code, 200, body)

        s = self.skill('sql')
        self.assertEqual(s['status'], 'verified')
        self.assertEqual(s['verified_via'], ['reviewed_evidence'])
        self.assertIsNotNone(s['last_verified_at'])

        # Editing verified evidence invalidates the review
        res, body = _api(self.c, 'put', f"/api/passport/me/evidence/{ev['id']}", json={'title': 'Senior data intern'})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(body['review_reset'])
        self.assertEqual(self.skill('sql')['status'], 'evidence_submitted')
        # A no-op edit does not reset anything
        _api(self.c, 'post', f"/api/passport/me/evidence/{ev['id']}/request_review")
        res, body = _api(self.c, 'put', f"/api/passport/me/evidence/{ev['id']}", json={'title': 'Senior data intern'})
        self.assertFalse(body['review_reset'])
        self.assertEqual(self.skill('sql')['status'], 'pending_verification')

    def test_admin_cannot_review_own_evidence(self):
        admin = app.test_client()
        login(admin, "admin@test.com")
        with app.app_context():
            sk = Skill(student_id=self.admin, skill_name='python', source='self_declared')
            db.session.add(sk)
            db.session.commit()
            skid = sk.id
        res, body = _api(admin, 'post', '/api/passport/me/evidence',
                         json={'kind': 'project', 'title': 'Mine', 'url': 'https://x.example', 'skill_ids': [skid]})
        _api(admin, 'post', f"/api/passport/me/evidence/{body['evidence']['id']}/request_review")
        res, _ = _api(admin, 'post', f"/api/passport/admin/evidence/{body['evidence']['id']}/review",
                      json={'decision': 'verified'})
        self.assertEqual(res.status_code, 403)

    def test_assessment_statuses(self):
        with app.app_context():
            db.session.add(SkillVerification(student_id=self.sid, skill_id=self.skills['docker'],
                                             quiz_question_count=8, quiz_correct_count=4,
                                             quiz_score_percent=50.0, verification_score=0.47))
            db.session.add(SkillVerification(student_id=self.sid, skill_id=self.skills['python'],
                                             quiz_question_count=5, quiz_correct_count=4,
                                             quiz_score_percent=80.0, verification_score=0.85))
            db.session.get(Skill, self.skills['python']).proficiency = 'Intermediate'
            db.session.commit()
        docker = self.skill('docker')
        self.assertEqual(docker['status'], 'assessment_completed')
        self.assertIsNone(docker['last_verified_at'])
        self.assertEqual(docker['assessment']['score_percent'], 50.0)
        py = self.skill('python')
        self.assertEqual(py['status'], 'verified')
        self.assertEqual(py['verified_via'], ['assessment'])
        self.assertEqual(py['proficiency'], 'Intermediate')
        self.assertEqual(py['assessment']['correct'], 4)
        self.assertIsNotNone(py['last_verified_at'])
        self.assertEqual(py['confidence']['verification_score'], 0.85)
        # A later failed attempt replaces the earlier pass: verification reflects the latest result
        with app.app_context():
            db.session.add(SkillVerification(student_id=self.sid, skill_id=self.skills['python'],
                                             quiz_question_count=5, quiz_correct_count=1,
                                             quiz_score_percent=20.0, verification_score=0.3,
                                             verified_on=datetime.now(timezone.utc) + timedelta(minutes=1)))
            db.session.commit()
        self.assertEqual(self.skill('python')['status'], 'assessment_completed')

    def test_evidence_link_validation_and_ownership(self):
        with app.app_context():
            bob_skill = Skill(student_id=self.other, skill_name='java', source='self_declared')
            db.session.add(bob_skill)
            db.session.commit()
            bob_skill_id = bob_skill.id
        res, _ = _api(self.c, 'post', '/api/passport/me/evidence',
                      json={'kind': 'project', 'title': 'X', 'skill_ids': [bob_skill_id]})
        self.assertEqual(res.status_code, 400)
        res, _ = _api(self.c, 'post', '/api/passport/me/evidence',
                      json={'kind': 'project', 'title': 'X', 'url': 'javascript:alert(1)'})
        self.assertEqual(res.status_code, 400)
        res, _ = _api(self.c, 'post', '/api/passport/me/evidence', json={'kind': 'hobby', 'title': 'X'})
        self.assertEqual(res.status_code, 400)
        ev = self.add_evidence(skill_ids=[self.skills['python']])
        res, _ = _api(self.c, 'post', f"/api/passport/me/evidence/{ev['id']}/request_review")
        self.assertEqual(res.status_code, 400)  # nothing a reviewer could check yet
        # wrong file content is rejected
        res, _ = _api(self.c, 'post', f"/api/passport/me/evidence/{ev['id']}/file",
                      data={'file': (io.BytesIO(b'MZ not a pdf'), 'x.pdf')}, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 400)

    def test_import_from_resume(self):
        p = self.passport()
        proj = next(c for c in p['resume_import_candidates']['project'] if c['title'] == 'Smart Attendance System')
        cert = p['resume_import_candidates']['certificate'][0]
        res, body = _api(self.c, 'post', '/api/passport/me/evidence/import',
                         json={'items': [{'kind': 'project', 'index': proj['index']},
                                         {'kind': 'certificate', 'index': cert['index']}]})
        self.assertEqual(res.status_code, 201, body)
        imported = {e['title']: e for e in body['evidence']}
        self.assertEqual(imported['Smart Attendance System']['source'], 'resume')
        self.assertIn('python', [s['skill_name'] for s in imported['Smart Attendance System']['skills']])
        self.assertEqual(imported['Smart Attendance System']['review_status'], 'not_requested')
        # Importing again does not duplicate
        res, body = _api(self.c, 'post', '/api/passport/me/evidence/import',
                         json={'items': [{'kind': 'project', 'index': proj['index']}]})
        self.assertEqual(body['skipped_existing'], 1)
        self.assertTrue(next(c for c in self.passport()['resume_import_candidates']['project']
                             if c['title'] == 'Smart Attendance System')['already_added'])
        res, _ = _api(self.c, 'post', '/api/passport/me/evidence/import', json={'items': [{'kind': 'project', 'index': 99}]})
        self.assertEqual(res.status_code, 400)


class ExportAndShareTests(PassportTestBase):
    def test_owner_pdf_export(self):
        res = self.c.get('/api/passport/me/pdf')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, 'application/pdf')
        self.assertTrue(res.data.startswith(b'%PDF'))
        self.assertIn('attachment', res.headers['Content-Disposition'])
        res = self.c.get('/api/passport/me/pdf?sections=skills&skill_filter=verified')
        self.assertTrue(res.data.startswith(b'%PDF'))

    def test_share_requires_consent_and_valid_settings(self):
        res, _ = _api(self.c, 'post', '/api/passport/me/shares', json={'expires_in_days': 7})
        self.assertEqual(res.status_code, 400)
        res, _ = _api(self.c, 'post', '/api/passport/me/shares', json={'consent': 'yes'})
        self.assertEqual(res.status_code, 400)
        res, _ = _api(self.c, 'post', '/api/passport/me/shares', json={'consent': True, 'expires_in_days': 365})
        self.assertEqual(res.status_code, 400)
        res, _ = _api(self.c, 'post', '/api/passport/me/shares',
                      json={'consent': True, 'visibility': {'sections': {'skills': False}}})
        self.assertEqual(res.status_code, 400)

    def test_share_link_token_qr_and_public_view(self):
        _api(self.c, 'put', '/api/passport/me/profile', json={'headline': 'Data person', 'summary': 'Hi'})
        body = self.make_share()
        url = body['url']
        token = url.rsplit('/', 1)[1]
        self.assertGreaterEqual(len(token), 43)
        self.assertIn('<svg', body['qr_svg'])
        with app.app_context():
            share = db.session.get(PassportShare, body['share']['id'])
            self.assertEqual(share.token_hash, hash_token(token))
            self.assertNotIn(token, json.dumps(share.to_dict()))
            self.assertIsNotNone(share.consent_at)
        self.assertNotIn(token, json.dumps(self.passport()['shares']))  # never shown again

        anon = app.test_client()
        res, pub = _api(anon, 'get', f'/api/passport/public/{token}')
        self.assertEqual(res.status_code, 200, pub)
        self.assertEqual(res.headers['Cache-Control'], 'no-store')
        self.assertEqual(pub['name'], 'Asha Rao')
        self.assertEqual(pub['profile']['headline'], 'Data person')
        raw = json.dumps(pub)
        for private in ('asha@test.com', 'asha.rao@example.com', '9876543210', 'password', 'student_id'):
            self.assertNotIn(private, raw)
        self.assertNotIn('"id"', raw)
        self.assertNotIn('snippets', raw)  # raw resume text stays private
        self.assertEqual(pub['education']['current']['institution'], 'Test College')
        self.assertEqual(pub['education']['from_resume'], [])  # un-imported resume content stays private
        self.assertNotIn('Smart Attendance System', raw)

        res = anon.get(f'/api/passport/public/{token}/pdf')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data.startswith(b'%PDF'))

        res, log = _api(self.c, 'get', f"/api/passport/me/shares/{body['share']['id']}/access_log")
        self.assertEqual(res.status_code, 200)
        self.assertEqual([l['event'] for l in log['access_log']], ['pdf', 'view'])
        self.assertEqual(log['share']['access_count'], 2)
        self.assertEqual(log['unique_viewers'], 1)
        with app.app_context():
            self.assertNotIn('127.0.0.1', json.dumps([l.to_dict() for l in PassportAccessLog.query.all()]))

    def test_visibility_restricts_sections_and_skills(self):
        with app.app_context():
            db.session.add(SkillVerification(student_id=self.sid, skill_id=self.skills['python'],
                                             quiz_question_count=5, quiz_correct_count=5,
                                             quiz_score_percent=100.0, verification_score=1.0))
            db.session.commit()
        self.add_evidence(kind='project', title='Secret side project', skill_ids=[self.skills['sql']])
        body = self.make_share(visibility={'sections': {'skills': True, 'assessments': True},
                                           'skill_filter': 'verified'}, allow_pdf=False)
        token = body['url'].rsplit('/', 1)[1]
        anon = app.test_client()
        _, pub = _api(anon, 'get', f'/api/passport/public/{token}')
        self.assertEqual([s['skill_name'] for s in pub['skills']], ['python'])
        self.assertEqual(pub['skills'][0]['assessment']['score_percent'], 100.0)
        for hidden in ('profile', 'links', 'education', 'projects', 'career_interests', 'certifications'):
            self.assertNotIn(hidden, pub)
        self.assertNotIn('Secret side project', json.dumps(pub))
        self.assertNotIn('Test College', json.dumps(pub))
        self.assertEqual(anon.get(f'/api/passport/public/{token}/pdf').status_code, 403)

    def test_rejected_evidence_is_never_public(self):
        ev = self.add_evidence(title='Bogus cert', kind='certificate', url='https://x.example',
                               skill_ids=[self.skills['docker']])
        _api(self.c, 'post', f"/api/passport/me/evidence/{ev['id']}/request_review")
        admin = app.test_client()
        login(admin, "admin@test.com")
        _api(admin, 'post', f"/api/passport/admin/evidence/{ev['id']}/review",
             json={'decision': 'rejected', 'note': 'Credential not found'})
        token = self.make_share()['url'].rsplit('/', 1)[1]
        _, pub = _api(app.test_client(), 'get', f'/api/passport/public/{token}')
        self.assertNotIn('Bogus cert', json.dumps(pub))
        self.assertNotIn('Credential not found', json.dumps(pub))

    def test_revoked_link_stops_working(self):
        body = self.make_share()
        token = body['url'].rsplit('/', 1)[1]
        anon = app.test_client()
        self.assertEqual(anon.get(f'/api/passport/public/{token}').status_code, 200)
        res, rv = _api(self.c, 'post', f"/api/passport/me/shares/{body['share']['id']}/revoke")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(rv['share']['status'], 'revoked')
        self.assertEqual(anon.get(f'/api/passport/public/{token}').status_code, 410)
        self.assertEqual(anon.get(f'/api/passport/public/{token}/pdf').status_code, 410)
        _, log = _api(self.c, 'get', f"/api/passport/me/shares/{body['share']['id']}/access_log")
        self.assertIn('denied_revoked', [l['event'] for l in log['access_log']])

    def test_expired_link_stops_working(self):
        body = self.make_share(expires_in_days=1)
        token = body['url'].rsplit('/', 1)[1]
        with app.app_context():
            share = db.session.get(PassportShare, body['share']['id'])
            share.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.session.commit()
        res, err = _api(app.test_client(), 'get', f'/api/passport/public/{token}')
        self.assertEqual(res.status_code, 410)
        self.assertNotIn('Asha', json.dumps(err))
        self.assertEqual(self.passport()['shares'][0]['status'], 'expired')

    def test_unknown_and_malformed_tokens(self):
        anon = app.test_client()
        self.make_share()
        self.assertEqual(anon.get('/api/passport/public/' + 'A' * 43).status_code, 404)
        self.assertEqual(anon.get('/api/passport/public/1').status_code, 404)
        self.assertEqual(anon.get("/api/passport/public/' OR 1=1 --").status_code, 404)


class AuthorizationTests(PassportTestBase):
    def test_owner_endpoints_require_login(self):
        anon = app.test_client()
        for method, url in (('get', '/api/passport/me'), ('put', '/api/passport/me/profile'),
                            ('post', '/api/passport/me/shares'), ('get', '/api/passport/me/pdf'),
                            ('post', '/api/passport/me/evidence'), ('get', '/api/passport/admin/evidence')):
            self.assertEqual(getattr(anon, method)(url).status_code, 401, url)

    def test_students_cannot_touch_each_others_data(self):
        ev = self.add_evidence(url='https://x.example', skill_ids=[self.skills['python']])
        self.c.post(f"/api/passport/me/evidence/{ev['id']}/file",
                    data={'file': (io.BytesIO(PNG_BYTES), 'p.png')}, content_type='multipart/form-data')
        share = self.make_share()['share']
        bob = app.test_client()
        login(bob, "bob@test.com")
        self.assertEqual(bob.put(f"/api/passport/me/evidence/{ev['id']}", json={'title': 'hacked'}).status_code, 404)
        self.assertEqual(bob.delete(f"/api/passport/me/evidence/{ev['id']}").status_code, 404)
        self.assertEqual(bob.get(f"/api/passport/me/evidence/{ev['id']}/file").status_code, 404)
        self.assertEqual(bob.post(f"/api/passport/me/evidence/{ev['id']}/request_review").status_code, 404)
        self.assertEqual(bob.post(f"/api/passport/me/shares/{share['id']}/revoke").status_code, 404)
        self.assertEqual(bob.get(f"/api/passport/me/shares/{share['id']}/access_log").status_code, 404)
        self.assertEqual(bob.delete(f"/api/passport/me/skills/{self.skills['python']}").status_code, 404)
        self.assertEqual(bob.get('/api/passport/admin/evidence').status_code, 403)
        self.assertEqual(bob.get(f"/api/passport/admin/evidence/{ev['id']}/file").status_code, 403)
        self.assertEqual(self.passport(bob)['skills'], [])
        self.assertEqual(self.passport(bob)['shares'], [])
        # owner still sees the untouched evidence
        self.assertEqual(self.passport()['evidence'][0]['title'], 'Churn model')
        res = self.c.get(f"/api/passport/me/evidence/{ev['id']}/file")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, PNG_BYTES)
        self.assertIn('attachment', res.headers['Content-Disposition'])
        res.close()

    def test_account_deletion_removes_passport_data_and_files(self):
        ev = self.add_evidence(skill_ids=[self.skills['python']])
        _, body = _api(self.c, 'post', f"/api/passport/me/evidence/{ev['id']}/file",
                       data={'file': (io.BytesIO(PNG_BYTES), 'p.png')}, content_type='multipart/form-data')
        with app.app_context():
            from utils.skill_passport import evidence_file_abspath
            path = evidence_file_abspath(db.session.get(PassportEvidence, ev['id']).file_path)
        self.assertTrue(os.path.isfile(path))
        token = self.make_share()['url'].rsplit('/', 1)[1]
        _api(app.test_client(), 'get', f'/api/passport/public/{token}')
        _api(self.c, 'put', '/api/passport/me/profile', json={'headline': 'h'})

        res, body = _api(self.c, 'delete', '/api/student/account/delete', json={'confirmation': 'DELETE_MY_ACCOUNT'})
        self.assertEqual(res.status_code, 200, body)
        self.assertEqual(body['evidence_files_removed'], 1)
        self.assertFalse(os.path.exists(path))
        with app.app_context():
            for model in (PassportEvidence, PassportShare, PassportAccessLog, PassportProfile):
                self.assertEqual(model.query.count(), 0, model.__name__)
            self.assertIsNone(Student.query.filter_by(email='asha@test.com').first())
        self.assertEqual(app.test_client().get(f'/api/passport/public/{token}').status_code, 404)


if __name__ == '__main__':
    unittest.main()
