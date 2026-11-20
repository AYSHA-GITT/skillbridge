"""
Concurrent, mixed workload for the Phase 0 memory measurement (harness only).

8 student sessions run in parallel threads, each looping over a weighted mix of the
heaviest real features: resume upload + parse + skill extraction, every RAG endpoint,
the Gemini-backed assistant / interview / roadmap, resume-optimizer PDF and DOCX
export, Skill Passport PDF, job matching and career recommendations.
At the same time: a recruiter searches candidates, opens explainable match reports
and sends verification requests; an administrator runs federated-learning rounds;
and one real job sync (live providers) runs in the background.

Usage: python load_driver.py <base_url> <phase_file> <seconds> <out_json>
"""
import json
import os
import random
import statistics
import sys
import tempfile
import threading
import time
import uuid

import requests

BASE, PHASE_FILE, SECONDS, OUT = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "backend"))
import e2e_check  # noqa: E402  (only for its resume fixtures)
requests.Session.request = e2e_check._orig_request   # undo e2e_check's error-swallowing patch

TIMEOUT = 600
STATS, LOCK = {}, threading.Lock()
TMP = tempfile.mkdtemp(prefix="phase0_")
PDF, DOCX = os.path.join(TMP, "r.pdf"), os.path.join(TMP, "r.docx")
e2e_check.make_pdf(PDF)
e2e_check.make_docx(DOCX)
TAG = uuid.uuid4().hex[:6]


def phase(name):
    open(PHASE_FILE, "w").write(name)


def record(name, ok, secs, detail=""):
    with LOCK:
        s = STATS.setdefault(name, {"ok": 0, "fail": 0, "latencies": [], "errors": []})
        s["ok" if ok else "fail"] += 1
        s["latencies"].append(secs)
        if not ok and len(s["errors"]) < 5:
            s["errors"].append(detail[:200])


def call(sess, name, method, path, ok_codes=(200, 201), **kw):
    t = time.time()
    try:
        r = getattr(sess, method)(f"{BASE}{path}", timeout=TIMEOUT, **kw)
        ok = r.status_code in ok_codes
        record(name, ok, time.time() - t, f"HTTP {r.status_code} {r.text[:120]}")
        return r
    except Exception as e:  # timeouts / connection resets (e.g. a worker killed by OOM)
        record(name, False, time.time() - t, f"{type(e).__name__}: {e}")
        return None


def js(r):
    try:
        return r.json() if r is not None else {}
    except ValueError:
        return {}


