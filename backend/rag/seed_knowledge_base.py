import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB_DIR = os.path.join(BASE_DIR, 'data', 'knowledge_base')
CAREERS_DIR = os.path.join(KB_DIR, 'careers')
JD_DIR = os.path.join(KB_DIR, 'job_descriptions')
SKILLS_DIR = os.path.join(KB_DIR, 'skills')

def ensure_dirs():
    os.makedirs(CAREERS_DIR, exist_ok=True)
    os.makedirs(JD_DIR, exist_ok=True)
    os.makedirs(SKILLS_DIR, exist_ok=True)

CAREERS = [
    {
        "career_id": "data_analyst",
        "title": "Data Analyst",
        "industry_domain": "Business Intelligence & Data Analytics",
        "description": "Translates quantitative data into actionable business intelligence. Uses SQL for database querying, Python/R and Excel for statistical analysis, and Tableau/Power BI for executive dashboard visualizations.",
        "experience_level": "Entry to Mid Level",
        "required_skills": ["sql", "excel", "python", "power bi", "tableau", "statistics"],
        "nice_to_have_skills": ["pandas", "numpy", "data visualization", "r", "communication", "etl"],
        "responsibilities": [
            "Query complex relational databases using advanced SQL joins, CTEs, and window functions.",
            "Build automated Power BI and Tableau dashboards for cross-functional stakeholders.",
            "Cleanse and transform unstructured datasets using Python Pandas and Excel Power Query.",
            "Perform statistical hypothesis testing, cohort analysis, and retention metrics calculation."
        ],
        "source": "IEEE Computer Society Industry Career Benchmark: Data Analytics 2026"
    },
    {
        "career_id": "data_scientist",
        "title": "Data Scientist",
        "industry_domain": "Artificial Intelligence & Predictive Modeling",
        "description": "Designs and trains predictive machine learning models, statistical algorithms, and data pipelines to solve complex business problems from large structured and unstructured datasets.",
        "experience_level": "Mid to Senior Level",
        "required_skills": ["python", "sql", "machine learning", "statistics", "pandas", "numpy"],
        "nice_to_have_skills": ["tensorflow", "pytorch", "scikit-learn", "tableau", "power bi", "deep learning", "nlp"],
        "responsibilities": [
            "Develop end-to-end predictive machine learning pipelines using Scikit-Learn, XGBoost, and PyTorch.",
            "Formulate statistical experiments, A/B testing frameworks, and feature engineering strategies.",
            "Query large-scale data warehouses using SQL to extract training and validation datasets.",
            "Deploy inference models into production environments with monitoring and drift detection."
        ],
        "source": "ACM Computing Classification System: Data Science Framework 2026"
    },
    {
        "career_id": "software_engineer",
        "title": "Software Engineer",
        "industry_domain": "Software Development & Systems Engineering",
        "description": "Designs, writes, tests, and maintains robust software systems, backend APIs, and scalable algorithmic services utilizing core object-oriented principles, data structures, and version control.",
        "experience_level": "Entry to Senior Level",
        "required_skills": ["python", "java", "sql", "git", "data structures", "algorithms"],
        "nice_to_have_skills": ["flask", "react", "docker", "aws", "rest api", "unit testing", "c++"],
        "responsibilities": [
            "Design modular, object-oriented software architectures with robust data structures and algorithms.",
            "Implement high-throughput RESTful APIs, database transactions, and backend business logic.",
            "Collaborate through Git branching workflows, pull requests, automated CI/CD pipelines, and peer code reviews.",
            "Write comprehensive unit and integration tests to ensure system reliability and regression prevention."
        ],
        "source": "ISO/IEC 12207 Software Engineering Lifecycle Industry Standards"
    },
    {
        "career_id": "web_developer",
        "title": "Web Developer",
        "industry_domain": "Frontend Web Technologies",
        "description": "Builds responsive, accessible, and dynamic user interfaces using modern HTML, CSS, JavaScript, and frontend frameworks like React, following progressive disclosure and mobile-first principles.",
        "experience_level": "Entry to Mid Level",
        "required_skills": ["html", "css", "javascript", "react", "git"],
        "nice_to_have_skills": ["flask", "node.js", "mongodb", "tailwind css", "responsive design", "typescript"],
        "responsibilities": [
            "Build interactive, accessible client-side single page applications using React and modern JavaScript.",
            "Translate UI/UX wireframes into responsive Tailwind CSS / vanilla CSS components across mobile and desktop.",
            "Integrate client-side states with asynchronous REST APIs using Axios or fetch.",
            "Manage code versions, issue tracking, and deployment branches using Git and GitHub."
        ],
        "source": "W3C Front-End Web Engineering Competency Standard 2026"
    },
    {
        "career_id": "full_stack_developer",
        "title": "Full Stack Developer",
        "industry_domain": "End-to-End Application Engineering",
        "description": "Engineers both client-facing dynamic interfaces and server-side logic, managing relational/NoSQL databases, authentication sessions, and containerized deployments.",
        "experience_level": "Mid to Senior Level",
        "required_skills": ["html", "css", "javascript", "react", "node.js", "sql", "git"],
        "nice_to_have_skills": ["docker", "mongodb", "aws", "typescript", "flask", "redis", "ci/cd"],
        "responsibilities": [
            "Architect and build responsive frontend user interfaces with React, state management, and modern CSS.",
            "Develop secure backend API endpoints, authentication middlewares, and session management systems.",
            "Design database schemas, indexes, and optimized query transactions in SQL and NoSQL engines.",
            "Containerize microservices using Docker and orchestrate deployment to cloud infrastructure."
        ],
        "source": "Open Web Application Security Project (OWASP) & Full Stack Curriculum Benchmark"
    },
    {
        "career_id": "devops_engineer",
        "title": "DevOps Engineer",
        "industry_domain": "Infrastructure & Continuous Delivery",
        "description": "Automates continuous integration, continuous delivery (CI/CD), infrastructure as code (IaC), container orchestration, and server monitoring across cloud environments.",
        "experience_level": "Mid to Senior Level",
        "required_skills": ["linux", "git", "docker", "kubernetes", "ci/cd", "bash"],
        "nice_to_have_skills": ["aws", "terraform", "ansible", "monitoring", "python", "helm"],
        "responsibilities": [
            "Construct robust GitHub Actions or GitLab CI/CD build, test, and release automation pipelines.",
            "Containerize backend services using Docker and manage distributed clusters with Kubernetes.",
            "Provision and maintain scalable cloud infrastructure using Terraform and AWS services.",
            "Maintain high system availability with proactive Prometheus, Grafana, and ELK monitoring stacks."
        ],
        "source": "Cloud Native Computing Foundation (CNCF) DevOps Professional Standard"
    },
    {
        "career_id": "machine_learning_engineer",
        "title": "Machine Learning Engineer",
        "industry_domain": "Applied ML & MLOps",
        "description": "Bridges the gap between data science experimentation and production software engineering by building scalable training pipelines, model registries, and inference APIs.",
        "experience_level": "Mid to Senior Level",
        "required_skills": ["python", "machine learning", "deep learning", "pytorch", "docker", "sql"],
        "nice_to_have_skills": ["tensorflow", "scikit-learn", "mlflow", "kubernetes", "aws", "fastapi", "git"],
        "responsibilities": [
            "Scale model training across distributed GPU environments using PyTorch and PyTorch Lightning.",
            "Serve low-latency real-time and batch model inference endpoints using FastAPI, Docker, and ONNX.",
            "Establish automated MLOps pipelines with MLflow for experiment tracking, model registry, and versioning.",
            "Implement differential privacy, model monitoring, data drift alarms, and continuous retraining."
        ],
        "source": "IEEE Computer Society Artificial Intelligence & Machine Learning Benchmark 2026"
    },
    {
        "career_id": "cloud_architect",
        "title": "Cloud Architect",
        "industry_domain": "Enterprise Cloud Infrastructure",
        "description": "Designs resilient, fault-tolerant, cost-effective cloud architectures and hybrid multi-cloud migrations following the Well-Architected Framework.",
        "experience_level": "Senior Level",
        "required_skills": ["aws", "linux", "docker", "kubernetes", "networking", "terraform"],
        "nice_to_have_skills": ["azure", "gcp", "security", "python", "serverless", "microservices"],
        "responsibilities": [
            "Architect high-availability multi-region cloud infrastructures across AWS VPC, EC2, S3, and RDS.",
            "Define security boundaries, IAM role policies, encryption at rest/transit, and compliance baselines.",
            "Automate enterprise cloud deployments with reusable Terraform and CloudFormation IaC modules.",
            "Optimize resource allocation, auto-scaling policies, and cloud cost management."
        ],
        "source": "AWS Well-Architected Framework & Enterprise Architecture Benchmark"
    },
    {
        "career_id": "cybersecurity_analyst",
        "title": "Cybersecurity Analyst",
        "industry_domain": "Information Security & Security Operations",
        "description": "Monitors networks for security breaches, investigates suspicious incidents, performs vulnerability assessments, and implements defense-in-depth security controls.",
        "experience_level": "Entry to Mid Level",
        "required_skills": ["networking", "linux", "python", "wireshark", "security", "git"],
        "nice_to_have_skills": ["siem", "splunk", "ethical hacking", "cryptography", "bash", "incident response"],
        "responsibilities": [
            "Monitor SIEM security event logs, IDS/IPS alerts, and system anomalies across corporate networks.",
            "Conduct vulnerability scans, risk assessments, and patch management verification.",
            "Triage security incident escalations, containment procedures, and root-cause post-mortems.",
            "Validate compliance with NIST, ISO 27001, and privacy regulations."
        ],
        "source": "NIST National Initiative for Cybersecurity Education (NICE) Framework 2026"
    }
]

