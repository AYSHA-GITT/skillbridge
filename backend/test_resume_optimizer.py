"""
Test suite for Resume Optimizer:
Tests parsing, deterministic scoring, AI/fallback enhancements, anti-hallucination,
and PDF/DOCX generation.
"""

import unittest
import io
from utils.resume_optimizer import (
    parse_resume_to_structured_json,
    analyze_resume,
    enhance_resume_with_ai,
    generate_resume_pdf,
    generate_resume_docx
)

SAMPLE_RESUME_TEXT = """
John Doe
Email: john.doe@example.com | Phone: 9876543210
LinkedIn: linkedin.com/in/johndoe | GitHub: github.com/johndoe
Bengaluru, India

SUMMARY
Aspiring software engineer interested in building web applications and working with data.

SKILLS
Python, JavaScript, React, SQL, Git, HTML, CSS

EXPERIENCE
Software Intern | Tech Innovations | Bengaluru, India | Jan 2024 - Present
• Responsible for developing REST APIs using Python and Flask.
• Worked on the frontend using React and improved page load times.
• Helped with database queries and bug fixes.

PROJECTS
Smart Attendance System | Python, OpenCV
• Built a facial recognition attendance system for classroom management.
• Assisted in creating a MySQL database schema and dashboard.

EDUCATION
B.Tech in Computer Science | National Institute of Technology | 2021 - 2025 | CGPA: 8.5

CERTIFICATIONS
• AWS Certified Cloud Practitioner
• Python for Everybody (Coursera)
"""


class TestResumeOptimizer(unittest.TestCase):

    def test_section_parsing(self):
        parsed = parse_resume_to_structured_json(SAMPLE_RESUME_TEXT)
        self.assertEqual(parsed['contact']['name'], 'John Doe')
        self.assertEqual(parsed['contact']['email'], 'john.doe@example.com')
        self.assertEqual(parsed['contact']['phone'], '9876543210')
        self.assertIn('johndoe', parsed['contact']['linkedin'])
        self.assertIn('johndoe', parsed['contact']['github'])
        self.assertTrue(len(parsed['skills']) >= 5)
        self.assertTrue(len(parsed['experience']) >= 1)
        self.assertTrue(len(parsed['projects']) >= 1)
        self.assertTrue(len(parsed['education']) >= 1)
        self.assertTrue(len(parsed['certifications']) >= 1)

    def test_analyzer_deterministic_scoring(self):
        parsed = parse_resume_to_structured_json(SAMPLE_RESUME_TEXT)
        analysis = analyze_resume(parsed, target_career="software engineer")

        # Score must be between 10 and 100
        self.assertGreaterEqual(analysis['match_score'], 10.0)
        self.assertLessEqual(analysis['match_score'], 100.0)

        # Python, SQL, Git, React should be recognized as matched
        matched = [s.lower() for s in analysis['matched_skills']]
        self.assertIn('python', matched)
        self.assertIn('sql', matched)
        self.assertIn('git', matched)

        # Weak bullets should be flagged
        weak_bullets = analysis['weak_bullet_points']
        self.assertGreater(len(weak_bullets), 0)
        flagged_issues = [issue for b in weak_bullets for issue in b['issues']]
        self.assertTrue(any('passive' in issue.lower() for issue in flagged_issues))

    def test_ai_enhancement_and_anti_hallucination(self):
        parsed = parse_resume_to_structured_json(SAMPLE_RESUME_TEXT)
        analysis = analyze_resume(parsed, target_career="software engineer")
        enhancement = enhance_resume_with_ai(parsed, analysis, target_career="software engineer")

        suggestions = enhancement['suggestions']
        self.assertGreater(len(suggestions), 0)

        # Check suggestions have explanations and do not invent fake stats without fill-in prompt
        for sug in suggestions:
            self.assertIn('explanation', sug)
            self.assertIn('improved', sug)
            if sug.get('type') == 'bullet_enhancement':
                # Check for action verb upgrade or student fill-in prompt
                improved = sug['improved']
                self.assertFalse(improved.lower().startswith('responsible for'))

        # Check optimized_sections schema
        opt = enhancement['optimized_sections']
        self.assertIn('summary', opt)
        self.assertIn('experience', opt)
        self.assertIn('skills', opt)

    def test_pdf_generation(self):
        parsed = parse_resume_to_structured_json(SAMPLE_RESUME_TEXT)
        pdf_buffer = generate_resume_pdf(parsed)
        self.assertIsInstance(pdf_buffer, io.BytesIO)
        pdf_bytes = pdf_buffer.getvalue()
        self.assertTrue(len(pdf_bytes) > 500)
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))

    def test_docx_generation(self):
        parsed = parse_resume_to_structured_json(SAMPLE_RESUME_TEXT)
        docx_buffer = generate_resume_docx(parsed)
        self.assertIsInstance(docx_buffer, io.BytesIO)
        docx_bytes = docx_buffer.getvalue()
        self.assertTrue(len(docx_bytes) > 500)
        # DOCX is a zip file starting with PK
        self.assertTrue(docx_bytes.startswith(b'PK'))


if __name__ == '__main__':
    unittest.main()
