from functools import wraps
from flask import Blueprint, jsonify, request
from flask_login import current_user
from models import Student, Resume, Skill, SkillVerification, SkillGap, FLTrainingRound
from extensions import db
from federated.server import (
    run_federated_round,
    get_federated_history,
    get_federated_round_details,
    get_federated_status,
    INSTITUTIONS
)

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({
                'error': 'Authentication required. Please log in to access institutional resources.'
            }), 401
        
        user_role = (getattr(current_user, 'role', '') or '').lower()
        if user_role != 'admin':
            return jsonify({
                'error': 'Access denied: Institutional Administrator privileges are strictly required.'
            }), 403

        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/stats', methods=['GET'])
@admin_required
def get_admin_stats():
    """
    Returns platform-level overview statistics calculated strictly from actual DB data.
    """
    total_students = Student.query.count()
    active_learners = Student.query.filter_by(is_active=True).count()
    total_resumes = Resume.query.count()
    total_skills = Skill.query.count()
    total_verifications = SkillVerification.query.count()

    students = Student.query.all()
    avg_readiness = (
        round(sum(s.readiness_score or 0 for s in students) / total_students, 1)
        if total_students > 0 else 0
    )

    # Readiness distribution brackets
    readiness_dist = {
        'foundation': 0,     # < 40%
        'developing': 0,     # 40% - 69%
        'job_ready': 0       # >= 70%
    }
    career_counts = {}

    for s in students:
        score = s.readiness_score or 0.0
        if score >= 70:
            readiness_dist['job_ready'] += 1
        elif score >= 40:
            readiness_dist['developing'] += 1
        else:
            readiness_dist['foundation'] += 1

        if s.target_career:
            norm_c = s.target_career.strip().title()
            career_counts[norm_c] = career_counts.get(norm_c, 0) + 1

    career_distribution = sorted(
        [{'career': k, 'count': v} for k, v in career_counts.items()],
        key=lambda x: x['count'],
        reverse=True
    )[:8]

    # Top skill gaps across all students
    gaps = SkillGap.query.all()
    gap_freq = {}
    for g in gaps:
        skill = g.missing_skill.strip().title() if g.missing_skill else 'Unknown'
        gap_freq[skill] = gap_freq.get(skill, 0) + 1

    top_gaps = sorted(
        [{'skill': k, 'count': v} for k, v in gap_freq.items()],
        key=lambda x: x['count'],
        reverse=True
    )[:8]

    # Skill trends (most detected skills across all enrolled students)
    all_skills = Skill.query.all()
    skill_freq = {}
    for sk in all_skills:
        name = sk.skill_name.strip().title() if sk.skill_name else 'Unknown'
        skill_freq[name] = skill_freq.get(name, 0) + 1

    skill_trends = sorted(
        [{'skill': k, 'count': v} for k, v in skill_freq.items()],
        key=lambda x: x['count'],
        reverse=True
    )[:10]

    # FL training summary from database
    latest_round = FLTrainingRound.query.order_by(FLTrainingRound.round_number.desc()).first()
    fl_accuracy = latest_round.global_accuracy_after_round if latest_round else None
    fl_rounds_count = latest_round.round_number if latest_round else 0

    return jsonify({
        'total_students': total_students,
        'active_learners': active_learners,
        'total_resumes': total_resumes,
        'total_skills_detected': total_skills,
        'total_verifications_completed': total_verifications,
        'average_readiness': avg_readiness,
        'readiness_distribution': readiness_dist,
        'career_distribution': career_distribution,
        'top_skill_gaps': top_gaps,
        'skill_trends': skill_trends,
        'federated_learning': {
            'total_rounds': fl_rounds_count,
            'current_global_accuracy': fl_accuracy,
            'participating_institutions': len(INSTITUTIONS)
        }
    }), 200


@admin_bp.route('/students', methods=['GET'])
@admin_required
def get_students_list():
    students = Student.query.order_by(Student.created_at.desc()).limit(100).all()
    return jsonify({
        'students': [s.to_dict() for s in students]
    }), 200


@admin_bp.route('/federated/train', methods=['POST'])
@admin_required
def trigger_fl_round():
    """
    Admin triggers a decentralized training round across institution partitions.
    """
    try:
        result = run_federated_round()
        return jsonify({
            'message': f"Federated Round {result['round_number']} completed successfully!",
            'data': result
        }), 200
    except Exception as e:
        return jsonify({'error': f'Federated training round failed: {str(e)}'}), 500


@admin_bp.route('/federated/rounds', methods=['GET'])
@admin_required
def get_fl_rounds():
    history = get_federated_history()
    return jsonify({'rounds': history}), 200


@admin_bp.route('/federated/nodes', methods=['GET'])
@admin_required
def get_fl_nodes():
    return jsonify({'institutions': INSTITUTIONS, 'nodes': INSTITUTIONS}), 200


