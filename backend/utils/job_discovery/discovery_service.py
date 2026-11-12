"""
Job discovery facade used by the API routes.

Search never triggers a provider sync (the old version synced inside a user's
request when the table was empty). Synchronization happens only through the
scheduler / CLI / admin trigger (see sync_service.run_job_sync).
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import or_

from extensions import db
from models import JobListing, JobSyncRun, SavedJob

logger = logging.getLogger(__name__)

SORTS = ("relevance", "recent", "match", "salary")
DATE_POSTED_DAYS = {"24h": 1, "3d": 3, "7d": 7, "14d": 14, "30d": 30}


def _aware(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _yearly_salary(job: JobListing) -> Optional[float]:
    val = job.salary_max or job.salary_min
    if val is None:
        return None
    mult = {"year": 1, "month": 12, "week": 52, "day": 260, "hour": 2080}.get(job.salary_period or "year", 1)
    return val * mult


class JobDiscoveryService:

    # ── Sync (delegates to the real pipeline) ────────────────────────────
    def sync_all_sources(self, trigger: str = "manual", actor_id: Optional[int] = None, **_ignored) -> Dict[str, Any]:
        from utils.job_discovery.sync_service import run_job_sync
        run = run_job_sync(trigger=trigger, actor_id=actor_id)
        return {
            "run": run,
            "status": run["status"],
            "total_pulled_this_sync": run["fetched_count"],
            "newly_saved_listings": run["inserted_count"],
            "total_listings_in_db": JobListing.query.count(),
            "quality_metrics": self.get_quality_metrics(),
        }

    def discover_and_sync(self, **kwargs) -> Dict[str, Any]:
        res = self.sync_all_sources(**kwargs)
        return {"new_jobs_added": res["newly_saved_listings"], "total_jobs_in_db": res["total_listings_in_db"], **res}

    # ── Search ────────────────────────────────────────────────────────────
    def search_jobs(
        self,
        query: Optional[str] = None,
        job_type: Optional[str] = None,
        domain: Optional[str] = None,
        work_arrangement: Optional[str] = None,
        skill: Optional[str] = None,
        is_sample: Optional[bool] = None,
        region: Optional[str] = None,
        limit: int = 50,
        *,
        location: Optional[str] = None,
        company: Optional[str] = None,
        entry_level: bool = False,
        internship: Optional[bool] = None,
        experience_max: Optional[float] = None,
        salary_min: Optional[float] = None,
        date_posted: Optional[str] = None,
        include_expired: bool = False,
        include_stale: bool = True,
        sort: str = "relevance",
        page: int = 1,
        student=None,
        min_match: Optional[float] = None,
        return_meta: bool = False,
    ):
        from utils.job_discovery.location_prioritizer import get_location_rank

        q = JobListing.query.filter(JobListing.duplicate_of_id.is_(None))

        # Status: samples are opt-in only; expired hidden unless requested
        if is_sample is True:
            q = q.filter(JobListing.is_sample.is_(True))
        else:
            q = q.filter(or_(JobListing.is_sample.is_(False), JobListing.is_sample.is_(None)))
            statuses = ["active"] + (["stale"] if include_stale else []) + (["expired"] if include_expired else [])
            q = q.filter(or_(JobListing.status.in_(statuses), JobListing.status.is_(None)))

        if query and query.strip():
            for term in query.strip().split()[:6]:
                kw = f"%{term}%"
                q = q.filter(or_(JobListing.title.ilike(kw), JobListing.company.ilike(kw),
                                 JobListing.description.ilike(kw), JobListing.required_skills.ilike(kw),
                                 JobListing.location.ilike(kw)))
        if job_type and job_type.strip() and job_type.lower() not in ("all", "all types"):
            q = q.filter(JobListing.job_type.ilike(f"%{job_type.strip()}%"))
        if internship is True:
            q = q.filter(JobListing.job_type == "Internship")
        elif internship is False:
            q = q.filter(JobListing.job_type != "Internship")
        if domain and domain.strip() and domain.lower() not in ("all", "all domains"):
            q = q.filter(or_(JobListing.career_category.ilike(f"%{domain.strip()}%"),
                             JobListing.domain.ilike(f"%{domain.strip()}%")))
        if work_arrangement and work_arrangement.strip() and work_arrangement.lower() != "all":
            q = q.filter(JobListing.work_arrangement.ilike(f"%{work_arrangement.strip()}%"))
        if location and location.strip():
            kw = f"%{location.strip()}%"
            q = q.filter(or_(JobListing.location.ilike(kw), JobListing.city.ilike(kw), JobListing.state.ilike(kw)))
        if company and company.strip():
            q = q.filter(JobListing.company.ilike(f"%{company.strip()}%"))
        if entry_level:
            q = q.filter(or_(JobListing.is_entry_level.is_(True), JobListing.job_type == "Internship"))
        if experience_max is not None:
            q = q.filter(or_(JobListing.experience_min_years.is_(None), JobListing.experience_min_years <= experience_max))
        if date_posted in DATE_POSTED_DAYS:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=DATE_POSTED_DAYS[date_posted])).replace(tzinfo=None)
            q = q.filter(JobListing.posting_date >= cutoff)

        listings: List[JobListing] = q.all()

        if skill and skill.strip():
            from utils.skill_taxonomy import normalize_skill_name
            target = normalize_skill_name(skill)
            listings = [j for j in listings
                        if target in [normalize_skill_name(s) for s in j.get_required_skills() + j.get_preferred_skills()]]
        if salary_min is not None:
            listings = [j for j in listings if (_yearly_salary(j) or 0) >= salary_min]
        if region and region.strip() and region.lower() not in ("all", "all regions"):
            reg = region.strip().lower()
            if reg == "india":
                listings = [j for j in listings if get_location_rank(j.location, j.title, j.company) == 0]
            elif reg == "asia":
                listings = [j for j in listings if get_location_rank(j.location, j.title, j.company) in (0, 1)]
            elif reg == "remote":
                listings = [j for j in listings if (j.work_arrangement or "").lower() == "remote"
                            or get_location_rank(j.location, j.title, j.company) == 2]
            elif reg in ("international", "other"):
                listings = [j for j in listings if get_location_rank(j.location, j.title, j.company) == 3]

        # Optional personalized scoring
        scores: Dict[int, Optional[float]] = {}
        profile = None
        if student is not None:
            from utils.job_matcher import build_student_profile, evaluate_job_match
            profile = build_student_profile(student=student)
            if sort == "match" or min_match is not None:  # needs every score; otherwise score the page only
                for j in listings:
                    scores[j.id] = evaluate_job_match(job=j, profile=profile, include_resources=False)["match_score"]
            if min_match is not None:
                listings = [j for j in listings if (scores.get(j.id) or 0) >= min_match]

        def posted_ts(j):
            p = _aware(j.posting_date)
            return p.timestamp() if p else 0

        if sort == "recent":
            listings.sort(key=lambda j: (j.posting_date is None, -posted_ts(j)))
        elif sort == "match" and scores:
            listings.sort(key=lambda j: (scores.get(j.id) is None, -(scores.get(j.id) or 0), -posted_ts(j)))
        elif sort == "salary":
            listings.sort(key=lambda j: (_yearly_salary(j) is None, -(_yearly_salary(j) or 0)))
        else:  # relevance: India first (location rank), then freshness
            listings.sort(key=lambda j: (get_location_rank(j.location, j.title, j.company),
                                         j.status == "stale", j.posting_date is None, -posted_ts(j)))

        total = len(listings)
        limit = max(1, min(int(limit or 50), 100))
        page = max(1, int(page or 1))
        page_items = listings[(page - 1) * limit: page * limit]
        out = []
        for j in page_items:
            d = j.to_dict()
            if profile is not None:
                if j.id not in scores:
                    scores[j.id] = evaluate_job_match(job=j, profile=profile, include_resources=False)["match_score"]
                d["match_score"] = scores[j.id]
            out.append(d)
        if return_meta:
            return {"jobs": out, "total": total, "page": page, "per_page": limit,
                    "pages": (total + limit - 1) // limit}
        return out

    def get_job_by_id(self, job_id: int) -> Optional[Dict[str, Any]]:
        job = db.session.get(JobListing, job_id)
        return job.to_dict() if job else None

    # ── Saved jobs ────────────────────────────────────────────────────────
    def save_job_for_student(self, student_id: int, job_id: int, notes: Optional[str] = None) -> Dict[str, Any]:
        if db.session.get(JobListing, job_id) is None:
            return {"status": "not_found"}
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

    # ── Metrics (computed from stored data, never hard-coded) ────────────
    def get_quality_metrics(self) -> Dict[str, Any]:
        from utils.job_discovery.sync_service import last_success, next_due_at, provider_health
        total = JobListing.query.count()
        by_status = {s: JobListing.query.filter_by(status=s).count() for s in ("active", "stale", "expired", "sample")}
        dup = JobListing.query.filter(JobListing.duplicate_of_id.isnot(None)).count()
        no_skills = JobListing.query.filter(or_(JobListing.required_skills == "[]",
                                                JobListing.required_skills.is_(None))).count()
        no_date = JobListing.query.filter(JobListing.posting_date.is_(None)).count()
        last_run = JobSyncRun.query.filter(JobSyncRun.status != "skipped").order_by(JobSyncRun.started_at.desc()).first()
        ok = last_success()
        return {
            "total_listings_in_db": total,
            "live_listings_count": total - by_status["sample"],
            "sample_benchmark_count": by_status["sample"],
            "listings_by_status": by_status,
            "duplicates_flagged": dup,
            "duplicates_filtered": dup,
            "listings_without_skills": no_skills,
            "listings_without_posting_date": no_date,
            "missing_fields_detected": last_run.invalid_count if last_run else 0,
            "validation_failures": last_run.invalid_count if last_run else 0,
            "stale_records_handled": by_status["stale"] + by_status["expired"],
            "last_sync_timestamp": _aware(last_run.started_at).isoformat() if last_run else None,
            "last_sync_status": last_run.status if last_run else None,
            "last_successful_sync": _aware(ok.finished_at or ok.started_at).isoformat() if ok else None,
            "next_scheduled_sync": next_due_at().isoformat(),
            "adapters": [{"name": p["source"], "is_sample_source": p["is_sample_source"], "health": p}
                         for p in provider_health()],
        }

    def get_data_quality_metrics(self) -> Dict[str, Any]:
        base = self.get_quality_metrics()
        last_run = JobSyncRun.query.filter(JobSyncRun.status != "skipped").order_by(JobSyncRun.started_at.desc()).first()
        fetched = last_run.fetched_count if last_run else 0
        invalid = last_run.invalid_count if last_run else 0
        rate = round(100.0 * (fetched - invalid) / fetched, 1) if fetched else None
        return {"total_ingested": base["total_listings_in_db"], "valid_schema_rate": rate, **base}


job_discovery_service = JobDiscoveryService()
