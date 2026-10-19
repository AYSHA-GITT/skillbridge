import os
import sys
import unittest
import json
from datetime import datetime

# Set backend path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import app
from extensions import db
from models import Student, Skill, SkillVerification, JobListing, SavedJob, InterviewSession, InterviewQA
from utils.job_discovery.discovery_service import JobDiscoveryService
from utils.job_matcher import evaluate_job_match, compare_multiple_jobs
from utils.rag_engine import rag_engine, LocalVectorStore, DocumentChunk
from utils.ai_providers import ai_provider_manager
from utils.interview_simulator import start_interview_session, evaluate_interview_answer
from utils.career_recommender import simulate_multi_career_paths


class TestExtendedFeaturesSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = app
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()

        with cls.app.app_context():
            db.create_all()

            # Ensure clean test user
            test_email = "extended_tester@skillbridge.edu"
            existing = Student.query.filter_by(email=test_email).first()
            if existing:
                # Clean up existing relations
                SavedJob.query.filter_by(student_id=existing.id).delete()
                session_ids = [s.id for s in InterviewSession.query.filter_by(student_id=existing.id).all()]
                if session_ids:
                    InterviewQA.query.filter(InterviewQA.session_id.in_(session_ids)).delete(synchronize_session=False)
                InterviewSession.query.filter_by(student_id=existing.id).delete()
                SkillVerification.query.filter_by(student_id=existing.id).delete()
                Skill.query.filter_by(student_id=existing.id).delete()
                db.session.delete(existing)
                db.session.commit()

            student = Student(
                name="Extended Tester",
                email=test_email,
                role="student",
                target_career="Full Stack Developer",
                readiness_score=75
            )
            student.set_password("testpass123")
            db.session.add(student)
            db.session.commit()
            cls.student_id = student.id

            # Add test skills
            skills = [
                Skill(student_id=student.id, skill_name="Python", proficiency="Advanced", extraction_confidence=0.9),
                Skill(student_id=student.id, skill_name="React", proficiency="Intermediate", extraction_confidence=0.85),
                Skill(student_id=student.id, skill_name="SQL", proficiency="Intermediate", extraction_confidence=0.8),
                Skill(student_id=student.id, skill_name="Docker", proficiency="Intermediate", extraction_confidence=0.75),
                Skill(student_id=student.id, skill_name="Git", proficiency="Advanced", extraction_confidence=0.95)
            ]
            db.session.add_all(skills)
            db.session.commit()

            # Verifications for Python, React, Git
            verifs = [
                SkillVerification(student_id=student.id, skill_id=skills[0].id, quiz_score_percent=90.0, verification_score=90.0),
                SkillVerification(student_id=student.id, skill_id=skills[1].id, quiz_score_percent=85.0, verification_score=85.0),
                SkillVerification(student_id=student.id, skill_id=skills[4].id, quiz_score_percent=95.0, verification_score=95.0)
            ]
            db.session.add_all(verifs)
            db.session.commit()


    def setUp(self):
        # Log in test user
        res = self.client.post('/api/auth/login', json={
            'email': 'extended_tester@skillbridge.edu',
            'password': 'testpass123'
        })
        self.assertEqual(res.status_code, 200, "Login must succeed for test user")

        with self.app.app_context():
            session_ids = [s.id for s in InterviewSession.query.filter_by(student_id=self.student_id).all()]
            if session_ids:
                InterviewQA.query.filter(InterviewQA.session_id.in_(session_ids)).delete(synchronize_session=False)
            InterviewSession.query.filter_by(student_id=self.student_id).delete()
            db.session.commit()

    # =========================================================================
    # 1. Job Discovery & Curation Tests
    # =========================================================================
    def test_01_job_discovery_curation(self):
        """Test curated benchmark and live discovery pipeline."""
        with self.app.app_context():
            service = JobDiscoveryService()
            results = service.discover_and_sync()
            self.assertGreaterEqual(results['new_jobs_added'], 0)
            self.assertGreater(results['total_jobs_in_db'], 0)

            # Check database for sample jobs
            sample_jobs = JobListing.query.filter_by(is_sample=True).all()
            self.assertGreaterEqual(len(sample_jobs), 4, "Should have benchmark sample tech jobs")

            # Check telemetry metrics
            metrics = service.get_data_quality_metrics()
            self.assertIn('total_ingested', metrics)
            self.assertIn('valid_schema_rate', metrics)
            self.assertEqual(metrics['valid_schema_rate'], 100.0)

    def test_02_job_endpoints_filter_and_save(self):
        """Test API endpoints for job search, filtering, saving and unsaving."""
        # Get jobs list
        res = self.client.get('/api/student/jobs?per_page=10')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('jobs', data)
        self.assertGreater(len(data['jobs']), 0)
        first_job = data['jobs'][0]

        # Save job
        res_save = self.client.post('/api/student/jobs/save', json={'job_id': first_job['id']})
        self.assertEqual(res_save.status_code, 200)

        # Retrieve saved jobs
        res_saved = self.client.get('/api/student/jobs/saved')
        self.assertEqual(res_saved.status_code, 200)
        saved_list = res_saved.get_json().get('saved_jobs', [])
        saved_ids = [j['id'] for j in saved_list]
        self.assertIn(first_job['id'], saved_ids)

        # Unsave job
        res_unsave = self.client.post('/api/student/jobs/unsave', json={'job_id': first_job['id']})
        self.assertEqual(res_unsave.status_code, 200)

    # =========================================================================
    # 2. Explainable Deterministic Job Matcher Tests
    # =========================================================================
    def test_03_deterministic_match_scoring(self):
        """Test deterministic 4-pillar match formula and transferable skill bridge."""
        user_skills = [
            {'skill_name': 'python', 'is_verified': True, 'proficiency': 'Advanced'},
            {'skill_name': 'react', 'is_verified': True, 'proficiency': 'Intermediate'},
            {'skill_name': 'docker', 'is_verified': False, 'proficiency': 'Intermediate'}
        ]

        # Job requiring python, react, kubernetes
        job_data = {
            'title': 'Senior Full Stack Cloud Engineer',
            'required_skills': ['python', 'react', 'kubernetes'],
            'preferred_skills': ['graphql', 'aws'],
            'experience_level': 'intermediate'
        }

        match = evaluate_job_match(
            user_skills=user_skills,
            job_data=job_data,
            user_experience_level='intermediate'
        )

        # Validate structure
        self.assertIn('match_score', match)
        self.assertIn('scoring_breakdown', match)
        breakdown = match['scoring_breakdown']

        # Mandatory: python (matched), react (matched), kubernetes (missing, but docker provides bridge)
        # Weights: 50% mandatory, 20% preferred, 15% transferable, 15% experience
        self.assertGreater(breakdown['mandatory_skills_score'], 0)
        self.assertEqual(breakdown['experience_eligibility_score'], 100.0)

        # Check transferable bridges: Docker transfers to Kubernetes
        bridges = match.get('transferable_bridges', [])
        bridge_pairs = [(b['user_skill'], b['target_skill']) for b in bridges]
        self.assertTrue(
            any(p == ('docker', 'kubernetes') for p in bridge_pairs),
            "Docker should bridge to Kubernetes in transferable skills"
        )

        # Check that score is strictly bounded [0, 100]
        self.assertGreaterEqual(match['match_score'], 0)
        self.assertLessEqual(match['match_score'], 100)

    def test_04_multi_job_comparison(self):
        """Test side-by-side job comparison and overlapping high-yield skills."""
        user_skills = [
            {'skill_name': 'python', 'is_verified': True, 'proficiency': 'Advanced'},
            {'skill_name': 'sql', 'is_verified': False, 'proficiency': 'Intermediate'}
        ]

        jobs_list = [
            {
                'id': 1,
                'title': 'Data Engineer',
                'company': 'Alpha Corp',
                'required_skills': ['python', 'sql', 'spark'],
                'preferred_skills': ['aws']
            },
            {
                'id': 2,
                'title': 'Backend Developer',
                'company': 'Beta Inc',
                'required_skills': ['python', 'sql', 'fastapi'],
                'preferred_skills': ['docker']
            }
        ]

        comparison = compare_multiple_jobs(user_skills, jobs_list)
        self.assertIn('jobs', comparison)
        self.assertEqual(len(comparison['jobs']), 2)

        # High yield overlapping skills should contain python and sql
        high_yield = [s.lower() for s in comparison.get('high_yield_overlapping_skills', [])]
        self.assertIn('python', high_yield)
        self.assertIn('sql', high_yield)

    # =========================================================================
    # 3. Genuine RAG Career Assistant & Tenant Isolation Tests
    # =========================================================================
    def test_05_rag_tenant_isolation(self):
        """Test that user A cannot retrieve user B's documents from vector store."""
        store = LocalVectorStore()

        # Ingest document for User 100
        store.add_document(
            document_id="user100_resume",
            title="User 100 Private Resume",
            source_type="user_profile",
            text="Confidential personal projects of user 100 in quantum computing algorithms and simulations.",
            user_id=100
        )

        # Ingest public document (user_id=None)
        store.add_document(
            document_id="public_guide",
            title="Public Python Career Roadmap",
            source_type="career_guide",
            text="Standard foundational path to junior Python developer using Flask and SQL.",
            user_id=None
        )

        # Query as User 200: must NOT see User 100's document
        results_user200 = store.search(
            query="quantum computing algorithms",
            top_k=5,
            requesting_user_id=200
        )
        found_doc_ids = [r['document_id'] for r in results_user200]
        self.assertNotIn("user100_resume", found_doc_ids, "Tenant isolation violation: User 200 retrieved User 100 private data")

        # Query as User 100: CAN see User 100's document
        results_user100 = store.search(
            query="quantum computing algorithms",
            top_k=5,
            requesting_user_id=100
        )
        found_doc_ids_100 = [r['document_id'] for r in results_user100]
        self.assertIn("user100_resume", found_doc_ids_100)

    def test_06_rag_citations_and_assistant(self):
        """Test RAG query answering returns verified citations and answer."""
        with self.app.app_context():
            res = rag_engine.answer_query(
                query="What skills do I need to learn for my target career?",
                student_id=self.student_id
            )
            self.assertIn('answer', res)
            self.assertIn('is_rag', res)
            self.assertIn('retrieved_sources', res)
            self.assertGreater(len(res['answer']), 20)


    # =========================================================================
    # 4. AI Provider Manager Tests
    # =========================================================================
    def test_07_ai_providers_manager(self):
        """Test provider discovery and cascading fallback."""
        status = ai_provider_manager.get_available_providers()
        self.assertIn('providers', status)
        self.assertIn('active_provider', status)

        provider_names = [p['name'] for p in status['providers']]
        self.assertIn('gemini', provider_names)
        self.assertIn('ollama', provider_names)
        self.assertIn('grok', provider_names)

        # Test selecting provider via endpoint
        res = self.client.post('/api/student/ai_providers/select', json={'provider_name': 'gemini'})
        self.assertEqual(res.status_code, 200)

    # =========================================================================
    # 5. Job-Specific Interview Simulator Tests
    # =========================================================================
    def test_08_interview_question_generation_and_evaluation(self):
        """Test 5-category interview generation and 4-pillar rubric evaluation."""
        with self.app.app_context():
            session = start_interview_session(
                student_id=self.student_id,
                custom_title="Full Stack Developer"
            )
            questions = session.get('questions', [])
            self.assertEqual(len(questions), 5, "Must generate exactly 5 category questions")

            categories = [q['category'] for q in questions]
            self.assertIn('Technical Fundamentals', categories)

            # Evaluate answer
            user_ans = "In my previous project, I designed a RESTful API using Flask with PostgreSQL. I indexed foreign keys to reduce query latency by 45%."
            evaluation = evaluate_interview_answer(
                session_id=session['id'],
                question_index=1,
                candidate_answer=user_ans,
                student_id=self.student_id
            )

            self.assertIn('overall_score', evaluation)
            self.assertIn('rubric_scores', evaluation)
            self.assertIn('missing_points', evaluation)
            self.assertIn('sample_ideal_answer', evaluation)

            rubric = evaluation['rubric_scores']
            self.assertIn('relevance_score', rubric)
            self.assertIn('technical_depth_score', rubric)
            self.assertIn('structure_score', rubric)
            self.assertIn('communication_score', rubric)

    def test_09_interview_session_api_flow(self):
        """Test starting interview session, answering, and fetching history."""
        # Start session
        res_start = self.client.post('/api/student/interview/start', json={
            'custom_title': 'Cloud Engineer'
        })
        self.assertEqual(res_start.status_code, 200)
        data = res_start.get_json().get('session', {})
        session_id = data.get('id')
        questions = data.get('questions', [])
        self.assertIsNotNone(session_id)
        self.assertEqual(len(questions), 5)

        # Answer question 1
        res_ans = self.client.post('/api/student/interview/answer', json={
            'session_id': session_id,
            'question_index': 1,
            'candidate_answer': 'I implement zero-downtime rolling updates using Kubernetes deployments and health probes.'
        })
        self.assertEqual(res_ans.status_code, 200)
        eval_data = res_ans.get_json().get('evaluation', {})
        self.assertIn('overall_score', eval_data)

        # Fetch history
        res_hist = self.client.get('/api/student/interview/history')
        self.assertEqual(res_hist.status_code, 200)
        hist_list = res_hist.get_json().get('sessions', [])
        self.assertGreater(len(hist_list), 0)

    # =========================================================================
    # 6. Multi-Path Career Simulation Tests
    # =========================================================================
    def test_10_multi_path_career_simulation(self):
        """Test multi-path career trajectory simulation endpoint."""
        paths = ["Full Stack Developer", "Data Scientist", "Cloud Architect"]
        with self.app.app_context():
            sim = simulate_multi_career_paths(
                verified_skills=["Python", "SQL", "Git"],
                career_names=paths,
                target_career="Full Stack Developer"
            )
            self.assertIn('shared_core_foundation', sim)
            self.assertIn('transitions', sim)
            self.assertIn('recommended_sequence', sim)

        # Test API endpoint
        res = self.client.post('/api/student/simulate_paths', json={'career_names': paths})
        self.assertEqual(res.status_code, 200)
        self.assertIn('simulation', res.get_json())


    # =========================================================================
    # 7. Privacy, Data Sovereignty & Explainability Tests
    # =========================================================================
    def test_11_data_export_and_deletion(self):
        """Test machine-readable JSON data export and irreversible deletion."""
        # Export account data
        res_export = self.client.get('/api/student/account/export')
        self.assertEqual(res_export.status_code, 200)
        export_data = res_export.get_json()
        self.assertIn('profile', export_data)
        self.assertIn('skills', export_data)
        self.assertIn('interview_history', export_data)
        self.assertEqual(export_data['profile']['email'], 'extended_tester@skillbridge.edu')

        # Attempt delete without confirmation: must fail with 400
        res_bad_del = self.client.delete('/api/student/account/delete', json={'confirmation': 'wrong'})
        self.assertEqual(res_bad_del.status_code, 400)

        # Delete with proper confirmation
        res_del = self.client.delete('/api/student/account/delete', json={'confirmation': 'DELETE_MY_ACCOUNT'})
        self.assertEqual(res_del.status_code, 200)

        # Verify user is completely erased from database
        with self.app.app_context():
            deleted = Student.query.filter_by(email='extended_tester@skillbridge.edu').first()
            self.assertIsNone(deleted, "Student must be completely purged from database")


if __name__ == '__main__':
    unittest.main()
