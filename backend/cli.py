"""
Flask CLI commands.

    flask --app app jobs sync            run a synchronization now (respects the lease)
    flask --app app jobs sync-if-due     run only if the 2-hour schedule says it is due (for cron)
    flask --app app jobs status          show schedule, last runs and provider health
    flask --app app jobs run-scheduler   run the scheduler loop in the foreground
    flask --app app skills reextract [--apply]
                                         re-run skill extraction on every student's latest resume;
                                         reports (and with --apply removes) unverified skills that
                                         the corrected extractor no longer finds (e.g. false 'c', 'r',
                                         'java' produced by the old substring matcher)
"""
import json

import click
from flask.cli import AppGroup

jobs_cli = AppGroup("jobs", help="Job discovery synchronization")
skills_cli = AppGroup("skills", help="Skill data maintenance")
users_cli = AppGroup("users", help="User administration")


@users_cli.command("make-admin")
@click.argument("email")
def users_make_admin(email):
    """Grant the admin role to an existing account (self-registration cannot)."""
    from extensions import db
    from models import Student
    from utils.audit import audit
    s = Student.query.filter(db.func.lower(Student.email) == email.strip().lower()).first()
    if not s:
        raise click.ClickException(f"No account with email {email}")
    s.role = "admin"
    db.session.commit()
    audit("users.make_admin", actor_id=None, target=f"student:{s.id}", details={"via": "cli"})
    click.echo(f"{s.email} is now an admin.")


@jobs_cli.command("sync")
def jobs_sync():
    from utils.job_discovery.sync_service import run_job_sync
    click.echo(json.dumps(run_job_sync(trigger="cli"), indent=2, default=str))


@jobs_cli.command("sync-if-due")
def jobs_sync_if_due():
    from utils.job_discovery.sync_service import is_due, next_due_at, run_job_sync
    if not is_due():
        click.echo(f"Not due. Next sync at {next_due_at().isoformat()}")
        return
    result = run_job_sync(trigger="scheduled")
    click.echo(f"Sync finished: status={result['status']} inserted={result['inserted_count']} "
               f"updated={result['updated_count']} expired={result['expired_count']}")


@jobs_cli.command("status")
def jobs_status():
    from models import JobListing, JobSyncRun
    from utils.job_discovery.sync_service import lease_status, next_due_at, provider_health
    runs = JobSyncRun.query.order_by(JobSyncRun.started_at.desc()).limit(5).all()
    click.echo(json.dumps({
        "next_due_at": next_due_at().isoformat(),
        "lease": lease_status(),
        "jobs_by_status": {s: JobListing.query.filter_by(status=s).count()
                           for s in ("active", "stale", "expired", "sample")},
        "recent_runs": [r.to_dict() for r in runs],
        "providers": provider_health(),
    }, indent=2, default=str))


@jobs_cli.command("market-demand")
def jobs_market_demand():
    """Recompute skill demand per career from current postings (also runs after every sync)."""
    from utils.market_demand import compute_market_demand
    res = compute_market_demand(save=True)
    for career, d in res["careers"].items():
        top = ", ".join(f"{s} {round(p * 100)}%" for s, p in list(d["skill_share"].items())[:8])
        click.echo(f"{career:22} postings={d['postings']:4} weighting={'yes' if d['usable_for_weighting'] else 'no '} {top}")


@jobs_cli.command("run-scheduler")
def jobs_run_scheduler():
    from flask import current_app
    from utils.job_discovery.scheduler import run_forever
    run_forever(current_app._get_current_object())


@skills_cli.command("reextract")
@click.option("--apply", is_flag=True, help="Actually delete stale unverified skills (default: dry run)")
def skills_reextract(apply):
    from extensions import db
    from models import Resume, Skill, SkillVerification
    from utils.skill_extractor import extract_skills

    verified_ids = {v.skill_id for v in SkillVerification.query.all()}
    report = []
    for resume in Resume.query.filter_by(is_latest=True).all():
        if not resume.parsed_text:
            continue
        found = {e["skill_name"]: e for e in extract_skills(resume.parsed_text)}
        for skill in Skill.query.filter_by(student_id=resume.student_id).all():
            key = skill.skill_name.lower().strip()
            if key in found:
                e = found[key]
                skill.evidence_strength = e["evidence_strength"]
                skill.evidence = json.dumps(e["evidence"])
                skill.extraction_explanation = e["explanation"][:400]
                skill.category = e["category"]
                skill.extraction_confidence = e["extraction_confidence"]
            elif skill.id not in verified_ids:
                report.append({"student_id": resume.student_id, "skill": skill.skill_name, "skill_id": skill.id})
                if apply:
                    db.session.delete(skill)
    if apply:
        db.session.commit()
    else:
        db.session.rollback()
    click.echo(json.dumps({"mode": "applied" if apply else "dry-run (use --apply to delete)",
                           "unsupported_unverified_skills": report}, indent=2))
