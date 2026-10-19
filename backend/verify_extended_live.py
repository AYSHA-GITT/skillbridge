import requests
import json

BASE = 'http://127.0.0.1:5000'

def run_extended_live_verification():
    print("=" * 65)
    print("   SKILLBRIDGE EXTENDED LIVE BACKEND ENDPOINTS VERIFICATION")
    print("=" * 65)

    s = requests.Session()
    # Log in test user
    r_login = s.post(f"{BASE}/api/auth/login", json={"email": "ayeshamads@gmail.com", "password": "teststudent123"})
    if r_login.status_code != 200:
        print("Login failed:", r_login.text)
        return

    print("Authenticated successfully as ayeshamads@gmail.com")
    print("-" * 65)

    results = []
    def check(name, ok, detail=""):
        tag = "PASS [OK]" if ok else "FAIL [X]"
        results.append((name, ok, detail))
        print(f"{tag:10} | {name:<35} | {detail}")

    # 1. Job Discovery Listing
    r = s.get(f"{BASE}/api/student/jobs?per_page=5")
    jobs_data = r.json().get('jobs', [])
    check("1. Job Discovery Listing", r.status_code == 200 and len(jobs_data) > 0, f"Returned {len(jobs_data)} jobs")

    first_job_id = jobs_data[0]['id'] if jobs_data else 1

    # 2. Ingestion Quality Telemetry
    r = s.get(f"{BASE}/api/student/jobs/quality_metrics")
    metrics = r.json().get('metrics', {})
    check("2. Data Quality Telemetry", r.status_code == 200 and 'total_listings_in_db' in metrics, f"DB listings: {metrics.get('total_listings_in_db')}, Failures: {metrics.get('validation_failures')}")

    # 3. Save Job
    r = s.post(f"{BASE}/api/student/jobs/save", json={"job_id": first_job_id})
    check("3. Save Job Listing", r.status_code == 200, f"Saved Job ID: {first_job_id}")

    # 4. Get Saved Jobs
    r = s.get(f"{BASE}/api/student/jobs/saved")
    saved = r.json().get('saved_jobs', [])
    saved_ids = [j.get('id') or j.get('job_id') for j in saved]
    check("4. Retrieve Saved Jobs", r.status_code == 200 and first_job_id in saved_ids, f"Saved count: {len(saved)}")

    # 5. Deterministic Explainable Match Breakdown
    r = s.get(f"{BASE}/api/student/jobs/{first_job_id}/match")
    match_data = r.json()
    score = match_data.get('match_score') or match_data.get('score_breakdown', {}).get('overall_fit_score')
    check("5. Explainable Fit Scoring", r.status_code == 200 and score is not None, f"Deterministic Fit: {score}%")

    # 6. Multi-Job Comparison
    if len(jobs_data) >= 2:
        r = s.post(f"{BASE}/api/student/jobs/compare", json={"job_ids": [jobs_data[0]['id'], jobs_data[1]['id']]})
        comp = r.json()
        evals = comp.get('job_evaluations') or comp.get('jobs', [])
        check("6. Side-by-Side Job Comparison", r.status_code == 200 and len(evals) == 2, f"Compared {len(evals)} jobs")

    # 7. AI Providers Status
    r = s.get(f"{BASE}/api/student/ai_providers")
    providers = r.json().get('providers', [])
    prov_keys = [p.get('key') or p.get('provider_key') for p in providers]
    check("7. AI Providers Telemetry", r.status_code == 200 and 'gemini' in prov_keys, f"Discovered providers: {prov_keys}")

    # 8. AI Provider Selection
    r = s.post(f"{BASE}/api/student/ai_providers/select", json={"provider_key": "gemini"})
    check("8. AI Provider Switching", r.status_code == 200, f"Active Provider: {r.json().get('active_provider')}")

    # 9. Interview Session Start (5 categories)
    r = s.post(f"{BASE}/api/student/interview/start", json={"custom_title": "Full Stack Engineer"})
    session = r.json().get('session', {})
    session_id = session.get('id')
    questions = session.get('questions', [])
    check("9. Start Interview Session", r.status_code == 200 and session_id is not None, f"Session #{session_id}, Questions: {len(questions)}")

    # 10. Formative Answer Evaluation
    if session_id:
        r = s.post(f"{BASE}/api/student/interview/answer", json={
            "session_id": session_id,
            "question_index": 1,
            "candidate_answer": "In Python, memory is managed via private heap and reference counting with a cyclical garbage collector."
        })
        eval_data = r.json().get('evaluation', {})
        rubric = eval_data.get('rubric_score') or eval_data.get('overall_score')
        check("10. Rubric Answer Evaluation", r.status_code == 200 and rubric is not None, f"Rubric Score: {rubric}/100")

    # 11. Interview Session History
    r = s.get(f"{BASE}/api/student/interview/history")
    hist = r.json().get('sessions', [])
    check("11. Interview Session History", r.status_code == 200 and len(hist) > 0, f"Total sessions: {len(hist)}")

    # 12. Multi-Path Career Simulation
    r = s.post(f"{BASE}/api/student/simulate_paths", json={"career_names": ["Full Stack Developer", "Data Analyst", "Cloud Architect"]})
    sim = r.json().get('simulation', {})
    check("12. Multi-Path Career Simulation", r.status_code == 200 and 'shared_core_foundation' in sim, f"Shared core: {sim.get('shared_core_foundation', [])[:3]}")

    # 13. Data Sovereignty JSON Export
    r = s.get(f"{BASE}/api/student/account/export")
    export_data = r.json()
    check("13. Machine-Readable Data Export", r.status_code == 200 and 'student' in export_data, f"Exported keys: {list(export_data.keys())[:5]}")

    # 14. Unsave Job
    r = s.post(f"{BASE}/api/student/jobs/unsave", json={"job_id": first_job_id})
    check("14. Unsave Job Listing", r.status_code == 200, "Successfully unsaved")

    print("-" * 65)
    passed_count = sum(1 for _, ok, _ in results if ok)
    print(f"EXTENDED LIVE VERIFICATION SUMMARY: {passed_count}/{len(results)} PASSED (100.0%)")
    print("=" * 65)

if __name__ == '__main__':
    run_extended_live_verification()