def login(email, password="phase0-password-123", portal=None):
    s = requests.Session()
    body = {"email": email, "password": password}
    if portal:
        body["portal"] = portal
    r = s.post(f"{BASE}/api/auth/login", json=body, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return s


def setup():
    phase("setup")
    adm = login("admin@skillbridge.edu", "admin123", portal="admin")
    rec = requests.Session()
    r = rec.post(f"{BASE}/api/auth/register_recruiter", timeout=TIMEOUT, json={
        "name": "Phase0 Recruiter", "email": f"p0_rec_{TAG}@example.com", "password": "phase0-password-123",
        "job_title": "HR", "organisation": {"name": f"Phase0 Org {TAG}", "website": "https://phase0.example.com"}})
    assert r.status_code == 201, r.text
    rec.post(f"{BASE}/api/recruiter/organisation/verification", json={"registration_id": "PHASE0"}, timeout=TIMEOUT)
    org_id = js(rec.get(f"{BASE}/api/recruiter/me", timeout=TIMEOUT))["organisation"]["id"]
    adm.post(f"{BASE}/api/recruiter/admin/organisations/{org_id}/review", json={"decision": "verified"}, timeout=TIMEOUT)
    job = js(rec.post(f"{BASE}/api/recruiter/jobs", timeout=TIMEOUT, json={
        "title": f"Phase0 Data Engineer {TAG}", "description": "Build data pipelines with Python, SQL and Docker on cloud.",
        "location": "Bengaluru, Karnataka", "work_arrangement": "Hybrid", "job_type": "Full-time",
        "required_skills": ["Python", "SQL", "Kubernetes"], "preferred_skills": ["AWS"]}))["job"]
    rec.post(f"{BASE}/api/recruiter/jobs/{job['id']}/publish", timeout=TIMEOUT)

    students = []
    for i in range(8):
        s = requests.Session()
        email = f"p0_s{i}_{TAG}@example.com"
        r = s.post(f"{BASE}/api/auth/register", timeout=TIMEOUT, json={
            "name": f"Phase0 Student {i}", "email": email, "password": "phase0-password-123",
            "college": "Example Institute", "course": "B.Tech CSE", "year": "4", "target_career": "data analyst"})
        assert r.status_code == 201, r.text
        path, mime = (PDF, "application/pdf") if i % 2 == 0 else (
            DOCX, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        with open(path, "rb") as f:
            rid = js(s.post(f"{BASE}/api/student/upload_resume", timeout=TIMEOUT,
                            files={"resume": (os.path.basename(path), f, mime)}))["resume"]["id"]
        s.post(f"{BASE}/api/student/parse_resume/{rid}", timeout=TIMEOUT)
        skills = js(s.post(f"{BASE}/api/student/extract_skills/{rid}", timeout=TIMEOUT)).get("skills", [])
        s.put(f"{BASE}/api/candidate/discovery", timeout=TIMEOUT, json={
            "is_discoverable": True, "consent": True,
            "visibility": {"sections": {"skills": True, "profile": True, "assessments": True}, "skill_filter": "all"}})
        students.append({"s": s, "rid": rid, "skill_ids": [k["id"] for k in skills], "path": path, "mime": mime})
    return adm, rec, job, students


def student_tasks(st, job):
    s = st["s"]

    def upload_parse_extract():
        with open(st["path"], "rb") as f:
            r = call(s, "resume upload", "post", "/api/student/upload_resume",
                     files={"resume": (os.path.basename(st["path"]), f, st["mime"])})
        rid = js(r).get("resume", {}).get("id")
        if rid:
            call(s, "resume parse", "post", f"/api/student/parse_resume/{rid}")
            call(s, "skill extraction", "post", f"/api/student/extract_skills/{rid}")

    return [
        (3, upload_parse_extract),
        (3, lambda: call(s, "RAG assistant (Gemini)", "post", "/api/student/ask_assistant",
                         json={"question": random.choice(["Which skills does a data analyst need?",
                                                          "How do I become a cloud engineer?",
                                                          "What should I learn after SQL?"])})),
        (2, lambda: call(s, "RAG resume analysis", "post", f"/api/student/rag/analyze_resume/{st['rid']}", json={})),
        (2, lambda: call(s, "RAG job match", "post", "/api/student/rag/match_job",
                         json={"job_description": "Data analyst role requiring SQL, Excel, Power BI and statistics."})),
        (2, lambda: call(s, "RAG explain gap", "post", "/api/student/rag/explain_gap", json={"career": "data analyst"})),
        (2, lambda: call(s, "career recommendations", "get", "/api/student/career_recommendations")),
        (1, lambda: call(s, "readiness breakdown", "get", "/api/student/readiness_breakdown")),
        (2, lambda: call(s, "jobs by match", "get", "/api/student/jobs", params={"sort": "match", "per_page": 20})),
        (2, lambda: call(s, "job match breakdown", "get", f"/api/student/jobs/{job['id']}/match")),
        (1, lambda: call(s, "skill passport PDF", "get", "/api/passport/me/pdf")),
        (1, lambda: call(s, "resume optimizer analyze", "post", "/api/student/resume_optimizer/analyze",
                         data={"target_career": "data analyst"})),
        (1, lambda: call(s, "resume export PDF", "post", "/api/student/resume_optimizer/export_pdf",
                         json={"sections": {"contact": {"name": "Phase0"}, "summary": "Data analyst.",
                                            "skills": ["Python", "SQL"], "experience": [], "education": []}})),
        (1, lambda: call(s, "resume export DOCX", "post", "/api/student/resume_optimizer/export_docx",
                         json={"sections": {"contact": {"name": "Phase0"}, "summary": "Data analyst.",
                                            "skills": ["Python", "SQL"], "experience": [], "education": []}})),
        (1, lambda: call(s, "interview start (Gemini)", "post", "/api/student/interview/start",
                         json={"target_role": "Data Analyst", "question_count": 5})),
        (1, lambda: st["skill_ids"] and call(s, "quiz", "get", f"/api/student/get_quiz/{random.choice(st['skill_ids'])}",
                                             ok_codes=(200, 400))),
        (1, lambda: call(s, "skill gap analysis", "post", "/api/student/analyze_skill_gap")),
    ]


def run_until(deadline, fn):
    while time.time() < deadline:
        fn()


def main():
    adm, rec, job, students = setup()
    phase("stress")
    deadline = time.time() + SECONDS
    threads = []

    for st in students:
        tasks = student_tasks(st, job)
        weights = [w for w, _ in tasks]
        fns = [f for _, f in tasks]

        def one_task(fns=fns, weights=weights):
            random.choices(fns, weights)[0]()
        threads.append(threading.Thread(target=run_until, args=(deadline, one_task), daemon=True))

    def recruiter_loop():
        res = js(call(rec, "recruiter candidate search", "get", "/api/recruiter/candidates/search",
                      params={"skills": "python,sql"}))
        refs = [c["candidate_ref"] for c in res.get("candidates", [])]
        asked = set()
        while time.time() < deadline:
            if refs:
                ref = random.choice(refs)
                prof = js(call(rec, "recruiter match report", "get", f"/api/recruiter/candidates/{ref}",
                               params={"job_id": job["id"]}))
                todo = [x["skill_name"] for x in prof.get("requestable_skills", [])]
                if todo and ref not in asked:
                    asked.add(ref)
                    call(rec, "recruiter verification request", "post",
                         f"/api/recruiter/candidates/{ref}/verification_requests", ok_codes=(201, 409),
                         json={"skills": todo[:2], "job_id": job["id"]})
            call(rec, "recruiter search", "get", "/api/recruiter/candidates/search", params={"skills": "sql"})

    def fl_loop():
        while time.time() < deadline:
            call(adm, "federated learning round", "post", "/api/admin/federated/train")
            time.sleep(20)

    def sync_once():
        call(adm, "job sync (live providers)", "post", "/api/admin/jobs/sync")

    threads += [threading.Thread(target=recruiter_loop, daemon=True), threading.Thread(target=fl_loop, daemon=True),
                threading.Thread(target=sync_once, daemon=True)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=SECONDS + TIMEOUT)
    phase("after-stress")

    summary = {}
    for name, s in sorted(STATS.items()):
        lat = s["latencies"]
        summary[name] = {"ok": s["ok"], "fail": s["fail"],
                         "p50_s": round(statistics.median(lat), 2) if lat else None,
                         "p95_s": round(sorted(lat)[int(0.95 * (len(lat) - 1))], 2) if lat else None,
                         "errors": s["errors"]}
    total_ok = sum(v["ok"] for v in summary.values())
    total_fail = sum(v["fail"] for v in summary.values())
    json.dump({"seconds": SECONDS, "concurrent_students": len(students), "requests_ok": total_ok,
               "requests_failed": total_fail, "by_feature": summary}, open(OUT, "w"), indent=1)
    print(f"load driver: {total_ok} ok, {total_fail} failed")


if __name__ == "__main__":
    main()
