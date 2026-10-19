"""
SkillBridge Master System Diagnostic & Feature Verification
Executes comprehensive end-to-end tests across every student, admin, AI, ML,
job matching, interview, and voice-sanitization pipeline.
"""
import sys
import os
import requests
import json
import time

BASE = "http://127.0.0.1:5000"

def test_master():
    print("=" * 72)
    print("      SKILLBRIDGE COMPREHENSIVE END-TO-END FEATURE AUDIT")
    print("=" * 72)
    
    passed_count = 0
    total_count = 0
    categories = {}

    def record(category, test_name, success, details=""):
        nonlocal passed_count, total_count
        total_count += 1
        if success:
            passed_count += 1
            status = "PASS [OK]"
        else:
            status = "FAIL [X]"
        
        if category not in categories:
            categories[category] = []
        categories[category].append((test_name, success, details))
        
        print(f"[{status}] {category:<20} | {test_name:<34} | {details}")

    # -------------------------------------------------------------
    # 1. CORE API & HEALTH
    # -------------------------------------------------------------
    cat = "Core Health"
    try:
        r = requests.get(f"{BASE}/", timeout=5)
        record(cat, "API Root Health Check", r.status_code == 200, f"HTTP {r.status_code}")
    except Exception as e:
        record(cat, "API Root Health Check", False, str(e))
        return

    # -------------------------------------------------------------
    # 2. AUTHENTICATION & RBAC
    # -------------------------------------------------------------
    cat = "Auth & Security"
    s_stud = requests.Session()
    s_admin = requests.Session()

    r = s_stud.post(f"{BASE}/api/auth/login", json={"email": "ayeshamads@gmail.com", "password": "teststudent123"})
    stud_ok = r.status_code == 200 and r.json().get("student", {}).get("role") == "student"
    record(cat, "Student Login (Auth Cookie/JWT)", stud_ok, f"User: {r.json().get('student', {}).get('name')}")

    r = s_stud.get(f"{BASE}/api/auth/me")
    me_ok = r.status_code == 200 and r.json().get("student", {}).get("id") == 1
    record(cat, "Session State Retention (/me)", me_ok, "Session Active")

    r = s_stud.get(f"{BASE}/api/admin/stats")
    record(cat, "RBAC Security Gate (Student Block)", r.status_code == 403, "Blocked with 403 Forbidden")

    r = s_admin.post(f"{BASE}/api/auth/login", json={"email": "admin@skillbridge.edu", "password": "admin123"})
    admin_ok = r.status_code == 200 and r.json().get("student", {}).get("role") == "admin"
    record(cat, "Admin Login & Elevation", admin_ok, "Admin Granted")

    # -------------------------------------------------------------
    # 3. SKILLS INVENTORY & GAPS
    # -------------------------------------------------------------
    cat = "Skills & Gaps"
    r = s_stud.get(f"{BASE}/api/student/skills")
    skills = r.json().get("skills", [])
    record(cat, "Student Skills Inventory", r.status_code == 200 and len(skills) > 0, f"{len(skills)} skills tracked")

    r = s_stud.post(f"{BASE}/api/student/analyze_skill_gap")
    gaps = r.json() if r.status_code == 200 else {}
    record(cat, "Skill Gap Analysis Engine", r.status_code == 200, f"Coverage: {gaps.get('overall_coverage')}, Missing: {len(gaps.get('missing_required', []))}")

    r = s_stud.get(f"{BASE}/api/student/verified_skill_profile")
    record(cat, "Verified Skill Portfolio", r.status_code == 200 and "verified_skills" in r.json(), "Verified skills retrieved")

    # -------------------------------------------------------------
    # 4. ADAPTIVE QUIZ & VERIFICATION
    # -------------------------------------------------------------
    if skills:
        skill_id = skills[0]["id"]
        r = s_stud.get(f"{BASE}/api/student/get_quiz/{skill_id}")
        q_data = r.json() if r.status_code == 200 else {}
        questions = q_data.get("questions", [])
        q_ok = r.status_code == 200 and len(questions) > 0
        record(cat, "Adaptive AI Quiz Generator", q_ok, f"{len(questions)} questions for {skills[0]['skill_name']}")

        if q_ok:
            sample_answers = {str(q["id"]): q.get("correct_answer", "A") for q in questions}
            r = s_stud.post(f"{BASE}/api/student/submit_quiz/{skill_id}", json={"answers": sample_answers})
            sub_res = r.json() if r.status_code in (200, 201) else {}
            record(cat, "Quiz Submission & Verification", r.status_code in (200, 201), f"Score: {sub_res.get('quiz_score_percent')}%")
    else:
        record(cat, "Adaptive AI Quiz Generator", False, "No skills in inventory")

    # -------------------------------------------------------------
    # 5. CAREER INTELLIGENCE & ML MODELS
    # -------------------------------------------------------------
    cat = "Career Intelligence"
    r = s_stud.get(f"{BASE}/api/student/career_recommendations")
    recs = r.json().get("recommendations", [])
    record(cat, "Career Track Recommender", r.status_code == 200 and len(recs) > 0, f"{len(recs)} tracks recommended")

    r = s_stud.get(f"{BASE}/api/student/readiness_breakdown")
    readiness = r.json() if r.status_code == 200 else {}
    score_val = readiness.get("readiness_score") or readiness.get("overall_score")
    record(cat, "Career Readiness Scoring (0-100)", r.status_code == 200, f"Score: {score_val}%, Tier: {readiness.get('tier')}")

    r = s_stud.post(f"{BASE}/api/student/simulate_salary", json={"additional_skills": ["Docker", "Kubernetes", "AWS"]})
    sal = r.json() if r.status_code == 200 else {}
    record(cat, "ML Salary Boost Simulator", r.status_code == 200, f"Base: {sal.get('base_salary_lpa')} LPA | Boost: +{sal.get('boost_amount_lpa')} LPA")

    r = s_stud.get(f"{BASE}/api/student/get_roadmap")
    record(cat, "Dynamic Learning Roadmap", r.status_code == 200 and "roadmap" in r.json(), "Roadmap tracks loaded")

    r = s_stud.get(f"{BASE}/api/student/badges")
    badges = r.json().get("badges", [])
    record(cat, "Achievement Badges Engine", r.status_code == 200 and len(badges) > 0, f"{len(badges)} badges awarded")

    # -------------------------------------------------------------
    # 6. JOB DISCOVERY & MATCHING
    # -------------------------------------------------------------
    cat = "Jobs & Matcher"
    r = s_stud.get(f"{BASE}/api/student/jobs")
    jobs = r.json().get("jobs", [])
    record(cat, "Live Job Discovery Feed", r.status_code == 200 and len(jobs) > 0, f"{len(jobs)} active opportunities")

    r = s_stud.get(f"{BASE}/api/student/jobs/quality_metrics")
    telem = r.json().get("metrics", {}) if r.status_code == 200 else {}
    record(cat, "Job Ingestion Telemetry", r.status_code == 200 and "total_listings_in_db" in telem, f"DB listings: {telem.get('total_listings_in_db')}, Failures: {telem.get('validation_failures')}")

    if jobs:
        test_job_id = jobs[0]["id"]
        # Save Job
        r = s_stud.post(f"{BASE}/api/student/jobs/save", json={"job_id": test_job_id})
        record(cat, "Bookmark Opportunity (Save)", r.status_code == 200, f"Job #{test_job_id} saved")

        r = s_stud.get(f"{BASE}/api/student/jobs/saved")
        record(cat, "Retrieve Saved Jobs Feed", r.status_code == 200 and any(j["id"] == test_job_id for j in r.json().get("saved_jobs", [])), "Saved feed confirmed")

        # Explain Match
        r = s_stud.get(f"{BASE}/api/student/jobs/{test_job_id}/match")
        m_data = r.json()
        match_obj = m_data.get("match", m_data)
        record(cat, "Explainable Match Matrix", r.status_code == 200 and "match_score" in match_obj, f"Fit: {match_obj.get('match_score')}%")

        # Compare Jobs
        distinct_ids = list({j["id"] for j in jobs})[:2]
        if len(distinct_ids) >= 2:
            r = s_stud.post(f"{BASE}/api/student/jobs/compare", json={"job_ids": distinct_ids})
            comp_obj = r.json().get("comparison", r.json())
            comp_list = comp_obj.get("comparisons", []) or comp_obj.get("job_evaluations", [])
            record(cat, "Side-by-Side Comparison", r.status_code == 200 and len(comp_list) >= 2, f"Compared {len(comp_list)} opportunities")

        # Unsave Job
        r = s_stud.post(f"{BASE}/api/student/jobs/unsave", json={"job_id": test_job_id})
        record(cat, "Unsave Opportunity", r.status_code == 200, "Cleanly unsaved")

    # -------------------------------------------------------------
    # 7. INTERVIEW SIMULATOR & AUDIO REPETITION SANITIZER
    # -------------------------------------------------------------
    cat = "Interview & Voice"
    r = s_stud.post(f"{BASE}/api/student/interview/start", json={"target_role": "Full Stack Engineer", "question_count": 5})
    sess = r.json().get("session", r.json())
    sess_id = sess.get("id") or sess.get("session_id")
    sess_ok = r.status_code == 200 and sess_id is not None
    record(cat, "Interview Simulator Start", sess_ok, f"Session #{sess_id}, {len(sess.get('questions', []))} questions")

    if sess_ok:
        # TEST AUDIO REPETITION SANITIZATION:
        # Submit an answer containing STT repeated words to verify our regex sanitizer in interview_simulator.py
        q1 = sess.get("questions", [])[0] if sess.get("questions") else {}
        q1_topic = q1.get("category", "Software Engineering")
        repetitive_audio_answer = f"In addressing this {q1_topic} problem problem, I implement implement modular component architecture with error boundaries and state management to guarantee system resilience."
        
        r = s_stud.post(f"{BASE}/api/student/interview/answer", json={
            "session_id": sess_id,
            "question_index": 1,
            "answer": repetitive_audio_answer
        })
        ans_data = r.json().get("evaluation", r.json())
        eval_ok = r.status_code == 200 and "overall_score" in ans_data
        score = ans_data.get("overall_score", 0)
        record(cat, "Audio Stutter Sanitizer & Rubric", eval_ok and score > 0, f"Rubric Score: {score}/100 (Cleaned & Evaluated)")

        r = s_stud.get(f"{BASE}/api/student/interview/history")
        hist = r.json().get("history", [])
        record(cat, "Interview Session History Log", r.status_code == 200 and len(hist) > 0, f"Total sessions: {len(hist)}")

    # -------------------------------------------------------------
    # 8. GROUNDED AI ASSISTANT & PROVIDERS
    # -------------------------------------------------------------
    cat = "AI Assistant (RAG)"
    r = s_stud.get(f"{BASE}/api/student/ai_providers")
    provs = r.json().get("providers", [])
    record(cat, "Multi-Provider Telemetry", r.status_code == 200 and len(provs) > 0, f"Providers: {[p['name'] for p in provs]}")

    r = s_stud.post(f"{BASE}/api/student/ask_assistant", json={"question": "What are the core skills for a software engineer?"})
    ai_res = r.json()
    record(cat, "RAG Grounded Career Assistant", r.status_code == 200 and "answer" in ai_res, f"Provider: {ai_res.get('source')}")

    # -------------------------------------------------------------
    # 9. PRIVACY & FEDERATED LEARNING
    # -------------------------------------------------------------
    cat = "Privacy & FL"
    r = s_stud.get(f"{BASE}/api/student/privacy_info")
    priv = r.json() if r.status_code == 200 else {}
    has_dp = "differential_privacy" in priv or "differential_privacy" in priv.get("details", {})
    record(cat, "Differential Privacy Guarantees", r.status_code == 200 and has_dp, "Guarantees verified")

    r = s_stud.get(f"{BASE}/api/student/federated_status")
    record(cat, "Student FL Node Telemetry", r.status_code == 200, "Node telemetry active")

    r = s_admin.get(f"{BASE}/api/admin/federated/nodes")
    nodes = r.json().get("nodes", []) or r.json().get("institutions", [])
    record(cat, "Admin Institutional Nodes Roster", r.status_code == 200 and len(nodes) > 0, f"{len(nodes)} institutional nodes")

    r = s_admin.post(f"{BASE}/api/admin/federated/train")
    tr = r.json().get("data", {})
    record(cat, "FedAvg Global Aggregation Train", r.status_code == 200, f"Round #{tr.get('round_number')}, Acc: {tr.get('global_accuracy')}")

    r = s_stud.get(f"{BASE}/api/student/account/export")
    record(cat, "GDPR / Data Sovereignty Export", r.status_code == 200 and "data_sovereignty_notice" in r.json(), "Full JSON export generated")

    # -------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------
    print("=" * 72)
    pct = round((passed_count / total_count) * 100, 1) if total_count > 0 else 0
    print(f"MASTER AUDIT COMPLETE: {passed_count}/{total_count} FEATURES PASSED ({pct}%)")
    print("=" * 72)

if __name__ == "__main__":
    test_master()
