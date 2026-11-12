"""
Personalized job alerts (in-app notifications).

* Evaluated only for jobs that were NEWLY discovered in a sync run.
* A job is alerted to a student at most once (unique (student_id, job_id)).
* Frequency control: 'instant' matches become visible immediately;
  'daily' / 'weekly' matches are held and released together once per period.
* Volume control: at most MAX_MATCHES_PER_ALERT_PER_RUN new matches per alert
  per sync, highest match score first.

Delivery is in-app (GET /api/student/job_alerts/notifications). No email/SMS
provider is configured in this project, so nothing is sent externally.
"""
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from extensions import db
from models import JobAlert, JobAlertMatch, JobListing, Student

MAX_MATCHES_PER_ALERT_PER_RUN = int(os.getenv("JOB_ALERT_MAX_PER_RUN", "10"))
PERIODS = {"instant": timedelta(0), "daily": timedelta(days=1), "weekly": timedelta(days=7)}


def _list(v) -> List[str]:
    try:
        data = json.loads(v) if isinstance(v, str) else (v or [])
    except Exception:
        return []
    return [str(x).strip().lower() for x in data if str(x).strip()]


def job_matches_alert_filters(job: JobListing, alert: JobAlert) -> bool:
    title = (job.title or "").lower()
    roles = _list(alert.roles)
    if roles and not any(all(w in title for w in r.split()) for r in roles):
        return False
    locations = _list(alert.locations)
    if locations:
        loc = f"{job.location or ''} {job.city or ''} {job.state or ''}".lower()
        is_remote = (job.work_arrangement or "").lower() == "remote"
        if not (any(l in loc for l in locations) or ("remote" in locations and is_remote)):
            return False
    job_types = _list(alert.job_types)
    if job_types and (job.job_type or "").lower() not in job_types:
        return False
    modes = _list(alert.work_modes)
    if modes and (job.work_arrangement or "").lower() not in modes:
        return False
    skills = _list(alert.skills)
    if skills:
        job_skills = {s.lower() for s in job.get_required_skills() + job.get_preferred_skills()}
        if not job_skills & set(skills):
            return False
    return True


def evaluate_alerts_for_new_jobs(new_job_ids: List[int], now: datetime = None) -> int:
    from utils.job_matcher import build_student_profile, evaluate_job_match

    now = now or datetime.now(timezone.utc)
    naive_now = now.replace(tzinfo=None)
    if not new_job_ids:
        return 0
    jobs = JobListing.query.filter(JobListing.id.in_(new_job_ids), JobListing.status == "active").all()
    created = 0
    profiles: Dict[int, Dict[str, Any]] = {}
    for alert in JobAlert.query.filter_by(is_active=True).all():
        student = db.session.get(Student, alert.student_id)
        if student is None:
            continue
        if alert.student_id not in profiles:
            profiles[alert.student_id] = build_student_profile(student=student)
        candidates = []
        for job in jobs:
            if not job_matches_alert_filters(job, alert):
                continue
            ev = evaluate_job_match(job=job, profile=profiles[alert.student_id], include_resources=False)
            score = ev["match_score"]
            if score is None or score < (alert.min_match_score or 0):
                continue
            candidates.append((score, job))
        candidates.sort(key=lambda x: x[0], reverse=True)
        for score, job in candidates[:MAX_MATCHES_PER_ALERT_PER_RUN]:
            exists = JobAlertMatch.query.filter_by(student_id=alert.student_id, job_id=job.id).first()
            if exists:
                continue
            db.session.add(JobAlertMatch(
                alert_id=alert.id, student_id=alert.student_id, job_id=job.id, match_score=score,
                created_at=naive_now,
                released_at=naive_now if (alert.frequency or "daily") == "instant" else None,
            ))
            created += 1
        alert.last_evaluated_at = naive_now
    db.session.commit()
    return created


def release_due_alert_matches(now: datetime = None) -> int:
    """Release held daily/weekly matches whose period has elapsed."""
    now = now or datetime.now(timezone.utc)
    naive_now = now.replace(tzinfo=None)
    released = 0
    for alert in JobAlert.query.filter(JobAlert.is_active.is_(True)).all():
        period = PERIODS.get(alert.frequency or "daily", PERIODS["daily"])
        pending = JobAlertMatch.query.filter_by(alert_id=alert.id, released_at=None).all()
        if not pending:
            continue
        last = alert.last_notified_at
        if period and last is not None and naive_now - last < period:
            continue
        for m in pending:
            m.released_at = naive_now
            released += 1
        alert.last_notified_at = naive_now
    db.session.commit()
    return released
