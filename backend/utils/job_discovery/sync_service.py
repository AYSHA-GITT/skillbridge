"""
Job synchronization pipeline.

run_job_sync() is the single entry point used by the scheduler worker, the
`flask jobs sync` CLI command and the admin "Sync now" button. It:

 1. acquires a database lease so only one sync can run at a time anywhere
    (other callers get a recorded "skipped" run instead of a duplicate run);
 2. queries every configured provider with a request-budgeted slice of the
    search plan (the slice rotates every run so the whole plan is covered);
 3. normalizes / validates each job, then upserts it:
      - same provider + provider id      -> update (last_seen / last_verified)
      - same canonical URL               -> same listing, update
      - same title|company|city from a DIFFERENT provider -> stored, but
        flagged duplicate_of the first copy (hidden from search, never merged)
      - otherwise                        -> insert
 4. marks listings stale / expired from real evidence only (deadline passed,
    provider stopped returning them while the provider itself was healthy,
    posting too old) - an outage never expires listings;
 5. evaluates job alerts for newly discovered jobs;
 6. records a JobSyncRun row with per-provider results and errors.
"""
import json
import logging
import os
import socket
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import or_, update

from extensions import db
from models import JobListing, JobSyncRun, SchedulerLease
from utils.job_discovery.base_adapter import (
    JobSourceAdapter, ProviderAuthError, ProviderBadResponse, ProviderError,
    ProviderNotConfigured, ProviderRateLimited, ProviderTransientError, RequestBudgetExceeded,
)
from utils.job_discovery.normalizer import canonicalize_url, make_fingerprint, normalize_job

logger = logging.getLogger("skillbridge.job_sync")

LEASE_NAME = "job_sync"
SYNC_INTERVAL = timedelta(hours=float(os.getenv("JOB_SYNC_INTERVAL_HOURS", "2")))
RETRY_AFTER_FAILURE = timedelta(minutes=float(os.getenv("JOB_SYNC_RETRY_MINUTES", "20")))
LEASE_TTL = timedelta(minutes=float(os.getenv("JOB_SYNC_LEASE_MINUTES", "30")))
STALE_AFTER = timedelta(hours=float(os.getenv("JOB_STALE_AFTER_HOURS", "72")))
EXPIRE_AFTER_UNSEEN = timedelta(days=float(os.getenv("JOB_EXPIRE_AFTER_DAYS", "21")))
MAX_POSTING_AGE = timedelta(days=float(os.getenv("JOB_MAX_POSTING_AGE_DAYS", "60")))

