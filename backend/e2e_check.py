"""
End-to-end feature check against the RUNNING SkillBridge servers.

Usage (backend on :5000 and frontend on :3000 must be running):
    cd backend && python e2e_check.py

Creates two throw-away student accounts (deleted at the end) and logs in as the
seeded admin account (admin@skillbridge.edu). Admin checks trigger one manual
job sync and one federated-learning round. Resume fixtures and the results
JSON are written to a temporary directory, not the repository.
"""
import io
import json
import os
import sys
import time
import uuid

import requests

_orig_request = requests.Session.request


class _Dead:
    status_code = 599
    text = ""
    content = b""

    def json(self):
        return {}


def _safe_request(self, *a, **kw):
    try:
        return _orig_request(self, *a, **kw)
    except requests.RequestException as e:
        print(f"   !! connection error: {type(e).__name__}", flush=True)
        return _Dead()


requests.Session.request = _safe_request

BASE = "http://127.0.0.1:5000"
FRONT = "http://localhost:3000"
import tempfile
OUT = tempfile.mkdtemp(prefix="skillbridge_e2e_")
RESULTS = []


def rec(area, feature, status, detail=""):
    RESULTS.append((area, feature, status, detail))
    mark = {"PASS": "PASS", "FAIL": "FAIL", "WARN": "WARN"}[status]
    print(f"[{mark}] {area:<18} {feature:<48} {detail}"[:220], flush=True)


def check(area, feature, cond, detail="", warn=False):
    rec(area, feature, "PASS" if cond else ("WARN" if warn else "FAIL"), detail)
    return cond


def timed(fn, *a, **kw):
    t = time.time()
    r = fn(*a, **kw)
    return r, round(time.time() - t, 1)


def js(r):
    try:
        return r.json()
    except Exception:
        return {}


# ── resume fixtures ──────────────────────────────────────────────────────
RESUME_LINES = [
    "Test Student",
    "SUMMARY",
    "Final-year B.Tech Computer Science student interested in backend and data roles.",
    "TECHNICAL SKILLS",
    "Python, JavaScript, React, SQL, Docker, Power BI",
    "PROJECTS",
    "Built a REST API in Python with Flask and PostgreSQL for a college event portal.",
    "Created a sales dashboard in Power BI for a student club.",
    "EXPERIENCE",
    "Software Intern at Acme Labs: used Git and Linux to deploy internal tools.",
    "CERTIFICATIONS",
    "AWS Cloud Practitioner",
    "EDUCATION",
    "B.Tech Computer Science, Example Institute of Technology, 2026",
]
EXPECTED_SKILLS = {"python", "javascript", "react", "sql", "docker", "power bi", "rest api", "flask",
                   "postgresql", "git", "linux", "aws"}


def make_docx(path):
    from docx import Document
    d = Document()
    for line in RESUME_LINES:
        d.add_paragraph(line)
    d.save(path)


def make_pdf(path):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(path, pagesize=A4)
    y = 800
    for line in RESUME_LINES:
        c.drawString(50, y, line)
        y -= 18
    c.save()


def register(s, email):
    return s.post(f"{BASE}/api/auth/register", json={
        "name": "E2E Check", "email": email, "password": "e2e-password-123",
        "college": "Example Institute", "course": "B.Tech CSE", "year": "4",
        "target_career": "software engineer"})


