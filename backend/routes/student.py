# pyrefly: ignore [missing-import]

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timezone
import os
import uuid
from utils.skill_extractor import extract_skills
from models import Skill, StudyPlan
from extensions import db
from models import Resume
from utils.resume_parser import parse_resume
from utils.ai_question_generator import generate_questions
from utils.skill_gap_analyzer import analyze_skill_gap, get_career_requirements
from models import SkillVerification, SkillGap
from utils.question_bank_manager import ensure_minimum_questions
from utils.roadmap_generator import ensure_roadmap_template
from utils.progress_tracker import record_student_snapshot, get_progress_timeline
from utils.badge_checker import get_student_badges
from ml.salary_model import salary_predictor
from ml.readiness_model import readiness_scorer
from ml.skill_gap_model import skill_gap_model
from utils.career_recommender import (
    get_all_career_recommendations,
    evaluate_career_match,
    compare_career_tracks
)
from federated.server import get_federated_status
from utils.career_assistant import ask_career_assistant

student_bp = Blueprint('student', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'docx'}
UPLOAD_FOLDER = os.path.join('uploads', 'resumes')


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@student_bp.route('/upload_resume', methods=['POST'])
@login_required
def upload_resume():
    # 1. Check a file was actually sent
    if 'resume' not in request.files:
        return jsonify({'error': 'No file part named "resume" in request'}), 400

    file = request.files['resume']

    if not file or not file.filename or file.filename.strip() == '':
        return jsonify({'error': 'No file selected'}), 400

    # 2. Validate file type
    if not allowed_file(file.filename):
        return jsonify({'error': 'Only PDF and DOCX files are allowed'}), 400

    # 3. Build a safe, unique filename so two students uploading
    #    "resume.pdf" never overwrite each other
    original_filename = secure_filename(file.filename)
    extension = original_filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{current_user.id}_{uuid.uuid4().hex}.{extension}"

    # 4. Make sure the upload folder exists, then save the file
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    file.save(file_path)

    # 5. Mark this student's previous resumes as not-latest
    #    (we keep old ones on disk and in DB — never delete —
    #    but only one should count as "current" for analysis)
    Resume.query.filter_by(student_id=current_user.id, is_latest=True) \
        .update({'is_latest': False})

    # 6. Create the DB record — parsing happens in a later step,
    #    so parsed_text and parsed_on stay empty for now
    new_resume = Resume(
        student_id=current_user.id,
        file_path=file_path,
        original_filename=original_filename,
        parsed_text=None,
        parsed_on=None,
        uploaded_on=datetime.now(timezone.utc),
        is_latest=True
    )

    db.session.add(new_resume)
    db.session.commit()

    return jsonify({
        'message': 'Resume uploaded successfully',
        'resume': new_resume.to_dict()
    }), 201

@student_bp.route('/parse_resume/<int:resume_id>', methods=['POST'])
@login_required
def parse_resume_endpoint(resume_id):
    resume = Resume.query.filter_by(
        id=resume_id, student_id=current_user.id
    ).first()

    if not resume:
        return jsonify({'error': 'Resume not found or does not belong to you'}), 404

    try:
        extracted_text = parse_resume(resume.file_path)
    except ValueError as e:
        return jsonify({'error': str(e)}), 422
    except Exception as e:
        return jsonify({'error': f'Failed to parse resume: {str(e)}'}), 500

    resume.parsed_text = extracted_text
    resume.parsed_on = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({
        'message': 'Resume parsed successfully',
        'resume_id': resume.id,
        'text_length': len(extracted_text),
        'preview': extracted_text[:300]  # first 300 chars, just to sanity-check
    }), 200

@student_bp.route('/extract_skills/<int:resume_id>', methods=['POST'])
@login_required
def extract_skills_endpoint(resume_id):
    resume = Resume.query.filter_by(
        id=resume_id, student_id=current_user.id
    ).first()

    if not resume:
        return jsonify({'error': 'Resume not found or does not belong to you'}), 404

    if not resume.parsed_text:
        return jsonify({'error': 'Resume has not been parsed yet. '
                                  'Call /parse_resume first.'}), 400

    extracted = extract_skills(resume.parsed_text)

    if not extracted:
        return jsonify({'message': 'No known skills detected in this resume',
                         'skills': []}), 200