DEFAULT_ROLES = [
    "software developer", "python developer", "java developer", "frontend developer",
    "backend developer", "full stack developer", "data analyst", "data scientist",
    "machine learning engineer", "ai engineer", "data engineer", "business analyst",
    "cloud engineer", "devops engineer", "cyber security analyst", "graduate engineer trainee",
    "software engineer trainee", "software engineer intern", "data analyst intern", "fresher software",
]
# "" means nationwide (the provider's country)
DEFAULT_LOCATIONS = ["Bengaluru", "", "Mangaluru", "Karnataka", "Udupi", "Bhatkal",
                     "Hyderabad", "Pune", "Chennai", "remote"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _env_list(name: str, default: List[str]) -> List[str]:
    raw = os.getenv(name)
    if raw is None:
        return list(default)
    return [x.strip() for x in raw.split(",")]


# ──────────────────────────────────────────────────────────────────────────
# Providers & search plan
# ──────────────────────────────────────────────────────────────────────────
def build_providers() -> List[JobSourceAdapter]:
    from utils.job_discovery.adzuna_adapter import AdzunaAdapter
    from utils.job_discovery.jooble_adapter import JoobleAdapter
    from utils.job_discovery.remote_api_adapter import RemoteJobApiAdapter
    from utils.job_discovery.curated_sample_adapter import CuratedSampleAdapter
    from utils.job_discovery.company_boards_adapter import GreenhouseBoardsAdapter, LeverBoardsAdapter

    enabled = {p.strip().lower() for p in
               os.getenv("JOB_PROVIDERS", "adzuna,jooble,greenhouse,lever,arbeitnow").split(",") if p.strip()}
    providers: List[JobSourceAdapter] = []
    if "adzuna" in enabled:
        providers.append(AdzunaAdapter())
    if "jooble" in enabled:
        providers.append(JoobleAdapter())
    if "greenhouse" in enabled:
        providers.append(GreenhouseBoardsAdapter())
    if "lever" in enabled:
        providers.append(LeverBoardsAdapter())
    if "arbeitnow" in enabled:
        providers.append(RemoteJobApiAdapter())
    providers.append(CuratedSampleAdapter())  # only active when JOB_INCLUDE_SAMPLE_LISTINGS=1
    return providers


def build_search_plan() -> List[Dict[str, str]]:
    """Roles x locations, plus roles demanded by real users (target careers,
    preferences and alerts) so discovery follows what students actually want."""
    roles = [r for r in _env_list("JOB_SEARCH_ROLES", DEFAULT_ROLES) if r]
    locations = _env_list("JOB_SEARCH_LOCATIONS", DEFAULT_LOCATIONS)

    demanded: List[str] = []
    try:
        from models import Student, JobAlert, JobPreference
        for (career,) in db.session.query(Student.target_career).filter(Student.target_career.isnot(None)).distinct():
            if career and career.strip():
                demanded.append(career.strip().lower())
        for alert in JobAlert.query.filter_by(is_active=True).all():
            demanded.extend(r.strip().lower() for r in alert.to_dict()["roles"] if r and r.strip())
        for pref in JobPreference.query.all():
            demanded.extend(r.strip().lower() for r in pref.to_dict()["preferred_roles"] if r and r.strip())
    except Exception as e:  # plan must still work if these tables are unavailable
        logger.warning("Could not read user demand for search plan: %s", e)

    ordered_roles: List[str] = []
    for r in demanded + roles:
        if r not in ordered_roles:
            ordered_roles.append(r)

    plan: List[Dict[str, str]] = []
    # interleave: every role gets its top locations before any role gets the tail
    for loc in locations:
        for role in ordered_roles:
            if loc == "remote":
                plan.append({"what": f"{role} remote", "where": ""})
            else:
                plan.append({"what": role, "where": loc})
    return plan


def plan_slice(plan: List[Dict[str, str]], budget: int, offset: int) -> List[Dict[str, str]]:
    if not plan or budget <= 0:
        return []
    n = min(budget, len(plan))
    return [plan[(offset + i) % len(plan)] for i in range(n)]


# ──────────────────────────────────────────────────────────────────────────
# Lease (prevents overlapping runs across processes / machines)
# ──────────────────────────────────────────────────────────────────────────
def _owner_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"


def acquire_lease(owner: str, ttl: timedelta = LEASE_TTL) -> bool:
    now = _now()
    naive_now = now.replace(tzinfo=None)
    if db.session.get(SchedulerLease, LEASE_NAME) is None:
        try:
            db.session.add(SchedulerLease(name=LEASE_NAME, owner=None, acquired_at=None,
                                          expires_at=naive_now - timedelta(seconds=1)))
            db.session.commit()
        except Exception:
            db.session.rollback()  # another process created it concurrently
    result = db.session.execute(
        update(SchedulerLease)
        .where(SchedulerLease.name == LEASE_NAME)
        .where(or_(SchedulerLease.owner.is_(None), SchedulerLease.expires_at < naive_now))
        .values(owner=owner, acquired_at=naive_now, expires_at=naive_now + ttl)
    )
    db.session.commit()
    return result.rowcount == 1


def renew_lease(owner: str, ttl: timedelta = LEASE_TTL) -> None:
    naive_now = _now().replace(tzinfo=None)
    db.session.execute(update(SchedulerLease)
                       .where(SchedulerLease.name == LEASE_NAME, SchedulerLease.owner == owner)
                       .values(expires_at=naive_now + ttl))
    db.session.commit()


def release_lease(owner: str) -> None:
    naive_now = _now().replace(tzinfo=None)
    db.session.execute(update(SchedulerLease)
                       .where(SchedulerLease.name == LEASE_NAME, SchedulerLease.owner == owner)
                       .values(owner=None, expires_at=naive_now))
    db.session.commit()


def lease_status() -> Dict[str, Any]:
    lease = db.session.get(SchedulerLease, LEASE_NAME)
    if not lease or not lease.owner or (_aware(lease.expires_at) and _aware(lease.expires_at) < _now()):
        return {"running": False}
    return {"running": True, "owner": lease.owner,
            "acquired_at": _aware(lease.acquired_at).isoformat() if lease.acquired_at else None,
            "expires_at": _aware(lease.expires_at).isoformat() if lease.expires_at else None}


# ──────────────────────────────────────────────────────────────────────────
# Scheduling state (persisted in DB -> survives restarts / deploys)
# ──────────────────────────────────────────────────────────────────────────
def last_attempt() -> Optional[JobSyncRun]:
    return (JobSyncRun.query.filter(JobSyncRun.status != "skipped")
            .order_by(JobSyncRun.started_at.desc()).first())


def last_success() -> Optional[JobSyncRun]:
    return (JobSyncRun.query.filter(JobSyncRun.status.in_(["success", "partial"]))
            .order_by(JobSyncRun.started_at.desc()).first())


NEVER_RUN = datetime(1970, 1, 1, tzinfo=timezone.utc)


def next_due_at() -> datetime:
    last = last_attempt()
    if last is None:
        return NEVER_RUN  # never synced: due immediately
    started = _aware(last.started_at)
    if last.status == "failed":
        return started + RETRY_AFTER_FAILURE
    if last.status == "running":
        # a crashed run leaves status=running; treat it as failed once its lease would have expired
        return started + max(LEASE_TTL, RETRY_AFTER_FAILURE)
    return started + SYNC_INTERVAL


def is_due() -> bool:
    return _now() >= next_due_at()


# ──────────────────────────────────────────────────────────────────────────
# Upsert / dedup
# ──────────────────────────────────────────────────────────────────────────
UPDATABLE_FIELDS = [
    "title", "company", "location", "city", "state", "country", "job_type", "work_arrangement",
    "domain", "career_category", "experience_level", "is_entry_level", "experience_min_years",
    "experience_max_years", "description", "eligibility", "application_url", "original_url",
    "canonical_url", "source", "deadline", "salary_min", "salary_max", "salary_currency",
    "salary_period", "salary_is_estimated", "skills_source", "fingerprint", "content_hash",
]


def _upsert(norm: Dict[str, Any], now: datetime, stats: Dict[str, int]) -> Optional[JobListing]:
    naive_now = now.replace(tzinfo=None)
    existing = JobListing.query.filter_by(external_id=norm["external_id"]).first()
    if existing is None:
        existing = (JobListing.query
                    .filter(JobListing.canonical_url == norm["canonical_url"],
                            JobListing.source_provider == norm["source_provider"])
                    .first())

    if existing is not None:
        existing.last_seen_at = naive_now
        existing.last_synced_at = naive_now
        if not norm["is_sample"]:
            existing.last_verified_at = naive_now  # provider listed it right now
        existing.times_seen = (existing.times_seen or 0) + 1
        if existing.status in ("stale", "expired") and not norm["is_sample"]:
            existing.status = "active"
            existing.expired_at = None
            existing.expiry_reason = None
        if existing.content_hash != norm["content_hash"]:
            for f in UPDATABLE_FIELDS:
                setattr(existing, f, norm.get(f))
            existing.required_skills = json.dumps(norm["required_skills"])
            existing.preferred_skills = json.dumps(norm["preferred_skills"])
            if norm["posting_date"] and not existing.posting_date:
                existing.posting_date = norm["posting_date"].replace(tzinfo=None)
            existing.last_changed_at = naive_now
            stats["updated"] += 1
        else:
            stats["unchanged"] += 1
        return None

    duplicate_of = None
    if not norm["is_sample"]:
        duplicate_of = (JobListing.query
                        .filter(JobListing.fingerprint == norm["fingerprint"],
                                JobListing.source_provider != norm["source_provider"],
                                JobListing.duplicate_of_id.is_(None),
                                JobListing.is_sample.is_(False))
                        .first())
    row = JobListing(
        external_id=norm["external_id"],
        source_provider=norm["source_provider"],
        source_job_id=norm["source_job_id"],
        required_skills=json.dumps(norm["required_skills"]),
        preferred_skills=json.dumps(norm["preferred_skills"]),
        is_sample=norm["is_sample"],
        posting_date=norm["posting_date"].replace(tzinfo=None) if norm["posting_date"] else None,
        collected_at=naive_now,
        first_seen_at=naive_now,
        last_seen_at=naive_now,
        last_synced_at=naive_now,
        last_verified_at=None if norm["is_sample"] else naive_now,
        status="sample" if norm["is_sample"] else "active",
        times_seen=1,
        duplicate_of_id=duplicate_of.id if duplicate_of else None,
        **{f: (norm.get(f).replace(tzinfo=None) if isinstance(norm.get(f), datetime) else norm.get(f))
           for f in UPDATABLE_FIELDS},
    )
    db.session.add(row)
    if duplicate_of:
        stats["duplicates"] += 1
    stats["inserted"] += 1
    return row


def repair_legacy_rows() -> int:
    """Fill dedup keys for listings created before the sync upgrade."""
    rows = JobListing.query.filter(or_(JobListing.canonical_url.is_(None), JobListing.fingerprint.is_(None))).all()
    for r in rows:
        r.canonical_url = r.canonical_url or canonicalize_url(r.original_url or r.application_url)
        r.fingerprint = r.fingerprint or make_fingerprint(r.title, r.company, r.city or (r.location or "").split(",")[0])
        if r.is_sample:
            r.status = "sample"
    if rows:
        db.session.commit()
    return len(rows)


def expire_removed_from_complete_listings(scopes: Dict[str, set], now: datetime,
                                          kept_ids: Optional[set] = None) -> int:
    """For sources that return a COMPLETE list of open postings (company job
    boards), a posting missing from a successful fetch has been removed by the
    employer - direct evidence, so it is expired immediately. Postings still
    listed but now outside the relevance filters are hidden with that reason."""
    naive_now = now.replace(tzinfo=None)
    removed = 0
    for prefix, live_ids in scopes.items():
        rows = (JobListing.query
                .filter(JobListing.external_id.like(f"{prefix}%"),
                        JobListing.status.in_(["active", "stale"]))
                .all())
        for job in rows:
            if job.external_id not in live_ids:
                reason = "No longer listed on the company's job board (confirmed by the source)"
            elif kept_ids is not None and job.external_id not in kept_ids:
                reason = "Hidden: outside SkillBridge's role/location filters (still listed by the employer)"
            else:
                continue
            job.status = "expired"
            job.expired_at = naive_now
            job.expiry_reason = reason
            removed += 1
    return removed


def apply_expiry(now: datetime, healthy_providers: List[str]) -> Dict[str, int]:
    """Mark listings stale/expired from evidence. Returns counts."""
    naive_now = now.replace(tzinfo=None)
    counts = {"expired": 0, "stale": 0}

    def _expire(job: JobListing, reason: str):
        job.status = "expired"
        job.expired_at = naive_now
        job.expiry_reason = reason
        counts["expired"] += 1

    active = JobListing.query.filter(JobListing.status.in_(["active", "stale"])).all()
    for job in active:
        if job.is_sample:
            continue
        deadline = _aware(job.deadline)
        posted = _aware(job.posting_date)
        seen = _aware(job.last_seen_at) or _aware(job.collected_at)
        if deadline and deadline < now:
            _expire(job, "Application deadline has passed")
            continue
        verified = _aware(job.last_verified_at)
        recently_confirmed = verified is not None and now - verified <= STALE_AFTER
        # Age alone is weak evidence: employers keep some roles open for months.
        # Only archive old postings that the source has not re-confirmed recently.
        if posted and now - posted > MAX_POSTING_AGE and not recently_confirmed:
            _expire(job, f"Posted more than {MAX_POSTING_AGE.days} days ago and not re-confirmed by the source")
            continue
        # Absence-based rules only when the job's provider is demonstrably working,
        # so a provider outage or missing credentials never expires listings.
        if job.source_provider not in healthy_providers or seen is None:
            continue
        unseen = now - seen
        if unseen > EXPIRE_AFTER_UNSEEN:
            # Providers are searched, not exhaustively crawled, so absence is not proof of
            # closure; after a long absence the listing is archived and labelled as such.
            _expire(job, f"Archived: not returned by {job.source_provider} searches for {unseen.days} days "
                         f"(likely closed; not confirmed by the source)")
        elif unseen > STALE_AFTER and job.status == "active":
            job.status = "stale"
            counts["stale"] += 1
    return counts


# ──────────────────────────────────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────────────────────────────────
def run_job_sync(trigger: str = "scheduled", actor_id: Optional[int] = None,
                 providers: Optional[List[JobSourceAdapter]] = None,
                 search_plan: Optional[List[Dict[str, str]]] = None,
                 now_fn=_now) -> Dict[str, Any]:
    owner = _owner_id()
    if not acquire_lease(owner):
        run = JobSyncRun(trigger=trigger, triggered_by=actor_id, status="skipped",
                         started_at=now_fn().replace(tzinfo=None), finished_at=now_fn().replace(tzinfo=None),
                         error="Another synchronization is already running")
        db.session.add(run)
        db.session.commit()
        logger.info("Job sync skipped: another run holds the lease")
        return run.to_dict()

    started = now_fn()
    run = JobSyncRun(trigger=trigger, triggered_by=actor_id, status="running", started_at=started.replace(tzinfo=None))
    db.session.add(run)
    db.session.commit()

    stats = {"fetched": 0, "inserted": 0, "updated": 0, "unchanged": 0, "duplicates": 0, "invalid": 0}
    provider_results: Dict[str, Dict[str, Any]] = {}
    new_job_ids: List[int] = []
    try:
        repair_legacy_rows()
        providers = providers if providers is not None else build_providers()
        plan = search_plan if search_plan is not None else build_search_plan()
        completed_runs = JobSyncRun.query.filter(JobSyncRun.status.in_(["success", "partial"])).count()

        for adapter in providers:
            key = adapter.provider_key
            res: Dict[str, Any] = {"source": adapter.source_name, "status": "ok", "fetched": 0,
                                   "accepted": 0, "rejected": 0, "requests": 0, "errors": []}
            provider_results[key] = res
            if not adapter.is_configured():
                res["status"] = "not_configured"
                continue
            adapter.reset_run_state()
            if not getattr(adapter, "uses_search_plan", True):
                # company boards: one complete listing per board, no keyword search
                searches, batches = [], [[]]
            elif adapter.provider_key in ("arbeitnow", "curated_sample"):
                searches, batches = plan, [plan]
            else:
                searches = plan_slice(plan, adapter.max_requests_per_run,
                                      completed_runs * adapter.max_requests_per_run)
                batches = [[s] for s in searches]
            res["searches"] = len(searches)
            for batch in batches:
                try:
                    raw_jobs = adapter.fetch_jobs(batch)
                except RequestBudgetExceeded:
                    break
                except ProviderRateLimited as e:
                    res["status"] = "rate_limited"; res["errors"].append(str(e)); break
                except ProviderAuthError as e:
                    res["status"] = "auth_failed"; res["errors"].append(str(e)); break
                except ProviderNotConfigured as e:
                    res["status"] = "not_configured"; res["errors"].append(str(e)); break
                except (ProviderTransientError, ProviderBadResponse) as e:
                    res["errors"].append(str(e))   # keep going with the next search
                    continue
                except ProviderError as e:
                    res["errors"].append(str(e)); continue
                res["fetched"] += len(raw_jobs)
                stats["fetched"] += len(raw_jobs)
                for raw in raw_jobs:
                    norm, reason = normalize_job(raw)
                    if norm is None:
                        res["rejected"] += 1
                        stats["invalid"] += 1
                        reasons = res.setdefault("rejection_reasons", {})
                        reasons[reason] = reasons.get(reason, 0) + 1
                        continue
                    res["accepted"] += 1
                    row = _upsert(norm, now_fn(), stats)
                    if row is not None:
                        db.session.flush()
                        if not row.duplicate_of_id and not row.is_sample:
                            new_job_ids.append(row.id)
                db.session.commit()
                renew_lease(owner)
            res["requests"] = adapter.requests_made
            res["errors"].extend(getattr(adapter, "run_errors", []))
            if hasattr(adapter, "filtered_out"):
                res["filtered_out_not_relevant"] = adapter.filtered_out
            scopes = getattr(adapter, "completed_scopes", None)
            if scopes:
                res["boards_checked"] = len(scopes)
                removed = expire_removed_from_complete_listings(scopes, now_fn(),
                                                                kept_ids=getattr(adapter, "kept_ids", None))
                res["confirmed_removed"] = removed
                stats["confirmed_removed"] = stats.get("confirmed_removed", 0) + removed
                db.session.commit()
            if res["status"] == "ok" and res["errors"] and res["fetched"] == 0:
                res["status"] = "error"
            elif res["status"] == "ok" and res["errors"]:
                res["status"] = "degraded"

        healthy = [k for k, r in provider_results.items() if r["status"] in ("ok", "degraded")]
        expiry = apply_expiry(now_fn(), healthy)
        db.session.commit()

        alerts_created = 0
        try:
            from utils.job_alerts import evaluate_alerts_for_new_jobs, release_due_alert_matches
            alerts_created = evaluate_alerts_for_new_jobs(new_job_ids, now_fn())
            release_due_alert_matches(now_fn())
        except Exception as e:
            logger.exception("Alert evaluation failed: %s", e)
            provider_results.setdefault("_alerts", {})["error"] = str(e)

        configured = [r for k, r in provider_results.items() if r.get("status") != "not_configured" and not k.startswith("_")]
        failed = [r for r in configured if r["status"] in ("error", "auth_failed", "rate_limited")]
        if not configured:
            status, error = "failed", "No job provider is configured (set ADZUNA_* / JOOBLE_* credentials)"
        elif len(failed) == len(configured):
            status, error = "failed", "All configured providers failed"
        elif failed or any(r["status"] == "degraded" for r in configured):
            status, error = "partial", None
        else:
            status, error = "success", None

        run.status = status
        run.error = error
        run.fetched_count = stats["fetched"]
        run.inserted_count = stats["inserted"]
        run.updated_count = stats["updated"]
        run.unchanged_count = stats["unchanged"]
        run.duplicate_count = stats["duplicates"]
        run.invalid_count = stats["invalid"]
        run.expired_count = expiry["expired"] + stats.get("confirmed_removed", 0)
        run.stale_count = expiry["stale"]
        run.alerts_created = alerts_created
    except Exception as e:  # unexpected bug: record it, never crash the worker
        db.session.rollback()
        logger.exception("Job sync crashed")
        run = db.session.get(JobSyncRun, run.id)
        run.status = "failed"
        run.error = f"Unexpected error: {type(e).__name__}: {e}"[:2000]
    finally:
        run.provider_results = json.dumps(provider_results, default=str)
        run.finished_at = now_fn().replace(tzinfo=None)
        db.session.commit()
        release_lease(owner)

    logger.info("Job sync %s: %s", run.status, json.dumps({k: v for k, v in run.to_dict().items()
                                                            if k.endswith("_count")}))
    return run.to_dict()


def provider_health() -> List[Dict[str, Any]]:
    """Configuration + last observed outcome per provider (from real sync runs)."""
    runs = JobSyncRun.query.filter(JobSyncRun.status != "skipped").order_by(JobSyncRun.started_at.desc()).limit(24).all()
    out = []
    for adapter in build_providers():
        last_result, last_ok_at = None, None
        for r in runs:
            pr = r.get_provider_results().get(adapter.provider_key)
            if pr is None:
                continue
            if last_result is None:
                last_result = {**pr, "run_id": r.id,
                               "at": _aware(r.started_at).isoformat() if r.started_at else None}
            if pr.get("status") in ("ok", "degraded") and last_ok_at is None:
                last_ok_at = _aware(r.started_at).isoformat() if r.started_at else None
        out.append({**adapter.health_snapshot(), "last_result": last_result, "last_success_at": last_ok_at})
    return out
