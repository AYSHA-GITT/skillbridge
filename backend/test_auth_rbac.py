import unittest
import json
from app import app
from extensions import db
from models import Student

class TestAuthAndRBAC(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_unauthenticated_admin_access(self):
        # 1. Unauthenticated request to admin endpoints should return 401
        res = self.client.get('/api/admin/stats')
        self.assertEqual(res.status_code, 401)
        self.assertIn('Authentication required', res.get_json().get('error', ''))

        res_fl = self.client.post('/api/admin/federated/train')
        self.assertEqual(res_fl.status_code, 401)

    def test_student_denied_admin_and_fl(self):
        # 2. Student login
        login_res = self.client.post('/api/auth/login', json={
            'email': 'ayeshamads@gmail.com',
            'password': 'password123'  # Let's check password or we can test with student
        })
        # If student login password fails, verify with student user or test student
        if login_res.status_code != 200:
            # Let's check user in DB
            with app.app_context():
                s = Student.query.filter_by(role='student').first()
                s.set_password('teststudent123')
                s_email = s.email
                db.session.commit()
            login_res = self.client.post('/api/auth/login', json={
                'email': s_email,
                'password': 'teststudent123'
            })

        self.assertEqual(login_res.status_code, 200)
        data = login_res.get_json()
        self.assertEqual(data['student']['role'], 'student')

        # 3. Student requests admin stats -> 403 Forbidden
        admin_res = self.client.get('/api/admin/stats')
        self.assertEqual(admin_res.status_code, 403)
        self.assertIn('Institutional Administrator privileges', admin_res.get_json().get('error', ''))

        # 4. Student requests FL train -> 403 Forbidden
        fl_train_res = self.client.post('/api/admin/federated/train')
        self.assertEqual(fl_train_res.status_code, 403)

        # 5. Student requests FL rounds -> 403 Forbidden
        fl_rounds_res = self.client.get('/api/admin/federated/rounds')
        self.assertEqual(fl_rounds_res.status_code, 403)

        # 6. Student requests privacy info -> 200 OK
        priv_res = self.client.get('/api/student/privacy_info')
        self.assertEqual(priv_res.status_code, 200)
        self.assertIn('Privacy-Preserving Intelligence', priv_res.get_json()['title'])

    def test_admin_allowed_access(self):
        # Admin login
        admin_login = self.client.post('/api/auth/login', json={
            'email': 'admin@skillbridge.edu',
            'password': 'admin123'
        })
        self.assertEqual(admin_login.status_code, 200)
        data = admin_login.get_json()
        self.assertEqual(data['student']['role'], 'admin')

        # Admin requests stats -> 200 OK
        admin_stats = self.client.get('/api/admin/stats')
        self.assertEqual(admin_stats.status_code, 200)
        stats_data = admin_stats.get_json()
        self.assertIn('total_students', stats_data)
        self.assertIn('active_learners', stats_data)
        self.assertIn('career_distribution', stats_data)
        self.assertIn('readiness_distribution', stats_data)

        # Admin requests FL nodes -> 200 OK
        fl_nodes = self.client.get('/api/admin/federated/nodes')
        self.assertEqual(fl_nodes.status_code, 200)
        self.assertEqual(len(fl_nodes.get_json()['institutions']), 4)

if __name__ == '__main__':
    unittest.main()
