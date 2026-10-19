from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from utils.job_discovery.base_adapter import JobSourceAdapter


class CuratedSampleAdapter(JobSourceAdapter):
    """
    Curated baseline opportunity adapter providing high-fidelity, clearly-labeled
    benchmark internships and junior positions aligned with Indian campus & remote tech tracks.
    Labels every listing explicitly as `is_sample=True` with honest source attribution.
    """

    @property
    def source_name(self) -> str:
        return "SkillBridge Curated Benchmark Index"

    @property
    def is_sample_source(self) -> bool:
        return True

    def _get_benchmark_catalog(self) -> List[Dict[str, Any]]:
        now = datetime.utcnow()
        return [
            {
                "external_id": "bench_sde_intern_01",
                "title": "Software Engineering Intern (Backend)",
                "company": "Cognizant Technology Solutions",
                "location": "Bengaluru, Karnataka (Hybrid)",
                "job_type": "Internship",
                "work_arrangement": "Hybrid",
                "domain": "Software Engineering",
                "experience_level": "Internship (Final/Pre-final Year)",
                "description": (
                    "Join our digital engineering practice building microservices in Python and SQL. "
                    "You will work alongside senior engineers implementing RESTful APIs, optimizing query performance, "
                    "and writing unit tests. Great opportunity for engineering students with solid CS fundamentals."
                ),
                "required_skills": ["python", "sql", "git", "data structures", "algorithms"],
                "preferred_skills": ["flask", "docker", "rest api", "postgresql"],
                "eligibility": "B.Tech/BE in CS/IT/ECE (2025/2026 Batch) with 60%+ throughout academics",
                "application_url": "https://careers.cognizant.com",
                "source": self.source_name,
                "is_sample": True,
                "posting_date": now - timedelta(days=2),
                "deadline": now + timedelta(days=28)
            },
            {
                "external_id": "bench_da_intern_02",
                "title": "Junior Data Analyst Trainee",
                "company": "Mu Sigma Analytics",
                "location": "Bengaluru, Karnataka (Onsite)",
                "job_type": "Full-time",
                "work_arrangement": "Onsite",
                "domain": "Data Analytics",
                "experience_level": "Entry-Level (0-1 yrs)",
                "description": (
                    "As a Decision Sciences trainee, you will clean real-world transactional datasets, "
                    "build exploratory business dashboards in Power BI/Tableau, and extract strategic insights using SQL. "
                    "Strong quantitative and statistical comprehension is essential."
                ),
                "required_skills": ["sql", "excel", "python", "power bi", "statistics"],
                "preferred_skills": ["tableau", "pandas", "numpy", "communication"],
                "eligibility": "B.Tech/B.Sc Statistics/Mathematics/BCA graduates with strong logical aptitude",
                "application_url": "https://www.mu-sigma.com/careers",
                "source": self.source_name,
                "is_sample": True,
                "posting_date": now - timedelta(days=4),
                "deadline": now + timedelta(days=21)
            },
            {
                "external_id": "bench_ml_intern_03",
                "title": "Machine Learning Research Intern",
                "company": "Tata Elxsi AI Labs",
                "location": "Hyderabad, Telangana (Remote)",
                "job_type": "Internship",
                "work_arrangement": "Remote",
                "domain": "Machine Learning & AI",
                "experience_level": "Internship (6 Months)",
                "description": (
                    "Assist in developing predictive maintenance and computer vision pipelines. "
                    "Responsibilities include dataset augmentation, fine-tuning baseline models using PyTorch/Scikit-Learn, "
                    "and validating model convergence on edge GPU nodes."
                ),
                "required_skills": ["python", "machine learning", "statistics", "pandas", "numpy"],
                "preferred_skills": ["pytorch", "deep learning", "docker", "git"],
                "eligibility": "BE/B.Tech/M.Tech with completed coursework in Linear Algebra and ML",
                "application_url": "https://tataelxsi.com/careers",
                "source": self.source_name,
                "is_sample": True,
                "posting_date": now - timedelta(days=1),
                "deadline": now + timedelta(days=35)
            },
            {
                "external_id": "bench_web_dev_04",
                "title": "Junior Full Stack Developer",
                "company": "ThoughtWorks India",
                "location": "Pune, Maharashtra (Hybrid)",
                "job_type": "Full-time",
                "work_arrangement": "Hybrid",
                "domain": "Web Development",
                "experience_level": "Entry-Level (0-2 yrs)",
                "description": (
                    "Build intuitive, accessible web interfaces in React and connect them with modern Node/Python backend APIs. "
                    "Practices extreme programming (XP), pair programming, and continuous integration with clean architecture."
                ),
                "required_skills": ["javascript", "react", "html", "css", "git"],
                "preferred_skills": ["node.js", "tailwind css", "rest api", "docker"],
                "eligibility": "B.Tech/BCA/MCA/Any Graduate with demonstrable full-stack portfolio projects",
                "application_url": "https://www.thoughtworks.com/careers",
                "source": self.source_name,
                "is_sample": True,
                "posting_date": now - timedelta(days=3),
                "deadline": now + timedelta(days=15)
            },
            {
                "external_id": "bench_cloud_devops_05",
                "title": "Cloud & DevOps Associate Intern",
                "company": "Wipro Cloud Practice",
                "location": "Chennai, Tamil Nadu (Remote)",
                "job_type": "Internship",
                "work_arrangement": "Remote",
                "domain": "Cloud & DevOps",
                "experience_level": "Internship (3-6 Months)",
                "description": (
                    "Support cloud infrastructure automation and deployment pipelines on AWS/Linux. "
                    "Containerize legacy modules using Docker, author GitHub Actions CI workflows, and monitor server health."
                ),
                "required_skills": ["linux", "git", "python", "networking", "cloud"],
                "preferred_skills": ["aws", "docker", "kubernetes", "ci/cd"],
                "eligibility": "B.Tech CS/IT/Electronics with foundational Linux command-line skills",
                "application_url": "https://careers.wipro.com",
                "source": self.source_name,
                "is_sample": True,
                "posting_date": now - timedelta(days=5),
                "deadline": now + timedelta(days=40)
            },
            {
                "external_id": "bench_cyber_analyst_06",
                "title": "Information Security & SOC Analyst Intern",
                "company": "Infosys Cyber Defense Center",
                "location": "Bengaluru, Karnataka (Onsite)",
                "job_type": "Internship",
                "work_arrangement": "Onsite",
                "domain": "Cybersecurity",
                "experience_level": "Internship",
                "description": (
                    "Monitor security events, triage intrusion detection alerts, and assist in vulnerability assessments. "
                    "Participate in threat intelligence analysis and compliance reporting across distributed campus networks."
                ),
                "required_skills": ["linux", "networking", "python", "cryptography"],
                "preferred_skills": ["wireshark", "ethical hacking", "sql", "owasp"],
                "eligibility": "Final-year students with basic understanding of TCP/IP, OSI model, and security fundamentals",
                "application_url": "https://www.infosys.com/careers",
                "source": self.source_name,
                "is_sample": True,
                "posting_date": now - timedelta(days=6),
                "deadline": now + timedelta(days=20)
            },
            {
                "external_id": "bench_razorpay_sde_07",
                "title": "Graduate Software Engineer Trainee",
                "company": "Razorpay Software",
                "location": "Bengaluru, Karnataka (Hybrid)",
                "job_type": "Full-time",
                "work_arrangement": "Hybrid",
                "domain": "Software Engineering",
                "experience_level": "Entry-Level (0-1 yrs)",
                "description": (
                    "Join our payment infrastructure engineering team. You will build high-concurrency payment APIs, "
                    "optimize database transactions, and implement idempotent microservices handling millions of daily requests."
                ),
                "required_skills": ["python", "sql", "rest api", "git", "data structures"],
                "preferred_skills": ["docker", "redis", "go", "postgresql"],
                "eligibility": "BE/B.Tech in CS/IT (2025/2026 Batch) with passion for high-scale distributed systems",
                "application_url": "https://razorpay.com/jobs",
                "source": self.source_name,
                "is_sample": True,
                "posting_date": now - timedelta(hours=8),
                "deadline": now + timedelta(days=25)
            },
            {
                "external_id": "bench_zoho_sde_08",
                "title": "Associate Software Developer",
                "company": "Zoho Corporation",
                "location": "Tenkasi / Chennai, Tamil Nadu (Onsite)",
                "job_type": "Full-time",
                "work_arrangement": "Onsite",
                "domain": "Web Development",
                "experience_level": "Entry-Level",
                "description": (
                    "Engineer scalable SaaS enterprise business applications. Focus on object-oriented system design, "
                    "database query optimization, and frontend responsive application modules for global business customers."
                ),
                "required_skills": ["java", "javascript", "sql", "html", "css"],
                "preferred_skills": ["c++", "linux", "git", "rest api"],
                "eligibility": "Any Engineering or CS graduate with strong problem-solving and algorithmic logic",
                "application_url": "https://www.zoho.com/careers",
                "source": self.source_name,
                "is_sample": True,
                "posting_date": now - timedelta(hours=14),
                "deadline": now + timedelta(days=30)
            },
            {
                "external_id": "bench_flipkart_fe_09",
                "title": "Frontend UI Engineering Intern",
                "company": "Flipkart Internet",
                "location": "Bengaluru, Karnataka (Hybrid)",
                "job_type": "Internship",
                "work_arrangement": "Hybrid",
                "domain": "Web Development",
                "experience_level": "Internship (6 Months)",
                "description": (
                    "Collaborate with the consumer product frontend guild building sub-second web experiences. "
                    "Optimize mobile browser rendering, implement fluid component animations, and maintain high accessibility standards."
                ),
                "required_skills": ["javascript", "react", "html", "css", "git"],
                "preferred_skills": ["typescript", "tailwind css", "webpack", "performance optimization"],
                "eligibility": "B.Tech/BE/BCA students with strong portfolio of React frontend web apps",
                "application_url": "https://www.flipkartcareers.com",
                "source": self.source_name,
                "is_sample": True,
                "posting_date": now - timedelta(hours=20),
                "deadline": now + timedelta(days=18)
            },
            {
                "external_id": "bench_freshworks_cloud_10",
                "title": "Cloud Operations Engineer Trainee",
                "company": "Freshworks",
                "location": "Chennai, Tamil Nadu (Remote)",
                "job_type": "Full-time",
                "work_arrangement": "Remote",
                "domain": "Cloud & DevOps",
                "experience_level": "Entry-Level (0-1 yrs)",
                "description": (
                    "Support multi-region AWS cloud infrastructure automation. Author Terraform templates, manage "
                    "Kubernetes container clusters, and configure Datadog metrics and monitoring dashboards."
                ),
                "required_skills": ["linux", "aws", "docker", "python", "networking"],
                "preferred_skills": ["terraform", "kubernetes", "git", "ci/cd"],
                "eligibility": "Graduates with hands-on coursework in cloud platforms and Linux operating systems",
                "application_url": "https://careers.freshworks.com",
                "source": self.source_name,
                "is_sample": True,
                "posting_date": now - timedelta(days=1),
                "deadline": now + timedelta(days=35)
            },
            {
                "external_id": "bench_swiggy_ds_11",
                "title": "Data Science & Logistics Analyst",
                "company": "Swiggy Tech",
                "location": "Bengaluru, Karnataka (Remote)",
                "job_type": "Full-time",
                "work_arrangement": "Remote",
                "domain": "Data Analytics",
                "experience_level": "Entry-Level (0-2 yrs)",
                "description": (
                    "Analyze high-velocity hyperlocal delivery datasets to optimize delivery fleet routing, forecast surge demand, "
                    "and build predictive models evaluating restaurant preparation delays."
                ),
                "required_skills": ["python", "sql", "pandas", "statistics", "machine learning"],
                "preferred_skills": ["tableau", "numpy", "scikit-learn", "data visualization"],
                "eligibility": "Quantitative background (Engineering, Statistics, Math, Economics) with SQL and Python mastery",
                "application_url": "https://careers.swiggy.com",
                "source": self.source_name,
                "is_sample": True,
                "posting_date": now - timedelta(days=1),
                "deadline": now + timedelta(days=22)
            },
            {
                "external_id": "bench_jio_ai_12",
                "title": "AI & Computer Vision Associate",
                "company": "Reliance Jio Platforms",
                "location": "Navi Mumbai, Maharashtra (Hybrid)",
                "job_type": "Full-time",
                "work_arrangement": "Hybrid",
                "domain": "Machine Learning & AI",
                "experience_level": "Entry-Level (0-2 yrs)",
                "description": (
                    "Build next-generation computer vision and speech recognition AI applications. Develop data annotation pipelines, "
                    "benchmark inference latency on edge hardware, and integrate lightweight ONNX models."
                ),
                "required_skills": ["python", "machine learning", "deep learning", "git"],
                "preferred_skills": ["pytorch", "opencv", "docker", "tensorflow"],
                "eligibility": "B.Tech/M.Tech with demonstrable AI projects in neural networks or vision",
                "application_url": "https://careers.jio.com",
                "source": self.source_name,
                "is_sample": True,
                "posting_date": now - timedelta(days=2),
                "deadline": now + timedelta(days=28)
            },
            {
                "external_id": "bench_cred_be_13",
                "title": "Backend SDE Intern (Go/Python)",
                "company": "CRED Tech",
                "location": "Bengaluru, Karnataka (Onsite)",
                "job_type": "Internship",
                "work_arrangement": "Onsite",
                "domain": "Software Engineering",
                "experience_level": "Internship (6 Months)",
                "description": (
                    "Design ultra-low-latency backend microservices. Implement event-driven architectures with Apache Kafka, "
                    "author fault-tolerant data models, and write bulletproof unit and integration tests."
                ),
                "required_skills": ["python", "sql", "data structures", "algorithms", "git"],
                "preferred_skills": ["go", "kafka", "redis", "docker"],
                "eligibility": "Engineering students with strong problem solving, CS fundamentals, and system design curiosity",
                "application_url": "https://careers.cred.club",
                "source": self.source_name,
                "is_sample": True,
                "posting_date": now - timedelta(days=2),
                "deadline": now + timedelta(days=20)
            },
            {
                "external_id": "bench_phonepe_da_14",
                "title": "Junior Data Analyst (Payments)",
                "company": "PhonePe",
                "location": "Bengaluru, Karnataka (Hybrid)",
                "job_type": "Full-time",
                "work_arrangement": "Hybrid",
                "domain": "Data Analytics",
                "experience_level": "Entry-Level",
                "description": (
                    "Triage merchant settlement reconciliation logs, extract transaction anomaly metrics using BigQuery, "
                    "and deliver automated executive dashboards tracking UPI payment success ratios."
                ),
                "required_skills": ["sql", "excel", "python", "power bi"],
                "preferred_skills": ["tableau", "statistics", "pandas"],
                "eligibility": "Graduates with proven command over relational queries and business dashboard design",
                "application_url": "https://www.phonepe.com/careers",
                "source": self.source_name,
                "is_sample": True,
                "posting_date": now - timedelta(days=3),
                "deadline": now + timedelta(days=24)
            },
            {
                "external_id": "bench_tcs_digital_15",
                "title": "Digital Software Engineer Trainee",
                "company": "Tata Consultancy Services (TCS)",
                "location": "Mumbai / Pune, Maharashtra (Hybrid)",
                "job_type": "Full-time",
                "work_arrangement": "Hybrid",
                "domain": "Software Engineering",
                "experience_level": "Entry-Level (Campus Batch)",
                "description": (
                    "Build cloud-native enterprise microservices in Java and Python. Participate in agile sprint retrospectives, "
                    "perform peer code reviews, and automate test suites for Fortune 500 digital transformation engagements."
                ),
                "required_skills": ["java", "python", "sql", "git", "data structures"],
                "preferred_skills": ["spring boot", "rest api", "cloud"],
                "eligibility": "B.Tech/BE/MCA freshers with solid foundational programming aptitude",
                "application_url": "https://www.tcs.com/careers",
                "source": self.source_name,
                "is_sample": True,
                "posting_date": now - timedelta(days=3),
                "deadline": now + timedelta(days=45)
            },
            {
                "external_id": "bench_zomato_devops_16",
                "title": "Site Reliability & DevOps Associate",
                "company": "Zomato Core Infrastructure",
                "location": "Gurgaon, Delhi NCR (Hybrid)",
                "job_type": "Full-time",
                "work_arrangement": "Hybrid",
                "domain": "Cloud & DevOps",
                "experience_level": "Entry-Level (0-2 yrs)",
                "description": (
                    "Maintain zero-downtime microservice fleet availability during peak dining hours. Deploy automated scaling policies, "
                    "manage Kubernetes pods, and configure Prometheus alerting thresholds."
                ),
                "required_skills": ["linux", "docker", "kubernetes", "python", "git"],
                "preferred_skills": ["aws", "ci/cd", "networking", "terraform"],
                "eligibility": "Passionate systems enthusiasts with practical containerization experience",
                "application_url": "https://www.zomato.com/careers",
                "source": self.source_name,
                "is_sample": True,
                "posting_date": now - timedelta(days=4),
                "deadline": now + timedelta(days=26)
            },
            {
                "external_id": "bench_grab_be_21",
                "title": "Junior Backend Engineer (Microservices)",
                "company": "Grab Holdings",
                "location": "Singapore (Hybrid)",
                "job_type": "Full-time",
                "work_arrangement": "Hybrid",
                "domain": "Software Engineering",
                "experience_level": "Entry-Level (0-2 yrs)",
                "description": (
                    "Join Southeast Asia's leading superapp engineering team. Build robust transaction processing services, "
                    "design distributed caches, and optimize booking pipelines across Singapore, Malaysia, and Indonesia."
                ),
                "required_skills": ["python", "go", "sql", "git", "rest api"],
                "preferred_skills": ["docker", "kafka", "redis", "microservices"],
                "eligibility": "CS/IT degree or equivalent practical backend development experience",
                "application_url": "https://grab.careers",
                "source": self.source_name,
                "is_sample": True,
                "posting_date": now - timedelta(days=1),
                "deadline": now + timedelta(days=30)
            },
            {
                "external_id": "bench_shopee_infra_22",
                "title": "Cloud Platform Systems Engineer",
                "company": "Shopee / Sea Group",
                "location": "Singapore (Remote Asia)",
                "job_type": "Full-time",
                "work_arrangement": "Remote",
                "domain": "Cloud & DevOps",
                "experience_level": "Junior (0-2 yrs)",
                "description": (
                    "Support pan-Asian e-commerce infrastructure scalability. Automate server configuration management, "
                    "implement deployment guardrails, and audit cloud security boundaries."
                ),
                "required_skills": ["linux", "python", "docker", "cloud", "git"],
                "preferred_skills": ["kubernetes", "aws", "networking", "shell scripting"],
                "eligibility": "Proficiency with Unix/Linux environments and distributed systems fundamentals",
                "application_url": "https://careers.shopee.sg",
                "source": self.source_name,
                "is_sample": True,
                "posting_date": now - timedelta(days=2),
                "deadline": now + timedelta(days=28)
            },
            {
                "external_id": "bench_rakuten_data_23",
                "title": "Data Engineering Associate",
                "company": "Rakuten Group",
                "location": "Tokyo, Japan / Bengaluru (Hybrid)",
                "job_type": "Full-time",
                "work_arrangement": "Hybrid",
                "domain": "Data Analytics",
                "experience_level": "Entry-Level (0-2 yrs)",
                "description": (
                    "Build automated ETL and data pipeline transformations for Rakuten Ichiba marketplace. "
                    "Write optimized SQL queries on Snowflake/BigQuery and schedule DAG workflows using Airflow."
                ),
                "required_skills": ["python", "sql", "git", "pandas"],
                "preferred_skills": ["data modeling", "docker", "airflow", "spark"],
                "eligibility": "Degree in Computer Science, Data Science, or related quantitative discipline",
                "application_url": "https://rakuten.careers",
                "source": self.source_name,
                "is_sample": True,
                "posting_date": now - timedelta(days=3),
                "deadline": now + timedelta(days=32)
            },
            {
                "external_id": "bench_careem_mobile_24",
                "title": "Mobile Software Engineer Intern",
                "company": "Careem Tech",
                "location": "Dubai, UAE (Remote Asia)",
                "job_type": "Internship",
                "work_arrangement": "Remote",
                "domain": "Software Engineering",
                "experience_level": "Internship (4-6 Months)",
                "description": (
                    "Design and implement responsive cross-platform mobile modules. Work with product designers to ship "
                    "accessible, high-performing ride-hailing and digital wallet interfaces."
                ),
                "required_skills": ["javascript", "react", "git", "mobile development"],
                "preferred_skills": ["react native", "typescript", "rest api"],
                "eligibility": "Undergraduate students with working knowledge of mobile or modern web development",
                "application_url": "https://www.careem.com/careers",
                "source": self.source_name,
                "is_sample": True,
                "posting_date": now - timedelta(days=4),
                "deadline": now + timedelta(days=25)
            }
        ]

    def fetch_jobs(self, query: Optional[str] = None, limit: int = 25) -> List[Dict[str, Any]]:
        jobs = self._get_benchmark_catalog()
        if not query:
            return jobs[:limit]

        q = query.lower().strip()
        filtered = [
            j for j in jobs
            if q in j["title"].lower()
            or q in j["company"].lower()
            or q in j["domain"].lower()
            or any(q in s.lower() for s in j["required_skills"])
            or q in j["description"].lower()
        ]
        return filtered[:limit]
