from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import uuid
from utils.skill_extractor import extract_skills
from models import Skill, StudyPlan
from extensions import db
from models import Resume
from utils.resume_parser import parse_resume
from utils.ai_question_generator import generate_questions
from utils.skill_gap_analyzer import analyze_skill_gap
from models import SkillVerification, SkillGap
from utils.question_bank_manager import ensure_minimum_questions
from utils.roadmap_generator import ensure_roadmap_template
from utils.progress_tracker import record_student_snapshot, get_progress_timeline
from utils.badge_checker import get_student_badges
from ml.salary_model import salary_predictor
from ml.readiness_model import readiness_scorer
from ml.skill_gap_model import skill_gap_model

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

    if file.filename == '':
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
        uploaded_on=datetime.utcnow(),
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
    resume.parsed_on = datetime.utcnow()
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

    for skill_name in result['missing_required']:
        gap = SkillGap(
            student_id=current_user.id,
            missing_skill=skill_name,
            importance='High',
            category='Required'
        )
        db.session.add(gap)

    for skill_name in result['missing_nice_to_have']:
        gap = SkillGap(
            student_id=current_user.id,
            missing_skill=skill_name,
            importance='Medium',
            category='Nice to have'
        )
        db.session.add(gap)

    # Update readiness score on the student record too
    current_user.readiness_score = round(result['overall_coverage'] * 100, 1)
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
    plan.completed_on = datetime.utcnow()
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