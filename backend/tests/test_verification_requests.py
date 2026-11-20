"""
Recruiter "request verification": consent and permission checks, the student's
accept / decline decision, completion through the real quiz and evidence-review
flows, recruiter notifications, cancellation and loss of access.
"""
from tests.base import app, db, reset_db, make_student, login  # must be first

import unittest
from unittest import mock

from models import QuestionBank, Skill, SkillVerificationRequest
from tests.test_recruiter_portal import RecruiterBase, _api

DISCOVERY = {'is_discoverable': True, 'consent': True,
             'visibility': {'sections': {'profile': True, 'skills': True, 'assessments': True,
                                         'projects': True, 'career_interests': True},
                            'skill_filter': 'all'}}


class VerificationRequestBase(RecruiterBase):
    def setUp(self):
        super().setUp()
        with app.app_context():
            for i in range(6):
                db.session.add(QuestionBank(skill_name='sql', question=f'SQL question {i}', option_a='right',
                                            option_b='wrong-b', option_c='wrong-c', option_d='wrong-d',
                                            correct_answer='A', difficulty='Medium'))
            db.session.add(Skill(student_id=self.sid, skill_name='rust', source='self_declared'))
            db.session.commit()
            self.sql_skill_id = Skill.query.filter_by(student_id=self.sid, skill_name='sql').first().id

    def make_visible(self, **visibility):
        payload = dict(DISCOVERY)
        if visibility:
            payload = {**DISCOVERY, 'visibility': {**DISCOVERY['visibility'], **visibility}}
        res, body = _api(self.stu, 'put', '/api/candidate/discovery', json=payload)
        self.assertEqual(res.status_code, 200, body)

    def request(self, skills, client=None, ref=None, **extra):
        return _api(client or self.rec, 'post',
                    f'/api/recruiter/candidates/{ref or self.ref()}/verification_requests',
                    json={'skills': skills, 'message': 'Please verify for our data role', **extra})

    def student_requests(self):
        res, body = _api(self.stu, 'get', '/api/candidate/verification_requests')
        self.assertEqual(res.status_code, 200, body)
        return body['requests']

    def respond(self, req_id, action, note=''):
        return _api(self.stu, 'post', f'/api/candidate/verification_requests/{req_id}/respond',
                    json={'action': action, 'note': note})

    def pass_sql_quiz(self, correct=True):
        with mock.patch('routes.student.ensure_minimum_questions', lambda *_: None):
            quiz = self.stu.get(f'/api/student/get_quiz/{self.sql_skill_id}').get_json()
        answers = {}
        for q in quiz['questions']:
            want = 'right' if correct else 'wrong-b'
            answers[str(q['id'])] = next(L for L in 'ABCD' if q[f'option_{L.lower()}'] == want)
        res = self.stu.post(f'/api/student/submit_quiz/{self.sql_skill_id}', json={'answers': answers})
        self.assertEqual(res.status_code, 201, res.get_json())
        return res.get_json()


class PermissionTests(VerificationRequestBase):
    def test_no_consent_means_not_found(self):
        self.verify_org(self.rec)
        res, body = self.request(['sql'])          # student is not visible and never applied
        self.assertEqual(res.status_code, 404, body)
        with app.app_context():
            self.assertEqual(SkillVerificationRequest.query.count(), 0)

    def test_unverified_org_with_application_access_cannot_request(self):
        job = self.published_job()
        self.apply(job['id'])
        # Revoke the organisation: application access remains, requests are refused
        with app.app_context():
            from models import Organisation
            org = db.session.get(Organisation, self.org_id(self.rec))
            org.verification_status = 'rejected'
            db.session.commit()
        res, body = self.request(['sql'])
        self.assertEqual(res.status_code, 403, body)

    def test_students_and_other_orgs_cannot_use_recruiter_endpoints(self):
        self.verify_org(self.rec)
        self.make_visible()
        res, body = self.request(['sql'])
        self.assertEqual(res.status_code, 201, body)
        req_id = body['requests'][0]['id']
        # a student cannot send requests or list an organisation's requests
        self.assertEqual(self.stu.get('/api/recruiter/verification_requests').status_code, 403)
        # another organisation cannot see or cancel it
        self.verify_org(self.rec2)
        res, body = _api(self.rec2, 'get', '/api/recruiter/verification_requests')
        self.assertEqual(body['requests'], [])
        self.assertEqual(self.rec2.post(f'/api/recruiter/verification_requests/{req_id}/cancel').status_code, 404)
        # a recruiter cannot answer for the student; another student cannot either
        self.assertEqual(self.rec.post(f'/api/candidate/verification_requests/{req_id}/respond',
                                       json={'action': 'accept'}).status_code, 403)
        bob = app.test_client()
        login(bob, 'bob@test.com')
        self.assertEqual(bob.post(f'/api/candidate/verification_requests/{req_id}/respond',
                                  json={'action': 'accept'}).status_code, 404)

    def test_only_shared_unverified_skills_can_be_requested(self):
        self.verify_org(self.rec)
        self.make_visible(skill_filter='evidence')   # hides self-declared 'rust' and resume-only 'sql'
        res, body = self.request(['rust'])
        self.assertEqual(res.status_code, 409, body)
        self.assertIn('Not shown', body['error'])
        # same answer as for a skill the student does not have at all
        res2, body2 = self.request(['haskell'])
        self.assertEqual(body['skipped'][0]['reason'], body2['skipped'][0]['reason'])

        self.make_visible()                           # all skills shown
        res, prof = _api(self.rec, 'get', f'/api/recruiter/candidates/{self.ref()}')
        names = {s['skill_name'] for s in prof['requestable_skills']}
        self.assertEqual(names, {'sql', 'rust'})      # python is already verified
        res, body = self.request(['python'])
        self.assertEqual(res.status_code, 409)
        self.assertIn('Already verified', body['error'])

        res, body = self.request(['sql', 'rust', 'python'])
        self.assertEqual(res.status_code, 201, body)
        self.assertEqual({r['skill_name'] for r in body['requests']}, {'sql', 'rust'})
        self.assertEqual(body['skipped'][0]['reason'], 'Already verified')
        res, body = self.request(['SQL'])             # duplicate, any case
        self.assertEqual(res.status_code, 409)
        self.assertIn('already open', body['error'])

    def test_validation(self):
        self.verify_org(self.rec)
        self.make_visible()
        self.assertEqual(self.request([])[0].status_code, 400)
        self.assertEqual(self.request('x' * 61)[0].status_code, 400)
        self.assertEqual(self.request(['a', 'b', 'c', 'd', 'e', 'f'])[0].status_code, 400)
        self.assertEqual(self.request(['sql'], message='m' * 501)[0].status_code, 400)
        self.assertEqual(self.request(['sql'], job_id=999999)[0].status_code, 404)