JOB_DESCRIPTIONS = [
    {
        "job_id": "jd_fintech_data_analyst",
        "company": "FinTech Capital Global",
        "role": "Junior Data Analyst",
        "location": "Bengaluru / Remote",
        "salary_range": "6 - 9 LPA",
        "career_category": "data analyst",
        "description": "We are seeking a detail-oriented Data Analyst to join our quantitative risk team. You will query transaction records, design real-time portfolio dashboards, and synthesize trends for executive leadership.",
        "required_skills": ["sql", "python", "excel", "power bi", "statistics"],
        "preferred_skills": ["pandas", "tableau", "communication"],
        "responsibilities": "Query financial transaction databases using PostgreSQL; develop interactive executive risk dashboards in Power BI; prepare weekly executive metric summaries; perform cohort and retention analysis.",
        "source": "FinTech Capital Global Placement Board 2026 - JD #DA-104"
    },
    {
        "job_id": "jd_healthtech_data_scientist",
        "company": "PulseHealth Analytics",
        "role": "Associate Data Scientist",
        "location": "Hyderabad / Hybrid",
        "salary_range": "8 - 14 LPA",
        "career_category": "data scientist",
        "description": "PulseHealth is looking for an Associate Data Scientist to build clinical risk prediction models and analyze patient health outcomes using advanced statistical techniques and machine learning.",
        "required_skills": ["python", "machine learning", "sql", "pandas", "numpy", "statistics"],
        "preferred_skills": ["pytorch", "scikit-learn", "data visualization"],
        "responsibilities": "Clean and preprocess large electronic medical records; train predictive classifiers using Scikit-Learn and XGBoost; perform feature selection and cross-validation; present statistical insights to clinical directors.",
        "source": "PulseHealth Analytics Careers - Job Posting #DS-882"
    },
    {
        "job_id": "jd_saas_fullstack_dev",
        "company": "CloudForge Software",
        "role": "Full Stack Software Engineer",
        "location": "Pune / Remote",
        "salary_range": "7 - 12 LPA",
        "career_category": "full stack developer",
        "description": "Join our fast-growing B2B SaaS platform engineering team. You will build user-facing React dashboards and robust backend REST APIs using Python and Node.js.",
        "required_skills": ["javascript", "react", "python", "sql", "git", "html", "css"],
        "preferred_skills": ["docker", "flask", "aws", "typescript"],
        "responsibilities": "Develop modular responsive React components; design secure REST API endpoints in Python / Flask; optimize SQL queries and database schemas; write automated tests and participate in sprint code reviews.",
        "source": "CloudForge Engineering Recruitment - Ref #FS-319"
    },
    {
        "job_id": "jd_ecommerce_devops_eng",
        "company": "SwiftKart Technologies",
        "role": "DevOps & Cloud Automation Engineer",
        "location": "Bengaluru / On-site",
        "salary_range": "9 - 15 LPA",
        "career_category": "devops engineer",
        "description": "SwiftKart is hiring a DevOps Engineer to manage high-traffic e-commerce microservices infrastructure. Focus on container orchestration, automated release pipelines, and cloud reliability.",
        "required_skills": ["linux", "docker", "kubernetes", "git", "ci/cd", "bash"],
        "preferred_skills": ["aws", "terraform", "monitoring", "python"],
        "responsibilities": "Maintain Kubernetes production clusters; build automated CI/CD pipelines in GitHub Actions; manage Docker container registries; monitor server latency with Prometheus and Grafana.",
        "source": "SwiftKart Infrastructure Hiring Portal - Req #DO-550"
    },
    {
        "job_id": "jd_edtech_software_engineer",
        "company": "EduLearn Systems",
        "role": "Software Engineer (Backend)",
        "location": "Gurugram / Hybrid",
        "salary_range": "7 - 11 LPA",
        "career_category": "software engineer",
        "description": "We are seeking a Backend Software Engineer with strong algorithmic foundations in Python/Java to power our live educational platform and interactive student assessment systems.",
        "required_skills": ["python", "java", "data structures", "algorithms", "sql", "git"],
        "preferred_skills": ["flask", "docker", "rest api", "unit testing"],
        "responsibilities": "Develop scalable backend services with optimal time and space complexity; implement database transactions and indexing; maintain automated testing suites; review code and collaborate with frontend developers.",
        "source": "EduLearn Systems Job Requisition #SE-204"
    },
    {
        "job_id": "jd_ai_ml_engineer",
        "company": "CognitiveAI Labs",
        "role": "Machine Learning Engineer (NLP / CV)",
        "location": "Bengaluru / Remote",
        "salary_range": "10 - 18 LPA",
        "career_category": "machine learning engineer",
        "description": "CognitiveAI Labs is expanding its foundational AI team. Build, fine-tune, and deploy transformer models and computer vision pipelines into scalable production endpoints.",
        "required_skills": ["python", "machine learning", "deep learning", "pytorch", "docker", "sql"],
        "preferred_skills": ["transformers", "fastapi", "aws", "kubernetes"],
        "responsibilities": "Fine-tune pretrained deep learning and transformer models; deploy low-latency inference containers; build data preprocessing pipelines; evaluate model performance and monitor for data drift.",
        "source": "CognitiveAI Labs Research & Engineering - Job #ML-772"
    }
]

