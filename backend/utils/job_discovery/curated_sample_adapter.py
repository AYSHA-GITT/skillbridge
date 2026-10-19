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
