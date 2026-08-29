from flask import Blueprint, jsonify, request
from models import Student, Resume, Skill, SkillVerification, SkillGap, FLTrainingRound
from extensions import db
from federated.server import run_federated_round, get_federated_history, INSTITUTIONS

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/stats', methods=['GET'])
def get_admin_stats():
    """
    Returns platform-level overview statistics.
    """
    total_students = Student.query.count()
    total_resumes = Resume.query.count()
    total_skills = Skill.query.count()
    total_verifications = SkillVerification.query.count()

    students = Student.query.all()
    avg_readiness = (
        round(sum(s.readiness_score or 0 for s in students) / total_students, 1)
        if total_students > 0 else 0
    )

    # Top skill gaps across all students
    gaps = SkillGap.query.all()
    gap_freq = {}
    for g in gaps:
        skill = g.missing_skill.lower() if g.missing_skill else 'unknown'
        gap_freq[skill] = gap_freq.get(skill, 0) + 1

    top_gaps = sorted(
        [{'skill': k, 'count': v} for k, v in gap_freq.items()],
        key=lambda x: x['count'],
        reverse=True
    )[:8]

    # FL training summary
    latest_round = FLTrainingRound.query.order_by(FLTrainingRound.round_number.desc()).first()
    fl_accuracy = latest_round.global_accuracy_after_round if latest_round else 0.78
    fl_rounds_count = latest_round.round_number if latest_round else 0

    return jsonify({
        'total_students': total_students,
        'total_resumes': total_resumes,
        'total_skills_detected': total_skills,
        'total_verifications_completed': total_verifications,
        'average_readiness': avg_readiness,
        'top_skill_gaps': top_gaps,
        'federated_learning': {
            'total_rounds': fl_rounds_count,
            'current_global_accuracy': fl_accuracy,
            'participating_institutions': len(INSTITUTIONS)
        }
    }), 200


@admin_bp.route('/students', methods=['GET'])
def get_students_list():
    students = Student.query.order_by(Student.created_at.desc()).limit(50).all()
    return jsonify({
        'students': [s.to_dict() for s in students]
    }), 200


@admin_bp.route('/federated/train', methods=['POST'])
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
def get_fl_rounds():
    history = get_federated_history()
    return jsonify({'rounds': history}), 200


@admin_bp.route('/federated/nodes', methods=['GET'])
def get_fl_nodes():
    return jsonify({'institutions': INSTITUTIONS}), 200