SKILL_DEFINITIONS = {
    "python": {
        "canonical_name": "python",
        "category": "Programming Languages",
        "definition": "High-level, interpreted programming language widely used for machine learning, data analysis, web backend APIs, and automation.",
        "synonyms": ["py", "python3", "python programming"],
        "key_ecosystem": ["pandas", "numpy", "scikit-learn", "flask", "fastapi", "django", "pytorch"]
    },
    "sql": {
        "canonical_name": "sql",
        "category": "Databases & Querying",
        "definition": "Standard domain-specific language for storing, querying, manipulating, and retrieving relational data across enterprise databases.",
        "synonyms": ["structured query language", "postgresql", "mysql", "sqlite", "tsql"],
        "key_ecosystem": ["joins", "indexes", "ctes", "window functions", "stored procedures"]
    },
    "machine learning": {
        "canonical_name": "machine learning",
        "category": "Artificial Intelligence",
        "definition": "Branch of artificial intelligence focusing on algorithms that learn patterns from training data to make predictions or decisions without explicit programming.",
        "synonyms": ["ml", "statistical learning", "predictive modeling"],
        "key_ecosystem": ["scikit-learn", "xgboost", "regression", "classification", "clustering", "cross-validation"]
    },
    "react": {
        "canonical_name": "react",
        "category": "Frontend Frameworks",
        "definition": "Declarative, component-based JavaScript library developed by Meta for building dynamic, reactive user interfaces and single page applications.",
        "synonyms": ["react.js", "reactjs"],
        "key_ecosystem": ["jsx", "hooks", "virtual dom", "react router", "redux", "state management"]
    },
    "docker": {
        "canonical_name": "docker",
        "category": "DevOps & Containers",
        "definition": "OS-level virtualization platform for packaging software applications and their exact dependencies into isolated, reproducible containers.",
        "synonyms": ["containerization", "containers", "dockerfile"],
        "key_ecosystem": ["docker-compose", "container image", "docker hub", "kubernetes"]
    },
    "git": {
        "canonical_name": "git",
        "category": "Developer Tools & Version Control",
        "definition": "Distributed version control system for tracking changes in source code during software development, enabling branching, merging, and collaboration.",
        "synonyms": ["version control", "github", "gitlab"],
        "key_ecosystem": ["commit", "branch", "pull request", "merge", "rebase"]
    },
    "power bi": {
        "canonical_name": "power bi",
        "category": "Business Intelligence & Visualization",
        "definition": "Microsoft business analytics service providing interactive visualizations and business intelligence capabilities with an interface for reports.",
        "synonyms": ["powerbi", "microsoft power bi", "dax"],
        "key_ecosystem": ["power query", "dax", "data modeling", "reports", "dashboards"]
    },
    "tableau": {
        "canonical_name": "tableau",
        "category": "Business Intelligence & Visualization",
        "definition": "Visual analytics platform transforming raw data into intuitive, interactive dashboards, visual charts, and exploratory business reports.",
        "synonyms": ["tableau desktop", "tableau public"],
        "key_ecosystem": ["calculated fields", "parameters", "visual dashboards", "story points"]
    },
    "aws": {
        "canonical_name": "aws",
        "category": "Cloud Computing",
        "definition": "Amazon Web Services comprehensive cloud computing platform offering compute (EC2), storage (S3), databases (RDS), and serverless architectures.",
        "synonyms": ["amazon web services", "amazon cloud"],
        "key_ecosystem": ["s3", "ec2", "lambda", "iam", "rds", "vpc", "cloudformation"]
    },
    "kubernetes": {
        "canonical_name": "kubernetes",
        "category": "DevOps & Containers",
        "definition": "Open-source container orchestration platform for automating deployment, scaling, and management of containerized applications.",
        "synonyms": ["k8s", "container orchestration"],
        "key_ecosystem": ["pods", "deployments", "services", "helm", "ingress", "cluster"]
    },
    "data structures": {
        "canonical_name": "data structures",
        "category": "Computer Science Fundamentals",
        "definition": "Specialized formats for organizing, processing, retrieving, and storing data efficiently in memory (arrays, linked lists, trees, graphs, hash tables).",
        "synonyms": ["dsa", "data structures and algorithms"],
        "key_ecosystem": ["arrays", "hashmaps", "trees", "graphs", "stacks", "queues"]
    },
    "algorithms": {
        "canonical_name": "algorithms",
        "category": "Computer Science Fundamentals",
        "definition": "Step-by-step procedures or formulas for solving problems and computational tasks with defined time and space complexities.",
        "synonyms": ["sorting", "searching", "dynamic programming", "graph algorithms"],
        "key_ecosystem": ["time complexity", "big o", "recursion", "dynamic programming", "binary search"]
    }
}

def seed():
    ensure_dirs()
    print("Writing career benchmarks...")
    for career in CAREERS:
        filepath = os.path.join(CAREERS_DIR, f"{career['career_id']}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(career, f, indent=2)
        print(f" - Saved {career['title']} -> {filepath}")

    print("Writing job descriptions...")
    for jd in JOB_DESCRIPTIONS:
        filepath = os.path.join(JD_DIR, f"{jd['job_id']}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(jd, f, indent=2)
        print(f" - Saved {jd['role']} ({jd['company']}) -> {filepath}")

    print("Writing skill definitions...")
    skills_file = os.path.join(SKILLS_DIR, "skill_definitions.json")
    with open(skills_file, 'w', encoding='utf-8') as f:
        json.dump(SKILL_DEFINITIONS, f, indent=2)
    print(f" - Saved {len(SKILL_DEFINITIONS)} skill definitions -> {skills_file}")

    print("Knowledge base seeded successfully!")

if __name__ == '__main__':
    seed()
