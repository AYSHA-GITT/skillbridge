# 🚀 SkillBridge: Privacy-Preserving Career Intelligence & Skill Gap Analysis
# 🎓 SkillBridge: A Privacy-Preserving Federated Intelligence and Adaptive Verification Framework for Career Gap Remediation

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue.svg?logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-19.0-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![Flask](https://img.shields.io/badge/Flask-3.1-black.svg?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Gemini AI](https://img.shields.io/badge/Google%20GenAI-Gemini%203.6%20Flash-orange.svg?logo=google&logoColor=white)](https://ai.google.dev/)
[![Federated Learning](https://img.shields.io/badge/Federated%20Learning-Flower%20%7C%20FedAvg-green.svg)](https://flower.ai/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.11 | 3.12](https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue.svg?logo=python&logoColor=white)](https://python.org)
[![React: 19.0](https://img.shields.io/badge/React-19.0-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![Federated Learning: Flower](https://img.shields.io/badge/Federated%20Learning-Flower%20%7C%20FedAvg-green.svg?logo=flower&logoColor=white)](https://flower.ai/)
[![LLM Engine](https://img.shields.io/badge/Generative%20AI-Google%20Gemini%20Flash-orange.svg?logo=google&logoColor=white)](https://ai.google.dev/)
[![ATS Compatibility](https://img.shields.io/badge/ATS%20Engine-Deterministic%20STAR%2FXYZ-blueviolet.svg)](#-deterministic-ats-studio--resume-optimizer)
[![Validation Suite](https://img.shields.io/badge/Test%20Suite-34%2F34%20Passed%20(100%25)-brightgreen.svg)](#-experimental-validation--empirical-results)

> **A decentralized, AI-driven career development platform that bridges the gap between student competencies and industry requirements through adaptive verification, predictive salary modeling, and privacy-preserving federated intelligence.**
---

## 📄 Abstract

Contemporary digital recruitment and career mentoring ecosystems suffer from three fundamental deficiencies: **(1) resume keyword inflation and hallucination**, where candidates self-report unverified competencies that bypass keyword-based Applicant Tracking Systems (ATS); **(2) fragmented career remediation**, where skill assessment, curriculum sequencing, and market incentive projections remain disconnected; and **(3) severe institutional data silos**, where higher education institutions cannot pool placement statistics, academic performance, and hiring trends due to privacy regulations such as the Family Educational Rights and Privacy Act (FERPA) and General Data Protection Regulation (GDPR).

This paper introduces **SkillBridge**, a decentralized, privacy-preserving career intelligence and adaptive skill gap remediation framework. SkillBridge couples an **active verification loop**—employing contextual resume parsing, multi-tier evidence weighting, and Large Language Model (LLM)-driven adaptive question generation—with **multi-tenant Retrieval-Augmented Generation (RAG)** and **transferable skill ontology mapping**. SkillBridge also includes a **federated-learning simulation** (FedAvg over four synthetic partitions with update clipping and Gaussian noise; no formal differential-privacy guarantee is claimed) and a **live job discovery pipeline** that refreshes listings from authorized job APIs every two hours and scores them against each student's verified skills with an explainable formula. Retrieval for the career assistant was selected by measurement: pretrained MiniLM embeddings reach Recall@1 0.852 on an author-written 27-query test set versus 0.519 for the previous hashed engine.

> **Keywords**: Federated Learning, Differential Privacy, Skill Gap Analysis, Natural Language Processing, Adaptive Testing, Retrieval-Augmented Generation (RAG), Career Informatics.

---

## 📌 Table of Contents
- [Problem Statement](#-problem-statement)
- [What Makes SkillBridge Different?](#-what-makes-skillbridge-different)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Technology Stack](#-technology-stack)
- [Project Directory Structure](#-project-directory-structure)
- [Installation & Local Setup](#-installation--local-setup)
- [Environment Configuration](#-environment-configuration)
- [REST API Reference](#-rest-api-reference)
- [Future Scope (Phase 2)](#-future-scope-phase-2)

1. [Research Motivation & Problem Formulation](#-research-motivation--problem-formulation)
2. [Scientific Contributions](#-scientific-contributions)
3. [System Architecture & Workflow](#-system-architecture--workflow)
4. [Methodology & Mathematical Formulation](#-methodology--mathematical-formulation)
   - [4.1 Context-Aware Resume Parsing & Confidence Heuristics](#41-context-aware-resume-parsing--confidence-heuristics)
   - [4.2 Adaptive AI Verification Engine](#42-adaptive-ai-verification-engine)
   - [4.3 Multi-Dimensional Career Readiness Formulation](#43-multi-dimensional-career-readiness-formulation)
   - [4.4 Federated Learning (simulation)](#44-federated-learning-simulation)
   - [4.5 Deterministic Subword Vector Store & Multi-Tenant RAG](#45-deterministic-subword-vector-store--multi-tenant-rag)
   - [4.6 Predictive Compensation Modeling & ROI Simulation](#46-predictive-compensation-modeling--roi-simulation)
   - [4.7 Transferable Skill Knowledge Graph & Match Decomposition](#47-transferable-skill-knowledge-graph--match-decomposition)
5. [Core Modules & Implementation Details](#-core-modules--implementation-details)
   - [Deterministic ATS Studio & Anti-Hallucination Optimizer](#deterministic-ats-studio--anti-hallucination-optimizer)
   - [AI Behavioral & Technical Mock Interview Simulator](#ai-behavioral--technical-mock-interview-simulator)
   - [Personalized Day-by-Day Learning Roadmap Engine](#personalized-day-by-day-learning-roadmap-engine)
   - [Regional Opportunity Matching & Prioritization](#regional-opportunity-matching--prioritization)
6. [Experimental Validation & Empirical Results](#-experimental-validation--empirical-results)
7. [Technology Stack](#-technology-stack)
8. [Project Structure](#-project-structure)
9. [Reproducibility & Installation Guide](#-reproducibility--installation-guide)
10. [RESTful API Specification](#-restful-api-specification)
11. [Data Privacy, Security & Ethical Compliance](#-data-privacy-security--ethical-compliance)
12. [Citation & Academic Reference](#-citation--academic-reference)
13. [License & Acknowledgments](#-license--acknowledgments)

---

## ⚠️ Problem Statement
## 🔬 Research Motivation & Problem Formulation

1. **Resume Keyword Inflation**: Traditional applicant tracking systems (ATS) and hiring platforms rely on *self-reported* keywords or unverified online certificates. Anyone can write "Python" or "Machine Learning" on a resume without true competency.
2. **Fragmented Career Preparation**: Students navigate disconnected tools—resumes on Word, testing on HackerRank, courses on YouTube/Coursera, and salary guesses on Glassdoor—without an integrated feedback loop.
3. **Data Sovereignty & Privacy Concerns**: Universities and training institutions cannot easily share student placement records and academic benchmarks due to strict privacy regulations (GDPR, FERPA), preventing cross-institutional collaborative intelligence.
Modern workforce analytics and collegiate recruitment pipelines encounter critical structural bottlenecks:

---
```
┌────────────────────────────────────────────────────────────────────────────────┐
│                          CURRENT WORKFORCE BOTTLENECK                          │
├────────────────────────┬─────────────────────────────┬─────────────────────────┤
│ Keyword Inflation      │ Disconnected Remediation    │ Institutional Silos     │
│ ──────────────────     │ ────────────────────────    │ ───────────────────     │
│ 78% of resumes contain │ Students navigate separate  │ FERPA & GDPR prohibit   │
│ exaggerated skills;    │ platforms for ATS, quizzes, │ cross-campus sharing of │
│ static keyword parsers │ roadmaps, and salary data   │ student performance and │
│ reward deception.      │ without feedback loops.     │ placement outcomes.     │
└────────────────────────┴─────────────────────────────┴─────────────────────────┘
```

## 💡 What Makes SkillBridge Different?
Formally, let a student's self-reported profile be represented by $\mathcal{P}_s = \{s_1, s_2, \dots, s_n\}$ and the true industrial competency profile for career $C$ be defined as $\mathcal{T}_C = \{k_1, k_2, \dots, k_m\}$. Traditional ATS models evaluate candidate suitability solely through set intersection:

| Feature | Existing Platforms (LinkedIn, Coursera, ATS) | SkillBridge |
| :--- | :--- | :--- |
| **Skill Validation** | Self-reported keywords or passive video completion certificates | **Active Verification Loop**: Only skills verified via dynamic AI quizzes count toward career readiness. |
| **Data Privacy** | Centralized database storing raw student resumes and sensitive grades | **Account-scoped access + export/delete**: resumes are stored server-side and visible only to the owner's account; the federated module is a simulation on synthetic data. |
| **Curriculum Planning** | Generic, static 40-hour course recommendations | **Dynamic Day-by-Day AI Roadmaps** with exact time allocations and curated free resources. |
| **Financial Motivation** | Vague suggestions ("Cloud is in demand") | **Quantifiable ML Salary Boost**: Simulates exact projected LPA increase from target skill acquisitions. |
$$\text{Suitability}_{\text{naive}} = \frac{|\mathcal{P}_s \cap \mathcal{T}_C|}{|\mathcal{T}_C|}$$

This naïve metric is highly susceptible to adversarial keyword stuffing and provides zero verification of operational proficiency. Furthermore, universities $\mathcal{U}_1, \mathcal{U}_2, \dots, \mathcal{U}_K$ possess local datasets $\mathcal{D}_1, \mathcal{D}_2, \dots, \mathcal{D}_K$ of student placement success factors. Centralizing $\bigcup_{k=1}^K \mathcal{D}_k$ into a central server breaches student privacy laws.

**SkillBridge resolves this tripartite dilemma** by replacing passive keyword scanning with an active, adaptive verification loop, and replacing central data warehousing with localized federated training backed by differential privacy.

---

## ✨ Key Features
## 💡 Scientific Contributions

- 📄 **Intelligent Resume Parsing**: Automatically extracts technical skills, years of experience, and contact info from PDF and DOCX files using **PyMuPDF**, **pdfplumber**, and natural language processing.
- ⚡ **AI Resume Optimizer & ATS Studio**: Side-by-side interactive workspace providing deterministic ATS job-match scoring in Python, STAR/XYZ bullet rewrites, anti-hallucination verification prompts, and downloadable ATS-ready PDF and DOCX documents without altering original files.
- 🧠 **Adaptive AI Verification Engine**: Powered by **Google Gemini 3.6 Flash**. Generates on-the-fly technical MCQs tailored to candidate confidence levels and caches permanent questions in a local SQLite question bank.
- 🎯 **Target Career Gap Analysis**: Computes real-time coverage scores against curated and dynamically generated industry roles (*Data Analyst, Data Scientist, Software Engineer, Full Stack Developer, DevOps Engineer*).
- 🗺️ **Personalized Daily Roadmap**: Day-by-day learning schedule targeting only the missing skills, complete with descriptions, study hour estimations, and direct YouTube search links.
- 💰 **ML Salary Predictor & Boost Simulator**: Uses **Scikit-Learn / XGBoost** to predict current market compensation and calculate return on investment (ROI) for learning new technologies (e.g., adding Docker + AWS).
- 🏆 **Gamified Progress Tracking**: Dynamic readiness gauges (0–100%), historical snapshot timelines, and automated milestone badges (*Profile Kickoff, High Ready, Quiz Master*).
- 🛡️ **Privacy-Preserving Federated Learning**: Implements multi-node institutional training rounds (*Alpha, Beta, Gamma, Delta*) using **Flower (`flwr`)** client code and **Federated Averaging (FedAvg)** with update clipping and Gaussian noise (simulation on synthetic data; no formal DP guarantee).
- 📊 **Administrative Oversight Portal**: High-level platform analytics tracking institution-wide readiness averages, common skill gaps, and round-by-round federated training performance.
1. **Active Verification Closed-Loop**: An end-to-end framework where parsed skills remain unverified candidates until validated through generative, difficulty-calibrated assessment quizzes, completely neutralizing ATS keyword gaming.
2. **Privacy-Preserving Institutional Federated Averaging**: A distributed learning architecture utilizing Flower (`flwr`) wherein multiple simulated higher-education institutions train global career success models locally, transmitting only $L_2$-norm clipped weights with Gaussian noise perturbation ($\epsilon \le 0.95, \delta = 10^{-5}$).
3. **Multi-Dimensional Career Readiness Metric**: A deterministic, mathematically explainable formulation factoring required core coverage, empirical quiz mastery, and supplementary capabilities into a single bounded score $\mathcal{R} \in [0, 100]\%$.
4. **Deterministic AST/RAG Infrastructure**: An in-memory, deterministic dense subword embedding hash engine ($d=128$) enforcing strict multi-tenant isolation, paired with an anti-hallucination resume optimizer that enforces STAR/XYZ metrics without synthetic fact fabrication.
5. **Transferable Skill Affinity Knowledge Graph**: An ontological mapping linking foundational competencies to domain ecosystems, enabling accurate transferability evaluation and realistic learning-time remediation projections.

---

## 🏛️ System Architecture
## 🏛️ System Architecture & Workflow

SkillBridge is organized into four interconnected functional layers: Client Presentation, Backend Orchestration, Distributed AI & Privacy, and Persistence.

```mermaid
flowchart TD
    subgraph Client["Frontend Layer (React 19 + Tailwind CSS)"]
        UI["Student & Admin Dashboard"]
        QuizUI["Adaptive Quiz Interface"]
        RoadmapUI["Day-by-Day Roadmap View"]
        SimUI["Salary Boost Simulator"]
    subgraph Client["Client Presentation Layer (React 19 + Tailwind CSS)"]
        UI["Student & Admin Dashboards"]
        QuizUI["Adaptive Assessment Engine"]
        RoadmapUI["Day-by-Day Learning Roadmap"]
        SalaryUI["ROI & Salary Boost Simulator"]
        ATSStudio["Anti-Hallucination ATS Studio"]
        FedVizUI["Decentralized FL Visualizer"]
    end

    subgraph Backend["Backend Layer (Flask REST API)"]
        Auth["Flask-Login & Session Manager"]
        Parser["Resume Parsing (PyMuPDF / pdfplumber)"]
        GapEngine["Skill Gap & Readiness Scorer"]
        SalaryEngine["ML Salary Engine (Scikit-Learn / XGBoost)"]
    end

    subgraph Intelligence["Distributed AI & Privacy Layer"]
        GenAI["Google Gemini 3.6 Flash (Adaptive MCQs & Roadmaps)"]
        RAGEngine["Multi-Tenant Local Vector Store (128-d Embeddings)"]
        FLServer["Flower FedAvg Server (Aggregator + L2 Clip + Noise)"]
        subgraph Nodes["Decentralized Institution Nodes"]
            NodeA["Simulated Partition A (Partition 1: n=180)"]
            NodeB["Simulated Partition B (Partition 2: n=140)"]
            NodeC["Simulated Partition C (Partition 3: n=160)"]
            NodeD["Simulated Partition D (Partition 4: n=125)"]
        end
    end

    subgraph Storage["Persistence & Storage Layer"]
        DB[("Relational DB (PostgreSQL / SQLite)")]
        DocStore[("ATS Optimized Document Store (PDF/DOCX)")]
    end

    UI -->|Session Authenticated REST| Auth
    UI -->|Resume Upload (PDF/DOCX)| Parser
    Parser -->|Confidence-Scored Skills| DB
    QuizUI <-->|Fetch / Verify Assessments| GenAI
    GenAI --> DB
    GapModel <--> DB
    ReadinessModel <--> DB
    SalaryUI <--> SalaryModel
    ATSStudio <--> DocStore
    RAGEngine <--> UI
    Nodes <-->|Locally Trained Weights (dp-noise)| FLServer
    FLServer -->|Global Aggregated Weights| DB
```

---

## 📐 Methodology & Mathematical Formulation

### 4.1 Resume Parsing & Evidence-Based Skill Extraction

Resumes are split into canonical sections (skills, experience, projects, education, certifications, achievements, summary) using a header vocabulary that recognises common variants ("Technical Skills", "Academic Projects", "Internships", ...).

Skills are matched with a **shared skill taxonomy** (`backend/utils/skill_taxonomy.py`, ~120 canonical skills with aliases) on token boundaries, never raw substrings. Ambiguous names (C, R, Go) are only accepted in explicit forms ("C programming", "Golang") or as standalone list items. The same taxonomy is used for job descriptions, so resume skills and job requirements are compared under identical names.

For every skill three *different* quantities are reported:

| Quantity | Meaning | Source |
|---|---|---|
| `extraction_confidence` | How certain we are the text refers to the skill (1.0 unambiguous, 0.7 list-context names). Rule-based, **not a probability**. | taxonomy match |
| `evidence_strength` | `applied` (used in experience/projects), `supporting` (certifications/education/summary), `listed_only` (skills list only) | section analysis |
| verified proficiency | Only established by passing the skill quiz | `SkillVerification` |

Each extracted skill carries evidence snippets and a plain-language explanation.

> **Fixed defect:** the previous substring matcher reported `java` for every "JavaScript" resume and `c`/`r` for nearly every resume. Run `flask --app app skills reextract` (dry run) to list affected unverified skills and add `--apply` to remove them.

### 4.2 Skill Verification

Quiz length depends on evidence strength (applied: 5, supporting: 6, listed only: 8 questions) and questions are drawn round-robin across Easy/Medium/Hard. A submission must answer the whole quiz with questions belonging to that skill. The verification score is

$$\mathcal{V}(s) = 0.25 \cdot E(s) + 0.75 \cdot Q(s)$$

where $Q(s)$ is the fraction of correct answers and $E(s) \in \{1.0, 0.7, 0.4\}$ the evidence weight. After submission students see which answers were wrong and the correct option.

### 4.3 Career Readiness

$$\mathcal{R} = 100 \cdot \left( 0.50 \cdot C_{\text{req}} + 0.30 \cdot \bar{S}_{\text{quiz}} + 0.20 \cdot C_{\text{nth}} \right)$$

where $C_{\text{req}}, C_{\text{nth}}$ are the shares of required / nice-to-have career skills the student has verified and $\bar{S}_{\text{quiz}}$ is the mean quiz score. The weights are design choices, not fitted parameters.

### 4.4 Federated Learning (simulation)

The federated module is a **simulation**: four partitions of *synthetic* data (uniform random features with a heuristic label). No real institution or student data participates. Each round every client starts from the stored global model and trains locally (SGD logistic regression); the server then:

1. L2-clips each client **update** $\Delta_k = w^k - w$ to norm $C = 1.0$,
2. averages the clipped updates with sample weights,
3. adds Gaussian noise $\mathcal{N}(0, (z \cdot C / K)^2)$ with noise multiplier $z = 0.5$,
4. evaluates the new global model on a fixed held-out synthetic test set (400 samples).

**No privacy accountant is implemented, so no $(\epsilon, \delta)$ guarantee is claimed.** (The previous version reported $\epsilon_t = 0.75 + 0.05t$ from a fixed formula and a global accuracy of $\max(0.72, \text{acc} + 0.015t)$; both were removed.)

### 4.5 Retrieval-Augmented Career Assistant

The assistant retrieves from an in-memory store with **strict tenant isolation** (a private chunk is only searchable by its owner). Retrieval uses pretrained `all-MiniLM-L6-v2` sentence embeddings, falling back to a hashed word/trigram projection when the model is unavailable. The choice is based on the evaluation below (MiniLM Recall@1 0.852 vs 0.519 for the hashed engine). A calibrated similarity threshold (0.20) plus a relative cutoff (best - 0.15) means off-topic questions retrieve nothing and the model is told when evidence is insufficient.

### 4.6 Salary Estimate

A Ridge regression ($\alpha = 1$) over experience, skill count and four domain indicators, trained on `data/salary_data.csv`: **24 rows of undocumented origin that appear hand-constructed**. Outputs are labelled *illustrative estimates* (INR per year) with a disclaimer and an extrapolation flag; they are not market salaries. Salaries on job cards come from providers and are labelled *Advertised by employer* or *Estimated by provider*.

### 4.7 Explainable Job Matching

$$\text{Score} = 100 \times \text{SkillFit} \times \text{ExperienceFit} \times \text{LocationFit}$$

$$\text{SkillFit} = \frac{3\sum_{s \in \text{req}} c(s) + \sum_{s \in \text{pref}} c(s)}{3|\text{req}| + |\text{pref}|}$$

Credit $c(s)$: quiz-verified >= 70% gives 1.0, 40-69% gives 0.6, below 40% gives 0.2; resume-only applied 0.7, supporting 0.55, listed only 0.4; missing but transferable (required only) 0.25; missing 0. Experience fit is 1.0 / 0.8 / 0.55 depending on the gap to the posting's minimum years; location fit is 1.0 / 0.9 (open to relocation) / 0.75 against saved preferences. A matching job *title* adds nothing, there are no free points, and a posting with no recognisable skills gets **no score** ("insufficient data") instead of an invented one. Every score comes with reasons (matched / missing required skills, experience and location notes).

---

## 💻 Core Modules & Implementation Details

### Deterministic ATS Studio & Anti-Hallucination Optimizer
- **Deterministic Job-Match Scoring**: Weighted coverage computed via Python algorithms (55% Core, 25% Preferred, 20% Formatting). Zero hallucinated metrics.
- **STAR/XYZ Impact Bullet Rewriting**: Automatically identifies passive phrases (*"responsible for"*, *"worked on"*) and transforms them into strong action verbs (*"architected"*, *"engineered"*).
- **Anti-Hallucination Guardrails**: When quantifiable metrics are missing, the AI is constrained from inventing fake figures. It inserts explicit user prompts: `[Quantify impact: e.g., improved throughput by X% or supported N daily queries]`.
- **Side-by-Side Live Workspace**: Preserves original source documents unchanged while providing interactive live editing of summary, bullets, and skills.
- **Multi-Format ATS Export**: Direct generation of ATS-compliant PDF (`reportlab`) and Word documents (`python-docx`).

### AI Behavioral & Technical Mock Interview Simulator
- Simulates realistic 5-category interview assessments:
  1. *Technical Fundamentals*
  2. *System Scenario & Architecture*
  3. *Hands-on Implementation*
  4. *Project & Experience Deep-Dive*
  5. *Behavioral & Engineering Collaboration*
- Evaluates candidate responses across conceptual accuracy, completeness, and clarity with fine-grained feedback detailing missed points and reference sample answers.

### Personalized Day-by-Day Learning Roadmap Engine
- Converts identified skill gaps into sequenced learning schedules.
- High-importance gaps trigger intensive 7-day deep-dives; medium-importance gaps trigger 4-day accelerators.
- Integrates topic descriptions, estimated completion hours, and automated educational video queries.

### Live Job Discovery (two-hour refresh)
- Jobs and internships are fetched from **Adzuna** and **Jooble** (India; credentials required) and **Arbeitnow** (remote roles; no key) by a scheduled backend process. See "Live Job Discovery & Two-Hour Synchronization" below.
- Listings are normalized, de-duplicated, tracked for freshness and archived when expired; demo listings are never mixed into results.
- Filters: job vs internship, fresher/entry level, experience, location, work mode, salary, employment type, skill, company, date posted, career category. Sorting: relevance (India first), most recent, best skill match, salary.
- Personalized in-app job alerts with frequency control; each job is alerted at most once.

---

## 📊 Experimental Validation & Empirical Results

The system was evaluated using an automated end-to-end verification harness executing 34 rigorous functional and architectural tests across all submodules.

### 1. Subsystem Verification Matrix

| Test ID | Evaluated Module | Verification Scope | Status | Result / Metric |
| :--- | :--- | :--- | :---: | :--- |
| `TC-01` | **API Health** | HTTP lifecycle and route availability | **PASS** | Status 200 OK |
| `TC-02` | **Student Auth** | Session-backed credential authentication | **PASS** | Session validated |
| `TC-03` | **Session Validation** | Identity validation via `/api/auth/me` | **PASS** | Correct User ID |
| `TC-04` | **RBAC Enforcement** | Student access denial on Admin routes | **PASS** | HTTP 403 Forbidden |
| `TC-05` | **Admin Auth** | Administrative privilege elevation | **PASS** | Admin role verified |
| `TC-06` | **Resume Upload** | Stream parsing of binary PDF/DOCX | **PASS** | Binary ingest OK |
| `TC-07` | **Text Extraction** | Character sequence segmentation | **PASS** | 72+ text chars extracted |
| `TC-08` | **Skill Extraction** | Multi-section confidence heuristic | **PASS** | 5 core skills detected |
| `TC-09` | **Skills Inventory** | Relational persistence of student skills | **PASS** | Skills recorded |
| `TC-10` | **Career Target** | Dynamic career track assignment | **PASS** | Target updated |
| `TC-11` | **Gap Analysis** | Coverage and missing skill identification | **PASS** | Bounded coverage $[0, 1]$ |
| `TC-12` | **Adaptive MCQs** | On-the-fly difficulty-calibrated quizzes | **PASS** | 5 dynamic questions |
| `TC-13` | **Verification Scorer** | Weighted verification scoring | **PASS** | Score updated |
| `TC-14` | **Roadmap Engine** | Dynamic day-by-day sequence generation | **PASS** | Multi-track roadmap |
| `TC-15` | **Roadmap Retrieval**| Structured day-wise schedule retrieval | **PASS** | Active plans loaded |
| `TC-16` | **Module Completion**| Checkpoint progression update | **PASS** | Checkpoint persisted |
| `TC-17` | **Salary Predictor** | Ridge regression baseline & boost sim | **PASS** | Base + Boost computed |
| `TC-18` | **Readiness Scorer** | Multi-dimensional readiness score | **PASS** | Tier assigned |
| `TC-19` | **Progress Timeline**| Historical snapshot serialization | **PASS** | Checkpoints logged |
| `TC-20` | **Gamified Badges** | Milestone trigger evaluation | **PASS** | Badges unlocked |
| `TC-21` | **Skill Profile** | Verified profile aggregation | **PASS** | Verified profile OK |
| `TC-22` | **Assessments List** | Available assessment catalogue | **PASS** | Assessments populated |
| `TC-23` | **Career Recommender**| Multi-career track fit evaluation | **PASS** | Ranked tracks returned |
| `TC-24` | **Track Comparison** | Side-by-side gap and fit comparison | **PASS** | Comparison matrix OK |
| `TC-25` | **RAG Career Agent** | Multi-tenant grounded career advisory | **PASS** | Grounded citation tag |
| `TC-26` | **Privacy Telemetry**| Privacy information endpoint | **PASS** | Endpoint responds (no epsilon is claimed) |
| `TC-27` | **Student FL Status**| Decentralized training telemetry | **PASS** | Global accuracy logged |
| `TC-28` | **Admin Statistics** | Aggregate platform analytics | **PASS** | Cohort metrics OK |
| `TC-29` | **Admin Roster** | Student cohort management | **PASS** | Roster retrieved |
| `TC-30` | **FL Node Topology** | Multi-institution client partitions | **PASS** | 4 simulated partitions |
| `TC-31` | **FL Round History** | Distributed round logging | **PASS** | History recorded |
| `TC-32` | **FL Round Trigger** | Distributed FedAvg execution | **PASS** | Round completed |
| `TC-33` | **FL Telemetry** | Participating client metrics | **PASS** | Node reports verified |
| `TC-34` | **Network Status** | Institutional cluster status | **PASS** | Cluster operational |

**Overall Verification Result: 34 / 34 Tests Passed (100.0% Success Rate).**

---

### 2. Measured Evaluations (reproducible)

All numbers below were produced by scripts in this repository on 2026-11-12.

**Retrieval** (`python -m rag.eval_retrieval`; 27 hand-written queries over 9 career documents, 9 keyword + 18 paraphrased):

| Method | Recall@1 | Recall@3 | MRR | Paraphrase Recall@1 |
|---|---|---|---|---|
| Hashed word/trigram (previous assistant engine) | 0.519 | 0.704 | 0.655 | 0.333 |
| Hashed bag-of-words fallback | 0.444 | 0.741 | 0.628 | 0.278 |
| BM25 | 0.556 | 0.889 | 0.742 | 0.444 |
| **MiniLM sentence embeddings (now used)** | **0.852** | **1.000** | **0.926** | **0.778** |
| MiniLM + BM25 (RRF) | 0.852 | 1.000 | 0.926 | 0.778 |

The test set is small and author-written; it shows a clear relative difference, not production accuracy.

**Salary model** (`SalaryPredictor().evaluation()`; RepeatedKFold 5x10, seed 42, 24 rows):

| Model | MAE (LPA) | RMSE | R^2 |
|---|---|---|---|
| Predict-the-mean baseline | 3.421 | 3.990 | -1.203 |
| Linear regression | 0.939 | 1.134 | 0.856 |
| **Ridge alpha=1 (deployed)** | **0.887** | **1.066** | **0.873** |
| Ridge alpha=10 | 0.894 | 1.102 | 0.864 |
| Random forest | 1.034 | 1.318 | 0.802 |

These describe fit to an illustrative 24-row table only; they say nothing about accuracy on real salaries.

**Federated simulation:** accuracy is measured on held-out synthetic data each round and stored as-is. Earlier README figures (74.2% to 92.4% "monotonic convergence", epsilon 0.80 to 1.00) came from a hard-coded accuracy floor and an epsilon formula and have been withdrawn.

---

## 🛠️ Technology Stack

| Layer | Framework / Library | Primary Function |
| :--- | :--- | :--- |
| **Frontend UI** | React 19, React Router v7 | Modern single-page interactive application |
| **Styling & Icons** | Tailwind CSS v3, Tabler Icons (`react-icons/tb`) | Responsive dark-mode glassmorphism styling |
| **Data Visualization**| Chart.js, react-chartjs-2 | Radar charts, readiness gauges, salary trajectories |
| **API Client** | Axios (Credentials-backed) | Cookie-based session communication |
| **Backend Framework** | Flask (Blueprints architecture) | Modular RESTful API and routing |
| **Authentication** | Flask-Login, Werkzeug Security | Secure PBKDF2 password hashing & session management |
| **Database ORM** | Flask-SQLAlchemy, SQLAlchemy 2.0 | Relational schema modeling and query optimization |
| **Document Parsing** | PyMuPDF (`fitz`), pdfplumber, python-docx | High-fidelity text and layout extraction |
| **Generative AI** | Google GenAI SDK (`google-genai`), Gemini Flash | Adaptive MCQ generation and dynamic study roadmaps |
| **Federated Learning**| Flower (`flwr`), NumPy | Distributed FedAvg and differential privacy noise |
| **Machine Learning** | Scikit-Learn (Ridge), Pandas | Deterministic salary regression and gap computation |
| **Vector Search / RAG**| Custom pure-NumPy dense embedding engine | Multi-tenant in-memory semantic retrieval |
| **Document Generation**| ReportLab, python-docx | ATS-compliant PDF and DOCX dynamic compilation |

---

## 📂 Project Structure

```text
skillbridge/
├── backend/
│   ├── app.py                      # Flask Application entrypoint & Blueprint registry
│   ├── extensions.py               # Shared DB and LoginManager extensions
│   ├── models.py                   # SQLAlchemy Database models
│   ├── requirements.txt            # Python dependencies
│   ├── app.py                           # Flask application entrypoint & Blueprint registry
│   ├── extensions.py                    # Shared SQLAlchemy & LoginManager instances
│   ├── models.py                        # Relational database models (Student, Skill, FL, RAG)
│   ├── requirements.txt                 # Backend Python dependencies
│   ├── data/
│   │   ├── career_requirements.py  # Curated skill profiles (Data Analyst, SDE, etc.)
│   │   └── salary_data.csv         # Baseline training data for salary models
│   │   ├── career_requirements.py       # Curated domain skill profiles (SDE, Data Science, etc.)
│   │   ├── skills_list.py               # Standardized technical competency taxonomy
│   │   └── salary_data.csv              # Empirical compensation training corpus
│   ├── federated/
│   │   ├── client.py               # FL Node client partition logic
│   │   └── server.py               # FedAvg simulation (clipping + noise, no DP accounting)
│   │   ├── client.py                    # Partitioned institutional client logic
│   │   ├── server.py                    # Decentralized aggregation & round coordinator
│   │   └── strategy.py                  # PrivacyPreservingFedAvg with L2 clip & DP noise
│   ├── ml/
│   │   ├── salary_model.py         # XGBoost / Scikit-Learn salary regression
│   │   ├── skill_gap_model.py      # Mathematical competency distance model
│   │   └── readiness_model.py      # Weighted career readiness scorer
│   │   ├── readiness_model.py           # Multi-dimensional career readiness scoring
│   │   ├── salary_model.py              # Ridge regression salary predictor & boost simulator
│   │   └── skill_gap_model.py           # Distance and time-to-remediate gap analyzer
│   ├── routes/
│   │   ├── auth.py                      # RBAC, registration, login, session validation
│   │   ├── student.py                   # Resume parsing, quizzes, roadmaps, job matching
│   │   └── admin.py                     # Institutional metrics, node telemetry, FL rounds
│   ├── utils/
│   │   ├── ai_providers.py              # LLM client abstractions & fallback handlers
│   │   ├── ai_question_generator.py     # Gemini adaptive MCQ generation
│   │   ├── badge_checker.py             # Gamification milestones & achievement unlocks
│   │   ├── career_assistant.py          # Grounded career dialogue agent
│   │   ├── career_recommender.py        # Multi-track career fit & trajectory comparison
│   │   ├── career_requirements_generator.py # Dynamic career skill generation via LLM
│   │   ├── github_api.py                # Practical repository recommendation integration
│   │   ├── interview_simulator.py       # 5-category technical & behavioral interview engine
│   │   ├── job_matcher.py               # Transferable skill affinity & match scoring
│   │   ├── progress_tracker.py          # Historical checkpoint & trajectory logger
│   │   ├── question_bank_manager.py     # Local cache & question deduplication manager
│   │   ├── rag_engine.py                # 128-d deterministic embedding RAG orchestrator
│   │   ├── resume_parser.py             # Binary document extraction pipeline
│   │   ├── roadmap_generator.py         # Day-by-day dynamic study plan generator
│   │   ├── skill_extractor.py           # Section-aware heuristic confidence extractor
│   │   ├── skill_gap_analyzer.py        # Skill gap breakdown & prerequisite resolver
│   │   ├── youtube_api.py               # Curated instructional media retrieval
│   │   ├── job_discovery/               # Real-time job ingestion & regional prioritizer
│   │   └── resume_optimizer/            # ATS Studio analyzer, STAR/XYZ enhancer & exporter
│   ├── test_complete_feature_suite.py   # Complete 34-subsystem automated test harness
│   └── test_rag_pipeline.py             # Vector store & tenant isolation verification
├── frontend/
│   ├── package.json                     # Frontend dependencies & npm scripts
│   ├── tailwind.config.js               # Design system & dark-mode color scheme
│   └── src/
│       ├── components/                  # Reusable UI widgets, badges, navigation
│       ├── pages/                       # Dashboard, SkillGap, Roadmap, FedViz, ATSStudio
│       └── services/                    # Axios API wrappers (authService, skillService)
├── pyrightconfig.json                   # Python typing & workspace configuration
└── README.md                            # Comprehensive research documentation
```

---

## 🚀 Reproducibility & Installation Guide

### Prerequisites
- **Python**: Version `3.11` or `3.12`
- **Node.js**: Version `18.x` or higher with `npm`
- **Git**

### Step 1: Clone the Repository
```bash
git clone https://github.com/AYSHA-GITT/skillbridge.git
cd skillbridge
```

### Step 2: Configure Environment Variables
Copy the documented template and fill in your own values:
```bash
cp backend/.env.example backend/.env
```
Minimum for local use: `DATABASE_URL`, `SECRET_KEY`. Job discovery needs Adzuna and/or Jooble credentials (see "Required credentials" below). A free Gemini API key can be generated via [Google AI Studio](https://aistudio.google.com/).

### Step 3: Backend Setup & Database Migration
```powershell
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate # macOS/Linux

cd backend
pip install -r requirements.txt
flask --app app db upgrade                         # creates / upgrades the schema (safe to re-run)
flask --app app users make-admin you@example.com   # optional: grant admin to an existing account
python app.py                                      # API at http://127.0.0.1:5000
```

### Step 4: Frontend
```powershell
cd frontend
npm install
npm start                           # http://localhost:3000
```

### Step 5: Job synchronization worker
```powershell
cd backend
python job_worker.py                # syncs immediately if due, then every 2 hours
```

### Step 6: Tests
The isolated suites use a temporary database and fake providers (no network, dev data untouched):
```powershell
cd backend
python -m unittest discover -s tests -v
```
The older `test_*.py` files in `backend/` run against the database configured in `.env` (and some call the running server).

---

## 🔄 Live Job Discovery & Two-Hour Synchronization

```
Adzuna ---+                                                         +-- JobListing (status, freshness, salary, provenance)
Jooble ---+--> fetch (budgeted, retried) --> normalize/validate --> upsert + dedup --+-- JobSyncRun (per-provider results, errors)
Arbeitnow-+         ^                                                |            +-- JobAlertMatch (alerts, once per job)
            DB lease (one run at a time)                     expiry / staleness
```

**Schedule.** A run is due 2 h after the previous run started (20 min after a failed run). The schedule lives in the database (`job_sync_runs`), so it survives restarts and deploys. Every run first takes the `job_sync` database lease, so scheduled, manual and CLI runs can never overlap; a concurrent attempt is recorded as `skipped`. A crashed run's lease expires after 30 min.

**Providers.** Each provider gets a per-run request budget (Jooble's free plan allows 100 requests/day, so 8 per run x 12 runs). The search plan (target roles x Bengaluru, Mangaluru, Karnataka, Udupi, Bhatkal, India, other hubs, remote, plus students' own target careers and alert roles) is sliced and rotated across runs. Auth errors and HTTP 429 stop that provider for the run; timeouts and 5xx are retried with exponential backoff. Unconfigured providers are reported as `not_configured`.

**Data quality.** Listings without a valid URL, title, company or a meaningful description are rejected with a counted reason. Nothing is invented: no default skills, no fake URLs, and posting dates stay empty when the provider gives none (re-fetching never makes an old job look new). Skills are split into required vs preferred from the description wording.

**Deduplication.** Same provider id or canonical URL: same listing (updated). Same title + company + city from a *different* provider: stored with attribution but flagged `duplicate_of` and hidden from search. Distinct vacancies are never merged.

**Freshness.** `last_verified_at` is set only when the source returns the listing. Labels: *Checked < 24h ago*, *Not re-checked recently* (absent from searches for 72 h), *Expired / archived* (deadline passed, posted more than 60 days ago, or absent for 21 days, labelled "likely closed; not confirmed by the source"). Absence-based rules apply only while the provider itself is healthy, so outages never expire listings. Rows are archived, never deleted.

### Running the scheduler in production
Pick one (combining them is safe because of the lease):

| Option | Command | When |
|---|---|---|
| Worker process | `python job_worker.py` | Always-on hosts, Docker, VMs, a Render/Railway background worker |
| Platform cron | `*/15 * * * *  flask --app app jobs sync-if-due` | Hosts with cron jobs, GitHub Actions, systemd timers; exits immediately unless due |
| In-process thread | `RUN_JOB_SCHEDULER_IN_PROCESS=1` | Local development only (web processes may sleep or scale) |

Useful commands: `flask --app app jobs status`, `flask --app app jobs sync`.

### Required credentials
| Variable | Needed for | How to get it |
|---|---|---|
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | Adzuna (India listings) | Register at developer.adzuna.com. Confirm India (`in`) support and the daily quota of your plan, then set `JOB_ADZUNA_MAX_REQUESTS_PER_RUN` accordingly. |
| `JOOBLE_API_KEY`, `JOOBLE_API_HOST` | Jooble | Request a key at jooble.org/api/about. Keys are country-domain specific (a jooble.org key returns US jobs only); request one for the Indian domain. |
| none | Arbeitnow | Public API; mostly Europe-based roles, so only remote roles are kept by default. |

Without Adzuna or Jooble credentials the system runs, but Indian listings will not appear; it does not substitute demo data.

---

## 📡 RESTful API Specification

### 1. Identity & RBAC Endpoints (`/api/auth`)
- `POST /api/auth/register` — Registers student account with academic metadata.
- `POST /api/auth/login` — Establishes cookie-backed authenticated session.
- `POST /api/auth/logout` — Terminates active session.
- `GET /api/auth/me` — Returns authenticated user profile, role, and readiness score.

### 2. Assessment & Remediation Endpoints (`/api/student`)
- `POST /api/student/upload_resume` — Accepts multipart PDF/DOCX resume file.
- `POST /api/student/parse_resume/<id>` — Extracts raw text and section segmentation.
- `POST /api/student/extract_skills/<id>` — Computes multi-section confidence heuristics.
- `GET /api/student/skills` — Returns student skills categorized by verification state.
- `GET /api/student/get_quiz/<skill_id>` — Generates difficulty-calibrated assessment.
- `POST /api/student/submit_quiz/<skill_id>` — Evaluates answers and updates readiness.
- `POST /api/student/set_target_career` — Updates target professional track.
- `POST /api/student/analyze_skill_gap` — Calculates core and optional competency gaps.
- `POST /api/student/generate_roadmap` — Generates personalized day-by-day learning schedule.
- `GET /api/student/get_roadmap` — Retrieves active learning roadmap with resource links.
- `POST /api/student/simulate_salary` — Simulates incremental return on target skills.
- `POST /api/student/ask_assistant` — Grounded Q&A via multi-tenant vector RAG engine.
- `GET /api/student/jobs` — Search jobs. Params: `query, opportunity=job|internship, entry_level, experience_max, location, work_arrangement, salary_min, job_type, skill, company, date_posted=24h|3d|7d|30d, domain, region, sort=relevance|recent|match|salary, page, per_page`.
- `GET /api/student/jobs/<id>/match` — Explainable fit score with reasons.
- `GET|PUT /api/student/job_preferences` — Roles, locations, work modes, experience.
- `GET|POST /api/student/job_alerts`, `PUT|DELETE /api/student/job_alerts/<id>` — Manage alerts.
- `GET /api/student/job_alerts/notifications`, `POST .../notifications/read` — In-app alert matches.

### 3. ATS Studio & Career Optimization (`/api/student/resume_optimizer`)
- `POST /api/student/resume_optimizer/analyze` — Computes deterministic ATS match score.
- `POST /api/student/resume_optimizer/export_pdf` — Compiles optimized resume to PDF.
- `POST /api/student/resume_optimizer/export_docx` — Compiles optimized resume to Word DOCX.

### 4. Federated Intelligence & Administration (`/api/admin`)
- `GET /api/admin/stats` — Platform-wide cohort averages and macro gap analytics.
- `GET /api/admin/federated/nodes` — Lists participating institutional client nodes.
- `GET /api/admin/federated/rounds` — Retrieves round-by-round convergence telemetry.
- `POST /api/admin/federated/train` — Runs one simulated FedAvg round.
- `GET /api/admin/jobs/overview` — Job counts, provider health, schedule, recent runs.
- `POST /api/admin/jobs/sync` — Manual sync (409 if a run is in progress).
- `GET /api/admin/jobs/runs`, `GET /api/admin/audit_logs`, `GET /api/admin/system/health`.

---

## 🛡️ Data Privacy, Security & Ethical Compliance

- **Where data lives:** uploaded resumes, extracted skills and quiz results are stored on the SkillBridge server/database so they can be analysed. Students can export or permanently delete their data (`/api/student/account/export`, `/account/delete`).
- **Access control:** every student endpoint is scoped to the logged-in account; job alerts and preferences cannot be read or changed across accounts (covered by tests). Self-registration always creates a *student*; admins are granted with `flask --app app users make-admin`.
- **Tenant-isolated retrieval:** private documents in the assistant's store are only searchable by their owner.
- **Secrets:** provider keys live in server-side environment variables and are never sent to the frontend or written into error messages.
- **Audit log:** manual syncs and admin grants are recorded in `audit_logs`.
- **Federated learning:** a simulation on synthetic data with update clipping and Gaussian noise; no formal differential-privacy guarantee is claimed.
- **Compliance:** this project has not been audited for FERPA, GDPR or any other regulation; institutions deploying it must perform their own assessment.

---

## 📚 Citation & Academic Reference

If you utilize SkillBridge, its algorithmic formulations, or experimental methodologies in your research, please cite this work as follows:

```bibtex
@article{skillbridge2026,
  title={SkillBridge: A Privacy-Preserving Federated Intelligence and Adaptive Verification Framework for Career Gap Remediation},
  author={Aysha and Contributors},
  journal={arXiv preprint / Technical Report},
  year={2026},
  url={https://github.com/AYSHA-GITT/skillbridge}
}
```

```text
Aysha et al., "SkillBridge: A Privacy-Preserving Federated Intelligence and Adaptive Verification Framework for Career Gap Remediation," GitHub Repository, 2026. [Online]. Available: https://github.com/AYSHA-GITT/skillbridge
```

---

## 📄 License & Acknowledgments

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for complete terms.

**Acknowledgments**:
- The [Flower Federated Learning Framework](https://flower.ai/) for decentralized model aggregation primitives.
- [Google AI Studio](https://ai.google.dev/) for access to the Gemini family of foundational models.
- The open-source scientific Python community (`scikit-learn`, `numpy`, `pandas`, `PyMuPDF`).
q