#from here
# Skills that already have a verification must be preserved —
    # deleting them would break skill_verifications' foreign key
    # and destroy the student's proven quiz history
    verified_skill_ids = {
        v.skill_id for v in SkillVerification.query.filter_by(
            student_id=current_user.id
        ).all()
    }

    existing_skills = Skill.query.filter_by(resume_id=resume.id).all()

    kept_verified_skills = [
        s for s in existing_skills if s.id in verified_skill_ids
    ]
    kept_verified_names = {s.skill_name for s in kept_verified_skills}

    # Delete only the unverified ones — safe to regenerate
    for s in existing_skills:
        if s.id not in verified_skill_ids:
            db.session.delete(s)

    saved_skills = list(kept_verified_skills)

    for item in extracted:
        if item['skill_name'] in kept_verified_names:
            continue  # already have a verified version, don't duplicate

        skill = Skill(
            student_id=current_user.id,
            resume_id=resume.id,
            skill_name=item['skill_name'],
            extraction_confidence=item['extraction_confidence'],
            proficiency=None
        )
        db.session.add(skill)
        saved_skills.append(skill)

    db.session.commit()

    #till here


    return jsonify({
        'message': f'{len(saved_skills)} skills extracted',
        'skills': [s.to_dict() for s in saved_skills]
    }), 201

import random
from models import QuestionBank, SkillVerification

def get_quiz_question_count(confidence):
    if confidence >= 0.7:
        return 3
    elif confidence >= 0.4:
        return 5
    else:
        return 8


@student_bp.route('/get_quiz/<int:skill_id>', methods=['GET'])
@login_required
def get_quiz(skill_id):
    skill = Skill.query.filter_by(
        id=skill_id, student_id=current_user.id
    ).first()

    if not skill:
        return jsonify({'error': 'Skill not found or does not belong to you'}), 404

    question_count = get_quiz_question_count(skill.extraction_confidence)

#from here
    
 # Ensure at least MINIMUM_QUESTIONS_PER_SKILL exist, generating
    # only the missing amount via Gemini if needed
    ensure_minimum_questions(skill.skill_name)

    available_questions = QuestionBank.query.filter_by(
        skill_name=skill.skill_name
    ).all()

    if not available_questions:
        return jsonify({
            'error': f'No quiz questions available for "{skill.skill_name}" '
                      'and AI generation failed. Please try again shortly.'
        }), 503   

#till here




    

    # Pick up to question_count questions, randomly, without repeats
    selected = random.sample(
        available_questions,
        min(question_count, len(available_questions))
    )

    return jsonify({
        'skill_id': skill.id,
        'skill_name': skill.skill_name,
        'extraction_confidence': skill.extraction_confidence,
        'question_count': len(selected),
        'questions': [q.to_dict() for q in selected]
    }), 200

@student_bp.route('/submit_quiz/<int:skill_id>', methods=['POST'])
@login_required
def submit_quiz(skill_id):
    skill = Skill.query.filter_by(
        id=skill_id, student_id=current_user.id
    ).first()

    if not skill:
        return jsonify({'error': 'Skill not found or does not belong to you'}), 404

    data = request.get_json()
    # Expected format: {"answers": {"3": "B", "7": "A", "12": "C"}}
    # keys are QuestionBank ids (as strings from JSON), values are the
    # student's chosen option letter
    submitted_answers = data.get('answers', {})

    if not submitted_answers:
        return jsonify({'error': 'No answers submitted'}), 400

    question_ids = [int(qid) for qid in submitted_answers.keys()]
    questions = QuestionBank.query.filter(
        QuestionBank.id.in_(question_ids)
    ).all()

    correct_count = 0
    for question in questions:
        submitted = submitted_answers.get(str(question.id))
        if submitted and submitted.upper() == question.correct_answer:
            correct_count += 1

    total_questions = len(questions)
    quiz_score_percent = round((correct_count / total_questions) * 100, 2) \
        if total_questions > 0 else 0

    # Combine resume-evidence confidence with quiz performance
    verification_score = round(
        (skill.extraction_confidence * 0.4) +
        ((quiz_score_percent / 100) * 0.6),
        2
    )

    verification = SkillVerification(
        student_id=current_user.id,
        skill_id=skill.id,
        extraction_confidence=skill.extraction_confidence,
        quiz_question_count=total_questions,
        quiz_correct_count=correct_count,
        quiz_score_percent=quiz_score_percent,
        verification_score=verification_score
    )
    db.session.add(verification)
    db.session.commit()

    return jsonify({
        'message': 'Quiz submitted and scored',
        'skill_name': skill.skill_name,
        'quiz_score_percent': quiz_score_percent,
        'correct_count': correct_count,
        'total_questions': total_questions,
        'verification_score': verification_score
    }), 201



