"""
Security tests for Forgot Password / Set New Password.

Covers: delivery only to the registered address, no token/link in responses or logs,
valid/expired/reused/missing/tampered tokens, single use (including a race), account
enumeration, rate limits, all three roles, session invalidation, and e-mail failure modes.
"""
from tests.base import app, db, reset_db, make_student, login  # must be first

import logging
import os
import re
import unittest
from datetime import timedelta
from unittest import mock

from models import Student, PasswordResetToken
from utils import password_reset as pr
from utils.rate_limit import reset as reset_rate_limits

MAIL_ENV = {'MAIL_SERVER': 'smtp.test', 'MAIL_USERNAME': 'mailer@test', 'MAIL_PASSWORD': 'x',
            'MAIL_FROM': 'noreply@skillbridge.test', 'FRONTEND_URL': 'https://skillbridge.test'}
NEW_PASSWORD = 'N3w-Strong-Passw0rd'
TOKEN_RE = re.compile(r'#token=([A-Za-z0-9_\-]+)')


class ResetBase(unittest.TestCase):
    def setUp(self):
        reset_db()
        reset_rate_limits()
        self.client = app.test_client()
        self.student_id = make_student('student@example.com')
        self.recruiter_id = make_student('recruiter@example.com', role='recruiter')
        self.admin_id = make_student('admin@example.com', role='admin')
        self.env = mock.patch.dict(os.environ, MAIL_ENV)
        self.env.start()
        self.sent = []
        self.mailer = mock.patch.object(pr, 'send_email', side_effect=self._capture)
        self.mailer.start()

    def tearDown(self):
        self.mailer.stop()
        self.env.stop()
        app.config['RATELIMIT_ENABLED'] = False

    def _capture(self, to_email, subject, text, html=None):
        self.sent.append({'to': to_email, 'text': text, 'html': html})
        return True, 'sent'

    def request_link(self, email='student@example.com', client=None):
        res = (client or self.client).post('/api/auth/forgot_password', json={'email': email})
        self.assertEqual(res.status_code, 200)
        return res

    def last_token(self):
        self.assertTrue(self.sent, 'no e-mail was sent')
        return TOKEN_RE.search(self.sent[-1]['text']).group(1)

    def reset(self, token, password=NEW_PASSWORD, confirm=None, client=None):
        return (client or self.client).post('/api/auth/reset_password', json={
            'token': token, 'new_password': password,
            'confirm_password': password if confirm is None else confirm})

    def can_login(self, email, password):
        return app.test_client().post('/api/auth/login', json={
            'email': email, 'password': password}).status_code == 200


class DeliveryAndExposureTests(ResetBase):
    def test_link_goes_only_to_registered_address(self):
        # Mixed case and spaces in the request; the e-mail goes to the stored address.
        self.request_link('  Student@Example.COM ')
        self.assertEqual([m['to'] for m in self.sent], ['student@example.com'])
        self.assertIn('https://skillbridge.test/reset-password#token=', self.sent[0]['text'])

    def test_response_never_contains_token_or_link(self):
        res = self.request_link()
        body = res.get_data(as_text=True)
        token = self.last_token()
        self.assertNotIn(token, body)
        self.assertNotIn('reset-password', body)
        self.assertNotIn('dev_info', body)
        self.assertEqual(set(res.get_json()), {'message'})

    def test_no_link_in_response_even_when_mail_is_not_configured(self):
        self.mailer.stop()
        with mock.patch.dict(os.environ, {'MAIL_SERVER': '', 'SKILLBRIDGE_ENV': 'production'}):
            res = self.request_link()
        self.mailer.start()
        body = res.get_data(as_text=True)
        self.assertNotIn('token', body)
        self.assertNotIn('reset-password', body)

    def test_database_stores_only_a_hash(self):
        self.request_link()
        token = self.last_token()
        with app.app_context():
            stored = PasswordResetToken.query.one().token
        self.assertNotEqual(stored, token)
        self.assertEqual(stored, pr.hash_token(token))

    def test_production_logs_never_contain_the_link(self):
        self.mailer.stop()
        with mock.patch.dict(os.environ, {'MAIL_SERVER': '', 'SKILLBRIDGE_ENV': 'production'}), \
                self.assertLogs(level=logging.DEBUG) as logs, \
                mock.patch('builtins.print') as printed:
            logging.getLogger('test').info('marker')
            self.request_link()
        self.mailer.start()
        printed.assert_not_called()
        joined = '\n'.join(logs.output)
        self.assertIn('not configured', joined)
        self.assertNotIn('#token=', joined)
        self.assertNotIn('reset-password', joined)

    def test_smtp_failure_is_logged_without_link_and_response_is_generic(self):
        self.mailer.stop()
        with mock.patch.object(pr, 'send_email', return_value=(False, 'SMTPAuthenticationError: 535')), \
                self.assertLogs('utils.password_reset', level='ERROR') as logs:
            res = self.request_link()
        self.mailer.start()
        self.assertEqual(set(res.get_json()), {'message'})
        self.assertIn('SMTPAuthenticationError', logs.output[0])
        self.assertNotIn('token', logs.output[0])

    def test_verify_endpoint_masks_email_and_token_not_in_url(self):
        self.request_link()
        token = self.last_token()
        res = self.client.post('/api/auth/verify_reset_token', json={'token': token})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()['email'], 's******@example.com')
        # The old GET /verify_reset_token/<token> form (token in the URL) is gone.
        self.assertIn(self.client.get(f'/api/auth/verify_reset_token/{token}').status_code, (404, 405))


