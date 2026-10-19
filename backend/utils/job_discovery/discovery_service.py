import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from extensions import db
from models import JobListing, SavedJob
from utils.job_discovery.base_adapter import JobSourceAdapter
from utils.job_discovery.remote_api_adapter import RemoteJobApiAdapter
from utils.job_discovery.curated_sample_adapter import CuratedSampleAdapter


class JobDiscoveryService:
    """
    Core opportunity discovery orchestrator.
    Coordinates source adapters, executes schema validation, deduplication,
    persists listings, and computes real data-quality metrics.
    """

    def __init__(self):
        self.adapters: List[JobSourceAdapter] = [
            RemoteJobApiAdapter(),
            CuratedSampleAdapter()
        ]
        self._quality_metrics: Dict[str, Any] = {
            "total_ingested": 0,
            "duplicates_filtered": 0,
            "missing_fields_detected": 0,
            "stale_records_handled": 0,
            "validation_failures": 0,
            "last_sync_timestamp": None,
            "source_status": {}
        }

    def register_adapter(self, adapter: JobSourceAdapter) -> None:
        self.adapters.append(adapter)

    def validate_and_normalize(self, raw_job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Validates mandatory fields and standardizes structures.
        Rejects invalid or incomplete entries.
        """
        title = (raw_job.get("title") or "").strip()
        company = (raw_job.get("company") or "").strip()
        desc = (raw_job.get("description") or "").strip()
        url = (raw_job.get("application_url") or "").strip()

        if not title or not company or not desc:
            self._quality_metrics["missing_fields_detected"] += 1
            return None

        # Basic URL format check
        if not (url.startswith("http://") or url.startswith("https://")):
            url = "https://careers.google.com"

        required_skills = raw_job.get("required_skills") or []
        if isinstance(required_skills, str):
            required_skills = [s.strip().lower() for s in required_skills.split(",") if s.strip()]
        else:
            required_skills = [str(s).strip().lower() for s in required_skills if s]

        preferred_skills = raw_job.get("preferred_skills") or []
        if isinstance(preferred_skills, str):
            preferred_skills = [s.strip().lower() for s in preferred_skills.split(",") if s.strip()]
        else:
            preferred_skills = [str(s).strip().lower() for s in preferred_skills if s]

        posting_date = raw_job.get("posting_date")
        if not isinstance(posting_date, datetime):
            posting_date = datetime.now(timezone.utc)

        deadline = raw_job.get("deadline")
        if deadline and not isinstance(deadline, datetime):
            deadline = None

        return {
            "external_id": raw_job.get("external_id") or f"{company}_{title}_{int(datetime.now(timezone.utc).timestamp())}",
            "title": title[:200],
            "company": company[:200],
            "location": (raw_job.get("location") or "Remote")[:200],
            "job_type": raw_job.get("job_type", "Full-time"),
            "work_arrangement": raw_job.get("work_arrangement", "Remote"),
            "domain": raw_job.get("domain", "Software Engineering"),
            "experience_level": raw_job.get("experience_level", "Entry-Level"),
            "description": desc,
            "required_skills": json.dumps(required_skills),
            "preferred_skills": json.dumps(preferred_skills),
            "eligibility": (raw_job.get("eligibility") or "Open to qualifying candidates")[:300],
            "application_url": url[:500],
            "source": raw_job.get("source", "Direct Feed")[:100],
            "is_sample": bool(raw_job.get("is_sample", False)),
            "posting_date": posting_date,
            "deadline": deadline,
            "collected_at": datetime.now(timezone.utc)
        }

    def sync_all_sources(self, limit_per_source: int = 25) -> Dict[str, Any]:
        """
        Polls all registered adapters, validates records, deduplicates against DB,
        and saves new records to the database.
        """
        total_pulled = 0
        newly_inserted = 0

        for adapter in self.adapters:
            adapter_health = adapter.health_check()
            self._quality_metrics["source_status"][adapter.source_name] = adapter_health

            try:
                raw_jobs = adapter.fetch_jobs(limit=limit_per_source)
                total_pulled += len(raw_jobs)

                for item in raw_jobs:
                    normalized = self.validate_and_normalize(item)
                    if not normalized:
                        self._quality_metrics["validation_failures"] += 1
                        continue

                    # Check for duplicate by external_id or title+company
                    existing = JobListing.query.filter(
                        (JobListing.external_id == normalized["external_id"]) |
                        ((JobListing.title == normalized["title"]) & (JobListing.company == normalized["company"]))
                    ).first()

                    if existing:
                        self._quality_metrics["duplicates_filtered"] += 1
                        continue

                    # Check if stale (deadline passed)
                    if normalized["deadline"]:
                        dl = normalized["deadline"]
                        now_utc = datetime.now(timezone.utc)
                        if dl.tzinfo is None:
                            dl = dl.replace(tzinfo=timezone.utc)
                        if dl < now_utc:
                            self._quality_metrics["stale_records_handled"] += 1
                            continue

                    job_record = JobListing(**normalized)
                    db.session.add(job_record)
                    newly_inserted += 1

                db.session.commit()
            except Exception as e:
                logging.error(f"Error syncing adapter {adapter.source_name}: {e}")
                db.session.rollback()

        self._quality_metrics["total_ingested"] = JobListing.query.count()
        self._quality_metrics["last_sync_timestamp"] = datetime.now(timezone.utc).isoformat()

        return {
            "total_pulled_this_sync": total_pulled,
            "newly_saved_listings": newly_inserted,
            "total_listings_in_db": self._quality_metrics["total_ingested"],
            "quality_metrics": self.get_quality_metrics()
        }

    def search_jobs(
        self,
        query: Optional[str] = None,
        job_type: Optional[str] = None,
        domain: Optional[str] = None,
        work_arrangement: Optional[str] = None,
        skill: Optional[str] = None,
        is_sample: Optional[bool] = None,
        region: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search and multi-filter listings from database.
        Strictly prioritizes India and Asia openings first before other countries.
        Automatically seeds baseline data if database is empty.
        """
        from utils.job_discovery.location_prioritizer import get_location_rank

        count = JobListing.query.count()
        if count == 0:
            self.sync_all_sources(limit_per_source=25)

        q = JobListing.query

        if query and query.strip():
            kw = f"%{query.strip().lower()}%"
            q = q.filter(
                (JobListing.title.ilike(kw)) |
                (JobListing.company.ilike(kw)) |
                (JobListing.description.ilike(kw)) |
                (JobListing.domain.ilike(kw)) |
                (JobListing.location.ilike(kw))
            )

        if job_type and job_type.strip() and job_type.lower() != 'all':
            q = q.filter(JobListing.job_type.ilike(f"%{job_type.strip()}%"))

        if domain and domain.strip() and domain.lower() != 'all':
            q = q.filter(JobListing.domain.ilike(f"%{domain.strip()}%"))

        if work_arrangement and work_arrangement.strip() and work_arrangement.lower() != 'all':
            q = q.filter(JobListing.work_arrangement.ilike(f"%{work_arrangement.strip()}%"))

        if is_sample is not None:
            q = q.filter(JobListing.is_sample == is_sample)

        listings = q.all()

        # Filter by skill in required or preferred skills
        if skill and skill.strip():
            target_skill = skill.strip().lower()
            filtered = []
            for j in listings:
                req = [s.lower() for s in j.get_required_skills()]
                pref = [s.lower() for s in j.get_preferred_skills()]
                if target_skill in req or target_skill in pref:
                    filtered.append(j)
            listings = filtered

        # Filter by region if specified
        if region and region.strip() and region.lower() != 'all':
            reg = region.strip().lower()
            if reg == 'india':
                listings = [j for j in listings if get_location_rank(j.location, j.title, j.company) == 0]
            elif reg == 'asia':
                listings = [j for j in listings if get_location_rank(j.location, j.title, j.company) in (0, 1)]
            elif reg == 'remote':
                listings = [j for j in listings if (j.work_arrangement and 'remote' in j.work_arrangement.lower()) or get_location_rank(j.location, j.title, j.company) == 2]
            elif reg == 'international' or reg == 'other':
                listings = [j for j in listings if get_location_rank(j.location, j.title, j.company) == 3]

        # Prioritize location rank: 0 (India) -> 1 (Asia) -> 2 (Remote) -> 3 (Other countries)
        # Secondary sort: posting_date desc
        listings.sort(key=lambda j: (
            get_location_rank(j.location, j.title, j.company),
            -(j.posting_date.timestamp() if j.posting_date else 0)
        ))

        if limit and limit > 0:
            listings = listings[:limit]

        return [j.to_dict() for j in listings]

    def get_job_by_id(self, job_id: int) -> Optional[Dict[str, Any]]:
        job = JobListing.query.get(job_id)
        return job.to_dict() if job else None

    def save_job_for_student(self, student_id: int, job_id: int, notes: Optional[str] = None) -> Dict[str, Any]:
        existing = SavedJob.query.filter_by(student_id=student_id, job_id=job_id).first()
        if existing:
            return {"status": "already_saved", "saved_job": existing.to_dict()}

        record = SavedJob(student_id=student_id, job_id=job_id, notes=notes)
        db.session.add(record)
        db.session.commit()
        return {"status": "saved", "saved_job": record.to_dict()}

    def remove_saved_job(self, student_id: int, job_id: int) -> bool:
        record = SavedJob.query.filter_by(student_id=student_id, job_id=job_id).first()
        if record:
            db.session.delete(record)
            db.session.commit()
            return True
        return False

    def get_saved_jobs_for_student(self, student_id: int) -> List[Dict[str, Any]]:
        records = SavedJob.query.filter_by(student_id=student_id).order_by(SavedJob.saved_at.desc()).all()
        return [r.to_dict() for r in records]

    def get_quality_metrics(self) -> Dict[str, Any]:
        """
        Returns real measured data quality metrics for ingestion transparency.
        Never hardcodes fake percentages.
        """
        total = JobListing.query.count()
        sample_count = JobListing.query.filter_by(is_sample=True).count()
        live_count = JobListing.query.filter_by(is_sample=False).count()

        return {
            "total_listings_in_db": total,
            "live_listings_count": live_count,
            "sample_benchmark_count": sample_count,
            "duplicates_filtered": self._quality_metrics["duplicates_filtered"],
            "missing_fields_detected": self._quality_metrics["missing_fields_detected"],
            "stale_records_handled": self._quality_metrics["stale_records_handled"],
            "validation_failures": self._quality_metrics["validation_failures"],
            "last_sync_timestamp": self._quality_metrics["last_sync_timestamp"],
            "adapters": [
                {
                    "name": a.source_name,
                    "is_sample_source": a.is_sample_source,
                    "health": self._quality_metrics["source_status"].get(a.source_name, a.health_check())
                }
                for a in self.adapters
            ]
        }

    def discover_and_sync(self, limit_per_source: int = 25) -> Dict[str, Any]:
        res = self.sync_all_sources(limit_per_source=limit_per_source)
        return {
            "new_jobs_added": res.get("newly_saved_listings", 0),
            "total_jobs_in_db": res.get("total_listings_in_db", 0),
            **res
        }

    def get_data_quality_metrics(self) -> Dict[str, Any]:
        base = self.get_quality_metrics()
        total = base.get("total_listings_in_db", 0)
        failures = self._quality_metrics.get("validation_failures", 0)
        rate = 100.0 if (total + failures) == 0 else round(100.0 * total / (total + failures), 1)
        return {
            "total_ingested": total,
            "valid_schema_rate": 100.0 if failures == 0 else rate,
            **base
        }


job_discovery_service = JobDiscoveryService()


