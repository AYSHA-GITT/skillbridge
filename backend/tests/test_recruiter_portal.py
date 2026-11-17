"""
Recruiter portal: recruiter registration and roles, organisation verification,
employer job posting integrated with job discovery, consent-scoped candidate
access (applications and opt-in discovery), explainable matching, shortlists,
notes, invitations, the hiring pipeline, student updates, cross-organisation
protection and rate limiting.
"""
from tests.base import app, db, reset_db, make_student, login  # must be first

import json
import unittest
from datetime import datetime, timedelta, timezone

from models import (Skill, SkillVerification, JobListing, JobApplication, Organisation, RecruiterAccessLog,
                    ApplicationEvent, RecruitmentNote, ShortlistEntry, JobInvitation, CandidateDiscoverySetting,
                    Student)
from utils.recruiting import candidate_ref, compatibility_report

PW = "password123"
ALL_SECTIONS = {k: True for k in ('profile', 'links', 'education', 'skills', 'projects', 'certifications',
                                  'experience', 'practical_challenges', 'assessments', 'career_interests')}


def _api(client, method, url, **kw):
    res = getattr(client, method)(url, **kw)
    return res, (res.get_json(silent=True) or {})


def register_recruiter(client, email, org_name, website="https://acme.example.com"):
    res, body = _api(client, 'post', '/api/auth/register_recruiter', json={
        'name': 'Rita Recruiter', 'email': email, 'password': PW, 'job_title': 'Talent Lead',
        'role': 'admin',   # must be ignored
        'organisation': {'name': org_name, 'industry': 'Software', 'website': website,
                         'contact_email': 'hr@acme.example.com'}})
    assert res.status_code == 201, body
    return body


JOB = {'title': 'Junior Data Engineer', 'description': 'Build data pipelines with Python and SQL for analytics.',
       'location': 'Bengaluru, Karnataka', 'work_arrangement': 'Hybrid', 'job_type': 'Full-time',
       'required_skills': ['Python', 'SQL', 'Docker'], 'preferred_skills': ['AWS'],
       'experience_min_years': 0, 'experience_max_years': 2, 'education': 'B.Tech/BE in CS or IT',
       'salary_min': 600000, 'salary_max': 900000, 'salary_currency': 'INR', 'salary_period': 'year'}


class RecruiterBase(unittest.TestCase):
    def setUp(self):
        reset_db()
        self.admin_id = make_student("admin@test.com", role="admin", name="Admin")
        self.sid = make_student("asha@test.com", name="Asha Rao", target_career="Data Engineer")
        self.other_sid = make_student("bob@test.com", name="Bob")
        with app.app_context():
            sk_py = Skill(student_id=self.sid, skill_name='python', source='resume', evidence_strength='applied',
                          proficiency='Advanced', category='Programming')
            sk_sql = Skill(student_id=self.sid, skill_name='sql', source='resume', evidence_strength='applied',
                           category='Data')
            db.session.add_all([sk_py, sk_sql])
            db.session.flush()
            db.session.add(SkillVerification(student_id=self.sid, skill_id=sk_py.id, quiz_question_count=5,
                                             quiz_correct_count=4, quiz_score_percent=80.0,
                                             verification_score=0.8))
            db.session.commit()

        self.rec = app.test_client()
        register_recruiter(self.rec, "rita@acme.example.com", "Acme Analytics")
        self.rec2 = app.test_client()
        register_recruiter(self.rec2, "omar@other.example.com", "Other Corp", website="https://other.example.com")
        self.stu = app.test_client()
        login(self.stu, "asha@test.com")
        self.adm = app.test_client()
        login(self.adm, "admin@test.com")

    # helpers
    def org_id(self, client):
        return _api(client, 'get', '/api/recruiter/me')[1]['organisation']['id']

    def verify_org(self, client):
        res, body = _api(client, 'post', '/api/recruiter/organisation/verification',
                         json={'registration_id': 'U72900KA2020PTC000000'})
        self.assertEqual(res.status_code, 200, body)
        res, body = _api(self.adm, 'post', f'/api/recruiter/admin/organisations/{self.org_id(client)}/review',
                         json={'decision': 'verified'})
        self.assertEqual(res.status_code, 200, body)

    def create_job(self, client=None, **over):
        res, body = _api(client or self.rec, 'post', '/api/recruiter/jobs', json={**JOB, **over})
        self.assertEqual(res.status_code, 201, body)
        return body['job']

    def published_job(self, **over):
        self.verify_org(self.rec)
        job = self.create_job(**over)
        res, body = _api(self.rec, 'post', f"/api/recruiter/jobs/{job['id']}/publish")
        self.assertEqual(res.status_code, 200, body)
        return body['job']

    def apply(self, job_id, client=None, sections=None, skill_filter='all', **extra):
        payload = {'share_consent': True, 'contact_email': 'asha.apply@example.com',
                   'cover_note': 'Keen to join.',
                   'share_visibility': {'sections': sections or ALL_SECTIONS, 'skill_filter': skill_filter}}
        payload.update(extra)
        return _api(client or self.stu, 'post', f'/api/student/jobs/{job_id}/apply', json=payload)

    def ref(self, sid=None):
        with app.app_context():
            r = candidate_ref(sid or self.sid)
            db.session.commit()
            return r