def main():
    pdf_path, docx_path = os.path.join(OUT, "e2e_resume.pdf"), os.path.join(OUT, "e2e_resume.docx")
    make_pdf(pdf_path)
    make_docx(docx_path)
    tag = uuid.uuid4().hex[:8]
    email_a, email_b = f"e2e_a_{tag}@example.com", f"e2e_b_{tag}@example.com"
    s = requests.Session()
    s2 = requests.Session()
    adm = requests.Session()

    # ── Infrastructure ───────────────────────────────────────────────────
    A = "Infrastructure"
    check(A, "Backend health", requests.get(f"{BASE}/api/health").status_code == 200)
    r = requests.get(FRONT)
    check(A, "Frontend serves app", r.status_code == 200 and '<div id="root">' in r.text)

    # ── Auth & security ──────────────────────────────────────────────────
    A = "Auth & security"
    r = register(s, email_a)
    check(A, "Register student", r.status_code == 201, f"HTTP {r.status_code}")
    r = s2.post(f"{BASE}/api/auth/register", json={"name": "X", "email": email_b, "password": "e2e-password-123",
                                                   "college": "c", "course": "c", "role": "admin"})
    check(A, "Register ignores role=admin", r.status_code == 201 and js(r)["student"]["role"] == "student",
          f"role={js(r).get('student', {}).get('role')}")
    check(A, "Weak password rejected", requests.post(f"{BASE}/api/auth/register", json={
        "name": "x", "email": f"weak_{tag}@example.com", "password": "123", "college": "c", "course": "c"}).status_code == 400)
    check(A, "Duplicate email rejected", register(requests.Session(), email_a).status_code == 409)
    check(A, "Wrong password rejected", requests.post(f"{BASE}/api/auth/login", json={
        "email": email_a, "password": "nope"}).status_code == 401)
    check(A, "Session /me", js(s.get(f"{BASE}/api/auth/me")).get("student", {}).get("email") == email_a)
    check(A, "Unauthenticated blocked", requests.get(f"{BASE}/api/student/skills").status_code == 401)
    check(A, "Student blocked from admin", s.get(f"{BASE}/api/admin/stats").status_code == 403)
    check(A, "Student blocked from manual sync", s.post(f"{BASE}/api/student/jobs/sync").status_code == 403)
    r = adm.post(f"{BASE}/api/auth/login", json={"email": "admin@skillbridge.edu", "password": "admin123"})
    admin_ok = check(A, "Admin login", r.status_code == 200 and js(r)["student"]["role"] == "admin")

    # ── Resume pipeline ──────────────────────────────────────────────────
    A = "Resume"
    for label, path, mime in [("PDF", pdf_path, "application/pdf"),
                              ("DOCX", docx_path,
                               "application/vnd.openxmlformats-officedocument.wordprocessingml.document")]:
        with open(path, "rb") as f:
            r = s.post(f"{BASE}/api/student/upload_resume", files={"resume": (os.path.basename(path), f, mime)})
        ok = check(A, f"Upload {label}", r.status_code == 201, f"HTTP {r.status_code}")
        rid = js(r).get("resume", {}).get("id")
        if not ok:
            continue
        r = s.post(f"{BASE}/api/student/parse_resume/{rid}")
        check(A, f"Parse {label}", r.status_code == 200 and js(r).get("text_length", 0) > 300,
              f"{js(r).get('text_length')} chars")
        r = s.post(f"{BASE}/api/student/extract_skills/{rid}")
        found = {sk["skill_name"] for sk in js(r).get("skills", [])}
        check(A, f"Extract skills {label} (exact set)", found == EXPECTED_SKILLS,
              f"missing={sorted(EXPECTED_SKILLS - found)} extra={sorted(found - EXPECTED_SKILLS)}")
        resume_id = rid
    with open(os.path.join(OUT, "bad.txt"), "w") as f:
        f.write("hello")
    with open(os.path.join(OUT, "bad.txt"), "rb") as f:
        check(A, "Reject non-PDF/DOCX", s.post(f"{BASE}/api/student/upload_resume",
                                               files={"resume": ("bad.txt", f, "text/plain")}).status_code == 400)
    skills = js(s.get(f"{BASE}/api/student/skills"))
    sk_list = skills.get("skills") or skills.get("all_skills") or []
    if isinstance(skills, dict) and not sk_list:
        for v in skills.values():
            if isinstance(v, list) and v and isinstance(v[0], dict) and "skill_name" in v[0]:
                sk_list = v
                break
    by_name = {x["skill_name"]: x for x in sk_list}
    check(A, "No duplicate skills after 2 uploads", len(sk_list) == len(by_name) == len(EXPECTED_SKILLS),
          f"{len(sk_list)} rows")
    ev = {n: by_name[n].get("evidence_strength") for n in ("flask", "docker", "aws") if n in by_name}
    check(A, "Evidence strength per skill", ev == {"flask": "applied", "docker": "listed_only", "aws": "supporting"},
          str(ev))
    check(A, "Explanations present", all(x.get("extraction_explanation") for x in sk_list))
    r = s2.post(f"{BASE}/api/student/parse_resume/{resume_id}")
    check(A, "Other user cannot parse my resume", r.status_code == 404)

    # ── Quiz / verification ──────────────────────────────────────────────
    A = "Skill verification"
    py = by_name.get("python")
    r, t = timed(s.get, f"{BASE}/api/student/get_quiz/{py['id']}", timeout=180)
    quiz = js(r)
    qs = quiz.get("questions", [])
    check(A, "Get quiz (python)", r.status_code == 200 and len(qs) >= 5, f"{len(qs)} questions, {t}s")
    if qs:
        check(A, "Answers not leaked to client", all("correct_answer" not in q for q in qs))
        check(A, "Difficulty mix", len({q.get("difficulty") for q in qs}) >= 2,
              str(sorted({str(q.get('difficulty')) for q in qs})))
        r = s.post(f"{BASE}/api/student/submit_quiz/{py['id']}", json={"answers": {str(qs[0]["id"]): "A"}})
        check(A, "Partial quiz rejected", r.status_code == 400)
        r = s.post(f"{BASE}/api/student/submit_quiz/{py['id']}", json={"answers": {str(q["id"]): "A" for q in qs}})
        body = js(r)
        check(A, "Full quiz scored + review", r.status_code == 201 and len(body.get("review", [])) == len(qs),
              f"score={body.get('quiz_score_percent')}% proficiency={body.get('proficiency')}")
    r = s.get(f"{BASE}/api/student/get_quiz/{py['id']}")
    check(A, "Other user cannot quiz my skill", s2.get(f"{BASE}/api/student/get_quiz/{py['id']}").status_code == 404)
    r = s.get(f"{BASE}/api/student/assessments")
    check(A, "Assessment history", r.status_code == 200)
    r = s.get(f"{BASE}/api/student/verified_skill_profile")
    check(A, "Verified skill profile", r.status_code == 200)

    # ── Career guidance ──────────────────────────────────────────────────
    A = "Career guidance"
    r = s.post(f"{BASE}/api/student/set_target_career", json={"target_career": "data analyst"})
    check(A, "Set target career", r.status_code == 200)
    r, t = timed(s.post, f"{BASE}/api/student/analyze_skill_gap", timeout=180)
    gap = js(r)
    check(A, "Skill gap analysis", r.status_code == 200, f"{t}s keys={list(gap)[:6]}")
    r = s.get(f"{BASE}/api/student/readiness_breakdown")
    rb = js(r)
    check(A, "Readiness breakdown", r.status_code == 200, json.dumps(rb)[:150])
    r, t = timed(s.get, f"{BASE}/api/student/career_recommendations", timeout=180)
    recs = js(r)
    check(A, "Career recommendations", r.status_code == 200, f"{t}s")
    r = s.get(f"{BASE}/api/student/career_recommendation/data analyst", timeout=180)
    check(A, "Single career recommendation", r.status_code == 200)
    r = s.post(f"{BASE}/api/student/compare_careers", json={"careers": ["data analyst", "software engineer"]}, timeout=180)
    check(A, "Compare careers", r.status_code == 200)
    r = s.post(f"{BASE}/api/student/simulate_paths", json={"career_names": ["data analyst", "data scientist"]}, timeout=180)
    check(A, "Simulate career paths", r.status_code == 200)
    r = s.get(f"{BASE}/api/student/career_insights")
    check(A, "Career insights", r.status_code == 200)

    # ── Roadmap ──────────────────────────────────────────────────────────
    A = "Roadmap"
    r, t = timed(s.post, f"{BASE}/api/student/generate_roadmap", timeout=300)
    check(A, "Generate roadmap", r.status_code in (200, 201), f"HTTP {r.status_code} {t}s {str(js(r))[:120]}")
    r = s.get(f"{BASE}/api/student/get_roadmap")
    rm = js(r)
    groups = rm.get("roadmap") or []
    plans = [d for g in groups for d in g.get("days", [])]
    check(A, "Get roadmap", r.status_code == 200 and len(plans) > 0, f"{len(groups)} skills, {len(plans)} days")
    order = [g["skill"] for g in groups]
    missing_req = gap.get("missing_required", [])
    missing_all = set(missing_req) | set(gap.get("missing_nice_to_have", []))
    check(A, "Roadmap covers exactly the gaps", set(order) == missing_all,
          f"roadmap={order}")
    n_req = len(missing_req)
    check(A, "Required gaps come first", set(order[:n_req]) == set(missing_req),
          f"first {n_req}: {order[:n_req]}")
    on_resume = [g["skill"] for g in groups if g.get("already_on_resume")]
    check(A, "Flags gaps already on resume", set(on_resume) == (missing_all & EXPECTED_SKILLS),
          f"flagged={on_resume}")
    print("   roadmap sample:", [(g["skill"], g.get("category"), g["days"][0].get("topic")) for g in groups[:4]], flush=True)
    if plans and isinstance(plans[0], dict) and plans[0].get("id"):
        r = s.post(f"{BASE}/api/student/complete_roadmap_day/{plans[0]['id']}")
        check(A, "Complete a roadmap day", r.status_code == 200)
        check(A, "Other user cannot complete my day",
              s2.post(f"{BASE}/api/student/complete_roadmap_day/{plans[0]['id']}").status_code == 404)

    # ── Progress, badges, salary ─────────────────────────────────────────
    A = "Progress & salary"
    check(A, "Progress history", s.get(f"{BASE}/api/student/progress_history").status_code == 200)
    check(A, "Badges", s.get(f"{BASE}/api/student/badges").status_code == 200)
    r = s.post(f"{BASE}/api/student/simulate_salary", json={"additional_skills": ["docker", "aws"]})
    sal = js(r)
    txt = json.dumps(sal)
    check(A, "Salary simulation", r.status_code == 200, txt[:140])
    check(A, "Salary labelled as estimate", "Illustrative" in txt or "is_estimate" in txt, "", warn=True)

    # ── RAG / assistant ──────────────────────────────────────────────────
    A = "RAG assistant"
    r, t = timed(s.post, f"{BASE}/api/student/ask_assistant",
                 json={"question": "Which skills does a data analyst need?"}, timeout=180)
    a = js(r)
    check(A, "Ask assistant", r.status_code == 200 and len(str(a.get("answer", ""))) > 20,
          f"{t}s is_rag={a.get('is_rag')} sources={len(a.get('retrieved_sources') or [])} provider={a.get('provider') or a.get('ai_provider')}")
    r, t = timed(s.post, f"{BASE}/api/student/ask_assistant",
                 json={"question": "What is the best chocolate cake recipe?"}, timeout=180)
    a = js(r)
    check(A, "Off-topic: no career sources cited", r.status_code == 200 and not a.get("retrieved_sources"),
          f"sources={len(a.get('retrieved_sources') or [])}", warn=True)
    r = s.post(f"{BASE}/api/student/rag/analyze_resume/{resume_id}", json={}, timeout=180)
    check(A, "RAG resume analysis", r.status_code == 200, f"HTTP {r.status_code}")
    r = s.post(f"{BASE}/api/student/rag/match_job", json={"job_description":
               "Data analyst role requiring SQL, Excel, Power BI and statistics."}, timeout=180)
    check(A, "RAG job match", r.status_code == 200, f"HTTP {r.status_code}")
    r = s.post(f"{BASE}/api/student/rag/explain_gap", json={"career": "data analyst"}, timeout=180)
    check(A, "RAG explain gap", r.status_code == 200, f"HTTP {r.status_code}")
    check(A, "RAG catalog", s.get(f"{BASE}/api/student/rag/catalog").status_code == 200)

    # ── Jobs ─────────────────────────────────────────────────────────────
    A = "Jobs"
    r = s.get(f"{BASE}/api/student/jobs", params={"per_page": 5, "sort": "recent"})
    d = js(r)
    jobs = d.get("jobs", [])
    check(A, "Search + pagination", r.status_code == 200 and d.get("total", 0) > 0 and len(jobs) <= 5,
          f"total={d.get('total')} pages={d.get('pages')}")
    check(A, "No demo listings in results", all(not j["is_sample"] for j in jobs))
    check(A, "Freshness + source on each job", all(j.get("freshness") and j.get("source") for j in jobs))
    check(A, "Match score attached", all("match_score" in j for j in jobs))
    dates = [j["posting_date"] for j in jobs if j["posting_date"]]
    check(A, "Sort by recent", dates == sorted(dates, reverse=True))
    filt_ok = True
    for params, pred in [
        ({"opportunity": "internship"}, lambda j: j["job_type"] == "Internship"),
        ({"work_arrangement": "Remote"}, lambda j: j["work_arrangement"] == "Remote"),
        ({"date_posted": "7d"}, lambda j: j["freshness"]["posted_days_ago"] is not None and j["freshness"]["posted_days_ago"] <= 7),
        ({"skill": "python"}, lambda j: "python" in j["required_skills"] + j["preferred_skills"]),
        ({"entry_level": "true"}, lambda j: j["is_entry_level"] or j["job_type"] == "Internship"),
    ]:
        res = js(s.get(f"{BASE}/api/student/jobs", params={**params, "per_page": 50})).get("jobs", [])
        good = all(pred(j) for j in res)
        filt_ok &= good
        check(A, f"Filter {list(params)[0]}", good, f"{len(res)} results")
    r = s.get(f"{BASE}/api/student/jobs", params={"sort": "match", "per_page": 10})
    ms = [j["match_score"] for j in js(r).get("jobs", []) if j["match_score"] is not None]
    check(A, "Sort by best match", ms == sorted(ms, reverse=True), f"top={ms[:3]}")
    if jobs:
        jid = jobs[0]["id"]
        check(A, "Job detail", s.get(f"{BASE}/api/student/jobs/{jid}").status_code == 200)
        r, t = timed(s.get, f"{BASE}/api/student/jobs/{jid}/match", timeout=120)
        m = js(r)
        check(A, "Explainable match", r.status_code == 200 and "match_reasons" in m, f"{t}s score={m.get('match_score')}")
        check(A, "Save job", s.post(f"{BASE}/api/student/jobs/save", json={"job_id": jid}).status_code == 200)
        check(A, "Saved list", jid in [x["id"] for x in js(s.get(f"{BASE}/api/student/jobs/saved"))["saved_jobs"]])
        check(A, "Saved list private", jid not in [x["id"] for x in js(s2.get(f"{BASE}/api/student/jobs/saved"))["saved_jobs"]])
        check(A, "Unsave job", s.post(f"{BASE}/api/student/jobs/unsave", json={"job_id": jid}).status_code == 200)
        r = s.post(f"{BASE}/api/student/jobs/{jid}/apply", json={"cover_note": "e2e"})
        check(A, "Track application", r.status_code == 201)
        check(A, "Duplicate application blocked",
              js(s.post(f"{BASE}/api/student/jobs/{jid}/apply", json={})).get("status") == "already_applied")
        check(A, "Applications list", js(s.get(f"{BASE}/api/student/jobs/applied")).get("total_count") == 1)
        check(A, "Withdraw application", s.post(f"{BASE}/api/student/jobs/{jid}/withdraw").status_code == 200)
        if len(jobs) >= 2:
            r = s.post(f"{BASE}/api/student/jobs/compare", json={"job_ids": [jobs[0]["id"], jobs[1]["id"]]})
            check(A, "Compare jobs", r.status_code == 200 and len(js(r).get("jobs", [])) == 2)
    qm = js(s.get(f"{BASE}/api/student/jobs/quality_metrics"))
    check(A, "Data-source metrics", "next_scheduled_sync" in qm and "listings_by_status" in qm,
          f"last_success={qm.get('last_successful_sync')} next={qm.get('next_scheduled_sync')}")
    configured = {a['health']['provider']: a['health']['configured'] for a in qm.get('adapters', [])}
    check(A, "Adzuna configured", configured.get("adzuna"), "credentials not set", warn=True)
    check(A, "Jooble configured", configured.get("jooble"), "credentials not set", warn=True)
    india = js(s.get(f"{BASE}/api/student/jobs", params={"region": "india"})).get("total", 0)
    check(A, "Real Indian listings available", india > 0, f"{india} listings", warn=True)

    # ── Preferences & alerts ─────────────────────────────────────────────
    A = "Preferences/alerts"
    r = s.put(f"{BASE}/api/student/job_preferences", json={"preferred_locations": ["Bengaluru", "Mangaluru"],
                                                          "work_modes": ["Remote", "Hybrid"], "experience_years": 0})
    check(A, "Save preferences", r.status_code == 200)
    check(A, "Read preferences", js(s.get(f"{BASE}/api/student/job_preferences"))["preferences"]["preferred_locations"]
          == ["Bengaluru", "Mangaluru"])
    r = s.post(f"{BASE}/api/student/job_alerts", json={"name": "Data roles", "roles": ["data analyst"],
                                                       "locations": ["remote"], "frequency": "daily"})
    aid = js(r).get("alert", {}).get("id")
    check(A, "Create alert", r.status_code == 201)
    check(A, "Invalid alert rejected", s.post(f"{BASE}/api/student/job_alerts", json={"name": "x"}).status_code == 400)
    check(A, "Update alert", s.put(f"{BASE}/api/student/job_alerts/{aid}", json={"is_active": False}).status_code == 200)
    check(A, "Other user cannot edit alert", s2.put(f"{BASE}/api/student/job_alerts/{aid}", json={"name": "x"}).status_code == 404)
    check(A, "Notifications", s.get(f"{BASE}/api/student/job_alerts/notifications").status_code == 200)
    check(A, "Mark read", s.post(f"{BASE}/api/student/job_alerts/notifications/read", json={}).status_code == 200)
    check(A, "Delete alert", s.delete(f"{BASE}/api/student/job_alerts/{aid}").status_code == 200)

    # ── Interview prep ───────────────────────────────────────────────────
    A = "Interview prep"
    r, t = timed(s.post, f"{BASE}/api/student/interview/start", json={"target_role": "Data Analyst", "question_count": 5},
                 timeout=300)
    iv = js(r)
    sess = iv.get("session") or iv
    sid = sess.get("session_id") or sess.get("id") or iv.get("session_id")
    qlist = sess.get("questions") or iv.get("questions") or []
    check(A, "Start session", r.status_code == 200 and len(qlist) == 5, f"{t}s {len(qlist)} questions")
    if sid and qlist:
        q0 = qlist[0]
        r, t = timed(s.post, f"{BASE}/api/student/interview/answer", json={
            "session_id": sid, "question_id": q0.get("id"), "question_index": q0.get("question_index", 0),
            "answer": "I would use SQL joins and group by to aggregate sales, then visualise trends in Power BI."},
            timeout=300)
        check(A, "Evaluate answer", r.status_code == 200 and "overall_score" in json.dumps(js(r)), f"{t}s")
        check(A, "Session detail", s.get(f"{BASE}/api/student/interview/session/{sid}").status_code == 200)
        check(A, "Other user cannot read session", s2.get(f"{BASE}/api/student/interview/session/{sid}").status_code in (403, 404))
    check(A, "History", s.get(f"{BASE}/api/student/interview/history").status_code == 200)

    # ── Resume optimizer ─────────────────────────────────────────────────
    A = "Resume optimizer"
    check(A, "Careers list", s.get(f"{BASE}/api/student/resume_optimizer/careers").status_code == 200)
    check(A, "My resumes", s.get(f"{BASE}/api/student/resume_optimizer/my_resumes").status_code == 200)
    r, t = timed(s.post, f"{BASE}/api/student/resume_optimizer/analyze", data={"target_career": "data analyst"}, timeout=300)
    an = js(r)
    check(A, "Analyze resume", r.status_code == 200 and "match_analysis" in an,
          f"{t}s score={an.get('match_analysis', {}).get('match_score')}")
    sections = an.get("optimized_sections") or {"contact": {"name": "E2E"}, "summary": "x", "skills": ["Python"],
                                                 "experience": [], "education": []}
    r = s.post(f"{BASE}/api/student/resume_optimizer/export_pdf", json={"sections": sections})
    check(A, "Export PDF", r.status_code == 200 and r.content[:4] == b"%PDF", f"{len(r.content)} bytes")
    r = s.post(f"{BASE}/api/student/resume_optimizer/export_docx", json={"sections": sections})
    check(A, "Export DOCX", r.status_code == 200 and r.content[:2] == b"PK", f"{len(r.content)} bytes")

    # ── AI providers, privacy, FL ────────────────────────────────────────
    A = "AI / privacy / FL"
    prov = js(s.get(f"{BASE}/api/student/ai_providers"))
    check(A, "AI providers list", bool(prov.get("providers")))
    check(A, "Select AI provider", s.post(f"{BASE}/api/student/ai_providers/select",
                                          json={"provider_key": "gemini"}).status_code == 200)
    pi = js(s.get(f"{BASE}/api/student/privacy_info"))
    check(A, "Privacy info (no DP claim)", "Guaranteed" not in json.dumps(pi) and bool(pi.get("guarantees")))
    fs = js(s.get(f"{BASE}/api/student/federated_status"))
    check(A, "Student FL status", s.get(f"{BASE}/api/student/federated_status").status_code == 200, json.dumps(fs)[:100])

    # ── Admin ────────────────────────────────────────────────────────────
    A = "Admin"
    if admin_ok:
        st = js(adm.get(f"{BASE}/api/admin/stats"))
        check(A, "Stats", "total_students" in st)
        check(A, "Students list", adm.get(f"{BASE}/api/admin/students").status_code == 200)
        ov = js(adm.get(f"{BASE}/api/admin/jobs/overview"))
        check(A, "Jobs overview", "schedule" in ov and "providers" in ov,
              f"jobs={ov.get('totals', {}).get('jobs_total')} next={ov.get('schedule', {}).get('next_scheduled_sync')}")
        check(A, "Sync runs", adm.get(f"{BASE}/api/admin/jobs/runs").status_code == 200)
        r, t = timed(adm.post, f"{BASE}/api/admin/jobs/sync", timeout=300)
        run = js(r).get("run", {})
        check(A, "Manual sync", r.status_code in (200, 409) and run.get("status") in ("success", "partial", "skipped"),
              f"{t}s status={run.get('status')} new={run.get('inserted_count')} upd={run.get('updated_count')}")
        logs = js(adm.get(f"{BASE}/api/admin/audit_logs")).get("logs", [])
        check(A, "Audit log records manual sync", any(l["action"] == "jobs.manual_sync" for l in logs))
        h = js(adm.get(f"{BASE}/api/admin/system/health"))
        check(A, "System health", "ai_services" in h and "models" in h)
        check(A, "FL nodes are simulated", all("Simulated" in n["name"] for n in js(adm.get(f"{BASE}/api/admin/federated/nodes"))["nodes"]))
        r = adm.post(f"{BASE}/api/admin/federated/train")
        fl = js(r).get("data", {})
        check(A, "FL round (measured, no epsilon)", r.status_code == 200 and fl.get("privacy_guarantee") is None,
              f"acc={fl.get('global_accuracy')}")
        rounds = js(adm.get(f"{BASE}/api/admin/federated/rounds"))["rounds"]
        check(A, "FL rounds history", bool(rounds))
        check(A, "FL round detail", adm.get(f"{BASE}/api/admin/federated/round/{rounds[-1]['round_number']}").status_code == 200)
        check(A, "FL status", adm.get(f"{BASE}/api/admin/federated/status").status_code == 200)

    # ── Account export / delete (cleanup) ────────────────────────────────
    A = "Account"
    ex = js(s.get(f"{BASE}/api/student/account/export"))
    check(A, "Export my data", ex.get("profile", {}).get("email") == email_a and len(ex.get("skills", [])) == len(EXPECTED_SKILLS))
    check(A, "Delete needs confirmation", s.delete(f"{BASE}/api/student/account/delete", json={}).status_code == 400)
    for sess_, em in ((s, email_a), (s2, email_b)):
        r = sess_.delete(f"{BASE}/api/student/account/delete", json={"confirmation": "DELETE_MY_ACCOUNT"})
        check(A, f"Delete account {em[:14]}", r.status_code == 200)
    check(A, "Deleted account cannot log in", requests.post(f"{BASE}/api/auth/login", json={
        "email": email_a, "password": "e2e-password-123"}).status_code == 401)
    s.post(f"{BASE}/api/auth/logout")

    # ── summary ──────────────────────────────────────────────────────────
    n = {k: sum(1 for r in RESULTS if r[2] == k) for k in ("PASS", "WARN", "FAIL")}
    print(f"\nSUMMARY: {n['PASS']} passed, {n['WARN']} warnings, {n['FAIL']} failed (of {len(RESULTS)})")
    json.dump(RESULTS, open(os.path.join(OUT, "e2e_results.json"), "w"), indent=1)
    print(f"Detailed results: {os.path.join(OUT, 'e2e_results.json')}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        n = {k: sum(1 for r in RESULTS if r[2] == k) for k in ("PASS", "WARN", "FAIL")}
        print(f"\nABORTED after {len(RESULTS)} checks: {n}")
        sys.exit(1)
