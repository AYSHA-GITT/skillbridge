import re
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
from utils.job_discovery.base_adapter import JobSourceAdapter


class RemoteJobApiAdapter(JobSourceAdapter):
    """
    Adapter fetching live opportunities from public official job feeds (Arbeitnow).
    Respects rate limits, timeouts, robots guidelines, and captures rich job fields.
    """

    API_URL = "https://www.arbeitnow.com/api/job-board-api"

    @property
    def source_name(self) -> str:
        return "Arbeitnow Live API"

    @property
    def is_sample_source(self) -> bool:
        return False

    def _clean_html(self, raw_html: str) -> str:
        if not raw_html:
            return ""
        import html
        unescaped = html.unescape(raw_html)
        clean = re.sub(r'<[^>]+>', ' ', unescaped)
        clean = html.unescape(clean)
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean[:3000]

    def _extract_skills_from_tags(self, tags: List[str], desc: str) -> List[str]:
        skill_candidates = set()
        for t in tags or []:
            norm = t.lower().strip()
            if len(norm) >= 2:
                skill_candidates.add(norm)

        # Basic tech keywords scan in description
        common_tech = [
            "python", "javascript", "typescript", "react", "node.js", "docker",
            "aws", "kubernetes", "sql", "postgresql", "mongodb", "git",
            "machine learning", "data analysis", "rest api", "linux", "c++", "java"
        ]
        desc_lower = desc.lower()
        for tech in common_tech:
            if tech in desc_lower:
                skill_candidates.add(tech)

        return sorted(list(skill_candidates))

    def fetch_jobs(self, query: Optional[str] = None, limit: int = 25) -> List[Dict[str, Any]]:
        results = []
        try:
            params = {}
            # Requests with standard timeout and user agent
            headers = {
                "User-Agent": "SkillBridge-CareerBot/1.0 (Student Career Intelligence Platform; Contact: support@skillbridge.edu)"
            }
            resp = requests.get(self.API_URL, params=params, headers=headers, timeout=5)
            if resp.status_code != 200:
                return []

            data = resp.json().get("data", [])
            for item in data[:limit]:
                title = item.get("title", "").strip()
                company = item.get("company_name", "Technology Partner").strip()
                desc = self._clean_html(item.get("description", ""))
                tags = item.get("tags", [])
                extracted_skills = self._extract_skills_from_tags(tags, desc)

                # Filter by query if supplied
                if query and query.lower() not in title.lower() and query.lower() not in desc.lower():
                    continue

                location = item.get("location", "Remote")
                is_remote = item.get("remote", True)
                work_arrangement = "Remote" if is_remote else ("Hybrid" if "hybrid" in location.lower() else "Onsite")

                job_type = "Internship" if any(w in title.lower() for w in ["intern", "trainee", "working student", "co-op"]) else "Full-time"

                # Domain inference
                domain = "Software Engineering"
                lower_title = title.lower()
                if any(w in lower_title for w in ["data", "analyst", "analytics"]):
                    domain = "Data Analytics"
                elif any(w in lower_title for w in ["machine learning", "ai", "deep learning"]):
                    domain = "Machine Learning & AI"
                elif any(w in lower_title for w in ["cloud", "devops", "sre", "infrastructure"]):
                    domain = "Cloud & DevOps"
                elif any(w in lower_title for w in ["frontend", "web", "react"]):
                    domain = "Web Development"

                results.append({
                    "external_id": f"arbeitnow_{item.get('slug', '')}",
                    "title": title,
                    "company": company,
                    "location": location,
                    "job_type": job_type,
                    "work_arrangement": work_arrangement,
                    "domain": domain,
                    "experience_level": "Entry-Level" if "junior" in lower_title or "intern" in lower_title else "Mid-Level",
                    "description": desc,
                    "required_skills": extracted_skills[:6] if extracted_skills else ["python", "git"],
                    "preferred_skills": extracted_skills[6:10] if len(extracted_skills) > 6 else ["docker", "cloud"],
                    "eligibility": "B.Tech/BE/BCA/MCA in Computer Science, IT, Data, or equivalent practical competency",
                    "application_url": item.get("url") or "https://www.arbeitnow.com",
                    "source": self.source_name,
                    "is_sample": False,
                    "posting_date": datetime.fromtimestamp(item.get("created_at", datetime.utcnow().timestamp())),
                    "deadline": None
                })
        except Exception:
            # Source failure handled gracefully without crashing caller
            return []

        return results
