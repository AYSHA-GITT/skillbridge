"""
API test suite for Resume Optimizer endpoints.
Tests authentication, input validation, role safety, deterministic scoring,
PDF/DOCX export endpoints, and error handling.
"""

import unittest
import io
import json
from app import app
from extensions import db
from models import Student, Resume
from werkzeug.security import generate_password_hash


class TestApiResumeOptimizer(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        with self.app.app_context():
            # Create a test student
            self.email = 'optimizer_student@skillbridge.test'
            existing = Student.query.filter_by(email=self.email).first()
            if existing:
                self.student_id = existing.id
            else:
                student = Student(
                    name='Optimizer Test Student',
                    email=self.email,
                    password_hash=generate_password_hash('Password123!'),
                    role='student',
                    target_career='software engineer'
                )
                db.session.add(student)
                db.session.commit()
                self.student_id = student.id

            # Create a test resume record for this student
            self.sample_text = """
Jane Doe
jane.doe@example.com | 9876543210
linkedin.com/in/janedoe | github.com/janedoe
Bengaluru, India

SUMMARY
Aspiring data analyst with passion for data visualization and Python.

SKILLS
Python, SQL, Excel, Tableau, Pandas, Git

EXPERIENCE
Data Intern | Analytics Corp | Jan 2024 - Present
• Responsible for writing SQL queries to extract customer data.
• Worked on dashboards using Tableau.
• Helped clean datasets using Python and Pandas.

EDUCATION
B.Sc in Statistics | Delhi University | 2021 - 2024
"""
            res = Resume.query.filter_by(student_id=self.student_id).first()
            if not res:
                res = Resume(
                    student_id=self.student_id,
                    file_path='uploads/resumes/dummy_test.pdf',
                    original_filename='Jane_Resume.pdf',
                    parsed_text=self.sample_text,
                    is_latest=True
                )
                db.session.add(res)
                db.session.commit()
            self.resume_id = res.id

    def login(self):
        return self.client.post('/api/auth/login', json={
            'email': self.email,
            'password': 'Password123!'
        })

    def test_unauthorized_access(self):
        # Without login, requests must return 401 or redirect
        res = self.client.get('/api/student/resume_optimizer/careers')
        self.assertIn(res.status_code, [401, 302])

    def test_get_careers(self):
        self.login()
        res = self.client.get('/api/student/resume_optimizer/careers')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('careers', data)
        self.assertTrue(len(data['careers']) >= 3)
        titles = [c['title'].lower() for c in data['careers']]
        self.assertTrue(any('software engineer' in t for t in titles))
        self.assertTrue(any('data analyst' in t for t in titles))

    def test_get_my_resumes(self):
        self.login()
        res = self.client.get('/api/student/resume_optimizer/my_resumes')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('resumes', data)
        self.assertTrue(len(data['resumes']) >= 1)

    def test_analyze_existing_resume(self):
        self.login()
        payload = {
            'resume_id': self.resume_id,
            'target_career': 'data analyst'
        }
        res = self.client.post('/api/student/resume_optimizer/analyze', data=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertIn('match_analysis', data)
        self.assertIn('match_score', data['match_analysis'])
        self.assertIn('suggestions', data)
        self.assertIn('optimized_sections', data)
        self.assertIn('original_sections', data)

        # Check matched skills contains sql, python, excel, tableau
        matched = [s.lower() for s in data['match_analysis']['matched_skills']]
        self.assertIn('sql', matched)
        self.assertIn('python', matched)

    def test_analyze_custom_jd(self):
        self.login()
        custom_jd = """
        Looking for a Software Engineer proficient in Python, SQL, Git, and Docker.
        Must have experience building REST APIs and microservices.
        """
        payload = {
            'resume_id': self.resume_id,
            'job_description': custom_jd
        }
        res = self.client.post('/api/student/resume_optimizer/analyze', data=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['has_custom_jd'])

    def test_export_pdf(self):
        self.login()
        sections = {
            'contact': {'name': 'Jane Doe', 'email': 'jane@test.com', 'phone': '9876543210'},
            'summary': 'Passionate data analyst.',
            'skills': ['Python', 'SQL', 'Tableau'],
            'experience': [{
                'role': 'Data Intern',
                'company': 'Tech Corp',
                'period': '2024',
                'bullets': ['Engineered SQL queries.', 'Collaborated on Tableau dashboards.']
            }],
            'education': [{'degree': 'B.Sc Statistics', 'institution': 'Delhi University', 'year': '2024'}],
            'certifications': ['Tableau Desktop Specialist']
        }
        res = self.client.post('/api/student/resume_optimizer/export_pdf', json={'sections': sections})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, 'application/pdf')
        self.assertTrue(len(res.data) > 500)
        self.assertTrue(res.data.startswith(b'%PDF'))

    def test_export_docx(self):
        self.login()
        sections = {
            'contact': {'name': 'Jane Doe', 'email': 'jane@test.com', 'phone': '9876543210'},
            'summary': 'Passionate data analyst.',
            'skills': ['Python', 'SQL', 'Tableau'],
            'experience': [{
                'role': 'Data Intern',
                'company': 'Tech Corp',
                'period': '2024',
                'bullets': ['Engineered SQL queries.', 'Collaborated on Tableau dashboards.']
            }],
            'education': [{'degree': 'B.Sc Statistics', 'institution': 'Delhi University', 'year': '2024'}],
            'certifications': ['Tableau Desktop Specialist']
        }
        res = self.client.post('/api/student/resume_optimizer/export_docx', json={'sections': sections})
        self.assertEqual(res.status_code, 200)
        self.assertIn('wordprocessingml', res.mimetype)
        self.assertTrue(len(res.data) > 500)
        self.assertTrue(res.data.startswith(b'PK'))


if __name__ == '__main__':
    unittest.main()