@student_bp.route('/analyze_skill_gap', methods=['POST'])
@login_required
def analyze_skill_gap_endpoint():
    if not current_user.target_career:
        return jsonify({
            'error': 'Please set your target career first'
        }), 400

    # Get only VERIFIED skills — a skill counts only if the student
    # passed its quiz, not just because it was extracted from resume
    verifications = SkillVerification.query.filter_by(
        student_id=current_user.id
    ).all()

    verified_skill_ids = [v.skill_id for v in verifications]
    verified_skills = Skill.query.filter(
        Skill.id.in_(verified_skill_ids)
    ).all()

    verified_skill_names = [s.skill_name for s in verified_skills]

    result = analyze_skill_gap(verified_skill_names, current_user.target_career)

    if result is None:
        return jsonify({
            'error': f'Could not determine requirements for '
                      f'"{current_user.target_career}"'
        }), 500

    # Save missing required skills into the SkillGap table for
    # later use (e.g. Learning Roadmap generation)
    SkillGap.query.filter_by(student_id=current_user.id).delete()

    missing_req = result.get('missing_required')
    if isinstance(missing_req, list):
        for skill_name in missing_req:
            gap = SkillGap(
                student_id=current_user.id,
                missing_skill=str(skill_name),
                importance='High',
                category='Required'
            )
            db.session.add(gap)

    missing_nice = result.get('missing_nice_to_have')
    if isinstance(missing_nice, list):
        for skill_name in missing_nice:
            gap = SkillGap(
                student_id=current_user.id,
                missing_skill=str(skill_name),
                importance='Medium',
                category='Nice to have'
            )
            db.session.add(gap)

    # Update readiness score on the student record too
    raw_coverage = result.get('overall_coverage')
    overall_coverage = float(raw_coverage) if isinstance(raw_coverage, (int, float, str)) else 0.0
    current_user.readiness_score = round(overall_coverage * 100, 1)
    db.session.commit()

    return jsonify(result), 200



