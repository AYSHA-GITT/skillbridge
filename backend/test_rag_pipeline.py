"""
Validation suite for SkillLens / SkillBridge RAG (Retrieval-Augmented Generation)
Tests semantic retrieval, SentenceTransformer embeddings, FAISS / NumPy vector indexing,
and Gemini grounded synthesis.
"""

import sys
import os
import requests
import io

BASE = 'http://127.0.0.1:5000'

def test_rag_suite():
    print("=" * 65)
    print("      SKILLBRIDGE RAG RETRIEVAL & GROUNDING VALIDATION")
    print("=" * 65)

    results = []
    def log(name, passed, detail=""):
        status = "PASS [OK]" if passed else "FAIL [X]"
        results.append((name, passed, detail))
        print(f"{status:10} | {name:<42} | {detail}")

    # 1. Login session
    s = requests.Session()
    r_login = s.post(f"{BASE}/api/auth/login", json={"email": "ayeshamads@gmail.com", "password": "teststudent123"})
    log("1. Student Authentication", r_login.status_code == 200, f"Logged in: {r_login.json().get('student', {}).get('name')}")

    # 2. RAG Catalog Retrieval
    r_cat = s.get(f"{BASE}/api/student/rag/catalog")
    cat_ok = r_cat.status_code == 200
    cat_data = r_cat.json() if cat_ok else {}
    careers = cat_data.get('careers', [])
    jds = cat_data.get('job_descriptions', [])
    chunks = cat_data.get('total_indexed_chunks', 0)
    log("2. RAG Knowledge Catalog (/rag/catalog)", cat_ok, f"Careers: {len(careers)} | JDs: {len(jds)} | Chunks: {chunks}")

    # 3. Resume Upload for RAG Test
    test_pdf_content = (
        b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources <<>> /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n"
        b"4 0 obj\n<< /Length 190 >>\nstream\n"
        b"BT /F1 12 Tf 72 712 Td (Candidate: Aysha Daniya. Skills: Python, SQL, PostgreSQL, Docker, Git, Flask, React, Pandas. Experience: Built scalable backend microservices and automated data cleansing pipelines.) Tj ET\n"
        b"endstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n0000000118 00000 n\n0000000208 00000 n\n"
        b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n450\n%%EOF\n"
    )
    r_up = s.post(f"{BASE}/api/student/upload_resume", files={'resume': ('rag_test_resume.pdf', io.BytesIO(test_pdf_content), 'application/pdf')})
    resume_id = r_up.json().get('resume', {}).get('id') if r_up.status_code in (200, 201) else None
    log("3. Resume Upload for RAG", resume_id is not None, f"Resume ID: {resume_id}")

    # 4. RAG Semantic Resume Analysis
    if resume_id:
        r_rag_res = s.post(f"{BASE}/api/student/rag/analyze_resume/{resume_id}", json={"target_career": "Data Analyst"})
        rag_res_ok = r_rag_res.status_code == 200
        analysis = r_rag_res.json().get('rag_analysis', {}) if rag_res_ok else {}
        match_score = analysis.get('semantic_match_score', 0)
        explicit = analysis.get('explicit_skills', [])
        missing = analysis.get('missing_skills', [])
        sources = analysis.get('retrieved_sources', [])
        log("4. RAG Resume Analysis (/rag/analyze_resume)", rag_res_ok, f"Score: {match_score}% | Explicit: {len(explicit)} | Missing: {len(missing)}")
        log("5. Citation Traceability (RAG Sources)", len(sources) > 0, f"Retrieved {len(sources)} benchmarks: {[s.get('title') for s in sources[:2]]}")
    else:
        log("4. RAG Resume Analysis (/rag/analyze_resume)", False, "Upload failed")
        log("5. Citation Traceability (RAG Sources)", False, "Upload failed")

    # 6. Interactive Semantic Job Matching (Custom JD)
    sample_jd = """
    FinTech Global is seeking a Junior Software Engineer with Python and SQL experience.
    Must understand Git version control, Docker containerization, and RESTful API design.
    Familiarity with React or frontend development is a strong plus.
    """
    r_match = s.post(f"{BASE}/api/student/rag/match_job", json={"job_description": sample_jd, "resume_id": resume_id})
    match_ok = r_match.status_code == 200
    match_data = r_match.json().get('match_results', {}) if match_ok else {}
    jd_fit = match_data.get('overall_match_percent', 0)
    matched_skills = match_data.get('matched_skills', [])
    missing_skills = match_data.get('missing_skills', [])
    log("6. Semantic Job Matcher (/rag/match_job)", match_ok, f"Fit: {jd_fit}% | Matched: {matched_skills} | Missing: {missing_skills}")

    # 7. Grounded Skill Gap Explanation (RAG)
    r_gap = s.post(f"{BASE}/api/student/rag/explain_gap", json={"career": "Data Scientist"})
    gap_ok = r_gap.status_code == 200
    gap_data = r_gap.json().get('gap_report', {}) if gap_ok else {}
    source_bm = gap_data.get('benchmark_source', '')
    sample_jds = gap_data.get('related_postings_sample', [])
    log("7. Grounded Skill Gap Report (/rag/explain_gap)", gap_ok, f"Benchmark: {source_bm[:35]}... | Postings: {len(sample_jds)}")

    # 8. Dynamic Addition of Custom Job Description
    new_jd_payload = {
        "role": "Cloud Security DevOps Engineer",
        "company": "SecureVantage Cyber Corp",
        "location": "Mumbai / Remote",
        "salary_range": "11 - 16 LPA",
        "career_category": "devops engineer",
        "description": "Seeking a Cloud Security Engineer with deep expertise in Docker, Kubernetes, Linux, AWS, and CI/CD pipelines.",
        "required_skills": ["docker", "kubernetes", "linux", "aws", "ci/cd"],
        "preferred_skills": ["python", "terraform", "wireshark"],
        "source": "SecureVantage Corporate Careers 2026 #SEC-501"
    }
    r_add = s.post(f"{BASE}/api/student/rag/add_job", json=new_jd_payload)
    add_ok = r_add.status_code in (200, 201)
    log("8. Dynamic Knowledge Addition (/rag/add_job)", add_ok, f"Job Added ID: {r_add.json().get('job_id')}")

    # 9. Verify Assistant Grounded Citations
    r_ask = s.post(f"{BASE}/api/student/ask_assistant", json={"question": "What skills do I need to learn to become a data analyst and what do companies look for?"})
    ask_ok = r_ask.status_code == 200
    ask_res = r_ask.json() if ask_ok else {}
    citations = ask_res.get('citations', [])
    log("9. AI Assistant RAG Grounding (/ask_assistant)", ask_ok, f"Source: {ask_res.get('source')} | Citations: {len(citations)}")

    # Summary
    print("=" * 65)
    passed_count = sum(1 for _, p, _ in results if p)
    total_count = len(results)
    print(f"RAG VALIDATION SUMMARY: {passed_count}/{total_count} PASSED ({round(passed_count/total_count*100, 1)}%)")
    print("=" * 65)

if __name__ == '__main__':
    test_rag_suite()
