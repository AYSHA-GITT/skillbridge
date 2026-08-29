from datetime import datetime, timedelta
from extensions import db
from models import Progress, Student, Skill, SkillVerification, SkillGap, StudyPlan


def record_student_snapshot(student_id):
    """
    Captures a point-in-time snapshot of the student's progress and stores
    it in the Progress table.
    """
    student = Student.query.get(student_id)
    if not student:
        return None

    skill_count = Skill.query.filter_by(student_id=student_id).count()
    verified_skill_count = SkillVerification.query.filter_by(student_id=student_id).count()
    skill_gap_count = SkillGap.query.filter_by(student_id=student_id).count()

    # Avoid duplicate snapshots within the same hour
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent = Progress.query.filter(
        Progress.student_id == student_id,
        Progress.date >= one_hour_ago
    ).order_by(Progress.date.desc()).first()

    if recent:
        recent.readiness_score = student.readiness_score
        recent.skill_count = skill_count
        recent.verified_skill_count = verified_skill_count
        recent.skill_gap_count = skill_gap_count
        db.session.commit()
        return recent

    new_snapshot = Progress(
        student_id=student_id,
        date=datetime.utcnow(),
        readiness_score=student.readiness_score,
        skill_count=skill_count,
        verified_skill_count=verified_skill_count,
        skill_gap_count=skill_gap_count
    )
    db.session.add(new_snapshot)
    db.session.commit()
    return new_snapshot


def get_progress_timeline(student_id):
    """
    Fetches the historical progress snapshots and summary stats.
    """
    snapshots = Progress.query.filter_by(student_id=student_id).order_by(Progress.date.asc()).all()

    # If no snapshot yet, generate an initial one
    if not snapshots:
        initial = record_student_snapshot(student_id)
        snapshots = [initial] if initial else []

    total_roadmap_days = StudyPlan.query.filter_by(student_id=student_id).count()
    completed_days = StudyPlan.query.filter_by(student_id=student_id, is_completed=True).count()

    roadmap_completion_pct = round((completed_days / total_roadmap_days * 100), 1) if total_roadmap_days > 0 else 0

    return {
        'snapshots': [s.to_dict() for s in snapshots],
        'total_roadmap_days': total_roadmap_days,
        'completed_days': completed_days,
        'roadmap_completion_pct': roadmap_completion_pct
    }