@student_bp.route('/set_target_career', methods=['POST'])
@login_required
def set_target_career():
    data = request.get_json(silent=True) or {}
    career = data.get('target_career', '').strip()

    if not career:
        return jsonify({'error': 'target_career is required'}), 400

    try:
        current_user.target_career = career
        db.session.commit()
        return jsonify({
            'message': 'Target career updated',
            'target_career': current_user.target_career
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update target career: {str(e)}'}), 500





@student_bp.route('/generate_roadmap', methods=['POST'])
@login_required
def generate_roadmap():
    gaps = SkillGap.query.filter_by(student_id=current_user.id).all()

    if not gaps:
        from utils.skill_gap_analyzer import get_career_requirements
        target = current_user.target_career or "Software Engineer"
        career_reqs = get_career_requirements(target) or {}
        req_skills = career_reqs.get('required', ['Python', 'SQL', 'Git', 'Data Structures'])

        existing_skills = [s.skill_name.lower() for s in Skill.query.filter_by(student_id=current_user.id).all()]
        missing = [s for s in req_skills if s.lower() not in existing_skills][:3]
        if not missing:
            missing = req_skills[:3] if req_skills else ['Python', 'SQL', 'Git']

        for s in missing:
            new_gap = SkillGap(
                student_id=current_user.id,
                missing_skill=s,
                importance='High',
                estimated_days=7,
                category='Core'
            )
            db.session.add(new_gap)
        db.session.commit()
        gaps = SkillGap.query.filter_by(student_id=current_user.id).all()

    StudyPlan.query.filter_by(student_id=current_user.id).delete()

    for gap in gaps:
        template_days = ensure_roadmap_template(gap.missing_skill, gap.importance)

        for day in template_days:
            db.session.add(StudyPlan(
                student_id=current_user.id,
                skill_name=gap.missing_skill,
                day_number=day.day_number,
                topic=day.topic,
                description=day.description,
                resource_link=day.resource_hint,
                resource_type='suggested',
                duration_hours=day.duration_hours,
                is_completed=False
            ))

    db.session.commit()

    plan_rows = StudyPlan.query.filter_by(student_id=current_user.id) \
        .order_by(StudyPlan.skill_name, StudyPlan.day_number).all()

    grouped = {}
    for p in plan_rows:
        grouped.setdefault(p.skill_name, []).append(p.to_dict())

    return jsonify({
        'roadmap': [{'skill': s, 'days': d} for s, d in grouped.items()]
    }), 200


@student_bp.route('/get_roadmap', methods=['GET'])
@login_required
def get_roadmap():
    plan_rows = StudyPlan.query.filter_by(student_id=current_user.id) \
        .order_by(StudyPlan.skill_name, StudyPlan.day_number).all()

    if not plan_rows:
        return jsonify({'roadmap': [], 'message': 'No roadmap yet.'}), 200

    grouped = {}
    for p in plan_rows:
        grouped.setdefault(p.skill_name, []).append(p.to_dict())

    return jsonify({
        'roadmap': [{'skill': s, 'days': d} for s, d in grouped.items()]
    }), 200


@student_bp.route('/complete_roadmap_day/<int:plan_id>', methods=['POST'])
@login_required
def complete_roadmap_day(plan_id):
    plan = StudyPlan.query.filter_by(
        id=plan_id, student_id=current_user.id
    ).first()

    if not plan:
        return jsonify({'error': 'Roadmap day not found'}), 404

    plan.is_completed = True
    plan.completed_on = datetime.now(timezone.utc)
    db.session.commit()
    record_student_snapshot(current_user.id)

    return jsonify({'message': 'Marked complete', 'day': plan.to_dict()}), 200


@student_bp.route('/skills', methods=['GET'])
@login_required
def get_student_skills():
    """
    Returns all skills associated with the student, whether extracted or manually added,
    along with verification status and quiz records.
    """
    skills = Skill.query.filter_by(student_id=current_user.id).all()
    verifications = SkillVerification.query.filter_by(student_id=current_user.id).all()
    verification_map = {v.skill_id: v.to_dict() for v in verifications}

    result = []
    for s in skills:
        item = s.to_dict()
        verification = verification_map.get(s.id)
        item['is_verified'] = verification is not None
        item['verification'] = verification
        result.append(item)

    return jsonify({
        'skills': result,
        'total_count': len(result),
        'verified_count': len(verifications)
    }), 200


@student_bp.route('/readiness_breakdown', methods=['GET'])
@login_required
def get_readiness_breakdown():
    """
    Returns in-depth readiness breakdown, radar dimensions, and actionable recommendations.
    """
    career = current_user.target_career or 'Software Engineer'
    verifications = SkillVerification.query.filter_by(student_id=current_user.id).all()
    verified_ids = [v.skill_id for v in verifications]
    verified_skills = [
        s.skill_name for s in Skill.query.filter(Skill.id.in_(verified_ids)).all()
    ]

    gap_data = skill_gap_model.evaluate_gaps(verified_skills, career)
    readiness_data = readiness_scorer.calculate_readiness(gap_data, verifications)

    # Synchronize student readiness score
    current_user.readiness_score = readiness_data['readiness_score']
    db.session.commit()
    record_student_snapshot(current_user.id)

    return jsonify({
        'career': career,
        'readiness': readiness_data,
        'gap_summary': gap_data
    }), 200


@student_bp.route('/progress_history', methods=['GET'])
@login_required
def get_student_progress_history():
    """
    Returns timeline of snapshots and learning velocity.
    """
    data = get_progress_timeline(current_user.id)
    return jsonify(data), 200


@student_bp.route('/simulate_salary', methods=['POST'])
@login_required
def simulate_salary_endpoint():
    """
    Predicts base expected compensation and simulates boost from acquiring additional skills.
    """
    verifications = SkillVerification.query.filter_by(student_id=current_user.id).all()
    verified_ids = [v.skill_id for v in verifications]
    verified_skills = [
        s.skill_name for s in Skill.query.filter(Skill.id.in_(verified_ids)).all()
    ]

    data = request.get_json() or {}
    additional_skills = data.get('additional_skills', [])

    sim_result = salary_predictor.simulate_future_salary(
        current_skills=verified_skills,
        additional_skills=additional_skills
    )

    return jsonify(sim_result), 200


@student_bp.route('/badges', methods=['GET'])
@login_required
def get_badges_endpoint():
    """
    Returns unlocked and in-progress achievement badges.
    """
    badges = get_student_badges(current_user.id)
    return jsonify({'badges': badges}), 200


@student_bp.route('/career_insights', methods=['GET'])
@login_required
def get_career_insights():
    """
    Returns benchmark requirements, market demand, and student match rate across popular careers.
    """
    verifications = SkillVerification.query.filter_by(student_id=current_user.id).all()
    verified_ids = [v.skill_id for v in verifications]
    verified_skills = [
        s.skill_name for s in Skill.query.filter(Skill.id.in_(verified_ids)).all()
    ]

    popular_roles = ['Software Engineer', 'Data Scientist', 'Web Developer', 'Cloud Engineer', 'AI Engineer']
    insights = []

    for role in popular_roles:
        gaps = skill_gap_model.evaluate_gaps(verified_skills, role)
        salary_info = salary_predictor.predict_salary(gaps.get('matched_required', []))
        insights.append({
            'role': role,
            'match_percentage': round(gaps.get('overall_coverage', 0) * 100, 1),
            'matched_count': len(gaps.get('matched_required', [])),
            'missing_count': len(gaps.get('missing_required', [])),
            'missing_skills': gaps.get('missing_required', [])[:4],
            'estimated_salary_lpa': salary_info['estimated_lpa']
        })

    return jsonify({'careers': insights}), 200


@student_bp.route('/assessments', methods=['GET'])
@login_required
def get_student_assessments():
    """
    Returns available skills eligible for quizzes and completed assessment attempts.
    """
    skills = Skill.query.filter_by(student_id=current_user.id).all()
    verifications = SkillVerification.query.filter_by(student_id=current_user.id).all()
    v_map = {v.skill_id: v for v in verifications}

    available = []
    completed = []

    for s in skills:
        if s.id in v_map:
            v = v_map[s.id]
            completed.append({
                'skill_id': s.id,
                'skill_name': s.skill_name,
                'extraction_confidence': s.extraction_confidence,
                'score_percent': v.quiz_score_percent,
                'verification_score': v.verification_score,
                'verified_on': v.verified_on.isoformat(),
                'passed': v.quiz_score_percent >= 60.0
            })
        else:
            available.append({
                'skill_id': s.id,
                'skill_name': s.skill_name,
                'extraction_confidence': s.extraction_confidence
            })

    return jsonify({
        'available': available,
        'completed': completed
    }), 200


@student_bp.route('/career_recommendations', methods=['GET'])
@login_required
def get_career_recommendations():
    """
    Returns ranked career recommendations based strictly on verified skills,
    along with transparent explainability metrics for each career.
    """
    verifications = SkillVerification.query.filter_by(student_id=current_user.id).all()
    verified_ids = [v.skill_id for v in verifications]
    verified_skills = [
        s.skill_name for s in Skill.query.filter(Skill.id.in_(verified_ids)).all()
    ]
    recommendations = get_all_career_recommendations(
        verified_skills, current_user.target_career
    )
    top = recommendations[0] if recommendations else None
    return jsonify({
        'recommendations': recommendations,
        'top_recommendation': top,
        'total_evaluated': len(recommendations),
        'verified_skills_count': len(verified_skills)
    }), 200


@student_bp.route('/career_recommendation/<string:career_name>', methods=['GET'])
@login_required
def get_single_career_recommendation(career_name):
    """
    Returns deep explainability and match analysis for a specified career.
    """
    verifications = SkillVerification.query.filter_by(student_id=current_user.id).all()
    verified_ids = [v.skill_id for v in verifications]
    verified_skills = [
        s.skill_name for s in Skill.query.filter(Skill.id.in_(verified_ids)).all()
    ]
    result = evaluate_career_match(verified_skills, career_name)
    if not result:
        return jsonify({'error': f'Career "{career_name}" not found or requirements unavailable'}), 404
    return jsonify(result), 200


@student_bp.route('/compare_careers', methods=['POST'])
@login_required
def compare_careers_endpoint():
    """
    Compares 2-3 careers side-by-side on match %, readiness, missing skills, effort, and salary.
    """
    data = request.get_json(silent=True) or {}
    career_names = data.get('careers', [])
    if not career_names or not isinstance(career_names, list):
        return jsonify({'error': 'Please provide a list of careers to compare'}), 400

    verifications = SkillVerification.query.filter_by(student_id=current_user.id).all()
    verified_ids = [v.skill_id for v in verifications]
    verified_skills = [
        s.skill_name for s in Skill.query.filter(Skill.id.in_(verified_ids)).all()
    ]

    comparison = compare_career_tracks(verified_skills, career_names[:4])
    return jsonify({'comparison': comparison}), 200


@student_bp.route('/verified_skill_profile', methods=['GET'])
@login_required
def get_verified_skill_profile():
    """
    Returns structured 4-tier skill profile:
    1. Verified (passed quiz >= 70%)
    2. Needs Improvement (quiz taken < 70%)
    3. Needs Verification (resume-detected, not yet tested)
    4. Target Gaps (skills needed for target career but missing)
    """
    skills = Skill.query.filter_by(student_id=current_user.id).all()
    verifications = SkillVerification.query.filter_by(student_id=current_user.id).all()
    v_map = {v.skill_id: v for v in verifications}

    verified_list = []
    needs_improvement_list = []
    needs_verification_list = []

    for s in skills:
        if s.id in v_map:
            v = v_map[s.id]
            is_passed = (v.quiz_score_percent or 0) >= 70.0
            item = {
                'skill_id': s.id,
                'skill_name': s.skill_name,
                'proficiency': s.proficiency or 'Intermediate',
                'resume_detected': True,
                'quiz_score_percent': v.quiz_score_percent,
                'quiz_correct_count': v.quiz_correct_count,
                'quiz_question_count': v.quiz_question_count,
                'verified_on': v.verified_on.isoformat() if v.verified_on else None,
                'status': 'VERIFIED' if is_passed else 'NEEDS_IMPROVEMENT'
            }
            if is_passed:
                verified_list.append(item)
            else:
                needs_improvement_list.append(item)
        else:
            needs_verification_list.append({
                'skill_id': s.id,
                'skill_name': s.skill_name,
                'proficiency': s.proficiency or 'Beginner',
                'resume_detected': True,
                'quiz_score_percent': None,
                'quiz_correct_count': None,
                'quiz_question_count': None,
                'verified_on': None,
                'status': 'NEEDS_VERIFICATION'
            })

    target_career_gaps = []
    if current_user.target_career:
        verified_names = [v['skill_name'].lower() for v in verified_list]
        reqs = get_career_requirements(current_user.target_career)
        if reqs:
            for req_skill in reqs.get('required', []):
                if req_skill not in verified_names:
                    target_career_gaps.append({
                        'skill_name': req_skill,
                        'category': 'Required',
                        'importance': 'High',
                        'status': 'UNVERIFIED_GAP'
                    })

    return jsonify({
        'verified_skills': verified_list,
        'needs_improvement': needs_improvement_list,
        'needs_verification': needs_verification_list,
        'target_career_gaps': target_career_gaps,
        'summary': {
            'total_detected': len(skills),
            'verified_count': len(verified_list),
            'needs_improvement_count': len(needs_improvement_list),
            'needs_verification_count': len(needs_verification_list)
        }
    }), 200


@student_bp.route('/privacy_info', methods=['GET'])
@login_required
def get_student_privacy_info():
    """
    Returns non-operational privacy guarantees and educational telemetry
    explaining how raw student data is kept sovereign and local.
    """
    return jsonify({
        'title': 'Privacy-Preserving Intelligence',
        'description': 'Your career data is protected using privacy-preserving learning techniques.',
        'guarantees': [
            'Raw training data remains local',
            'Model updates are shared',
            'Federated aggregation is used',
            'Differential Privacy provides additional protection'
        ],
        'details': {
            'local_sovereignty': 'Raw resumes, transcripts, and quiz responses remain on-premise.',
            'gradient_sharing': 'Only numerical model weights (gradients) are communicated.',
            'aggregation_method': 'Federated Averaging (FedAvg) aggregates distributed updates.',
            'differential_privacy': 'Calibrated Gaussian perturbation prevents reconstruction attacks.'
        }
    }), 200


@student_bp.route('/federated_status', methods=['GET'])
@login_required
def get_student_federated_status():
    """
    Safe read-only informational privacy status for student dashboard.
    """
    status = get_federated_status()
    return jsonify({
        'status': status.get('status', 'Operational'),
        'privacy_statement': status.get('privacy_statement', ''),
        'differential_privacy': status.get('differential_privacy', {})
    }), 200


@student_bp.route('/ask_assistant', methods=['POST'])
@login_required
def ask_assistant_endpoint():
    """
    Answers career guidance queries grounded strictly on the student's actual profile data and RAG knowledge.
    """
    data = request.get_json(silent=True) or {}
    question = data.get('question', '').strip()
    selected_job_id = data.get('selected_job_id')
    if not question:
        return jsonify({'error': 'Please provide a question'}), 400

    verifications = SkillVerification.query.filter_by(student_id=current_user.id).all()
    verified_ids = [v.skill_id for v in verifications]
    verified_skills = [
        s.skill_name for s in Skill.query.filter(Skill.id.in_(verified_ids)).all()
    ]
    gaps = SkillGap.query.filter_by(student_id=current_user.id).all()
    missing_skills = [g.missing_skill for g in gaps if g.missing_skill]

    recs = get_all_career_recommendations(verified_skills, current_user.target_career)
    top_rec = recs[0] if recs else None
    salary_info = salary_predictor.predict_salary(verified_skills)

    profile = {
        'student_id': current_user.id,
        'target_career': current_user.target_career,
        'readiness_score': current_user.readiness_score or 0.0,
        'verified_skills': verified_skills,
        'missing_skills': missing_skills,
        'predicted_salary_lpa': salary_info.get('estimated_lpa', 6.0),
        'top_recommended_career': top_rec.get('career') if top_rec else None,
        'top_career_match_percent': top_rec.get('match_percentage') if top_rec else None
    }

    result = ask_career_assistant(
        profile,
        question,
        student_id=current_user.id,
        selected_job_id=int(selected_job_id) if selected_job_id else None
    )
    return jsonify(result), 200


# ─────────────────────────────────────────
# JOB & INTERNSHIP DISCOVERY ENDPOINTS
# ─────────────────────────────────────────
@student_bp.route('/jobs', methods=['GET'])
@login_required
def get_jobs():
    from utils.job_discovery import job_discovery_service
    from models import SavedJob
    query = request.args.get('query')
    job_type = request.args.get('job_type')
    domain = request.args.get('domain')
    work_arrangement = request.args.get('work_arrangement')
    skill = request.args.get('skill')
    is_sample_arg = request.args.get('is_sample')
    is_sample = None
    if is_sample_arg is not None and is_sample_arg.lower() != 'all':
        is_sample = is_sample_arg.lower() in ['true', '1']

    limit = min(100, int(request.args.get('limit', 50)))
    jobs = job_discovery_service.search_jobs(
        query=query,
        job_type=job_type,
        domain=domain,
        work_arrangement=work_arrangement,
        skill=skill,
        is_sample=is_sample,
        limit=limit
    )

    # Attach whether the student has saved each job
    saved_ids = set(
        sj.job_id for sj in SavedJob.query.filter_by(student_id=current_user.id).all()
    )
    for j in jobs:
        j['is_saved'] = j['id'] in saved_ids

    return jsonify({'jobs': jobs, 'total': len(jobs)}), 200


@student_bp.route('/jobs/<int:job_id>', methods=['GET'])
@login_required
def get_job_detail(job_id):
    from utils.job_discovery import job_discovery_service
    from models import SavedJob
    job = job_discovery_service.get_job_by_id(job_id)
    if not job:
        return jsonify({'error': 'Job listing not found'}), 404

    is_saved = SavedJob.query.filter_by(student_id=current_user.id, job_id=job_id).first() is not None
    job['is_saved'] = is_saved
    return jsonify(job), 200


@student_bp.route('/jobs/sync', methods=['POST'])
@login_required
def sync_job_sources():
    from utils.job_discovery import job_discovery_service
    result = job_discovery_service.sync_all_sources(limit_per_source=25)
    return jsonify(result), 200


@student_bp.route('/jobs/quality_metrics', methods=['GET'])
@login_required
def get_job_quality_metrics():
    from utils.job_discovery import job_discovery_service
    metrics = job_discovery_service.get_quality_metrics()
    return jsonify({'metrics': metrics, **metrics}), 200



@student_bp.route('/jobs/save', methods=['POST'])
@login_required
def save_job_endpoint():
    from utils.job_discovery import job_discovery_service
    data = request.get_json(silent=True) or {}
    job_id = data.get('job_id')
    notes = data.get('notes')
    if not job_id:
        return jsonify({'error': 'job_id is required'}), 400

    res = job_discovery_service.save_job_for_student(current_user.id, int(job_id), notes)
    return jsonify(res), 200


@student_bp.route('/jobs/save/<int:job_id>', methods=['DELETE'])
@login_required
def unsave_job_endpoint(job_id):
    from utils.job_discovery import job_discovery_service
    success = job_discovery_service.remove_saved_job(current_user.id, job_id)
    return jsonify({'success': success, 'job_id': job_id}), 200


@student_bp.route('/jobs/unsave', methods=['POST'])
@login_required
def unsave_job_post_endpoint():
    from utils.job_discovery import job_discovery_service
    data = request.get_json(silent=True) or {}
    job_id = data.get('job_id')
    if not job_id:
        return jsonify({'error': 'job_id is required'}), 400
    success = job_discovery_service.remove_saved_job(current_user.id, int(job_id))
    return jsonify({'success': success, 'job_id': job_id}), 200



@student_bp.route('/jobs/saved', methods=['GET'])
@login_required
def get_saved_jobs_endpoint():
    from utils.job_discovery import job_discovery_service
    saved = job_discovery_service.get_saved_jobs_for_student(current_user.id)
    return jsonify({'saved_jobs': saved, 'total': len(saved)}), 200


# ─────────────────────────────────────────
# EXPLAINABLE JOB-SPECIFIC MATCHING
# ─────────────────────────────────────────
@student_bp.route('/jobs/<int:job_id>/match', methods=['GET'])
@login_required
def get_job_match_breakdown(job_id):
    from models import JobListing
    from utils.job_matcher import evaluate_job_match
    job = JobListing.query.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    evaluation = evaluate_job_match(current_user, job)
    return jsonify(evaluation), 200


@student_bp.route('/jobs/compare', methods=['POST'])
@login_required
def compare_jobs_endpoint():
    from utils.job_matcher import compare_multiple_jobs
    data = request.get_json(silent=True) or {}
    job_ids = data.get('job_ids', [])
    if not job_ids or not isinstance(job_ids, list):
        return jsonify({'error': 'job_ids array is required'}), 400

    res = compare_multiple_jobs(current_user, [int(jid) for jid in job_ids[:4]])
    return jsonify(res), 200


# ─────────────────────────────────────────
# JOB-SPECIFIC INTERVIEW PREPARATION
# ─────────────────────────────────────────
@student_bp.route('/interview/start', methods=['POST'])
@login_required
def start_interview_endpoint():
    from utils.interview_simulator import start_interview_session
    data = request.get_json(silent=True) or {}
    job_id = data.get('job_id')
    custom_title = data.get('custom_title') or data.get('target_role')
    custom_desc = data.get('custom_desc')

    session_data = start_interview_session(
        student_id=current_user.id,
        job_id=int(job_id) if job_id else None,
        custom_title=custom_title,
        custom_desc=custom_desc
    )
    return jsonify({'session': session_data, **session_data}), 200


@student_bp.route('/interview/answer', methods=['POST'])
@login_required
def submit_interview_answer():
    from utils.interview_simulator import evaluate_interview_answer
    data = request.get_json(silent=True) or {}
    session_id = data.get('session_id')
    question_index = data.get('question_index') or data.get('question_id') or 1
    candidate_answer = data.get('candidate_answer') or data.get('spoken_or_typed_answer') or data.get('answer')

    if not session_id or not candidate_answer:
        return jsonify({'error': 'session_id and candidate_answer are required'}), 400

    try:
        eval_res = evaluate_interview_answer(
            session_id=int(session_id),
            question_index=int(question_index),
            candidate_answer=candidate_answer,
            student_id=current_user.id
        )
        return jsonify({'evaluation': eval_res, **eval_res}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@student_bp.route('/interview/history', methods=['GET'])
@login_required
def get_interview_history():
    from utils.interview_simulator import get_student_interview_history
    sessions = get_student_interview_history(current_user.id)
    return jsonify({'history': sessions, 'sessions': sessions, 'total': len(sessions)}), 200


@student_bp.route('/interview/session/<int:session_id>', methods=['GET'])
@login_required
def get_interview_session_detail(session_id):
    from models import InterviewSession
    session = InterviewSession.query.filter_by(id=session_id, student_id=current_user.id).first()
    if not session:
        return jsonify({'error': 'Interview session not found'}), 404
    d = session.to_dict()
    return jsonify({'session': d, **d}), 200


# ─────────────────────────────────────────
# AI PROVIDER MANAGEMENT (Gemini / Ollama / Grok)
# ─────────────────────────────────────────
@student_bp.route('/ai_providers', methods=['GET'])
@login_required
def get_ai_providers_endpoint():
    from utils.ai_providers import ai_provider_manager
    status_list = ai_provider_manager.get_providers_status()
    return jsonify({
        'providers': status_list,
        'active_provider': ai_provider_manager.active_provider_key
    }), 200


@student_bp.route('/ai_providers/select', methods=['POST'])
@login_required
def select_ai_provider():
    from utils.ai_providers import ai_provider_manager
    data = request.get_json(silent=True) or {}
    provider_key = data.get('provider_key') or data.get('provider_name')
    if not provider_key:
        return jsonify({'error': 'provider_key is required'}), 400

    ok = ai_provider_manager.set_active_provider(provider_key)
    if not ok:
        return jsonify({'error': f'Invalid provider: {provider_key}'}), 400

    return jsonify({
        'status': 'success',
        'active_provider': ai_provider_manager.active_provider_key
    }), 200


# ─────────────────────────────────────────
# MULTI-PATH CAREER SIMULATION
# ─────────────────────────────────────────
@student_bp.route('/simulate_paths', methods=['POST'])
@login_required
def simulate_career_paths_endpoint():
    from utils.career_recommender import simulate_multi_career_paths
    data = request.get_json(silent=True) or {}
    career_names = data.get('career_names') or data.get('paths') or []
    if not career_names or not isinstance(career_names, list):
        return jsonify({'error': 'career_names list is required'}), 400

    verifications = SkillVerification.query.filter_by(student_id=current_user.id).all()
    verified_ids = [v.skill_id for v in verifications]
    verified_skills = [
        s.skill_name for s in Skill.query.filter(Skill.id.in_(verified_ids)).all()
    ]

    simulation = simulate_multi_career_paths(
        verified_skills=verified_skills,
        career_names=career_names[:4],
        target_career=current_user.target_career
    )
    return jsonify({'simulation': simulation, **simulation}), 200



# ─────────────────────────────────────────
# STUDENT DATA MANAGEMENT & DELETION
# ─────────────────────────────────────────
@student_bp.route('/account/export', methods=['GET'])
@login_required
def export_student_data():
    """
    Exports full student profile, verifications, progress history, and saved data as JSON.
    """
    from utils.job_discovery import job_discovery_service
    from utils.interview_simulator import get_student_interview_history
    skills = [s.to_dict() for s in Skill.query.filter_by(student_id=current_user.id).all()]
    verifications = [v.to_dict() for v in SkillVerification.query.filter_by(student_id=current_user.id).all()]
    progress = [p.to_dict() for p in current_user.progress]
    study_plans = [sp.to_dict() for sp in current_user.study_plans]
    saved_jobs = job_discovery_service.get_saved_jobs_for_student(current_user.id)
    interviews = get_student_interview_history(current_user.id)

    student_dict = current_user.to_dict()
    export_payload = {
        'student': student_dict,
        'profile': student_dict,
        'extracted_skills': skills,
        'skills': skills,
        'verified_competencies': verifications,
        'progress_timeline': progress,
        'study_plans': study_plans,
        'saved_jobs': saved_jobs,
        'interview_sessions': interviews,
        'interview_history': interviews,
        'exported_at': datetime.utcnow().isoformat(),
        'data_sovereignty_notice': 'This export includes all profile and learning artifacts stored under your account.'
    }
    return jsonify(export_payload), 200


@student_bp.route('/account/delete', methods=['DELETE'])
@login_required
def delete_student_account():
    """
    Permanently deletes student account and cascades all associated private records.
    Requires explicit confirmation payload to prevent accidental deletion.
    """
    from flask_login import logout_user
    from models import Student
    data = request.get_json(silent=True) or {}
    confirmation = data.get('confirmation', '')
    if confirmation != 'DELETE_MY_ACCOUNT':
        return jsonify({'error': 'Explicit confirmation required. Send {"confirmation": "DELETE_MY_ACCOUNT"}'}), 400

    student = Student.query.get(current_user.id)
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    db.session.delete(student)
    db.session.commit()
    logout_user()

    return jsonify({
        'status': 'deleted',
        'message': 'Account and all associated private learning records have been permanently erased.'
    }), 200