class TokenValidityTests(ResetBase):
    def test_valid_token_resets_password_once(self):
        self.request_link()
        token = self.last_token()
        self.assertEqual(self.reset(token).status_code, 200)
        self.assertTrue(self.can_login('student@example.com', NEW_PASSWORD))
        self.assertFalse(self.can_login('student@example.com', 'password123'))

    def test_reused_token_is_rejected(self):
        self.request_link()
        token = self.last_token()
        self.assertEqual(self.reset(token).status_code, 200)
        again = self.reset(token, password='Another-Passw0rd!')
        self.assertEqual(again.status_code, 400)
        self.assertEqual(again.get_json()['code'], 'invalid_token')
        self.assertTrue(self.can_login('student@example.com', NEW_PASSWORD))

    def test_expired_token_is_rejected(self):
        self.request_link()
        token = self.last_token()
        with app.app_context():
            row = PasswordResetToken.query.one()
            row.expires_at = pr.now_utc() - timedelta(seconds=1)
            db.session.commit()
        self.assertEqual(self.client.post('/api/auth/verify_reset_token', json={'token': token}).status_code, 400)
        self.assertEqual(self.reset(token).status_code, 400)
        self.assertTrue(self.can_login('student@example.com', 'password123'))

    def test_missing_token_never_changes_a_password(self):
        for payload in ({}, {'token': ''}, {'token': None}, {'token': 123}, {'token': ['x']}):
            payload.update(new_password=NEW_PASSWORD, confirm_password=NEW_PASSWORD)
            res = self.client.post('/api/auth/reset_password', json=payload)
            self.assertEqual(res.status_code, 400, payload)
        self.assertEqual(self.client.post('/api/auth/reset_password').status_code, 400)
        for email in ('student@example.com', 'recruiter@example.com', 'admin@example.com'):
            self.assertTrue(self.can_login(email, 'password123'))

    def test_tampered_and_guessed_tokens_are_rejected(self):
        self.request_link()
        token = self.last_token()
        flipped = token[:-1] + ('A' if token[-1] != 'A' else 'B')
        for bad in (flipped, token[:-2], token + 'x', token.upper(), 'a' * 43,
                    pr.hash_token(token), "' OR '1'='1", '../../etc/passwd', 'x' * 500):
            self.assertEqual(self.reset(bad).status_code, 400, bad)
            self.assertEqual(self.client.post('/api/auth/verify_reset_token',
                                              json={'token': bad}).status_code, 400)
        self.assertTrue(self.can_login('student@example.com', 'password123'))
        self.assertEqual(self.reset(token).status_code, 200)   # the real one still works

    def test_requesting_a_new_link_invalidates_the_old_one(self):
        self.request_link()
        first = self.last_token()
        self.request_link()
        second = self.last_token()
        self.assertEqual(self.reset(first).status_code, 400)
        self.assertEqual(self.reset(second).status_code, 200)

    def test_token_of_one_account_cannot_reset_another(self):
        self.request_link('student@example.com')
        token = self.last_token()
        self.reset(token)
        self.assertTrue(self.can_login('admin@example.com', 'password123'))
        self.assertTrue(self.can_login('recruiter@example.com', 'password123'))

    def test_password_rules_checked_before_token_is_spent(self):
        self.request_link()
        token = self.last_token()
        self.assertEqual(self.reset(token, password='short').status_code, 400)
        self.assertEqual(self.reset(token, password=NEW_PASSWORD, confirm='different1').status_code, 400)
        self.assertEqual(self.reset(token, password='p' * 200).status_code, 400)
        self.assertEqual(self.reset(token).status_code, 200)

    def test_concurrent_use_only_succeeds_once(self):
        """Simulates a race: both requests pass validation, only one may consume."""
        self.request_link()
        token = self.last_token()
        import routes.auth as auth_routes
        original = auth_routes._usable_token
        with app.app_context():
            stale = PasswordResetToken.query.one()
            db.session.expunge(stale)
        # The second request sees the token as unused (as if read before the first committed).
        self.assertEqual(self.reset(token).status_code, 200)
        with mock.patch.object(auth_routes, '_usable_token', return_value=stale):
            res = self.reset(token, password='Second-Passw0rd!')
        self.assertIs(auth_routes._usable_token, original)
        self.assertEqual(res.status_code, 400)
        self.assertTrue(self.can_login('student@example.com', NEW_PASSWORD))

    def test_deactivated_account_gets_no_link_and_cannot_use_one(self):
        self.request_link()
        token = self.last_token()
        with app.app_context():
            db.session.get(Student, self.student_id).is_active = False
            db.session.commit()
        self.assertEqual(self.reset(token).status_code, 400)
        self.sent.clear()
        self.request_link()
        self.assertEqual(self.sent, [])