class RegistrationAndRolesTests(RecruiterBase):
    def test_registration_fixes_role_and_starts_unverified(self):
        res, me = _api(self.rec, 'get', '/api/recruiter/me')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(me['user']['role'], 'recruiter')          # 'admin' in the request was ignored
        self.assertEqual(me['organisation']['verification_status'], 'unverified')
        self.assertFalse(me['can_publish_jobs'])
        self.assertFalse(me['can_search_candidates'])

    def test_duplicate_email_and_validation(self):
        c = app.test_client()
        res, _ = _api(c, 'post', '/api/auth/register_recruiter', json={
            'name': 'X', 'email': 'asha@test.com', 'password': PW, 'organisation': {'name': 'Y'}})
        self.assertEqual(res.status_code, 409)
        res, body = _api(c, 'post', '/api/auth/register_recruiter', json={
            'name': 'X', 'email': 'new@x.com', 'password': PW, 'organisation': {'name': 'Y', 'website': 'javascript:alert(1)'}})
        self.assertEqual(res.status_code, 400, body)

    # ── Regression: the registration form (frontend RecruiterRegister.js) ──────
    @staticmethod
    def form_payload(email, website='', **org):
        """Exactly what the form sends: every field present, optional ones as empty strings."""
        return {'name': 'Priya Nair', 'email': email, 'password': 'a-strong-pass', 'job_title': '',
                'organisation': {'name': org.get('name', 'Nair Analytics'), 'industry': '', 'website': website,
                                 'contact_email': org.get('contact_email', ''), 'location': ''}}

    def test_form_registration_with_personal_email_and_no_website(self):
        c = app.test_client()
        res, body = _api(c, 'post', '/api/auth/register_recruiter',
                         json=self.form_payload('Priya.Nair@Gmail.com'))
        self.assertEqual(res.status_code, 201, body)
        self.assertEqual(body['organisation']['verification_status'], 'unverified')
        self.assertEqual(body['organisation']['website'], '')
        self.assertEqual(body['student']['email'], 'priya.nair@gmail.com')
        self.assertNotIn('password', json.dumps(body).lower().replace('password_', ''))
        # logged in straight away, so the redirect to /recruiter/organisation works
        res, me = _api(c, 'get', '/api/recruiter/me')
        self.assertEqual(res.status_code, 200)
        self.assertFalse(me['can_publish_jobs'])

    def test_pending_verification_does_not_block_sign_in(self):
        c = app.test_client()
        self.assertEqual(c.post('/api/auth/register_recruiter',
                                json=self.form_payload('lead@nair.example.com')).status_code, 201)
        # Website is optional at sign-up but required (with proof) before verification can be requested
        res, body = _api(c, 'post', '/api/recruiter/organisation/verification', json={'registration_id': 'U12345'})
        self.assertEqual(res.status_code, 400)
        self.assertIn('website', body['error'].lower())
        self.assertEqual(c.put('/api/recruiter/organisation', json={'website': 'https://nair.example.com'}).status_code, 200)
        res, body = _api(c, 'post', '/api/recruiter/organisation/verification', json={'registration_id': 'U12345'})
        self.assertEqual(res.status_code, 200, body)
        self.assertEqual(body['organisation']['verification_status'], 'pending')
        c.post('/api/auth/logout')
        res, body = _api(c, 'post', '/api/auth/login', json={
            'email': 'lead@nair.example.com', 'password': 'a-strong-pass', 'portal': 'recruiter'})
        self.assertEqual(res.status_code, 200, body)
        res, me = _api(c, 'get', '/api/recruiter/me')
        self.assertEqual(me['organisation']['verification_status'], 'pending')
        # still gated until an administrator approves
        self.assertFalse(me['can_publish_jobs'])
        self.assertEqual(c.get('/api/recruiter/candidates/search?skills=python').status_code, 403)

    def test_form_errors_are_specific_json_and_create_nothing(self):
        with app.app_context():
            before = (Organisation.query.count(), Student.query.count())
        cases = [
            (self.form_payload('new1@nair.example.com', website='nair.com'), 400, 'https'),
            (self.form_payload('ASHA@TEST.COM'), 409, 'already exists'),          # case-insensitive duplicate
            (self.form_payload('not-an-email'), 400, 'valid email'),
            ({**self.form_payload('new2@nair.example.com'), 'password': 'short'}, 400, 'at least 8'),
            (self.form_payload('new3@nair.example.com', name=''), 400, 'organisation name'),
            (self.form_payload('new4@nair.example.com', contact_email='hr@'), 400, 'contact email'),
        ]
        c = app.test_client()
        for payload, status, phrase in cases:
            res = c.post('/api/auth/register_recruiter', json=payload,
                         headers={'Origin': 'http://localhost:3000'})
            body = res.get_json(silent=True)
            self.assertEqual(res.status_code, status, (payload['email'], body))
            self.assertIsInstance(body, dict, 'error responses must be JSON so the form can show them')
            self.assertIn(phrase, body['error'].lower())
            # the browser can read the message only if CORS headers are on error responses too
            self.assertEqual(res.headers.get('Access-Control-Allow-Origin'), 'http://localhost:3000')
        with app.app_context():
            self.assertEqual((Organisation.query.count(), Student.query.count()), before)

    def test_role_separation_is_enforced_server_side(self):
        # recruiters cannot use student or passport-owner APIs
        for url in ('/api/student/skills', '/api/student/jobs', '/api/passport/me'):
            self.assertEqual(self.rec.get(url).status_code, 403, url)
        # students and admins cannot use recruiter APIs
        self.assertEqual(self.stu.get('/api/recruiter/me').status_code, 403)
        self.assertEqual(self.adm.get('/api/recruiter/jobs').status_code, 403)
        self.assertEqual(app.test_client().get('/api/recruiter/me').status_code, 401)
        # recruiters cannot use the admin review queue; students cannot use candidate settings as recruiters
        self.assertEqual(self.rec.get('/api/recruiter/admin/organisations').status_code, 403)
        self.assertEqual(self.rec.get('/api/candidate/discovery').status_code, 403)

    def test_login_portal_checks(self):
        c = app.test_client()
        res, _ = _api(c, 'post', '/api/auth/login', json={'email': 'asha@test.com', 'password': PW, 'portal': 'recruiter'})
        self.assertEqual(res.status_code, 403)
        res, _ = _api(c, 'post', '/api/auth/login',
                      json={'email': 'rita@acme.example.com', 'password': PW, 'portal': 'student'})
        self.assertEqual(res.status_code, 403)
        res, body = _api(c, 'post', '/api/auth/login',
                         json={'email': 'rita@acme.example.com', 'password': PW, 'portal': 'recruiter'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(body['student']['role'], 'recruiter')


class OrganisationVerificationTests(RecruiterBase):
    def test_verification_flow_and_signals(self):
        res, body = _api(self.rec, 'post', '/api/recruiter/organisation/verification', json={})
        self.assertEqual(res.status_code, 400)      # needs at least one piece of proof
        res, body = _api(self.rec, 'post', '/api/recruiter/organisation/verification',
                         json={'linkedin_url': 'https://www.linkedin.com/company/acme'})
        self.assertEqual(res.status_code, 200, body)
        org = body['organisation']
        self.assertEqual(org['verification_status'], 'pending')
        self.assertTrue(org['verification_details']['signals']['domains_match'])  # rita@acme.example.com
        res, q = _api(self.adm, 'get', '/api/recruiter/admin/organisations?status=pending')
        self.assertEqual([o['name'] for o in q['organisations']], ['Acme Analytics'])
        res, _ = _api(self.adm, 'post', f"/api/recruiter/admin/organisations/{org['id']}/review",
                      json={'decision': 'rejected'})
        self.assertEqual(res.status_code, 400)      # rejecting needs a reason
        res, _ = _api(self.adm, 'post', f"/api/recruiter/admin/organisations/{org['id']}/review",
                      json={'decision': 'verified'})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(_api(self.rec, 'get', '/api/recruiter/me')[1]['can_publish_jobs'])

    def test_identity_change_resets_verification(self):
        self.verify_org(self.rec)
        res, body = _api(self.rec, 'put', '/api/recruiter/organisation', json={'industry': 'Analytics'})
        self.assertFalse(body['verification_reset'])
        res, body = _api(self.rec, 'put', '/api/recruiter/organisation', json={'website': 'https://new.example.com'})
        self.assertTrue(body['verification_reset'])
        self.assertEqual(body['organisation']['verification_status'], 'unverified')

    def test_revoking_verification_closes_jobs(self):
        job = self.published_job()
        res, body = _api(self.adm, 'post', f"/api/recruiter/admin/organisations/{self.org_id(self.rec)}/review",
                         json={'decision': 'revoked', 'note': 'Domain no longer owned'})
        self.assertEqual(res.status_code, 200, body)
        self.assertEqual(body['jobs_closed'], 1)
        with app.app_context():
            self.assertEqual(db.session.get(JobListing, job['id']).status, 'closed')


class JobPostingTests(RecruiterBase):
    def test_draft_publish_and_integration_with_job_discovery(self):
        job = self.create_job()
        self.assertEqual(job['status'], 'draft')
        self.assertTrue(job['is_employer_posted'])
        self.assertEqual(job['required_skills'], ['python', 'sql', 'docker'])
        self.assertEqual(job['experience_level'], 'Entry-Level')
        # unpublished drafts are invisible to students
        self.assertEqual(self.stu.get(f"/api/student/jobs/{job['id']}").status_code, 404)
        self.assertEqual(self.stu.get(f"/api/student/jobs/{job['id']}/match").status_code, 404)
        self.assertNotIn(job['id'], [j['id'] for j in _api(self.stu, 'get', '/api/student/jobs')[1]['jobs']])
        # cannot publish before the organisation is verified
        res, _ = _api(self.rec, 'post', f"/api/recruiter/jobs/{job['id']}/publish")
        self.assertEqual(res.status_code, 403)
        self.verify_org(self.rec)
        res, body = _api(self.rec, 'post', f"/api/recruiter/jobs/{job['id']}/publish")
        self.assertEqual(res.status_code, 200, body)
        # now a normal listing: search, origin filter, match score and labels
        res, listing = _api(self.stu, 'get', '/api/student/jobs?origin=employer')
        self.assertEqual([j['id'] for j in listing['jobs']], [job['id']])
        found = listing['jobs'][0]
        self.assertTrue(found['accepts_in_app_applications'])
        self.assertEqual(found['employer']['name'], 'Acme Analytics')
        self.assertTrue(found['employer']['is_verified'])
        self.assertEqual(found['freshness']['verification_status'], 'employer_posted')
        self.assertIsNotNone(found['match_score'])
        self.assertEqual(_api(self.stu, 'get', '/api/student/jobs?origin=external')[1]['jobs'], [])

    def test_validation(self):
        res, body = _api(self.rec, 'post', '/api/recruiter/jobs', json={**JOB, 'required_skills': []})
        self.assertEqual(res.status_code, 400)
        res, body = _api(self.rec, 'post', '/api/recruiter/jobs', json={**JOB, 'deadline': '2020-01-01'})
        self.assertEqual(res.status_code, 400)
        res, body = _api(self.rec, 'post', '/api/recruiter/jobs', json={**JOB, 'salary_min': 10, 'salary_max': 5})
        self.assertEqual(res.status_code, 400)
        res, body = _api(self.rec, 'post', '/api/recruiter/jobs', json={**JOB, 'job_type': 'Gig'})
        self.assertEqual(res.status_code, 400)

    def test_cross_organisation_access_is_denied(self):
        job = self.published_job()
        jid = job['id']
        for method, url in (('get', f'/api/recruiter/jobs/{jid}'), ('put', f'/api/recruiter/jobs/{jid}'),
                            ('post', f'/api/recruiter/jobs/{jid}/close'), ('post', f'/api/recruiter/jobs/{jid}/publish'),
                            ('delete', f'/api/recruiter/jobs/{jid}'), ('get', f'/api/recruiter/jobs/{jid}/applicants')):
            res = getattr(self.rec2, method)(url, json={'title': 'Hacked'})
            self.assertEqual(res.status_code, 404, (method, url))
        res, apply_body = self.apply(jid)
        app_id = apply_body['application']['id']
        res, _ = _api(self.rec2, 'post', f'/api/recruiter/applications/{app_id}/stage', json={'stage': 'rejected'})
        self.assertEqual(res.status_code, 404)
        self.assertEqual(self.rec2.get(f'/api/recruiter/candidates/{self.ref()}').status_code, 404)
        with app.app_context():
            self.assertEqual(db.session.get(JobListing, jid).title, JOB['title'])
            self.assertEqual(db.session.get(JobApplication, app_id).stage, 'new')

    def test_close_and_delete_rules(self):
        job = self.published_job()
        res, _ = _api(self.rec, 'delete', f"/api/recruiter/jobs/{job['id']}")
        self.assertEqual(res.status_code, 400)        # published jobs are closed, not deleted
        res, body = _api(self.rec, 'post', f"/api/recruiter/jobs/{job['id']}/close")
        self.assertEqual(body['job']['status'], 'closed')
        res, body = self.apply(job['id'])
        self.assertEqual(res.status_code, 400)        # closed jobs take no applications
        draft = self.create_job(title='Draft only')
        self.assertEqual(self.rec.delete(f"/api/recruiter/jobs/{draft['id']}").status_code, 200)

    def test_expiry_rules_for_employer_jobs(self):
        from utils.job_discovery.sync_service import apply_expiry
        job = self.published_job()
        now = datetime.now(timezone.utc)
        with app.app_context():
            j = db.session.get(JobListing, job['id'])
            j.posting_date = (now - timedelta(days=200)).replace(tzinfo=None)   # old, but employer keeps it open
            db.session.commit()
            apply_expiry(now, healthy_providers=[])
            db.session.commit()
            self.assertEqual(db.session.get(JobListing, job['id']).status, 'active')
            j = db.session.get(JobListing, job['id'])
            j.deadline = (now - timedelta(hours=1)).replace(tzinfo=None)
            db.session.commit()
            apply_expiry(now, healthy_providers=[])
            db.session.commit()
            j = db.session.get(JobListing, job['id'])
            self.assertEqual((j.status, j.expiry_reason), ('expired', 'Application deadline has passed'))


class ApplicationAndConsentTests(RecruiterBase):
    def test_application_requires_consent_and_shares_only_selected_sections(self):
        job = self.published_job()
        res, body = _api(self.stu, 'post', f"/api/student/jobs/{job['id']}/apply",
                         json={'contact_email': 'asha.apply@example.com'})
        self.assertEqual(res.status_code, 400)        # no consent
        res, body = self.apply(job['id'], sections={'skills': True})
        self.assertEqual(res.status_code, 201, body)
        self.assertEqual(body['application']['stage'], 'new')
        self.assertTrue(body['application']['is_in_app'])

        res, prof = _api(self.rec, 'get', f"/api/recruiter/candidates/{self.ref()}?job_id={job['id']}")
        self.assertEqual(res.status_code, 200, prof)
        self.assertEqual(prof['basis'], 'application')
        self.assertEqual(prof['passport']['sections'], ['skills'])
        self.assertNotIn('career_interests', prof['passport'])
        self.assertNotIn('projects', prof['passport'])
        raw = json.dumps(prof)
        self.assertNotIn('asha@test.com', raw)        # account email never exposed
        self.assertIn('asha.apply@example.com', raw)  # contact email the student entered for this application
        # access is logged and visible to the student
        res, access = _api(self.stu, 'get', '/api/candidate/access')
        self.assertEqual(access['access_log'][0]['organisation'], 'Acme Analytics')
        self.assertEqual(access['access_log'][0]['basis'], 'application')
        self.assertEqual(access['organisations_with_application_access'][0]['jobs'][0]['shared_sections'], ['skills'])

    def test_withdrawing_ends_access(self):
        job = self.published_job()
        self.apply(job['id'])
        ref = self.ref()
        self.assertEqual(self.rec.get(f'/api/recruiter/candidates/{ref}').status_code, 200)
        self.assertEqual(self.stu.post(f"/api/student/jobs/{job['id']}/withdraw").status_code, 200)
        self.assertEqual(self.rec.get(f'/api/recruiter/candidates/{ref}').status_code, 404)

    def test_unrelated_student_is_not_accessible(self):
        self.published_job()
        ref_other = self.ref(self.other_sid)
        self.assertEqual(self.rec.get(f'/api/recruiter/candidates/{ref_other}').status_code, 404)
        self.assertEqual(self.rec.get('/api/recruiter/candidates/not-a-real-ref').status_code, 404)

    def test_compatibility_report_is_explainable_and_correct(self):
        job = self.published_job()
        self.apply(job['id'])
        res, prof = _api(self.rec, 'get', f"/api/recruiter/candidates/{self.ref()}?job_id={job['id']}")
        rep = prof['report']
        s = rep['summary']
        self.assertEqual((s['required_total'], s['required_matched'], s['required_verified']), (3, 2, 1))
        self.assertEqual(s['missing_mandatory'], ['docker'])
        self.assertEqual(s['needs_verification'], ['sql'])
        self.assertEqual(s['matching_preferred'], [])
        # python verified (1.0), sql resume-applied (0.70), docker missing; aws preferred missing
        self.assertEqual(rep['skill_fit_score'], round(100 * 3 * (1.0 + 0.70) / (3 * 3 + 1), 1))
        py = next(r for r in rep['required'] if r['skill'] == 'python')
        self.assertTrue(py['verified'])
        self.assertTrue(any('Assessment 80%' in e for e in py['evidence']))
        self.assertTrue(any('sql' in l for l in rep['limitations']))

    def test_report_respects_skill_filter(self):
        job = self.published_job()
        self.apply(job['id'], skill_filter='verified')
        res, prof = _api(self.rec, 'get', f"/api/recruiter/candidates/{self.ref()}?job_id={job['id']}")
        rep = prof['report']
        self.assertEqual(rep['summary']['missing_mandatory'], ['sql', 'docker'])   # sql not shared
        self.assertTrue(any('only verified skills' in l for l in rep['limitations']))

    def test_report_without_shared_skills_has_no_score(self):
        passport = {'sections': ['profile'], 'name': 'X'}
        rep = compatibility_report(passport, {'required_skills': ['python'], 'preferred_skills': []})
        self.assertIsNone(rep['skill_fit_score'])
        self.assertEqual(rep['fit_label'], 'Not enough information')


class PipelineTests(RecruiterBase):
    def test_stage_changes_reach_the_student_and_notes_stay_internal(self):
        job = self.published_job()
        _, body = self.apply(job['id'])
        app_id = body['application']['id']
        res, _ = _api(self.rec, 'post', f'/api/recruiter/applications/{app_id}/stage', json={'stage': 'bogus'})
        self.assertEqual(res.status_code, 400)
        res, body = _api(self.rec, 'post', f'/api/recruiter/applications/{app_id}/stage',
                         json={'stage': 'shortlisted', 'message': 'We liked your project.'})
        self.assertEqual(res.status_code, 200, body)
        ref = self.ref()
        res, _ = _api(self.rec, 'post', f'/api/recruiter/candidates/{ref}/notes',
                      json={'kind': 'note', 'body': 'Strong SQL in the call. INTERNAL-ONLY-MARKER'})
        self.assertEqual(res.status_code, 201)
        res, _ = _api(self.rec, 'post', f'/api/recruiter/candidates/{ref}/notes',
                      json={'kind': 'interview', 'application_id': app_id})
        self.assertEqual(res.status_code, 400)       # interview round required
        res, note = _api(self.rec, 'post', f'/api/recruiter/candidates/{ref}/notes',
                         json={'kind': 'interview', 'interview_round': 'Technical 1', 'outcome': 'passed',
                               'application_id': app_id, 'body': 'Good'})
        self.assertEqual(res.status_code, 201, note)

        res, upd = _api(self.stu, 'get', '/api/candidate/updates')
        stages = [u['to_stage'] for u in upd['application_updates']]
        self.assertEqual(stages, ['shortlisted', 'new'])
        self.assertEqual(upd['application_updates'][0]['message'], 'We liked your project.')
        self.assertEqual(upd['unread_count'], 2)
        self.assertNotIn('INTERNAL-ONLY-MARKER', json.dumps(upd))
        res, apps = _api(self.stu, 'get', '/api/student/jobs/applied')
        self.assertEqual(apps['applications'][0]['status'], 'Shortlisted')
        self.assertEqual(self.stu.post('/api/candidate/updates/read').status_code, 200)
        self.assertEqual(_api(self.stu, 'get', '/api/candidate/updates')[1]['unread_count'], 0)

        res, pipe = _api(self.rec, 'get', '/api/recruiter/pipeline')
        col = next(s for s in pipe['stages'] if s['key'] == 'shortlisted')
        self.assertEqual([a['application_id'] for a in col['applications']], [app_id])
        res, appl = _api(self.rec, 'get', f"/api/recruiter/jobs/{job['id']}/applicants")
        self.assertEqual(appl['applicants'][0]['stage'], 'shortlisted')
        self.assertIsNotNone(appl['applicants'][0]['report'])

    def test_shortlists(self):
        job = self.published_job()
        self.apply(job['id'])
        ref = self.ref()
        res, sl = _api(self.rec, 'post', '/api/recruiter/shortlists', json={'name': 'Data team', 'job_id': job['id']})
        self.assertEqual(res.status_code, 201)
        sid = sl['shortlist']['id']
        res, _ = _api(self.rec, 'post', f'/api/recruiter/shortlists/{sid}/entries', json={'candidate_ref': ref})
        self.assertEqual(res.status_code, 201)
        res, _ = _api(self.rec, 'post', f'/api/recruiter/shortlists/{sid}/entries', json={'candidate_ref': ref})
        self.assertEqual(res.status_code, 409)
        self.assertEqual(self.rec2.get(f'/api/recruiter/shortlists/{sid}').status_code, 404)
        res, got = _api(self.rec, 'get', f'/api/recruiter/shortlists/{sid}')
        self.assertEqual(got['shortlist']['entries'][0]['name'], 'Asha Rao')
        # after the student withdraws, the entry no longer reveals who it was
        self.stu.post(f"/api/student/jobs/{job['id']}/withdraw")
        res, got = _api(self.rec, 'get', f'/api/recruiter/shortlists/{sid}')
        entry = got['shortlist']['entries'][0]
        self.assertFalse(entry['available'])
        self.assertNotIn('name', entry)


class DiscoveryTests(RecruiterBase):
    def enable(self, **over):
        payload = {'is_discoverable': True, 'consent': True,
                   'visibility': {'sections': {'profile': True, 'skills': True, 'assessments': True,
                                               'career_interests': True, 'education': True},
                                  'skill_filter': 'all'}}
        payload.update(over)
        return _api(self.stu, 'put', '/api/candidate/discovery', json=payload)

    def test_opt_in_search_and_revocation(self):
        res, _ = _api(self.rec, 'get', '/api/recruiter/candidates/search?skills=python')
        self.assertEqual(res.status_code, 403)        # unverified organisation
        self.verify_org(self.rec)
        res, body = _api(self.rec, 'get', '/api/recruiter/candidates/search?skills=python')
        self.assertEqual(body['candidates'], [])      # nobody opted in
        res, body = self.enable(consent=False)
        self.assertEqual(res.status_code, 400)
        res, body = self.enable()
        self.assertEqual(res.status_code, 200, body)

        res, body = _api(self.rec, 'get', '/api/recruiter/candidates/search?skills=python,docker')
        self.assertEqual([c['name'] for c in body['candidates']], ['Asha Rao'])
        cand = body['candidates'][0]
        self.assertEqual(cand['report']['summary']['missing_mandatory'], ['docker'])
        self.assertNotIn('asha@test.com', json.dumps(body))
        # filters
        self.assertEqual(len(_api(self.rec, 'get', '/api/recruiter/candidates/search?skills=sql&verified_only=1')[1]['candidates']), 0)
        self.assertEqual(len(_api(self.rec, 'get', '/api/recruiter/candidates/search?skills=python&verified_only=1')[1]['candidates']), 1)
        self.assertEqual(len(_api(self.rec, 'get', '/api/recruiter/candidates/search?skills=python,docker&match_all=1')[1]['candidates']), 0)
        self.assertEqual(len(_api(self.rec, 'get', '/api/recruiter/candidates/search?min_assessment=75')[1]['candidates']), 1)
        self.assertEqual(len(_api(self.rec, 'get', '/api/recruiter/candidates/search?min_assessment=90')[1]['candidates']), 0)
        self.assertEqual(len(_api(self.rec, 'get', '/api/recruiter/candidates/search?role=data%20engineer')[1]['candidates']), 1)
        self.assertEqual(len(_api(self.rec, 'get', '/api/recruiter/candidates/search?min_readiness=10')[1]['candidates']), 0)  # readiness not shared
        self.assertEqual(len(_api(self.rec, 'get', '/api/recruiter/candidates/search?has_projects=1')[1]['candidates']), 0)

        ref = cand['candidate_ref']
        res, prof = _api(self.rec, 'get', f'/api/recruiter/candidates/{ref}')
        self.assertEqual(prof['basis'], 'discovery')
        # unverified organisation cannot see discoverable students
        self.assertEqual(self.rec2.get(f'/api/recruiter/candidates/{ref}').status_code, 404)
        # switching off removes access immediately
        self.enable(is_discoverable=False)
        self.assertEqual(self.rec.get(f'/api/recruiter/candidates/{ref}').status_code, 404)
        self.assertEqual(_api(self.rec, 'get', '/api/recruiter/candidates/search?skills=python')[1]['candidates'], [])

    def test_invitations(self):
        job = self.published_job()
        self.enable()
        ref = self.ref()
        res, body = _api(self.rec, 'post', f'/api/recruiter/candidates/{ref}/invite',
                         json={'job_id': job['id'], 'message': 'Would love you to apply.'})
        self.assertEqual(res.status_code, 201, body)
        res, _ = _api(self.rec, 'post', f'/api/recruiter/candidates/{ref}/invite', json={'job_id': job['id']})
        self.assertEqual(res.status_code, 409)
        res, upd = _api(self.stu, 'get', '/api/candidate/updates')
        inv = upd['invitations'][0]
        self.assertEqual((inv['job_title'], inv['organisation']['name'], inv['applied']),
                         (JOB['title'], 'Acme Analytics', False))
        self.apply(job['id'])
        self.assertTrue(_api(self.stu, 'get', '/api/candidate/updates')[1]['invitations'][0]['applied'])

    def test_job_matches_rank_discoverable_candidates(self):
        job = self.published_job()
        self.enable()
        res, body = _api(self.rec, 'get', f"/api/recruiter/jobs/{job['id']}/matches")
        self.assertEqual(res.status_code, 200, body)
        self.assertEqual(body['candidates'][0]['report']['summary']['required_verified'], 1)


class GovernanceTests(RecruiterBase):
    def test_student_account_deletion_removes_recruiter_records(self):
        job = self.published_job()
        _, body = self.apply(job['id'])
        app_id = body['application']['id']
        ref = self.ref()
        self.rec.get(f'/api/recruiter/candidates/{ref}')
        _api(self.rec, 'post', f'/api/recruiter/candidates/{ref}/notes', json={'body': 'x'})
        _api(self.rec, 'post', f'/api/recruiter/applications/{app_id}/stage', json={'stage': 'interview'})
        res, _ = _api(self.stu, 'delete', '/api/student/account/delete', json={'confirmation': 'DELETE_MY_ACCOUNT'})
        self.assertEqual(res.status_code, 200)
        with app.app_context():
            self.assertIsNone(db.session.get(Student, self.sid))
            for model in (JobApplication, ApplicationEvent, RecruitmentNote, RecruiterAccessLog,
                          CandidateDiscoverySetting):
                self.assertEqual(model.query.count(), 0, model.__name__)
            self.assertIsNotNone(db.session.get(JobListing, job['id']))   # the employer's job stays

    def test_data_export_includes_employer_access(self):
        job = self.published_job()
        self.apply(job['id'])
        self.rec.get(f'/api/recruiter/candidates/{self.ref()}')
        res, exp = _api(self.stu, 'get', '/api/student/account/export')
        self.assertEqual(exp['employer_access']['profile_views'][0]['organisation'], 'Acme Analytics')
        self.assertEqual(exp['employer_access']['application_updates'][0]['to_stage'], 'new')

    def test_audit_log_records_recruiter_actions(self):
        from models import AuditLog
        job = self.published_job()
        with app.app_context():
            actions = {a.action for a in AuditLog.query.all()}
        self.assertTrue({'recruiter.registered', 'recruiter.org_verification_requested',
                         'admin.organisation_reviewed', 'recruiter.job_created', 'recruiter.job_published'} <= actions)


class RateLimitTests(unittest.TestCase):
    def setUp(self):
        reset_db()
        make_student("rl@test.com")
        from utils.rate_limit import reset
        reset()
        app.config['RATELIMIT_ENABLED'] = True

    def tearDown(self):
        app.config['RATELIMIT_ENABLED'] = False
        from utils.rate_limit import reset
        reset()

    def test_failed_logins_are_throttled(self):
        c = app.test_client()
        for _ in range(10):
            self.assertEqual(c.post('/api/auth/login', json={'email': 'rl@test.com', 'password': 'wrong-pass'}).status_code, 401)
        res = c.post('/api/auth/login', json={'email': 'rl@test.com', 'password': PW})
        self.assertEqual(res.status_code, 429)
        self.assertIn('Retry-After', res.headers)
        # other accounts are not affected
        make_student("other@test.com")
        self.assertEqual(c.post('/api/auth/login', json={'email': 'other@test.com', 'password': PW}).status_code, 200)

    def test_recruiter_registration_is_throttled(self):
        c = app.test_client()
        codes = [c.post('/api/auth/register_recruiter', json={
            'name': 'R', 'email': f'r{i}@x.example.com', 'password': PW,
            'organisation': {'name': f'Org {i}'}}).status_code for i in range(6)]
        self.assertEqual(codes[:5], [201] * 5)
        self.assertEqual(codes[5], 429)


if __name__ == '__main__':
    unittest.main()