@admin_bp.route('/federated/round/<int:round_id>', methods=['GET'])
@admin_required
def get_fl_round_details(round_id):
    details = get_federated_round_details(round_id)
    if not details:
        return jsonify({'error': f'Round {round_id} not found'}), 404
    return jsonify(details), 200


@admin_bp.route('/federated/status', methods=['GET'])
@admin_required
def get_fl_status():
    status = get_federated_status()
    return jsonify(status), 200


# ─────────────────────────────────────────
# JOB SYNCHRONIZATION MONITORING
# ─────────────────────────────────────────
@admin_bp.route('/jobs/overview', methods=['GET'])
@admin_required
def get_jobs_overview():
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import func
    from models import JobListing, JobSyncRun, JobApplication, JobAlertMatch, SavedJob
    from utils.job_discovery.sync_service import (
        last_success, lease_status, next_due_at, provider_health, SYNC_INTERVAL)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    day_ago = now - timedelta(hours=24)
    by_status = dict(db.session.query(JobListing.status, func.count(JobListing.id))
                     .group_by(JobListing.status).all())
    by_provider = [
        {'provider': p or 'unknown', 'status': s or 'unknown', 'count': c}
        for p, s, c in db.session.query(JobListing.source_provider, JobListing.status, func.count(JobListing.id))
        .group_by(JobListing.source_provider, JobListing.status).all()
    ]
    runs = JobSyncRun.query.order_by(JobSyncRun.started_at.desc()).limit(20).all()
    failed_24h = JobSyncRun.query.filter(JobSyncRun.started_at >= day_ago,
                                         JobSyncRun.status == 'failed').count()
    ok = last_success()
    return jsonify({
        'totals': {
            'jobs_total': JobListing.query.count(),
            'jobs_by_status': by_status,
            'new_jobs_last_24h': JobListing.query.filter(JobListing.first_seen_at >= day_ago,
                                                         JobListing.is_sample.is_(False)).count(),
            'duplicates_flagged': JobListing.query.filter(JobListing.duplicate_of_id.isnot(None)).count(),
            'jobs_without_skills': JobListing.query.filter(JobListing.required_skills == '[]').count(),
        },
        'by_provider': by_provider,
        'schedule': {
            'interval_hours': SYNC_INTERVAL.total_seconds() / 3600,
            'last_successful_sync': ok.finished_at.isoformat() if ok and ok.finished_at else None,
            'next_scheduled_sync': next_due_at().isoformat(),
            'currently_running': lease_status(),
            'failed_runs_last_24h': failed_24h,
        },
        'providers': provider_health(),
        'activity': {
            'applications_total': JobApplication.query.count(),
            'saved_jobs_total': SavedJob.query.count(),
            'alert_matches_last_24h': JobAlertMatch.query.filter(JobAlertMatch.created_at >= day_ago).count(),
        },
        'recent_runs': [r.to_dict() for r in runs],
    }), 200


@admin_bp.route('/jobs/sync', methods=['POST'])
@admin_required
def admin_trigger_job_sync():
    """Manual sync. Uses the same lease as the scheduler, so it can never overlap
    a scheduled run (it is recorded as 'skipped' instead) or create duplicates."""
    from utils.job_discovery.sync_service import run_job_sync
    from utils.audit import audit
    run = run_job_sync(trigger='manual', actor_id=current_user.id)
    audit('jobs.manual_sync', actor_id=current_user.id, target=f"job_sync_run:{run['id']}",
          details={'status': run['status']})
    code = 409 if run['status'] == 'skipped' else 200
    return jsonify({'run': run}), code


@admin_bp.route('/jobs/runs', methods=['GET'])
@admin_required
def admin_list_job_runs():
    from models import JobSyncRun
    limit = min(int(request.args.get('limit', 50) or 50), 200)
    runs = JobSyncRun.query.order_by(JobSyncRun.started_at.desc()).limit(limit).all()
    return jsonify({'runs': [r.to_dict() for r in runs]}), 200


@admin_bp.route('/audit_logs', methods=['GET'])
@admin_required
def admin_audit_logs():
    from models import AuditLog
    limit = min(int(request.args.get('limit', 100) or 100), 500)
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return jsonify({'logs': [l.to_dict() for l in logs]}), 200


@admin_bp.route('/system/health', methods=['GET'])
@admin_required
def admin_system_health():
    """AI provider availability and model evaluation metrics (measured, not hard-coded)."""
    from utils.ai_providers import ai_provider_manager
    try:
        ai = ai_provider_manager.get_providers_status()
    except Exception as e:
        ai = {'error': str(e)}
    try:
        from ml.salary_model import salary_predictor
        salary_eval = salary_predictor.evaluation()
    except Exception as e:
        salary_eval = {'error': str(e)}
    return jsonify({'ai_services': ai, 'models': {'salary': salary_eval},
                    'federated': get_federated_status()}), 200