class EnumerationTests(ResetBase):
    def test_same_response_for_registered_and_unknown_addresses(self):
        known = self.request_link('student@example.com')
        unknown = self.request_link('nobody@example.com')
        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known.get_json(), unknown.get_json())
        self.assertEqual(len(self.sent), 1)

    def test_mail_is_sent_off_the_request_thread_outside_tests(self):
        calls = []
        with mock.patch.object(pr.threading, 'Thread') as thread, \
                mock.patch.dict(app.config, {'TESTING': False}):
            thread.return_value.start.side_effect = lambda: calls.append('started')
            self.request_link()
        self.assertEqual(calls, ['started'])
        self.assertEqual(self.sent, [])   # nothing was sent synchronously


class RateLimitTests(ResetBase):
    def setUp(self):
        super().setUp()
        app.config['RATELIMIT_ENABLED'] = True

    def test_forgot_password_is_limited_per_ip(self):
        codes = [self.client.post('/api/auth/forgot_password',
                                  json={'email': f'user{i}@example.com'}).status_code for i in range(6)]
        self.assertEqual(codes, [200] * 5 + [429])

    def test_per_address_limit_is_silent(self):
        for i in range(5):
            # A fresh rate-limit window per IP is simulated by clearing only the IP bucket.
            reset_rate_limits('forgot_password:')
            res = self.request_link()
            self.assertEqual(set(res.get_json()), {'message'})
        self.assertEqual(len(self.sent), 3)

    def test_token_endpoints_are_limited(self):
        codes = [self.client.post('/api/auth/verify_reset_token', json={'token': 'x' * 43}).status_code
                 for _ in range(21)]
        self.assertEqual(codes[-1], 429)
        self.assertEqual(self.reset('x' * 43).status_code, 429)


class RolesAndSessionTests(ResetBase):
    def test_reset_works_for_every_role(self):
        for email in ('student@example.com', 'recruiter@example.com', 'admin@example.com'):
            self.request_link(email)
            self.assertEqual(self.sent[-1]['to'], email)
            self.assertEqual(self.reset(self.last_token()).status_code, 200)
            self.assertTrue(self.can_login(email, NEW_PASSWORD))
        with app.app_context():
            roles = {s.email: s.role for s in Student.query.all()}
        self.assertEqual(roles['admin@example.com'], 'admin')
        self.assertEqual(roles['recruiter@example.com'], 'recruiter')

    def test_reset_signs_out_existing_sessions(self):
        for email in ('student@example.com', 'admin@example.com'):
            other_device = app.test_client()
            login(other_device, email)
            self.assertEqual(other_device.get('/api/auth/me').status_code, 200)
            self.request_link(email)
            self.assertEqual(self.reset(self.last_token()).status_code, 200)
            self.assertEqual(other_device.get('/api/auth/me').status_code, 401)
            login(other_device, email, NEW_PASSWORD)
            self.assertEqual(other_device.get('/api/auth/me').status_code, 200)

    def test_change_password_keeps_this_session_and_ends_others(self):
        this_device, other_device = app.test_client(), app.test_client()
        login(this_device, 'student@example.com')
        login(other_device, 'student@example.com')
        res = this_device.post('/api/auth/change_password', json={
            'current_password': 'password123', 'new_password': NEW_PASSWORD,
            'confirm_password': NEW_PASSWORD})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(this_device.get('/api/auth/me').status_code, 200)
        self.assertEqual(other_device.get('/api/auth/me').status_code, 401)

    def test_forged_session_ids_are_rejected(self):
        with app.app_context():
            from app import load_user
            student = db.session.get(Student, self.student_id)
            good = student.get_id()
            self.assertIsNotNone(load_user(good))
            for bad in (str(self.student_id), f'{self.student_id}:', f'{self.student_id}:deadbeef',
                        f'{self.admin_id}:{good.split(":")[1]}', 'abc:def', ''):
                self.assertIsNone(load_user(bad), bad)


class MailConfigTests(unittest.TestCase):
    def test_mail_configured_requires_all_settings(self):
        with mock.patch.dict(os.environ, MAIL_ENV):
            self.assertTrue(pr.mail_configured())
            with mock.patch.dict(os.environ, {'MAIL_PASSWORD': ''}):
                self.assertFalse(pr.mail_configured())

    def test_send_email_never_raises_on_network_errors(self):
        with mock.patch.dict(os.environ, MAIL_ENV), \
                mock.patch.object(pr.smtplib, 'SMTP', side_effect=OSError('connection refused')):
            sent, reason = pr.send_email('a@b.c', 's', 't')
        self.assertFalse(sent)
        self.assertIn('connection refused', reason)

    def test_mask_email(self):
        self.assertEqual(pr.mask_email('ab@x.org'), 'a***@x.org')
        self.assertEqual(pr.mask_email('bad'), '')


if __name__ == '__main__':
    unittest.main()