class WorkflowTests(VerificationRequestBase):
    def test_full_flow_quiz_completion_notifies_recruiter(self):
        job = self.published_job()
        self.make_visible()
        res, body = self.request(['sql'], job_id=job['id'])
        self.assertEqual(res.status_code, 201, body)

        # Student is notified in the employer updates feed
        res, upd = _api(self.stu, 'get', '/api/candidate/updates')
        self.assertEqual(len(upd['verification_requests']), 1)
        item = upd['verification_requests'][0]
        self.assertEqual(item['status'], 'pending')
        self.assertFalse(item['seen'])
        self.assertEqual(item['organisation']['name'], 'Acme Analytics')
        self.assertEqual(item['job_title'], job['title'])
        self.assertEqual(item['skill_id'], self.sql_skill_id)
        self.assertGreaterEqual(upd['unread_count'], 1)

        # A failed attempt before accepting is not reported and does not complete anything
        self.pass_sql_quiz(correct=False)
        res = self.respond(item['id'], 'accept', 'Happy to')
        self.assertEqual(res[0].status_code, 200, res[1])
        self.assertEqual(res[1]['request']['status'], 'accepted')

        res, lst = _api(self.rec, 'get', '/api/recruiter/verification_requests')
        r = lst['requests'][0]
        self.assertEqual((r['status'], r['unread'], r['student_note']), ('accepted', True, 'Happy to'))
        self.assertEqual(r['candidate_name'], 'Asha Rao')
        self.assertEqual(lst['unread'], 1)
        self.assertNotIn('score', str(r).lower().replace('skill_fit', ''))   # no failed score leaked
        self.rec.post('/api/recruiter/verification_requests/read')

        # Passing the real quiz completes it immediately (hook in submit_quiz)
        self.pass_sql_quiz(correct=True)
        with app.app_context():
            stored = SkillVerificationRequest.query.one()
            self.assertEqual(stored.status, 'completed')
            self.assertEqual(stored.completed_via, 'assessment')
            self.assertFalse(stored.seen_by_recruiter)
        res, dash = _api(self.rec, 'get', '/api/recruiter/dashboard')
        self.assertEqual(dash['verification_requests'], {'open': 0, 'unread': 1})
        res, prof = _api(self.rec, 'get', f'/api/recruiter/candidates/{self.ref()}')
        self.assertEqual(prof['verification_requests'][0]['status'], 'completed')
        self.assertIn('assessment', prof['verification_requests'][0]['completed_via_label'])
        self.assertNotIn('sql', {s['skill_name'] for s in prof['requestable_skills']})
        sql = next(s for s in prof['passport']['skills'] if s['skill_name'] == 'sql')
        self.assertEqual(sql['status'], 'verified')

        # student sees it completed
        self.assertEqual(self.student_requests()[0]['status'], 'completed')

    def test_evidence_review_completes_request(self):
        self.verify_org(self.rec)
        self.make_visible()
        res, body = self.request(['rust'])
        req_id = body['requests'][0]['id']
        self.respond(req_id, 'accept')
        with app.app_context():
            rust_id = Skill.query.filter_by(student_id=self.sid, skill_name='rust').first().id
        res, ev = _api(self.stu, 'post', '/api/passport/me/evidence', json={
            'kind': 'project', 'title': 'Rust CLI tool', 'url': 'https://github.com/asha/rust-cli',
            'skill_ids': [rust_id]})
        self.assertEqual(res.status_code, 201, ev)
        ev_id = ev['evidence']['id']
        self.assertEqual(self.stu.post(f'/api/passport/me/evidence/{ev_id}/request_review').status_code, 200)
        # pending review is not completion
        self.assertEqual(self.student_requests()[0]['status'], 'accepted')
        res, out = _api(self.adm, 'post', f'/api/passport/admin/evidence/{ev_id}/review',
                        json={'decision': 'verified'})
        self.assertEqual(res.status_code, 200, out)
        with app.app_context():
            r = db.session.get(SkillVerificationRequest, req_id)
            self.assertEqual((r.status, r.completed_via), ('completed', 'reviewed_evidence'))

    def test_pending_request_is_not_completed_without_consent(self):
        self.verify_org(self.rec)
        self.make_visible()
        self.request(['sql'])
        self.pass_sql_quiz(correct=True)                   # verified on their own, never accepted
        reqs = self.student_requests()
        self.assertEqual(reqs[0]['status'], 'pending')
        self.assertTrue(reqs[0]['skill_verified'])
        res, lst = _api(self.rec, 'get', '/api/recruiter/verification_requests')
        self.assertEqual(lst['requests'][0]['status'], 'pending')
        self.assertEqual(lst['requests'][0]['completed_via'], [])
        # Accepting now reports it at once
        res, body = self.respond(reqs[0]['id'], 'accept')
        self.assertEqual(body['request']['status'], 'completed')

    def test_decline_cooldown_and_cancel(self):
        self.verify_org(self.rec)
        self.make_visible()
        res, body = self.request(['sql', 'rust'])
        sql_req = next(r['id'] for r in body['requests'] if r['skill_name'] == 'sql')
        rust_req = next(r['id'] for r in body['requests'] if r['skill_name'] == 'rust')
        res, out = self.respond(sql_req, 'decline', 'Not now')
        self.assertEqual(out['request']['status'], 'declined')
        self.assertEqual(self.respond(sql_req, 'accept')[0].status_code, 400)
        self.assertEqual(self.respond(sql_req, 'maybe')[0].status_code, 400)
        res, body = self.request(['sql'])
        self.assertEqual(res.status_code, 409)
        self.assertIn('declined this recently', body['error'])

        res, out = _api(self.rec, 'post', f'/api/recruiter/verification_requests/{rust_req}/cancel')
        self.assertEqual(res.status_code, 200, out)
        self.assertEqual(self.rec.post(f'/api/recruiter/verification_requests/{rust_req}/cancel').status_code, 400)
        self.assertEqual(self.respond(rust_req, 'accept')[0].status_code, 400)
        statuses = {r['skill_name']: r['status'] for r in self.student_requests()}
        self.assertEqual(statuses, {'sql': 'declined', 'rust': 'cancelled'})

    def test_withdrawing_consent_closes_requests_and_hides_candidate(self):
        self.verify_org(self.rec)
        self.make_visible()
        res, body = self.request(['sql'])
        req_id = body['requests'][0]['id']
        self.respond(req_id, 'accept')
        _api(self.stu, 'put', '/api/candidate/discovery', json={'is_discoverable': False})
        res, lst = _api(self.rec, 'get', '/api/recruiter/verification_requests')
        r = lst['requests'][0]
        self.assertEqual(r['status'], 'closed')
        self.assertIsNone(r['candidate_ref'])
        self.assertIsNone(r['candidate_name'])
        # a later pass is not reported to the organisation
        self.pass_sql_quiz(correct=True)
        with app.app_context():
            self.assertEqual(db.session.get(SkillVerificationRequest, req_id).status, 'closed')
        self.assertEqual(self.request(['sql'])[0].status_code, 404)

    def test_mark_read_and_export_and_account_deletion(self):
        self.verify_org(self.rec)
        self.make_visible()
        self.request(['sql'])
        res, upd = _api(self.stu, 'get', '/api/candidate/updates')
        self.assertEqual(upd['unread_count'], 1)
        self.stu.post('/api/candidate/updates/read')
        res, upd = _api(self.stu, 'get', '/api/candidate/updates')
        self.assertEqual(upd['unread_count'], 0)
        res, exp = _api(self.stu, 'get', '/api/student/account/export')
        self.assertEqual(exp['employer_access']['verification_requests'][0]['skill_name'], 'sql')
        res = self.stu.delete('/api/student/account/delete', json={'confirmation': 'DELETE_MY_ACCOUNT'})
        self.assertEqual(res.status_code, 200)
        with app.app_context():
            self.assertEqual(SkillVerificationRequest.query.count(), 0)


if __name__ == '__main__':
    unittest.main()
