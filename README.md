# 🎓 SkillBridge: A Privacy-Preserving Federated Intelligence and Adaptive Verification Framework for Career Gap Remediation

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue.svg?logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![Flask](https://img.shields.io/badge/Flask-3.1-black.svg?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Gemini](https://img.shields.io/badge/LLM-Google%20Gemini%20Flash-orange.svg?logo=google&logoColor=white)](https://ai.google.dev/)
[![Federated Learning](https://img.shields.io/badge/Federated%20Learning-Flower%20%7C%20FedAvg%20(simulation)-green.svg)](https://flower.ai/)
[![CI](https://github.com/AYSHA-GITT/skillbridge/actions/workflows/ci.yml/badge.svg)](https://github.com/AYSHA-GITT/skillbridge/actions/workflows/ci.yml)
[![Backend tests](https://img.shields.io/badge/Backend%20tests-239%20passing%20(SQLite%20%2B%20PostgreSQL)-brightgreen.svg)](#9-experimental-validation--results)
[![Frontend tests](https://img.shields.io/badge/Frontend%20tests-42%20passing-brightgreen.svg)](#9-experimental-validation--results)
[![E2E](https://img.shields.io/badge/Live%20E2E%20checks-204%20pass%20%2F%200%20fail-brightgreen.svg)](#9-experimental-validation--results)

> **SkillBridge turns what a student *claims* on a resume into what they can *show*.** Resume skills stay unverified until the student passes an assessment or a reviewer accepts their evidence. The result is a shareable **Verified Skill Passport**. Students use it to find skill gaps, plan learning, match against live Indian job listings, and apply to verified employers, who see only the parts of the profile the student chose to share.

---

## 📄 Abstract

Campus recruitment and early-career hiring have three structural problems. **(1) Unverified self-reporting:** resumes list skills that keyword-based Applicant Tracking Systems (ATS) accept at face value. **(2) Fragmented preparation:** skill assessment, learning plans, job search and salary information sit in separate tools with no feedback loop between them. **(3) Privacy and consent:** candidate data is usually exposed to employers wholesale, and institutions cannot pool placement data under regulations such as GDPR and FERPA.

**SkillBridge** is a full-stack platform (React 19 + Flask, 36 relational tables, 155+ REST routes) that addresses these problems with one shared definition of *verified*. A section-aware, taxonomy-based resume parser extracts skills with evidence strength (*applied*, *supporting*, *listed only*). Skills become **verified** only through a difficulty-mixed assessment (pass mark 70%, drawn from 233 hand-reviewed questions plus validated LLM-generated ones) or reviewer-accepted evidence. The same six-level status model drives career readiness, skill-gap analysis, explainable job matching, badges, the Skill Passport and the employer-side compatibility report, so students and employers see identical per-skill credit.

The platform also includes:
- a **live job discovery pipeline** that refreshes Indian listings from public company career boards (Greenhouse, Lever), Adzuna, Jooble and Arbeitnow every two hours, under a database lease, with evidence-based expiry;
- a **Recruiter Portal** with admin-verified organisations, consent-scoped candidate profiles, opaque candidate references, a hiring pipeline, access logs that students can see, and **skill verification requests** that the student accepts or declines;
- **connected next steps**: every analysis page links to the action it implies (take the quiz, add evidence, add a missing skill to the roadmap, open matching jobs);
- a **retrieval-augmented career assistant** whose retriever was chosen by measurement (MiniLM Recall@1 = 0.852 vs 0.519 for the previous hashed engine on a 27-query test set);
- an **illustrative salary estimator** (Ridge regression, evaluated against a mean baseline; see the known issue in Section 19);
- a **federated-learning simulation** (FedAvg over four synthetic partitions with update clipping and Gaussian noise; no formal differential-privacy guarantee is claimed).

The system is checked by 239 isolated backend tests (run on both SQLite and PostgreSQL 17 in GitHub Actions CI), 42 frontend tests and a 204-check live end-to-end script. Password reset uses hashed, single-use, rate-limited tokens.

> **Keywords:** Skill Verification, Skill Passport, Explainable Job Matching, Consent-Based Data Sharing, Applicant Tracking Systems, Retrieval-Augmented Generation (RAG), Adaptive Assessment, Federated Learning, Career Informatics, Responsible AI.

---

## 📌 Table of Contents

1. [Problem Statement & Motivation](#1-problem-statement--motivation)
2. [Objectives](#2-objectives)
3. [Contributions](#3-contributions)
4. [How SkillBridge Differs from Existing Platforms](#4-how-skillbridge-differs-from-existing-platforms)
5. [Features by User Role](#5-features-by-user-role)
6. [System Architecture & Workflow](#6-system-architecture--workflow)
7. [Methodology & Mathematical Formulation](#7-methodology--mathematical-formulation)
8. [Data Model](#8-data-model)
9. [Experimental Validation & Results](#9-experimental-validation--results)
10. [Development Timeline & Change History](#10-development-timeline--change-history)
11. [Corrections Made for Scientific Integrity](#11-corrections-made-for-scientific-integrity)
12. [Technology Stack](#12-technology-stack)
13. [Project Structure](#13-project-structure)
14. [Installation & Reproducibility](#14-installation--reproducibility)
15. [Environment Configuration](#15-environment-configuration)
16. [Live Job Discovery & Two-Hour Synchronization](#16-live-job-discovery--two-hour-synchronization)
17. [REST API Reference](#17-rest-api-reference)
18. [Privacy, Security & Ethics](#18-privacy-security--ethics)
19. [Limitations & Threats to Validity](#19-limitations--threats-to-validity)
20. [Future Scope](#20-future-scope)
21. [Citation](#21-citation)
22. [Acknowledgments](#22-acknowledgments)

---

## 1. Problem Statement & Motivation

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                        EARLY-CAREER HIRING BOTTLENECKS                         │
├──────────────────────────┬──────────────────────────┬──────────────────────────┤
│ Unverified claims        │ Fragmented preparation   │ Privacy & consent        │
│ ───────────────────      │ ──────────────────────   │ ─────────────────        │
│ Resumes list skills that │ Resumes, quizzes, course │ Employers usually get    │
│ keyword ATS accept as-is;│ plans, job boards and    │ the whole profile; the   │
│ a "Python" claim and a   │ salary data live in      │ student cannot see or    │
│ Python skill look alike. │ separate tools.          │ limit who looked at it.  │
└──────────────────────────┴──────────────────────────┴──────────────────────────┘
```

Let a student's self-reported skill set be $\mathcal{P}_s = \{s_1, \dots, s_n\}$ and a role's requirements $\mathcal{T}_C = \{k_1, \dots, k_m\}$. A keyword ATS scores suitability by set overlap:

$$\text{Suitability}_{\text{naive}} = \frac{|\mathcal{P}_s \cap \mathcal{T}_C|}{|\mathcal{T}_C|}$$

This score treats every claim as equally true, so it rewards keyword stuffing and tells neither the student nor the employer which skills have been demonstrated. SkillBridge replaces the binary "skill present" with a **graded, evidence-backed credit** $c(s) \in [0,1]$ (Section 7.5). Every number it shows comes with the reasons behind it.

---

## 2. Objectives

1. Extract skills from resumes accurately, with the evidence and the section each one came from.
2. Separate *claimed* from *demonstrated* skills using assessments and reviewed evidence, under **one** rule used everywhere in the system.
3. Turn skill gaps against a target career into an ordered, day-by-day learning plan.
4. Match students to **real, current** job listings with an explainable score, without inventing data.
5. Let students share a verified profile with employers **on their own terms** (sections, expiry, revocation, visible access log).
6. Give administrators oversight: job-sync health, organisation verification, evidence review and audit logs.
7. Report every metric honestly, with the method used to produce it and its limitations.

---

## 3. Contributions

1. **Unified verification model.** A six-level skill status (*self-declared → AI-extracted → evidence submitted → pending verification → assessment completed → verified*) is computed in one function (`utils/skill_passport.py: skill_verification_states`). Matching, readiness, careers, badges, the passport and the recruiter report all use it. Before this was unified, "verified" had four different meanings in the codebase; a failed quiz could count as a verified skill.
2. **Evidence-aware resume parsing.** A shared skill taxonomy (~120 canonical skills with aliases) matches on token boundaries and handles ambiguous names (C, R, Go, "excel" used as a verb). Each skill gets an extraction confidence, an evidence strength and evidence snippets.
3. **Integrity-hardened assessments.** Quiz length depends on evidence strength. Questions are mixed across Easy/Medium/Hard, options are shuffled per student, every answer must belong to the skill, at least 5 questions are required, unvalidated fallback questions are never stored, and the 233-question curated bank keeps verification working without any LLM.
4. **Verified Skill Passport.** A consent-based portable profile with share links (SHA-256-hashed tokens, per-section visibility, expiry, revocation, access history), a QR code and a PDF export. The public view never includes email, phone, resume text, files or internal IDs.
5. **Consent-based Recruiter Portal.** Organisations are verified by an admin before they can post jobs or search candidates. Candidates are addressed by opaque references, employers see only shared passport sections, students see every employer access, and search is opt-in. The compatibility report uses the same credit function as the student-side matcher, and a student can preview the exact employer view before applying. Recruiters can ask a candidate to verify a shared skill; the request completes only after the student accepts **and** the skill becomes verified under the single rule.
6. **Explainable job matching on live data.** A multiplicative score (skill × experience × location fit) with per-skill reasons. A posting with no recognisable skills gets *no* score instead of an invented one.
7. **Reliable two-hour job synchronization.** A DB-persisted schedule, a lease against overlapping runs, per-provider budgets and retries, scheduler heartbeats, de-duplication and evidence-based expiry. Listings are archived, never deleted.
8. **Secure account recovery.** Password-reset tokens are 256-bit, stored only as SHA-256 hashes, single-use, expire after 60 minutes, travel in the URL fragment (never in server logs) and are rate-limited; a reset signs out every other session.
9. **Measured component choices.** The RAG retriever and the salary model were chosen by reproducible comparisons against baselines (Section 9.3). Earlier unsupported figures were withdrawn (Section 11).

---

## 4. How SkillBridge Differs from Existing Platforms

| Aspect | Typical platforms (job boards, ATS, MOOCs) | SkillBridge |
| :--- | :--- | :--- |
| **Skill validation** | Self-reported keywords or course-completion certificates | Six-level status; only a passed assessment (≥ 70%) or reviewer-accepted evidence counts as *verified* |
| **Match explanation** | Opaque "% match" | Per-skill credit, matched / missing required skills, experience and location notes, limitations |
| **Candidate data sharing** | Whole profile visible to any recruiter | Student chooses sections and skill filter; links expire and can be revoked; access log visible to the student |
| **Employer trust** | Anyone can post jobs | Organisations verified by an admin before posting or searching |
| **Job data** | Mixed with sponsored or demo listings | Real providers only, freshness labels, provenance, honest salary labels |
| **Learning plan** | Generic course lists | Day-by-day roadmap ordered by required gaps, with time estimates and resources |
| **Salary information** | Unlabelled estimates | Labelled *illustrative estimate* with a disclaimer and an extrapolation flag |

---

## 5. Features by User Role

### 👩‍🎓 Students
- **Resume upload & parsing** (PDF/DOCX): section detection, taxonomy-based skill extraction with evidence snippets.
- **Skill verification quizzes**: adaptive length, mixed difficulty, per-student option shuffling, answer review and short AI explanations after submission.
- **Verified Skill Profile & Skill Passport**: overview, skills & verification status, projects/certificates/experience/practical challenges as evidence (one-click import from the parsed resume), share links, QR code, PDF.
- **Career analysis**: target career, skill-gap analysis, career readiness breakdown, AI career recommendations, side-by-side career comparison, path simulation.
- **Learning roadmap & study plan**: day-by-day schedule for missing skills, progress checkpoints, and **Add to Roadmap** for a single missing skill from a job match (no regeneration; duplicates and already-verified skills are reported, not added; labelled *From job: X* or *Added by you* and kept across re-analysis).
- **Next steps everywhere**: Readiness, Assessment, Skill-gap and Roadmap pages link to the quiz, evidence form or matching jobs for each skill; career recommendations link to `/jobs?domain=…`, and the Jobs page accepts `?q=`, `?domain=` and `?skill=` deep links.
- **Live jobs & internships**: filters, sorting, saved jobs, applications with status tracking, job preferences, in-app alerts, explainable match with the Skill Passport status of each skill and a Verify / Retake-quiz link.
- **Apply to employers on SkillBridge**: explicit sharing consent and a **"How this employer will see you"** preview of the exact compatibility report.
- **Employer Access page**: which organisations viewed the profile and when, opt-in discovery settings, application stage updates, and **verification requests** from employers to accept or decline (sidebar badge for unread updates).
- **ATS Resume Studio**: deterministic ATS score, STAR/XYZ bullet rewriting without invented metrics, live editing, PDF/DOCX export.
- **Mock interview simulator** (5 categories, voice input), **salary boost simulator**, **badges**, **progress timeline**, **RAG career assistant**.
- **Account**: profile and photo, password change, secure email-based password reset with clear messages for expired or used links, data export, permanent deletion (including resume and evidence files).

### 🏢 Recruiters
- Registration with an organisation, then **admin verification** (website and email-domain signal) before publishing jobs or searching candidates.
- Job posts (draft / publish / close) shown to students with match scores.
- Applicants and best-match lists per job, each with a **compatibility report** built only from shared data.
- Opt-in candidate search with filters, candidate profiles by opaque reference, internal notes, shortlists and invitations.
- **Hiring pipeline**: *new → under review → shortlisted → assessment → interview → selected / not selected / on hold*; every stage change notifies the student.
- **Skill verification requests**: from a candidate profile, ask the candidate to verify shared but unverified skills; track answers on the *Verification Requests* page. Hidden skills look the same as skills the candidate does not have, failed attempts are never reported, a decline starts a 30-day cooldown, and open requests close when the student stops sharing.

### 🛡️ Administrators
- Platform statistics and student roster.
- **Job Synchronization** dashboard: provider health, schedule, scheduler liveness, run history, manual sync.
- **Organisation review** and **evidence review** queues.
- Federated-learning centre (simulation): nodes, rounds, trigger a round.
- Audit log and system health.

---

## 6. System Architecture & Workflow

```mermaid
flowchart TD
    subgraph Client["Presentation layer: React 19 + Tailwind CSS"]
        SUI["Student app: dashboard, quizzes, passport, jobs, roadmap, ATS studio, next steps"]
        RUI["Recruiter portal: jobs, candidates, pipeline, shortlists, verification requests"]
        AUI["Admin console: job sync, org and evidence review, FL centre"]
        PUB["Public passport page"]
    end

    subgraph API["Application layer: Flask blueprints"]
        AUTH["/api/auth: sessions, RBAC, rate limits"]
        STU["/api/student"]
        PAS["/api/passport"]
        REC["/api/recruiter and /api/candidate"]
        ADM["/api/admin"]
    end

    subgraph Core["Domain services"]
        PARSE["Resume parser + skill taxonomy"]
        VER["Skill verification states: single rule"]
        MATCH["Job matcher + compatibility report"]
        READY["Readiness, skill gap, roadmap"]
        RAG["RAG assistant: MiniLM retrieval"]
        SAL["Salary estimate: Ridge"]
        FL["FedAvg simulation: Flower"]
        LLM["LLM providers: Gemini, with fallbacks"]
    end

    subgraph Jobs["Job discovery"]
        PROV["Greenhouse, Lever, Adzuna, Jooble, Arbeitnow"]
        SYNC["Sync service: lease, normalize, dedup, expiry"]
        SCHED["Scheduler: worker, thread or cron"]
    end

    DB[("SQLite or PostgreSQL: 36 tables")]
    FILES[("Resume and evidence files")]

    SUI --> AUTH
    SUI --> STU
    SUI --> PAS
    RUI --> REC
    AUI --> ADM
    PUB --> PAS
    STU --> PARSE
    STU --> READY
    STU --> MATCH
    STU --> RAG
    STU --> SAL
    PAS --> VER
    REC --> MATCH
    MATCH --> VER
    READY --> VER
    STU --> LLM
    ADM --> FL
    ADM --> SYNC
    SCHED --> SYNC
    SYNC --> PROV
    SYNC --> DB
    VER --> DB
    PARSE --> FILES
    PAS --> FILES
```

### End-to-end student workflow

```
Upload resume ─► Parse sections ─► Extract skills (AI-extracted, with evidence strength)
      │
      ▼
Take quiz / attach evidence ─► Status: assessment completed │ pending review │ VERIFIED
      │
      ├─► Readiness score, skill gap ─► Day-by-day roadmap ─► retake quiz ─┐
      │                                                                  │
      ├─► Live job search ─► explainable match ─► save / apply           │
      │                                                                  │
      └─► Skill Passport ─► share link / PDF / apply to verified employer│
                               │                                         │
                               ▼                                         │
               Employer sees only the shared sections ─► pipeline stages ◄┘
                               │
                               ▼
                 Student sees the access log and stage updates
```

---

## 7. Methodology & Mathematical Formulation

### 7.1 Resume parsing & evidence-based skill extraction

Resumes (PDF via pdfplumber/PyMuPDF, DOCX via python-docx) are split into canonical sections (skills, experience, projects, education, certifications, achievements, summary) using a header vocabulary that recognises common variants ("Technical Skills", "Academic Projects", "Internships", …).

Skills are matched against a **shared skill taxonomy** (`backend/utils/skill_taxonomy.py`, ~120 canonical skills with aliases) on token boundaries, never raw substrings. Ambiguous names (C, R, Go) are accepted only in explicit forms ("C programming", "Golang") or as standalone list items. "Excel at …" is not read as the Excel skill. Job descriptions use the same taxonomy, so resume skills and job requirements are compared under identical names.

| Quantity | Meaning | Source |
|---|---|---|
| `extraction_confidence` | How certain we are the text refers to the skill (1.0 unambiguous, 0.7 list-context names). Rule-based, **not a probability**. | taxonomy match |
| `evidence_strength` | `applied` (used in experience/projects), `supporting` (certifications/education/summary), `listed_only` (skills list only) | section analysis |
| verification status | Six-level status (7.3) | assessments + reviewed evidence |

### 7.2 Skill assessment

Quiz length depends on evidence strength (applied: 5, supporting: 6, listed only: 8 questions). Questions are drawn round-robin across Easy/Medium/Hard from the question bank: 233 hand-reviewed questions for 42 skills (`data/curated_questions.py`), plus LLM-generated questions that pass validation before they are stored. Options are shuffled per student. A submission must answer every question, and every question must belong to that skill.

$$\mathcal{V}(s) = 0.25 \cdot E(s) + 0.75 \cdot Q(s), \qquad E(s) \in \{1.0,\ 0.7,\ 0.4\}$$

where $Q(s)$ is the fraction of correct answers. After submission the student sees which answers were wrong, the correct options and a short (≤ 60-word) explanation.

### 7.3 Unified verification states

For each skill $s$, with $a_s$ its **latest** assessment score and $\mathcal{E}_s$ its linked evidence:

| Status | Condition (strongest first) |
|---|---|
| `verified` | $a_s \ge 70\%$ **or** an evidence item for $s$ accepted by an administrator |
| `assessment_completed` | assessment taken, $a_s < 70\%$ |
| `pending_verification` | evidence submitted for review |
| `evidence_submitted` | project / certificate / experience / practical challenge linked, not yet submitted |
| `ai_extracted` | found in the resume only |
| `self_declared` | added by the student only |

A resume mention or an uploaded certificate **never** verifies a skill on its own, and editing reviewed evidence resets its review. $\text{Verified}(u) = \{ s : \text{status}(s) = \texttt{verified} \}$ is the only set used for readiness, skill gap, career recommendations, comparisons, RAG answers and badges.

### 7.4 Career readiness

$$\mathcal{R} = 100 \cdot \left( 0.50 \cdot C_{\text{req}} + 0.30 \cdot \bar{S}_{\text{quiz}} + 0.20 \cdot C_{\text{nth}} \right)$$

$C_{\text{req}}$ and $C_{\text{nth}}$ are the shares of required and nice-to-have skills for the target career that are in $\text{Verified}(u)$, and $\bar{S}_{\text{quiz}}$ is the mean quiz score. Career requirements were reviewed against ~480 current Indian tech postings. Per-skill demand weights are recomputed from current postings after each sync, with equal weights when there are fewer than 20 postings. The 0.50/0.30/0.20 weights are design choices, not fitted parameters.

### 7.5 Per-skill credit (shared by students and employers)

| Status / evidence | Credit $c(s)$ |
|---|---|
| Verified | 1.00 |
| Assessment below pass mark: score 40–69% / < 40% | 0.60 / 0.20 |
| Pending review | 0.60 |
| Evidence submitted | 0.55 (never below its resume credit) |
| Resume only: applied / supporting / listed only | 0.70 / 0.55 / 0.40 |
| Self-declared | 0.30 |
| Missing but transferable (required skills only, student-side matcher) | 0.25 |
| Missing / not shared | 0 |

`utils/job_matcher.skill_credit` implements this table. The recruiter compatibility report imports the same function, so a student and an employer always see the same credit for the same skill.

### 7.6 Explainable job matching (student side)

$$\text{Score} = 100 \times \text{SkillFit} \times \text{ExperienceFit} \times \text{LocationFit}$$

$$\text{SkillFit} = \frac{3\sum_{s \in \text{req}} c(s) + \sum_{s \in \text{pref}} c(s)}{3|\text{req}| + |\text{pref}|}$$

Experience fit is 1.0 / 0.8 / 0.55 depending on the gap to the posting's minimum years. Location fit is 1.0 / 0.9 (open to relocation) / 0.75 against saved preferences. A matching job title adds nothing and there are no free points. A posting with no recognisable skills gets **no score** ("insufficient data"). Every score lists matched and missing required skills, each skill's passport status with a Verify / Retake-quiz link, and experience and location notes.

### 7.7 Employer compatibility report (recruiter side)

The report is computed **only from the consent-scoped passport** the student shared:

$$\text{Fit} = 100 \cdot \frac{3\sum_{\text{req}} c(s) + \sum_{\text{pref}} c(s)}{3|\text{req}| + |\text{pref}|}$$

Labels: *Strong* ≥ 70, *Moderate* ≥ 45, *Developing* ≥ 25, otherwise *Low*. If the skills section is not shared, or the job lists no recognisable skills, no score is produced. Experience and education are **listed for the recruiter's judgement, not scored**. Name, college, location, gender and age are never part of the score. The report also lists relevant projects and assessments, skills that need verification, and explicit limitations. Students can generate the identical report read-only before applying (`POST /api/student/jobs/<id>/employer_preview`).

### 7.8 Secure sharing

- Share tokens are random and stored only as **SHA-256 hashes**. Links carry section visibility, a skill filter (all / with evidence / verified only), an expiry and a revocation flag.
- Each public view is logged with a hashed viewer fingerprint. The owner sees the access history.
- Evidence uploads are restricted to PDF/PNG/JPEG and checked by file signature (magic bytes), not only by extension.
- Public passport endpoints are rate-limited (60 views/min, 20 PDFs/min per client).

### 7.9 Retrieval-augmented career assistant

An in-memory store with **strict tenant isolation**: a private chunk is searchable only by its owner. Retrieval uses pretrained `all-MiniLM-L6-v2` sentence embeddings and falls back to a hashed word/trigram projection when the model is unavailable. A similarity threshold (0.20) plus a relative cutoff (best − 0.15) means off-topic questions retrieve nothing, and the LLM is told when the evidence is insufficient. The retriever was selected by the evaluation in Section 9.3.

### 7.10 Salary estimate

Ridge regression ($\alpha = 1$) over experience, skill count and four domain indicators, trained on `data/salary_data.csv`: **24 rows of undocumented origin that appear hand-constructed**. Outputs are labelled *illustrative estimates* (INR per year) with a disclaimer and an extrapolation flag. Salaries on job cards come from providers and are labelled *Advertised by employer* or *Estimated by provider*.

### 7.11 Federated learning (simulation)

Four partitions of **synthetic** data (uniform random features, heuristic label); no real institution or student data takes part. Each round, every client starts from the global model and trains locally (SGD logistic regression). The server then:

1. L2-clips each client update $\Delta_k = w^k - w$ to norm $C = 1.0$,
2. averages the clipped updates, weighted by sample counts,
3. adds Gaussian noise $\mathcal{N}(0, (z \cdot C / K)^2)$ with noise multiplier $z = 0.5$,
4. evaluates the new global model on a fixed held-out synthetic test set (400 samples).

**No privacy accountant is implemented, so no $(\epsilon, \delta)$ guarantee is claimed.**

---

## 8. Data Model

36 SQLAlchemy models (SQLite in development, PostgreSQL in production), managed by idempotent Alembic migrations (`backend/migrations/versions`, 9 revisions; head `a3d8f1c6e2b7`). The full test suite and the migrations run on both databases in CI.

| Domain | Tables |
|---|---|
| Identity & accounts | `Student` (role: student / recruiter / admin), `PasswordResetToken`, `AuditLog` |
| Resume & skills | `Resume`, `Skill` (source, evidence strength), `SkillVerification`, `QuestionBank` |
| Career & learning | `SkillGap`, `StudyPlan`, `RoadmapTemplate`, `Progress` |
| Skill Passport | `PassportProfile`, `PassportEvidence`, `PassportShare`, `PassportAccessLog` |
| Jobs | `JobListing`, `SavedJob`, `JobApplication`, `JobPreference`, `JobAlert`, `JobAlertMatch`, `JobSyncRun`, `SchedulerLease` |
| Recruiting | `Organisation`, `RecruiterProfile`, `CandidateDiscoverySetting`, `RecruiterAccessLog`, `ApplicationEvent`, `RecruitmentNote`, `CandidateShortlist`, `ShortlistEntry`, `JobInvitation`, `SkillVerificationRequest` |
| Interview | `InterviewSession`, `InterviewQA` |
| Federated learning | `FLTrainingRound` |

---

## 9. Experimental Validation & Results

### 9.1 Automated test suites

| Suite | Command | Scope | Result (2026-11-20) |
|---|---|---|---|
| Isolated backend unit/integration tests | `python -m unittest discover -s tests` | Temporary DB, fake job providers, no network: accuracy & integrity, job system, question bank, Skill Passport, Recruiter Portal, verification consistency and requests, roadmap navigation, password-reset security, SQLite locking, PostgreSQL compatibility | **239 passing on SQLite (foreign keys enforced) and on PostgreSQL 17** |
| Frontend unit tests | `npm test` | Routing and route guards, password-reset page and token handling, next steps / Add to Roadmap / verification-request UI, API error messages (5 suites) | **42 passing** |
| Production build | `npm ci && npm run build` | Clean install from the lock file | passes |
| Migrations | `flask db upgrade` twice on an empty PostgreSQL DB + `flask db check` | Idempotency; models match the schema | clean |
| Live end-to-end check | `python e2e_check.py` (servers running) | Every feature through the real HTTP API; creates and deletes throw-away accounts | **204 pass, 2 warnings (no Adzuna/Jooble keys), 0 fail** |
| Password-reset end-to-end | scripted, real SMTP | Request, email, verify, reset, reuse, expiry, session sign-out | 19/19 |
| Headless-browser walkthrough | Chrome, scripted | Student and recruiter flows through the real UI, including an application, the employer preview, a verification request and Add to Roadmap | 72/75 (the 3 flags were checker artefacts) |

Growth of the isolated suite across the project: 77 → 87 → 93 → 110 → 162 → 170 → 173 → 182 → 211 → 229 → 239 tests.

**Continuous integration** (`.github/workflows/ci.yml`, on every push and pull request to `main`): the backend suite on SQLite and on a PostgreSQL 17 service container, a clean install of the pinned `requirements.txt`, migrations on an empty PostgreSQL database, and the frontend `npm ci`, tests and production build. No secrets are used and nothing is deployed; Gemini is pointed at an unreachable address so tests never call it.

Key regression tests include: a failed quiz is never counted as verified anywhere; recruiters cannot read unshared sections or candidates who withdrew or opted out; a verification request never completes before the student accepts or on a failed attempt; reset tokens cannot be reused, raced or read back from the API; job alerts and preferences cannot be read across accounts; account deletion works under PostgreSQL's foreign keys; a registration waits out a 6.5 s SQLite writer instead of failing; migrations run on databases created by `db.create_all()`.

### 9.2 Earlier functional harness

An earlier harness (`backend/test_complete_feature_suite.py`) covered 34 subsystems (auth, RBAC, resume ingest, extraction, quizzes, gap analysis, roadmap, salary, readiness, badges, career recommender, RAG, privacy endpoint, FL nodes/rounds) and passed 34/34. It runs against the configured development database, so the isolated suite above is now the primary evidence.

### 9.3 Measured component evaluations (reproducible)

**Retrieval** (`python -m rag.eval_retrieval`; 27 hand-written queries over 9 career documents, 9 keyword + 18 paraphrased):

| Method | Recall@1 | Recall@3 | MRR | Paraphrase Recall@1 |
|---|---|---|---|---|
| Hashed word/trigram (previous engine) | 0.519 | 0.704 | 0.655 | 0.333 |
| Hashed bag-of-words fallback | 0.444 | 0.741 | 0.628 | 0.278 |
| BM25 | 0.556 | 0.889 | 0.742 | 0.444 |
| **MiniLM sentence embeddings (deployed)** | **0.852** | **1.000** | **0.926** | **0.778** |
| MiniLM + BM25 (RRF) | 0.852 | 1.000 | 0.926 | 0.778 |

**Salary model** (`SalaryPredictor().evaluation()`; RepeatedKFold 5×10, seed 42, 24 rows):

| Model | MAE (LPA) | RMSE | R² |
|---|---|---|---|
| Predict-the-mean baseline | 3.421 | 3.990 | −1.203 |
| Linear regression | 0.939 | 1.134 | 0.856 |
| **Ridge α=1 (deployed)** | **0.887** | **1.066** | **0.873** |
| Ridge α=10 | 0.894 | 1.102 | 0.864 |
| Random forest | 1.034 | 1.318 | 0.802 |

These figures describe fit to an illustrative 24-row table only, not accuracy on real salaries.

**Job data** (verified 2026-11-13): without any API keys, the company career boards provide about 500 Indian tech/data roles across 25 companies, mostly in Bengaluru, Gurugram, Hyderabad and Pune. Career requirements were checked against ~480 of these postings.

**Federated simulation:** accuracy is measured on held-out synthetic data each round and stored as-is.

### 9.4 Free-tier hosting measurements (Phase 0)

To decide whether SkillBridge can run on a free 512 MB web service (target: Netlify frontend + Render backend + Neon PostgreSQL), memory was measured on Linux under a 512 MB / 0.1 CPU limit in GitHub Actions. The harness and results are on the `phase0/memory-check` branch (`perf/phase0/results/SUMMARY.md`); `main` is not changed by it.

| Configuration | Result under 512 MB |
|---|---|
| Current app (PyTorch MiniLM, google-genai SDK, in-process sync) | Out-of-memory killed |
| ONNX MiniLM, untuned (batch 256, KB index rebuilt per worker) | Out-of-memory killed |
| **ONNX MiniLM via fastembed (batch 8, arena off), KB index prebuilt at build, REST Gemini client, `MALLOC_ARENA_MAX=2`, gunicorn 1 worker × 4 threads, job sync in a separate process** | **Peak 429 MB, 0 OOM, 1975/1975 load requests, 201 e2e checks pass, RAG p50 ≈ 1 s** |

The ONNX retriever returns the same results as PyTorch (27/27 queries, cosine 1.0), so semantic retrieval can be kept on the free tier.

---

## 10. Development Timeline & Change History

| Phase | Dates | Main changes |
|---|---|---|
| **1. Foundation** | Jul 16 – Sep 2, 2026 | Project setup; end-to-end skill-gap platform: resume upload & parsing, skill extraction, Gemini-generated quizzes, skill gap, readiness, roadmap, salary model, federated-learning module, full React UI; Gemini quota fallback and rate-limit handling; Data Analyst career added |
| **2. Intelligence & UX** | Oct 6–7 | AI career recommendations and explainable comparison; 4-tier verified skill profile; federated-learning centre; floating AI assistant; progressive-disclosure UI; institutional admin portal, RBAC, route guards, privacy information |
| **3. Platform extensions** | Oct 19 | Job discovery with India/Asia prioritisation and regional filters; explainable matching; RAG pipeline and knowledge base; multiple AI providers; mock interview simulator with voice input (STT de-duplication fix); data export/delete; job application flow and tracking; **AI Resume Optimizer / ATS Studio** with STAR rewriting, live score and PDF/DOCX export; system audit suites |
| **4. Documentation & dependencies** | Nov 12 | Research-style README; `requirements.txt` cleaned and pinned to the working venv |
| **5. Live jobs & integrity** | Nov 13 | Adzuna, Jooble, Arbeitnow adapters; two-hour DB-persisted sync with lease, de-duplication and expiry; job worker and CLI; alerts and preferences; shared skill taxonomy (fixes false java/c/r skills); quiz integrity rules; registration can no longer self-assign admin; measured FL accuracy, no fabricated ε; salary model evaluation; MiniLM retrieval; **free Indian jobs via Greenhouse/Lever company boards**; career data aligned with ~480 real postings; scheduler heartbeats; **233 curated quiz questions**; resume file cleanup on account deletion; profile settings, password change/reset, profile photo, post-quiz explanations |
| **6. Verified Skill Passport** | Nov 15 | Passport (overview, skills & verification, projects & evidence, share & export); six skill statuses; resume import of evidence; share links with consent, visibility, expiry, revocation, access history, QR code and PDF; admin evidence review |
| **7. Recruiter Portal** | Nov 17 | Organisations and recruiter accounts with admin verification; employer job posts; consent-based applications; candidate profiles by opaque reference; compatibility reports; shortlists, pipeline stages, notes, invitations; access logs visible to students; opt-in candidate search; rate limiting |
| **8. Consistency & reliability** | Nov 17 | **One definition of "verified"** across matching, careers, skill gap, readiness, RAG and badges; clear error messages for failed registration/login (server unreachable, timeout, rate limit); SQLite "database is locked" fix (30 s busy timeout, sync commits every 50 jobs); **"How this employer will see you" preview** and actionable next steps from skill-gap and match views |
| **9. Security & deployment prep** | Nov 19 | **Password-reset overhaul**: the old API returned the reset link in its response when email was not configured (account takeover risk); now hashed single-use tokens in the URL fragment, rate limits, identical responses for unknown emails, background email, sign-out of other sessions, `flask users test-email`. Docker deployment files (`deploy/`, Dockerfiles), `SKILLBRIDGE_ENV=production` safety checks, frontend calls `/api` on its own origin in production |
| **10. Recruiter requests & navigation** | Nov 20 | **Recruiter skill verification requests** (new table, consent-first completion); **Next Steps** on Readiness, Assessment and Roadmap; careers → matching jobs; **Add to Roadmap** from job matches; Jobs page deep links; Jest fixed for React Router 7 and the placeholder test replaced (42 frontend tests) |
| **11. Production readiness** | Nov 20 | Free-tier memory measurements (Phase 0, Section 9.4). **PostgreSQL compatibility** (Phase 1): account deletion order under PostgreSQL foreign keys, NumPy values in SQL, UTC sessions, connection pre-ping, lazy Gemini client so the app starts without a key, conflicting `SQLAlchemy` pin and out-of-sync `package-lock.json` fixed; tests on PostgreSQL; **GitHub Actions CI** |

---

## 11. Corrections Made for Scientific Integrity

Earlier versions of the project reported figures that the code did not support. They were found during review, corrected in the code, and are listed here so that any paper or report based on this project uses only valid claims.

| Earlier claim / behaviour | Problem | Correction |
|---|---|---|
| Federated accuracy rising "monotonically" from 74.2% to 92.4% | Produced by a hard-coded floor `max(0.72, acc + 0.015t)` | Accuracy is now measured on a held-out synthetic test set |
| Privacy budget ε = 0.80 → 1.00 (ε ≤ 0.95, δ = 10⁻⁵) | Computed by a fixed formula `0.75 + 0.05t`; no accountant exists | Removed; no (ε, δ) guarantee is claimed |
| FL "institutions" Alpha–Delta | Synthetic partitions, not institutions | Labelled as simulated partitions |
| Resume skills `java`, `c`, `r` on most resumes | Substring matching ("JavaScript" → java) | Token-boundary taxonomy; `flask skills reextract` cleans existing data |
| A failed quiz counted as verified in some features | Four different "verified" rules in the code | One rule (Section 7.3) used everywhere |
| Job cards with default skills, fake URLs, "posted now" dates | Normalizer filled in missing data | Nothing is invented; missing values stay empty |
| Template fallback quiz questions stored in the bank | Trivially answerable | Never stored; curated bank used instead |
| Skill demand weights from `job_skills.csv` | No documented source | File removed; weights measured from current postings |
| Salary predictions shown as market figures | 24-row illustrative training table | Labelled illustrative, with a disclaimer and an extrapolation flag |
| "Hashed 128-d embeddings" for the assistant | Measurably worse retrieval | Replaced by MiniLM after a measured comparison |
| Password reset "worked" without email | The API returned the reset link to whoever asked | Link is only emailed to the account's address; tokens hashed and single-use |
| "PostgreSQL supported" | Account deletion and readiness failed on PostgreSQL; tests ran only on SQLite | Fixed; the whole suite now runs on PostgreSQL in CI |

---

## 12. Technology Stack

| Layer | Technology | Use |
| :--- | :--- | :--- |
| Frontend | React 19, React Router 7, Tailwind CSS 3, Chart.js 4, Axios, Tabler Icons | Student, recruiter, admin and public passport UIs |
| Backend | Flask 3.1 (blueprints), Flask-Login, Flask-CORS, Werkzeug | REST API, sessions, RBAC, rate limiting |
| Persistence | SQLAlchemy 2.0, Flask-Migrate / Alembic, SQLite / PostgreSQL (psycopg2) | 36 tables, idempotent migrations |
| Document parsing | pdfplumber, PyMuPDF, python-docx | Resume text and section extraction |
| Document generation | ReportLab, python-docx | ATS resumes, Skill Passport PDF |
| Generative AI | Google GenAI SDK (Gemini Flash), optional Ollama / Grok providers | Question generation, explanations, roadmaps, interviews, assistant answers |
| Retrieval | sentence-transformers (all-MiniLM-L6-v2), optional FAISS, BM25 baseline | Tenant-isolated RAG |
| Machine learning | scikit-learn (Ridge), NumPy, pandas | Salary estimate, readiness, evaluation |
| Federated learning | Flower (`flwr`), NumPy | FedAvg simulation with clipping and noise |
| Job data | Greenhouse & Lever public APIs, Adzuna, Jooble, Arbeitnow, `requests` | Live job discovery |
| Testing & CI | unittest, Jest (react-scripts), live HTTP e2e script, headless Chrome, GitHub Actions | Verification on SQLite and PostgreSQL |
| Deployment | Docker, gunicorn, Caddy, PostgreSQL (`deploy/`) | Production packaging (not deployed yet; see Section 19) |
| Email | SMTP (e.g. Gmail app password) | Password-reset emails |

---

## 13. Project Structure

```text
skillbridge/
├── backend/
│   ├── app.py                      # Flask app, blueprint registry, in-process job scheduler
│   ├── cli.py                      # flask CLI: db, users, skills, resumes, jobs commands
│   ├── job_worker.py               # Stand-alone two-hour job sync worker
│   ├── e2e_check.py                # Live end-to-end check (204 checks)
│   ├── Dockerfile                  # Production image (gunicorn, non-root, health check)
│   ├── extensions.py / models.py   # SQLAlchemy, LoginManager, 36 models
│   ├── data/
│   │   ├── career_requirements.py  # Career skill profiles (reviewed against real postings)
│   │   ├── curated_questions.py    # 233 hand-reviewed quiz questions, 42 skills
│   │   ├── skills_list.py, salary_data.csv
│   │   └── knowledge_base/         # Career, job-description and skill docs for RAG
│   ├── federated/                  # client.py, server.py, strategy.py (FedAvg + clip + noise)
│   ├── ml/                         # readiness_model.py, salary_model.py, skill_gap_model.py
│   ├── rag/                        # embedding_engine, vector_store, rag_pipeline, eval_retrieval
│   ├── migrations/versions/        # 9 idempotent Alembic revisions
│   ├── routes/
│   │   ├── auth.py                 # Register (student/recruiter), login, profile, password reset
│   │   ├── student.py              # Resume, quizzes, careers, roadmap, jobs, interview, ATS studio
│   │   ├── passport.py             # Skill Passport, evidence, shares, public view, evidence review
│   │   ├── recruiter.py            # Recruiter portal + candidate-side (/api/candidate) endpoints
│   │   └── admin.py                # Stats, FL, job sync, audit log, health
│   ├── utils/
│   │   ├── skill_taxonomy.py       # Canonical skills, aliases, token-boundary matching
│   │   ├── skill_extractor.py, resume_parser.py, resume_files.py
│   │   ├── skill_passport.py       # Verification states (single rule), passport, PDF, QR
│   │   ├── job_matcher.py          # Explainable matching, shared skill_credit()
│   │   ├── recruiting.py           # Compatibility report, candidate search, pipeline
│   │   ├── job_discovery/          # Provider adapters, normalizer, sync service, scheduler
│   │   ├── resume_optimizer/       # ATS analyzer, STAR enhancer, exporter
│   │   ├── ai_providers.py, ai_question_generator.py, question_bank_manager.py
│   │   ├── career_recommender.py, skill_gap_analyzer.py, roadmap_generator.py
│   │   ├── interview_simulator.py, career_assistant.py, market_demand.py
│   │   ├── verification_requests.py # Recruiter verification requests: rules, completion sync
│   │   ├── password_reset.py       # Hashed single-use reset tokens, rate limits, email
│   │   └── rate_limit.py, audit.py, job_alerts.py, badge_checker.py, progress_tracker.py
│   └── tests/                      # Isolated suite (239 tests, temp DB or PostgreSQL, no network)
├── frontend/
│   └── src/
│       ├── pages/                  # 30 student/admin/public pages (incl. Forgot/Reset password)
│       ├── pages/recruiter/        # 10 recruiter pages (incl. Verification Requests)
│       ├── components/             # Layouts, route guards, MatchReport, NextSteps, review queues, charts
│       ├── services/               # api, auth, student, skill, passport, recruiter services
│       └── utils/                  # apiErrors.js (+ tests), voiceUtils.js
├── deploy/                         # docker-compose, Caddyfile, production.env.example, backup.sh, DEPLOY.md
├── .github/workflows/ci.yml        # CI: SQLite + PostgreSQL tests, migrations, frontend build
├── .env.example
└── README.md
```

---

## 14. Installation & Reproducibility

**Prerequisites:** Python 3.11 or 3.12, Node.js 18+ with npm, Git.

```bash
git clone https://github.com/AYSHA-GITT/skillbridge.git
cd skillbridge
cp backend/.env.example backend/.env      # set at least DATABASE_URL and SECRET_KEY
```

**Backend**
```powershell
python -m venv .venv
.venv\Scripts\activate                    # Windows  (source .venv/bin/activate on macOS/Linux)
cd backend
pip install -r requirements.txt
flask --app app db upgrade                # create / upgrade the schema (safe to re-run)
flask --app app skills seed-questions     # curated quiz questions (also auto-seeded on first quiz)
flask --app app users make-admin you@example.com   # optional: grant admin
python app.py                             # API on http://127.0.0.1:5000 + job scheduler thread
```

**Frontend**
```powershell
cd frontend
npm install
npm start                                 # http://localhost:3000
```

**Tests**
```powershell
cd backend
python -m unittest discover -s tests -v   # 239 isolated tests; dev data untouched
# same suite on PostgreSQL (database name must end in _test):
#   SKILLBRIDGE_TEST_DATABASE_URL=postgresql://user:pass@localhost/skillbridge_test
python e2e_check.py                       # live check; needs backend and frontend running
cd ../frontend && npm test                # frontend unit tests
python -m rag.eval_retrieval              # (from backend/) retrieval evaluation
```
The older `backend/test_*.py` and `verify_*.py` scripts use the database configured in `.env`; back it up before running them.

**Maintenance commands**
```powershell
flask --app app jobs status | sync | sync-if-due        # job sync and scheduler liveness
flask --app app skills reextract [--apply]              # remove false skills from the old matcher
flask --app app resumes prune-orphans [--apply]         # resume files no account references
flask --app app users test-email you@example.com        # check the password-reset email settings
```

---

## 15. Environment Configuration

| Variable | Purpose |
|---|---|
| `DATABASE_URL`, `SECRET_KEY` | Required. SQLite path or PostgreSQL URL; session secret |
| `FRONTEND_ORIGINS` | Allowed CORS origins |
| `GEMINI_API_KEY` | Question generation, explanations, roadmaps, interviews (free key at Google AI Studio; free tier ≈ 20 requests/day, so curated questions cover quizzes without it) |
| `ACTIVE_AI_PROVIDER`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `GROK_API_KEY`, `GROK_MODEL` | Optional alternative LLM providers |
| `YOUTUBE_API_KEY`, `GITHUB_TOKEN` | Optional learning-resource and repository recommendations |
| `JOB_PROVIDERS`, `ADZUNA_*`, `JOOBLE_*`, `ARBEITNOW_REMOTE_ONLY` | Job providers and their budgets |
| `JOB_SYNC_INTERVAL_HOURS` (2), `JOB_SYNC_RETRY_MINUTES` (20), `JOB_SYNC_LEASE_MINUTES` (30) | Sync schedule |
| `JOB_STALE_AFTER_HOURS`, `JOB_EXPIRE_AFTER_DAYS`, `JOB_MAX_POSTING_AGE_DAYS`, `JOB_ALERT_MAX_PER_RUN` | Freshness and alert rules |
| `RUN_JOB_SCHEDULER_IN_PROCESS`, `JOB_SYNC_COMMIT_EVERY` (50) | Scheduler mode; sync commit chunk size |
| `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_USE_TLS` / `MAIL_USE_SSL`, `MAIL_FROM` | SMTP for password-reset emails (without them no reset link is sent) |
| `FRONTEND_URL` | Base URL used in reset and share links |
| `SKILLBRIDGE_ENV=production` | Refuses a weak `SECRET_KEY` or a non-PostgreSQL database, HTTPS-only cookies, proxy-aware client IPs, warns if email is not configured |
| `SKILLBRIDGE_TEST_DATABASE_URL` | Run the test suite on PostgreSQL (name must end in `_test`) |

---

## 16. Live Job Discovery & Two-Hour Synchronization

```
Greenhouse/Lever ─┐
Adzuna ───────────┤                                                  ┌─ JobListing (status, freshness, salary, provenance)
Jooble ───────────┼─► fetch (budgeted, retried) ─► normalize/validate ─► upsert + dedup ─┼─ JobSyncRun (per-provider results, errors)
Arbeitnow ────────┘          ▲                                       │            └─ JobAlertMatch (alerts, once per job)
                   DB lease (one run at a time)              expiry / staleness
```

- **Schedule:** a run is due 2 h after the previous run started (20 min after a failed run). The schedule lives in the database, so it survives restarts. Every run takes the `job_sync` lease, so scheduled, manual and CLI runs never overlap; a crashed run's lease expires after 30 min. Every scheduler records a heartbeat, and the admin and student pages warn when the automatic refresh is not running.
- **Providers:** per-run request budgets (e.g. Jooble's 100 requests/day = 8 per run × 12 runs). Searches cover target roles × Bengaluru, Mangaluru, Karnataka, Udupi, Bhatkal, India, other hubs and remote, plus students' target careers and alert roles, rotated across runs. Auth errors and HTTP 429 stop that provider for the run; timeouts and 5xx are retried with exponential backoff.
- **Company boards** (25 companies, no key) return complete listings, so a posting that disappears is expired as *confirmed by the source*. Only India-based or APAC/anywhere-remote tech, data and analytics roles are kept.
- **Data quality:** listings without a valid URL, title, company or meaningful description are rejected with a counted reason. Skills are split into required vs preferred from the description wording, and company boilerplate is ignored.
- **De-duplication:** same provider ID or canonical URL means the same listing (updated). The same title + company + city from another provider is kept with attribution but flagged `duplicate_of` and hidden from search.
- **Freshness:** *Checked < 24 h ago*, *Not re-checked recently* (absent for 72 h), *Expired / archived* (deadline passed, posted more than 60 days ago, or absent for 21 days). Absence rules apply only while the provider itself is healthy. Rows are archived, never deleted.
- **SQLite concurrency:** a 30 s busy timeout and commits every 50 jobs keep user requests from failing while a sync writes.

| Production option | Command |
|---|---|
| Worker process | `python job_worker.py` |
| Platform cron | `*/15 * * * *  flask --app app jobs sync-if-due` |
| In-process thread (development) | default in `python app.py`; `RUN_JOB_SCHEDULER_IN_PROCESS=0` disables it |

---

## 17. REST API Reference

All endpoints use cookie sessions and are scoped to the logged-in account and role.

### `/api/auth`
`POST /register`, `POST /register_recruiter`, `POST /login`, `POST /logout`, `GET /me`, `PUT /profile`, `POST /profile/photo`, `POST /change_password`, `POST /forgot_password`, `POST /verify_reset_token` (token in the body), `POST /reset_password`

### `/api/student`
- **Resume & skills:** `POST /upload_resume`, `POST /parse_resume/<id>`, `POST /extract_skills/<id>`, `GET /skills`, `GET /verified_skill_profile`
- **Assessment:** `GET /get_quiz/<skill_id>`, `POST /submit_quiz/<skill_id>`, `POST /quiz_explanation/<skill_id>`, `GET /assessments`
- **Career:** `POST /set_target_career`, `POST /analyze_skill_gap`, `GET /readiness_breakdown`, `GET /career_insights`, `GET /career_recommendations`, `GET /career_recommendation/<name>`, `POST /compare_careers`, `POST /simulate_paths`, `POST /simulate_salary`
- **Learning & progress:** `POST /generate_roadmap`, `GET /get_roadmap`, `POST /roadmap/skills` (add one skill), `POST /complete_roadmap_day/<plan_id>`, `GET /progress_history`, `GET /badges`
- **Jobs:** `GET /jobs` (filters: `query, opportunity, entry_level, experience_max, location, work_arrangement, salary_min, job_type, skill, company, date_posted, domain, region, sort, page, per_page`), `GET /jobs/<id>`, `GET /jobs/<id>/match`, `POST /jobs/compare`, `POST|DELETE /jobs/save…`, `GET /jobs/saved`, `POST /jobs/<id>/apply`, `POST /jobs/<id>/employer_preview`, `POST /jobs/<id>/withdraw`, `GET /jobs/applications`, `GET|PUT /job_preferences`, `GET|POST /job_alerts`, `PUT|DELETE /job_alerts/<id>`, `GET /job_alerts/notifications`, `POST /job_alerts/notifications/read`, `GET /jobs/quality_metrics`
- **Assistant & RAG:** `POST /ask_assistant`, `POST /rag/analyze_resume/<id>`, `POST /rag/match_job`, `POST /rag/explain_gap`, `GET /rag/catalog`
- **Interview:** `POST /interview/start`, `POST /interview/answer`, `GET /interview/history`, `GET /interview/session/<id>`
- **ATS Studio:** `GET /resume_optimizer/careers`, `GET /resume_optimizer/my_resumes`, `POST /resume_optimizer/analyze`, `POST /resume_optimizer/export_pdf`, `POST /resume_optimizer/export_docx`
- **Privacy & account:** `GET /privacy_info`, `GET /federated_status`, `GET /account/export`, `DELETE /account/delete`, `GET /ai_providers`, `POST /ai_providers/select`

### `/api/passport`
`GET /me`, `PUT /me/profile`, `POST /me/skills`, `DELETE /me/skills/<id>`, `GET|POST /me/evidence`, `PUT|DELETE /me/evidence/<id>`, `POST /me/evidence/<id>/request_review`, `POST|GET /me/evidence/<id>/file`, `POST /me/evidence/import`, `GET /me/pdf`, `GET|POST /me/shares`, `POST /me/shares/<id>/revoke`, `GET /me/shares/<id>/access_log`, `GET /public/<token>`, `GET /public/<token>/pdf`, admin: `GET /admin/evidence`, `POST /admin/evidence/<id>/review`, `GET /admin/evidence/<id>/file`

### `/api/recruiter`
`GET /me`, `PUT /me/profile`, `PUT /organisation`, `POST /organisation/verification`, `GET /dashboard`, `GET|POST /jobs`, `GET|PUT|DELETE /jobs/<id>`, `POST /jobs/<id>/publish`, `POST /jobs/<id>/close`, `GET /jobs/<id>/applicants`, `GET /jobs/<id>/matches`, `GET /candidates/search`, `GET /candidates/<ref>`, `POST /candidates/<ref>/notes`, `DELETE /notes/<id>`, `POST /candidates/<ref>/invite`, `GET|POST /shortlists`, `GET|DELETE /shortlists/<id>`, `POST /shortlists/<id>/entries`, `DELETE /shortlists/<id>/entries/<entry_id>`, `GET /pipeline`, `POST /applications/<id>/stage`, `POST /candidates/<ref>/verification_requests`, `GET /verification_requests`, `POST /verification_requests/read`, `POST /verification_requests/<id>/cancel`, admin: `GET /admin/organisations`, `POST /admin/organisations/<id>/review`

### `/api/candidate` (student side of recruiting)
`GET|PUT /discovery` (opt-in search), `GET /access` (who viewed my profile), `GET /updates`, `GET /updates/unread_count`, `POST /updates/read`, `GET /verification_requests`, `POST /verification_requests/<id>/respond`, `GET /readiness_preview`

### `/api/admin`
`GET /stats`, `GET /students`, `POST /federated/train`, `GET /federated/rounds`, `GET /federated/nodes`, `GET /federated/round/<id>`, `GET /federated/status`, `GET /jobs/overview`, `POST /jobs/sync` (409 if a run is in progress), `GET /jobs/runs`, `GET /audit_logs`, `GET /system/health`

---

## 18. Privacy, Security & Ethics

- **Consent first:** employers see only the passport sections a student shared, through opaque candidate references. Access ends when the student withdraws or opts out, and every employer access is logged and shown to the student. Candidate search is opt-in.
- **Fairness:** the compatibility score uses skills only. Name, college, location, gender and age are not inputs. Experience and education are shown for human judgement, not scored. Every report states that it is "an explainable indicator of skill alignment, not a prediction of job performance".
- **Trusted employers:** organisations must be verified by an administrator (website and email-domain signal) before posting jobs or searching candidates.
- **Access control & RBAC:** student, recruiter and admin roles; self-registration can never create an admin (`flask users make-admin` grants it). Cross-account access to alerts, preferences, evidence and applications is covered by tests.
- **Data storage:** resumes, extracted skills, quiz results and evidence files are stored on the server so they can be analysed. Students can export or permanently delete their data, and deletion also removes resume and evidence files.
- **Share tokens:** stored only as SHA-256 hashes; links expire and can be revoked. Public views exclude contact details, resume text, files and internal IDs.
- **Abuse protection:** rate limits on registration (10/h students, 5/h recruiters), password reset, public passports, recruiter search and profile views, and verification requests. File uploads are checked by signature.
- **Password reset:** 256-bit tokens stored as SHA-256 hashes, 60-minute expiry, single use (one conditional update, so a race cannot use a token twice); a new request invalidates older links. The token travels in the URL fragment and POST bodies, never in request URLs or logs. Unknown and registered emails get the same response and timing. Rate limits: 5 requests / 15 min per IP, 3 / hour per address, 20 token checks / 15 min per IP. A reset or password change signs out all other sessions.
- **Production mode:** `SKILLBRIDGE_ENV=production` refuses to start with a weak secret key or a non-PostgreSQL database and makes cookies HTTPS-only.
- **Secrets:** provider keys stay in server-side environment variables and never reach the frontend or error messages.
- **Audit log:** manual syncs, admin grants and review decisions are recorded.
- **Federated learning:** a simulation on synthetic data; no formal differential-privacy guarantee.
- **Compliance:** not audited for GDPR, FERPA, India's DPDP Act or any other regulation; deploying institutions must do their own assessment.

---

## 19. Limitations & Threats to Validity

- **Small evaluation sets:** the retrieval test set (27 queries) and the career documents were written by the authors. The results show a relative difference between methods, not production accuracy.
- **Salary data:** 24 rows of undocumented, apparently hand-built data. Estimates are illustrative only.
- **Known issue (salary model not loaded):** `backend/ml/models/salary.pkl` (and `readiness.pkl`, `skill_gap.pkl`) are empty 0-byte files committed with the initial project. The loader tries to unpickle the empty file, fails, and the app falls back to its heuristic estimate (labelled *Fallback heuristic*). The Ridge figures in Section 9.3 come from `SalaryPredictor().evaluation()`, not from the running app, until the empty file is removed and the model is retrained.
- **Federated learning:** synthetic data, no privacy accountant, no real multi-institution deployment.
- **Assessment validity:** multiple-choice quizzes measure recall and understanding, not on-the-job performance. The 70% pass mark and the readiness weights are design choices that have not been calibrated against hiring outcomes.
- **No user study yet:** usability, student outcomes and recruiter trust have not been measured with real participants.
- **Job coverage:** without Adzuna/Jooble keys, listings come mainly from 25 large-company boards in major cities. Smaller cities (e.g. Mangaluru) need those keys.
- **LLM dependence:** the Gemini free tier (≈ 20 requests/day) limits AI-generated questions and explanations. Curated questions keep verification working, but explanations may be unavailable.
- **Deployment:** not deployed yet. Development uses SQLite and a single process; production needs PostgreSQL and a separate job worker. The Docker files in `deploy/` target a VM such as Oracle Cloud Always Free, which asks for a payment card; the planned card-free setup is Netlify (frontend) + Render free web service (backend) + Neon PostgreSQL. Phase 0 (Section 9.4) and Phase 1 (PostgreSQL compatibility) are done. Still to do: storing uploaded files and the FL model in the database (Render's disk is temporary), the ONNX/REST memory tuning on `main`, a token-protected endpoint for the external two-hour sync trigger, and email over HTTPS (Render blocks SMTP ports).

---

## 20. Future Scope

- Pilot study with students and recruiters (usability, time-to-shortlist, trust in verified skills).
- Practical coding challenges and project-based verification alongside multiple-choice quizzes.
- Email notifications for job alerts and pipeline updates.
- A real privacy accountant (e.g. RDP/moments accountant) and real institutional partners for federated learning.
- Salary model trained on documented, current Indian compensation data.
- Calibrating readiness weights and the pass mark against hiring outcomes.
- Institution (placement cell) dashboards and multi-campus tenancy.
- Free production deployment on Netlify + Render + Neon (remaining phases above); CI is already in place.

---

## 21. Citation

```bibtex
@misc{skillbridge2026,
  title  = {SkillBridge: A Privacy-Preserving Federated Intelligence and Adaptive Verification Framework for Career Gap Remediation},
  author = {Aysha Daniya and Contributors},
  year   = {2026},
  howpublished = {GitHub repository},
  url    = {https://github.com/AYSHA-GITT/skillbridge}
}
```

```text
A. Daniya et al., "SkillBridge: A Privacy-Preserving Federated Intelligence and Adaptive Verification Framework for Career Gap Remediation," GitHub repository, 2026. [Online]. Available: https://github.com/AYSHA-GITT/skillbridge
```

---

## 22. Acknowledgments

This project builds on the [Flower](https://flower.ai/) federated learning framework; [Google AI Studio](https://ai.google.dev/) for the Gemini models; the sentence-transformers, scikit-learn, NumPy, pandas, pdfplumber, PyMuPDF and ReportLab projects; and the Greenhouse, Lever, Adzuna, Jooble and Arbeitnow public job APIs.
