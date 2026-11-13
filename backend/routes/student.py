# pyrefly: ignore [missing-import]

from flask import Blueprint, request, jsonify, current_app, send_file
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
from utils.resume_optimizer import (
    parse_resume_to_structured_json,
    analyze_resume,
    enhance_resume_with_ai,
    generate_resume_pdf,
    generate_resume_docx
)
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

    try:
        # Fetch all existing skills for this student across all resumes
        existing_skills = Skill.query.filter_by(student_id=current_user.id).all()
        existing_skills_by_name = {s.skill_name.lower().strip(): s for s in existing_skills}

        # Skills that already have a verification must be preserved
        verified_skill_ids = {
            v.skill_id for v in SkillVerification.query.filter_by(
                student_id=current_user.id
            ).all()
        }

        saved_skills = []

        import json as _json
        for item in extracted:
            skill_name_clean = item['skill_name'].strip()
            key = skill_name_clean.lower()
            confidence = item.get('extraction_confidence', 1.0)
            evidence_fields = {
                'evidence_strength': item.get('evidence_strength'),
                'evidence': _json.dumps(item.get('evidence', [])),
                'extraction_explanation': (item.get('explanation') or '')[:400],
                'category': item.get('category'),
            }

            if key in existing_skills_by_name:
                existing = existing_skills_by_name[key]
                # The latest resume is the current evidence for this skill
                existing.extraction_confidence = confidence
                for f, v in evidence_fields.items():
                    setattr(existing, f, v)
                # Keep pointer to latest resume if not locked by verification
                if existing.id not in verified_skill_ids:
                    existing.resume_id = resume.id
                saved_skills.append(existing)
            else:
                skill = Skill(
                    student_id=current_user.id,
                    resume_id=resume.id,
                    skill_name=skill_name_clean,
                    extraction_confidence=confidence,
                    proficiency=None,
                    **evidence_fields
                )
                db.session.add(skill)
                existing_skills_by_name[key] = skill
                saved_skills.append(skill)

        db.session.commit()

        return jsonify({
            'message': f'{len(saved_skills)} skills extracted',
            'skills': [s.to_dict() for s in saved_skills],
            'note': ('Extraction confidence says how sure we are the resume mentions the skill; '
                     'evidence strength says how well the resume supports it. Proficiency is only '
                     'established by passing the skill quiz.')
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to extract skills: {str(e)}'}), 500

import random
from models import QuestionBank, SkillVerification

EVIDENCE_WEIGHT = {'applied': 1.0, 'supporting': 0.7, 'listed_only': 0.4, 'unclassified': 0.4}


def _option_order(student_id, question_id):
    """Per-student, per-question option order. The stored bank is skewed
    toward answers B/C (and AI generators repeat that bias); showing options
    in a keyed, stable shuffled order removes the 'always pick B' shortcut.
    Returns perm where perm[i] is the ORIGINAL letter shown at position i."""
    import hashlib
    secret = current_app.config.get('SECRET_KEY') or 'skillbridge'
    seed = hashlib.sha256(f"{secret}:{student_id}:{question_id}".encode()).hexdigest()
    perm = ['A', 'B', 'C', 'D']
    random.Random(seed).shuffle(perm)
    return perm


def _shuffled_question(q, student_id):
    d = q.to_dict()
    perm = _option_order(student_id, q.id)
    for pos, orig in zip('abcd', perm):
        d[f'option_{pos}'] = getattr(q, f'option_{orig.lower()}')
    return d


def get_quiz_question_count(confidence, evidence_strength=None):
    """Weaker resume evidence -> more questions are needed to verify the skill."""
    if evidence_strength in EVIDENCE_WEIGHT:
        return {'applied': 5, 'supporting': 6, 'listed_only': 8, 'unclassified': 8}[evidence_strength]
    # legacy rows (extracted before evidence tracking)
    confidence = confidence or 0.0
    if confidence >= 0.7:
        return 5
    elif confidence >= 0.4:
        return 6
    return 8


@student_bp.route('/get_quiz/<int:skill_id>', methods=['GET'])
@login_required
def get_quiz(skill_id):
    skill = Skill.query.filter_by(
        id=skill_id, student_id=current_user.id
    ).first()

    if not skill:
        return jsonify({'error': 'Skill not found or does not belong to you'}), 404

    question_count = get_quiz_question_count(skill.extraction_confidence, skill.evidence_strength)

    # Ensure at least MINIMUM_QUESTIONS_PER_SKILL exist, generating
    # only the missing (validated) amount via the AI provider if needed
    ensure_minimum_questions(skill.skill_name)

    available_questions = QuestionBank.query.filter_by(
        skill_name=skill.skill_name
    ).all()

    from utils.question_bank_manager import MIN_QUESTIONS_TO_VERIFY
    if len(available_questions) < MIN_QUESTIONS_TO_VERIFY:
        return jsonify({
            'error': f'Not enough validated quiz questions for "{skill.skill_name}" yet '
                     f'({len(available_questions)} of {MIN_QUESTIONS_TO_VERIFY} needed). '
                     'Question generation is currently unavailable - please try again later.',
            'available_questions': len(available_questions),
        }), 503

    # Balanced difficulty mix (Easy/Medium/Hard round-robin), random within each level
    by_level = {}
    for q in available_questions:
        by_level.setdefault((q.difficulty or 'Medium').title(), []).append(q)
    for qs in by_level.values():
        random.shuffle(qs)
    order = [lvl for lvl in ('Easy', 'Medium', 'Hard') if lvl in by_level] + \
            [lvl for lvl in by_level if lvl not in ('Easy', 'Medium', 'Hard')]
    selected = []
    target = min(question_count, len(available_questions))
    while len(selected) < target:
        for lvl in order:
            if by_level[lvl] and len(selected) < target:
                selected.append(by_level[lvl].pop())

    return jsonify({
        'skill_id': skill.id,
        'skill_name': skill.skill_name,
        'extraction_confidence': skill.extraction_confidence,
        'question_count': len(selected),
        'questions': [_shuffled_question(q, current_user.id) for q in selected]
    }), 200

@student_bp.route('/submit_quiz/<int:skill_id>', methods=['POST'])
@login_required
def submit_quiz(skill_id):
    skill = Skill.query.filter_by(
        id=skill_id, student_id=current_user.id
    ).first()

    if not skill:
        return jsonify({'error': 'Skill not found or does not belong to you'}), 404

    data = request.get_json(silent=True) or {}
    # Expected format: {"answers": {"3": "B", "7": "A", "12": "C"}}
    # keys are QuestionBank ids (as strings from JSON), values are the
    # student's chosen option letter
    submitted_answers = data.get('answers', {})

    if not submitted_answers or not isinstance(submitted_answers, dict):
        return jsonify({'error': 'No answers submitted'}), 400

    try:
        question_ids = [int(qid) for qid in submitted_answers.keys()]
    except (TypeError, ValueError):
        return jsonify({'error': 'Answer keys must be question ids'}), 400

    # Only questions belonging to THIS skill count (prevents answering easier
    # questions from another skill to get verified).
    questions = QuestionBank.query.filter(
        QuestionBank.id.in_(question_ids),
        QuestionBank.skill_name == skill.skill_name
    ).all()
    if len(questions) != len(set(question_ids)):
        return jsonify({'error': 'Some answers do not belong to this skill\'s quiz'}), 400

    # A verification needs the full quiz, not a hand-picked subset of answers
    from utils.question_bank_manager import MIN_QUESTIONS_TO_VERIFY
    available = QuestionBank.query.filter_by(skill_name=skill.skill_name).count()
    if available < MIN_QUESTIONS_TO_VERIFY:
        return jsonify({'error': f'This skill cannot be verified yet: only {available} validated questions exist '
                                 f'(minimum {MIN_QUESTIONS_TO_VERIFY}).'}), 400
    required_count = min(get_quiz_question_count(skill.extraction_confidence, skill.evidence_strength), available)
    if len(questions) < required_count:
        return jsonify({'error': f'Please answer all {required_count} questions of the quiz '
                                 f'({len(questions)} answered).'}), 400

    correct_count = 0
    review = []
    weak_by_level = {}
    for question in questions:
        # Options were shown in a per-student shuffled order; translate the
        # displayed letter back to the stored one before scoring.
        perm = _option_order(current_user.id, question.id)
        submitted = submitted_answers.get(str(question.id))
        shown = str(submitted).upper() if submitted else None
        original = perm['ABCD'.index(shown)] if shown in ('A', 'B', 'C', 'D') else None
        correct_shown = 'ABCD'[perm.index((question.correct_answer or 'A').upper())]
        is_correct = original is not None and original == (question.correct_answer or '').upper()
        if is_correct:
            correct_count += 1
        else:
            lvl = (question.difficulty or 'Medium').title()
            weak_by_level[lvl] = weak_by_level.get(lvl, 0) + 1
        review.append({
            'question_id': question.id,
            'question': question.question,
            'difficulty': question.difficulty,
            'your_answer': shown,
            'correct_answer': correct_shown,   # letter as displayed to this student
            'correct_option_text': getattr(question, f'option_{(question.correct_answer or "a").lower()}', None),
            'is_correct': is_correct,
        })

    total_questions = len(questions)
    quiz_score_percent = round((correct_count / total_questions) * 100, 2) \
        if total_questions > 0 else 0

    # Verification score: quiz performance dominates (it is the only direct
    # measurement of proficiency); resume evidence adds a smaller component.
    # Extraction confidence is NOT used - it only says the skill was mentioned.
    evidence_weight = EVIDENCE_WEIGHT.get(skill.evidence_strength, 0.4)
    verification_score = round(
        (evidence_weight * 0.25) +
        ((quiz_score_percent / 100) * 0.75),
        2
    )
    if quiz_score_percent >= 80:
        skill.proficiency = 'Advanced' if quiz_score_percent >= 90 and total_questions >= 6 else 'Intermediate'
    elif quiz_score_percent >= 50:
        skill.proficiency = 'Beginner'
    else:
        skill.proficiency = 'Not yet demonstrated'

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
        'verification_score': verification_score,
        'proficiency': skill.proficiency,
        'review': review,
        'incorrect_by_difficulty': weak_by_level,
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

    return jsonify({'roadmap': _ordered_roadmap(current_user.id)}), 200


def _ordered_roadmap(student_id):
    """Roadmap grouped by skill, ordered required gaps first (in the career's
    priority order), then nice-to-have gaps. Each group says whether the skill
    already appears on the student's resume, so they can verify it with a quiz
    instead of studying it from scratch."""
    plan_rows = StudyPlan.query.filter_by(student_id=student_id) \
        .order_by(StudyPlan.day_number).all()
    if not plan_rows:
        return []

    gaps = SkillGap.query.filter_by(student_id=student_id).order_by(SkillGap.id).all()
    rank = {'high': 0, 'medium': 1, 'low': 2}
    gap_order = {}
    for pos, g in enumerate(gaps):
        key = (g.missing_skill or '').lower()
        gap_order.setdefault(key, (rank.get((g.importance or '').lower(), 3), pos, g))

    resume_skills = {s.skill_name.lower(): s for s in Skill.query.filter_by(student_id=student_id).all()}

    grouped = {}
    for p in plan_rows:
        grouped.setdefault(p.skill_name, []).append(p.to_dict())

    def sort_key(skill):
        return gap_order.get((skill or '').lower(), (9, 999, None))[:2]

    out = []
    for skill in sorted(grouped, key=sort_key):
        g = gap_order.get((skill or '').lower(), (None, None, None))[2]
        on_resume = resume_skills.get((skill or '').lower())
        out.append({
            'skill': skill,
            'importance': g.importance if g else None,
            'category': g.category if g else None,
            'already_on_resume': on_resume is not None,
            'evidence_strength': on_resume.evidence_strength if on_resume else None,
            'recommendation': (
                f"Your resume already shows {skill}. Take its verification quiz first - "
                f"you may only need the later, more advanced days."
                if on_resume is not None else None),
            'days': grouped[skill],
        })
    return out


@student_bp.route('/get_roadmap', methods=['GET'])
@login_required
def get_roadmap():
    roadmap = _ordered_roadmap(current_user.id)
    if not roadmap:
        return jsonify({'roadmap': [], 'message': 'No roadmap yet.'}), 200
    return jsonify({'roadmap': roadmap}), 200


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
    seen_names = set()
    for s in skills:
        clean_name = s.skill_name.lower().strip()
        if clean_name in seen_names:
            continue
        seen_names.add(clean_name)

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
    Guarantees unique skill representation without duplicates.
    """
    skills = Skill.query.filter_by(student_id=current_user.id).all()
    verifications = SkillVerification.query.filter_by(student_id=current_user.id).all()
    v_map = {v.skill_id: v for v in verifications}

    # Also build a lookup of verifications by skill name
    v_by_name = {}
    for v in verifications:
        sk = db.session.get(Skill, v.skill_id)
        if sk:
            v_by_name[sk.skill_name.lower().strip()] = v

    available = []
    completed = []
    seen_names = set()

    for s in skills:
        clean_name = s.skill_name.lower().strip()
        if clean_name in seen_names:
            continue
        seen_names.add(clean_name)

        v = v_map.get(s.id) or v_by_name.get(clean_name)
        if v:
            completed.append({
                'skill_id': s.id,
                'skill_name': s.skill_name,
                'extraction_confidence': s.extraction_confidence,
                'score_percent': v.quiz_score_percent,
                'verification_score': v.verification_score,
                'verified_on': v.verified_on.isoformat(),
                'passed': (v.quiz_score_percent or 0) >= 60.0
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
    seen_names = set()

    for s in skills:
        clean_name = s.skill_name.lower().strip()
        if clean_name in seen_names:
            continue
        seen_names.add(clean_name)

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
        'description': 'How SkillBridge handles your data, stated plainly.',
        'guarantees': [
            'Your resume, skills and quiz results are only accessible to your account',
            'You can export or permanently delete your data at any time',
            'The federated-learning module is a simulation on synthetic data',
            'Federated updates are clipped and noised; no formal differential-privacy guarantee is claimed'
        ],
        'details': {
            'data_storage': 'Uploaded resumes are stored on the SkillBridge server so they can be parsed and analysed.',
            'access_control': 'Every student endpoint is scoped to the logged-in account.',
            'aggregation_method': 'The FL simulation uses Federated Averaging over simulated partitions.',
            'differential_privacy': 'Update clipping + Gaussian noise are applied, but no privacy accountant is '
                                    'implemented, so no epsilon/delta is claimed.'
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

    selected_job_id = (request.get_json(silent=True) or {}).get('selected_job_id')
    result = ask_career_assistant(
        profile,
        question,
        student_id=current_user.id,
        selected_job_id=int(selected_job_id) if selected_job_id else None
    )
    return jsonify(result), 200


# =============================================================================
# RAG (RETRIEVAL-AUGMENTED GENERATION) ENDPOINTS
# =============================================================================

@student_bp.route('/rag/analyze_resume/<int:resume_id>', methods=['POST'])
@login_required
def rag_analyze_resume_endpoint(resume_id):
    """
    Semantic RAG analysis of an uploaded resume:
    Retrieves matching industry benchmarks, segregates explicit vs. inferred skills,
    and returns a grounded AI career evaluation citing authoritative sources.
    """
    resume = Resume.query.filter_by(id=resume_id, student_id=current_user.id).first()
    if not resume:
        return jsonify({'error': 'Resume not found or does not belong to you'}), 404

    # Ensure text is parsed
    if not resume.parsed_text:
        target_path = resume.file_path
        if not os.path.exists(target_path):
            alt_path = os.path.join(current_app.root_path, target_path)
            if os.path.exists(alt_path):
                target_path = alt_path
        try:
            resume.parsed_text = parse_resume(target_path)
            resume.parsed_on = datetime.now(timezone.utc)
            db.session.commit()
        except Exception as e:
            return jsonify({'error': f'Resume parsing required before RAG analysis: {str(e)}'}), 400

    try:
        from rag.rag_pipeline import get_rag_pipeline
        pipeline = get_rag_pipeline(current_app.root_path)
        data = request.get_json(silent=True) or {}
        target_career = data.get('target_career') or current_user.target_career

        result = pipeline.analyze_resume_rag(resume.parsed_text, target_career=target_career)
        return jsonify({
            'status': 'success',
            'resume_id': resume.id,
            'rag_analysis': result
        }), 200
    except Exception as e:
        current_app.logger.error(f"RAG Resume Analysis error: {e}", exc_info=True)
        return jsonify({'error': f'RAG Analysis encountered an error: {str(e)}'}), 500


@student_bp.route('/rag/match_job', methods=['POST'])
@login_required
def rag_match_job_endpoint():
    """
    Evaluates candidate's skills and resume against a custom job description using RAG:
    Computes semantic similarity, identifies explicit matches vs missing requirements,
    and produces grounded interview advice.
    """
    data = request.get_json(silent=True) or {}
    job_desc = data.get('job_description', '').strip()
    if not job_desc:
        return jsonify({'error': 'Please provide a job description to match against'}), 400

    # Retrieve candidate verified skills
    verifications = SkillVerification.query.filter_by(student_id=current_user.id).all()
    verified_ids = [v.skill_id for v in verifications]
    verified_skills = [
        s.skill_name for s in Skill.query.filter(Skill.id.in_(verified_ids)).all()
    ]

    # Retrieve candidate resume text if available
    resume_text = ""
    resume_id = data.get('resume_id')
    if resume_id:
        res = Resume.query.filter_by(id=resume_id, student_id=current_user.id).first()
        if res and res.parsed_text:
            resume_text = res.parsed_text
    if not resume_text:
        latest_res = Resume.query.filter_by(student_id=current_user.id, is_latest=True).first()
        if latest_res and latest_res.parsed_text:
            resume_text = latest_res.parsed_text

    try:
        from rag.rag_pipeline import get_rag_pipeline
        pipeline = get_rag_pipeline(current_app.root_path)
        result = pipeline.match_job_rag(
            resume_text=resume_text,
            job_description_text=job_desc,
            student_skills=verified_skills
        )
        return jsonify({
            'status': 'success',
            'match_results': result
        }), 200
    except Exception as e:
        current_app.logger.error(f"RAG Job Match error: {e}", exc_info=True)
        return jsonify({'error': f'Job Match encountered an error: {str(e)}'}), 500


@student_bp.route('/rag/explain_gap', methods=['POST'])
@login_required
def rag_explain_gap_endpoint():
    """
    Generates an authoritative, citation-backed skill gap explanation for the student's career track.
    """
    data = request.get_json(silent=True) or {}
    career_name = data.get('career') or current_user.target_career or 'Software Engineer'

    verifications = SkillVerification.query.filter_by(student_id=current_user.id).all()
    verified_ids = [v.skill_id for v in verifications]
    verified_skills = [
        s.skill_name for s in Skill.query.filter(Skill.id.in_(verified_ids)).all()
    ]

    try:
        from rag.rag_pipeline import get_rag_pipeline
        pipeline = get_rag_pipeline(current_app.root_path)
        result = pipeline.explain_skill_gap_rag(
            student_verified_skills=verified_skills,
            career_name=career_name
        )
        return jsonify({
            'status': 'success',
            'gap_report': result
        }), 200
    except Exception as e:
        current_app.logger.error(f"RAG Explain Gap error: {e}", exc_info=True)
        return jsonify({'error': f'Skill Gap Explanation error: {str(e)}'}), 500


@student_bp.route('/rag/catalog', methods=['GET'])
@login_required
def rag_catalog_endpoint():
    """
    Returns available career benchmarks and real-world job postings currently indexed in RAG.
    """
    try:
        from rag.knowledge_manager import get_knowledge_manager
        km = get_knowledge_manager(current_app.root_path)
        careers = km.get_all_careers()
        jds = km.get_all_job_descriptions()
        return jsonify({
            'status': 'success',
            'careers': careers,
            'job_descriptions': jds,
            'total_indexed_chunks': km.vector_store.size()
        }), 200
    except Exception as e:
        current_app.logger.error(f"RAG Catalog error: {e}", exc_info=True)
        return jsonify({'error': f'Could not retrieve RAG catalog: {str(e)}'}), 500


@student_bp.route('/rag/add_job', methods=['POST'])
@login_required
def rag_add_job_endpoint():
    """
    Allows adding a new job description to the persistent RAG knowledge base.
    """
    data = request.get_json(silent=True) or {}
    role = data.get('role', '').strip()
    company = data.get('company', '').strip()
    description = data.get('description', '').strip()
    required_skills = data.get('required_skills', [])

    if not role or not description:
        return jsonify({'error': 'Role and description are required'}), 400

    try:
        from rag.knowledge_manager import get_knowledge_manager
        km = get_knowledge_manager(current_app.root_path)
        chunk = km.add_custom_job_description({
            'role': role,
            'company': company or 'Enterprise Organization',
            'location': data.get('location', 'Remote'),
            'salary_range': data.get('salary_range', 'Industry Standard'),
            'career_category': data.get('career_category', role).lower(),
            'description': description,
            'required_skills': required_skills,
            'preferred_skills': data.get('preferred_skills', []),
            'responsibilities': data.get('responsibilities', description[:200]),
            'source': data.get('source', f"{company or 'Custom'} Hiring Specification")
        })
        return jsonify({
            'status': 'success',
            'message': f"Job description for '{role}' successfully added to RAG knowledge base",
            'job_id': chunk.get('chunk_id')
        }), 201
    except Exception as e:
        current_app.logger.error(f"Add custom JD error: {e}", exc_info=True)
        return jsonify({'error': f'Could not add job description: {str(e)}'}), 500



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
    region = request.args.get('region')

    # Handle remote_only boolean flag from frontend
    remote_only = request.args.get('remote_only')
    if remote_only and remote_only.lower() in ['true', '1']:
        work_arrangement = 'Remote'

    # Handle sample / live filtering flags
    is_sample = None
    is_sample_arg = request.args.get('is_sample')
    sample_only = request.args.get('sample_only')
    live_only = request.args.get('live_only')

    if sample_only and sample_only.lower() in ['true', '1']:
        is_sample = True
    elif live_only and live_only.lower() in ['true', '1']:
        is_sample = False
    elif is_sample_arg is not None and is_sample_arg.lower() != 'all':
        is_sample = is_sample_arg.lower() in ['true', '1']

    limit_arg = request.args.get('limit') or request.args.get('per_page') or '50'
    try:
        limit = min(100, int(limit_arg))
    except (ValueError, TypeError):
        limit = 50

    def _flag(name):
        v = request.args.get(name)
        return v is not None and v.lower() in ('true', '1', 'yes')

    def _float(name):
        try:
            v = request.args.get(name)
            return float(v) if v not in (None, '') else None
        except (TypeError, ValueError):
            return None

    try:
        page = max(1, int(request.args.get('page', 1)))
    except (TypeError, ValueError):
        page = 1
    sort = request.args.get('sort', 'relevance')
    if sort not in ('relevance', 'recent', 'match', 'salary'):
        sort = 'relevance'
    opportunity = (request.args.get('opportunity') or '').lower()  # job | internship
    internship = True if opportunity == 'internship' else False if opportunity == 'job' else None

    result = job_discovery_service.search_jobs(
        query=query,
        job_type=job_type,
        domain=domain,
        work_arrangement=work_arrangement,
        skill=skill,
        is_sample=is_sample,
        region=region,
        limit=limit,
        location=request.args.get('location'),
        company=request.args.get('company'),
        entry_level=_flag('entry_level'),
        internship=internship,
        experience_max=_float('experience_max'),
        salary_min=_float('salary_min'),
        date_posted=request.args.get('date_posted'),
        include_expired=_flag('include_expired'),
        sort=sort,
        page=page,
        student=current_user,
        min_match=_float('min_match'),
        return_meta=True,
    )
    jobs = result['jobs']

    # Attach whether the student has saved each job
    saved_ids = set(
        sj.job_id for sj in SavedJob.query.filter_by(student_id=current_user.id).all()
    )

    # Attach whether the student has applied to each job
    from models import JobApplication
    applications_map = {
        app.job_id: app.to_dict()
        for app in JobApplication.query.filter_by(student_id=current_user.id).all()
    }

    # Filter applied_only if requested
    applied_only = request.args.get('applied_only')
    if applied_only and applied_only.lower() in ['true', '1']:
        jobs = [j for j in jobs if j['id'] in applications_map]

    for j in jobs:
        j['is_saved'] = j['id'] in saved_ids
        j['is_applied'] = j['id'] in applications_map
        j['application'] = applications_map.get(j['id'])

    return jsonify({
        'jobs': jobs,
        'total': result['total'],
        'total_count': result['total'],
        'page': result['page'],
        'pages': result['pages'],
        'per_page': result['per_page'],
        'sort': sort,
        'applied_count': len(applications_map)
    }), 200


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
    # Provider quotas are small and shared by everyone, so only admins may
    # trigger an extra sync. Listings refresh automatically every two hours.
    if not current_user.is_admin:
        from utils.job_discovery.sync_service import next_due_at
        return jsonify({
            'error': 'Job listings refresh automatically every two hours. Manual sync is limited to administrators.',
            'next_scheduled_sync': next_due_at().isoformat()
        }), 403
    from utils.job_discovery import job_discovery_service
    from utils.audit import audit
    result = job_discovery_service.discover_and_sync(trigger='manual', actor_id=current_user.id)
    audit('jobs.manual_sync', actor_id=current_user.id, target=f"job_sync_run:{result['run']['id']}",
          details={'status': result['status']})
    return jsonify(result), 200


# ─────────────────────────────────────────
# JOB PREFERENCES & ALERTS
# ─────────────────────────────────────────
def _clean_str_list(value, max_items=15, max_len=80):
    if not isinstance(value, list):
        return []
    out = []
    for v in value[:max_items]:
        if isinstance(v, str) and v.strip():
            out.append(v.strip()[:max_len])
    return out


@student_bp.route('/job_preferences', methods=['GET'])
@login_required
def get_job_preferences():
    from models import JobPreference
    pref = JobPreference.query.filter_by(student_id=current_user.id).first()
    default = {'preferred_roles': [], 'preferred_locations': [], 'work_modes': [], 'job_types': [],
               'experience_years': 0.0, 'open_to_relocation': False, 'updated_at': None}
    return jsonify({'preferences': pref.to_dict() if pref else default, 'is_set': pref is not None}), 200


@student_bp.route('/job_preferences', methods=['PUT', 'POST'])
@login_required
def update_job_preferences():
    import json as _json
    from models import JobPreference
    data = request.get_json(silent=True) or {}
    try:
        years = float(data.get('experience_years', 0) or 0)
    except (TypeError, ValueError):
        return jsonify({'error': 'experience_years must be a number'}), 400
    if not 0 <= years <= 50:
        return jsonify({'error': 'experience_years must be between 0 and 50'}), 400
    modes = [m for m in _clean_str_list(data.get('work_modes')) if m.lower() in ('remote', 'hybrid', 'onsite')]
    pref = JobPreference.query.filter_by(student_id=current_user.id).first()
    if pref is None:
        pref = JobPreference(student_id=current_user.id)
        db.session.add(pref)
    pref.preferred_roles = _json.dumps(_clean_str_list(data.get('preferred_roles')))
    pref.preferred_locations = _json.dumps(_clean_str_list(data.get('preferred_locations')))
    pref.work_modes = _json.dumps(modes)
    pref.job_types = _json.dumps(_clean_str_list(data.get('job_types')))
    pref.experience_years = years
    pref.open_to_relocation = bool(data.get('open_to_relocation', False))
    db.session.commit()
    return jsonify({'message': 'Job preferences saved', 'preferences': pref.to_dict()}), 200


@student_bp.route('/job_alerts', methods=['GET'])
@login_required
def list_job_alerts():
    from models import JobAlert
    alerts = JobAlert.query.filter_by(student_id=current_user.id).order_by(JobAlert.created_at.desc()).all()
    return jsonify({'alerts': [a.to_dict() for a in alerts]}), 200


def _apply_alert_payload(alert, data):
    import json as _json
    name = (data.get('name') or '').strip()
    if not name and alert.name is None:
        return 'name is required'
    if name:
        alert.name = name[:120]
    for field in ('roles', 'locations', 'skills', 'job_types', 'work_modes'):
        if field in data:
            setattr(alert, field, _json.dumps(_clean_str_list(data.get(field))))
    if 'frequency' in data:
        if data['frequency'] not in ('instant', 'daily', 'weekly'):
            return "frequency must be 'instant', 'daily' or 'weekly'"
        alert.frequency = data['frequency']
    if 'min_match_score' in data:
        try:
            score = float(data['min_match_score'])
        except (TypeError, ValueError):
            return 'min_match_score must be a number'
        if not 0 <= score <= 100:
            return 'min_match_score must be between 0 and 100'
        alert.min_match_score = score
    if 'is_active' in data:
        alert.is_active = bool(data['is_active'])
    if not any(_json.loads(getattr(alert, f) or '[]') for f in ('roles', 'skills', 'locations')):
        return 'An alert needs at least one role, skill or location'
    return None


@student_bp.route('/job_alerts', methods=['POST'])
@login_required
def create_job_alert():
    from models import JobAlert
    if JobAlert.query.filter_by(student_id=current_user.id).count() >= 10:
        return jsonify({'error': 'You can have at most 10 job alerts'}), 400
    data = request.get_json(silent=True) or {}
    alert = JobAlert(student_id=current_user.id, name=None, roles='[]', locations='[]', skills='[]',
                     job_types='[]', work_modes='[]', frequency='daily', min_match_score=50.0, is_active=True)
    err = _apply_alert_payload(alert, data)
    if err:
        return jsonify({'error': err}), 400
    db.session.add(alert)
    db.session.commit()
    return jsonify({'message': 'Job alert created', 'alert': alert.to_dict()}), 201


@student_bp.route('/job_alerts/<int:alert_id>', methods=['PUT', 'PATCH'])
@login_required
def update_job_alert(alert_id):
    from models import JobAlert
    alert = JobAlert.query.filter_by(id=alert_id, student_id=current_user.id).first()
    if not alert:
        return jsonify({'error': 'Alert not found'}), 404
    err = _apply_alert_payload(alert, request.get_json(silent=True) or {})
    if err:
        db.session.rollback()
        return jsonify({'error': err}), 400
    db.session.commit()
    return jsonify({'message': 'Job alert updated', 'alert': alert.to_dict()}), 200


@student_bp.route('/job_alerts/<int:alert_id>', methods=['DELETE'])
@login_required
def delete_job_alert(alert_id):
    from models import JobAlert
    alert = JobAlert.query.filter_by(id=alert_id, student_id=current_user.id).first()
    if not alert:
        return jsonify({'error': 'Alert not found'}), 404
    db.session.delete(alert)
    db.session.commit()
    return jsonify({'message': 'Job alert deleted'}), 200


@student_bp.route('/job_alerts/notifications', methods=['GET'])
@login_required
def get_job_alert_notifications():
    from models import JobAlertMatch
    unread_only = request.args.get('unread_only', '').lower() in ('1', 'true')
    q = JobAlertMatch.query.filter(JobAlertMatch.student_id == current_user.id,
                                   JobAlertMatch.released_at.isnot(None))
    if unread_only:
        q = q.filter(JobAlertMatch.is_read.is_(False))
    items = q.order_by(JobAlertMatch.released_at.desc()).limit(50).all()
    unread = JobAlertMatch.query.filter(JobAlertMatch.student_id == current_user.id,
                                        JobAlertMatch.released_at.isnot(None),
                                        JobAlertMatch.is_read.is_(False)).count()
    return jsonify({'notifications': [m.to_dict() for m in items], 'unread_count': unread}), 200


@student_bp.route('/job_alerts/notifications/read', methods=['POST'])
@login_required
def mark_job_alert_notifications_read():
    from models import JobAlertMatch
    data = request.get_json(silent=True) or {}
    ids = data.get('ids')
    q = JobAlertMatch.query.filter(JobAlertMatch.student_id == current_user.id)
    if isinstance(ids, list) and ids:
        q = q.filter(JobAlertMatch.id.in_([int(i) for i in ids if str(i).isdigit()]))
    updated = q.update({'is_read': True}, synchronize_session=False)
    db.session.commit()
    return jsonify({'updated': updated}), 200


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
# JOB APPLICATION ACTIONS
# ─────────────────────────────────────────
@student_bp.route('/jobs/<int:job_id>/apply', methods=['POST'])
@student_bp.route('/jobs/apply', methods=['POST'])
@login_required
def apply_to_job(job_id=None):
    from models import JobListing, JobApplication, Resume
    from utils.job_matcher import evaluate_job_match

    data = request.get_json(silent=True) or {}
    target_job_id = job_id or data.get('job_id')
    if not target_job_id:
        return jsonify({'error': 'job_id is required'}), 400

    job = JobListing.query.get(target_job_id)
    if not job:
        return jsonify({'error': 'Job listing not found'}), 404

    # Check if already applied
    existing = JobApplication.query.filter_by(
        student_id=current_user.id,
        job_id=target_job_id
    ).first()

    if existing:
        return jsonify({
            'message': 'You have already applied for this role',
            'status': 'already_applied',
            'application': existing.to_dict()
        }), 200

    # Determine resume to attach
    resume_id = data.get('resume_id')
    if not resume_id:
        latest_resume = Resume.query.filter_by(student_id=current_user.id, is_latest=True).first()
        if latest_resume:
            resume_id = latest_resume.id

    cover_note = (data.get('cover_note') or '').strip()
    contact_email = (data.get('contact_email') or current_user.email).strip()
    portfolio_url = (data.get('portfolio_url') or '').strip()

    # Calculate deterministic match score at time of application
    try:
        eval_res = evaluate_job_match(current_user, job, include_resources=False)
        match_score = eval_res.get('match_score')  # None when the posting lists no skills
    except Exception:
        current_app.logger.exception('Match scoring failed during application')
        match_score = None

    new_app = JobApplication(
        student_id=current_user.id,
        job_id=target_job_id,
        applied_at=datetime.now(timezone.utc),
        status='Applied',
        resume_id=resume_id,
        cover_note=cover_note,
        contact_email=contact_email,
        portfolio_url=portfolio_url,
        match_score=match_score
    )
    db.session.add(new_app)
    db.session.commit()

    return jsonify({
        'message': f'Application for {job.title} at {job.company} submitted successfully!',
        'status': 'applied',
        'application': new_app.to_dict()
    }), 201


@student_bp.route('/jobs/applied', methods=['GET'])
@student_bp.route('/jobs/applications', methods=['GET'])
@login_required
def get_applied_jobs():
    from models import JobApplication
    apps = JobApplication.query.filter_by(
        student_id=current_user.id
    ).order_by(JobApplication.applied_at.desc()).all()
    return jsonify({
        'applications': [a.to_dict() for a in apps],
        'total_count': len(apps)
    }), 200


@student_bp.route('/jobs/<int:job_id>/withdraw', methods=['POST', 'DELETE'])
@student_bp.route('/jobs/withdraw', methods=['POST'])
@login_required
def withdraw_application(job_id=None):
    from models import JobApplication
    data = request.get_json(silent=True) or {}
    target_job_id = job_id or data.get('job_id')
    if not target_job_id:
        return jsonify({'error': 'job_id is required'}), 400

    app_record = JobApplication.query.filter_by(
        student_id=current_user.id,
        job_id=target_job_id
    ).first()

    if not app_record:
        return jsonify({'error': 'Application record not found'}), 404

    db.session.delete(app_record)
    db.session.commit()

    return jsonify({
        'message': 'Application withdrawn successfully',
        'status': 'withdrawn',
        'job_id': target_job_id
    }), 200


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

    # Format matched_skills as array of objects with {skill, is_verified} for direct UI mapping
    matched_list = []
    for s in evaluation.get('matched_skills', {}).get('verified', []):
        matched_list.append({'skill': s, 'is_verified': True})
    for s in evaluation.get('matched_skills', {}).get('unverified', []):
        matched_list.append({'skill': s, 'is_verified': False})
    status = evaluation.get('skill_status', {})
    for s in evaluation.get('matched_skills', {}).get('preferred', []):
        matched_list.append({'skill': s, 'is_verified': status.get(s) == 'verified', 'is_preferred': True})

    missing_mandatory = evaluation.get('missing_skills', {}).get('mandatory', [])
    missing_preferred = evaluation.get('missing_skills', {}).get('preferred', [])

    # Format resource recommendations map
    resource_map = {}
    for r in evaluation.get('curated_resources', []):
        sk = r.get('skill_query') or (missing_mandatory[0] if missing_mandatory else 'technology')
        url = r.get('url') or ''
        if sk not in resource_map:
            resource_map[sk] = {}
        if 'youtube.com' in url and 'youtube' not in resource_map[sk]:
            resource_map[sk]['youtube'] = url
        elif 'github.com' in url and 'github' not in resource_map[sk]:
            resource_map[sk]['github'] = url

    # Format transferable bridges with transfer_coefficient
    bridges = []
    for b in evaluation.get('transferable_bridges', []):
        bridges.append({
            'user_skill': b.get('user_skill'),
            'target_skill': b.get('target_skill'),
            'transfer_coefficient': b.get('transfer_coefficient', 0.8),
            'rationale': b.get('rationale', '')
        })

    payload = {
        **evaluation,
        'matched_skills': matched_list,
        'matched_skills_dict': evaluation.get('matched_skills'),
        'missing_mandatory_skills': missing_mandatory,
        'missing_preferred_skills': missing_preferred,
        'resource_recommendations': resource_map,
        'transferable_bridges': bridges,
        'match_score': evaluation.get('match_score', 0)
    }

    return jsonify({
        'match': payload,
        **payload
    }), 200


@student_bp.route('/jobs/compare', methods=['POST'])
@login_required
def compare_jobs_endpoint():
    from utils.job_matcher import compare_multiple_jobs
    data = request.get_json(silent=True) or {}
    job_ids = data.get('job_ids', [])
    if not job_ids or not isinstance(job_ids, list):
        return jsonify({'error': 'job_ids array is required'}), 400

    res = compare_multiple_jobs(current_user, [int(jid) for jid in job_ids[:4]])
    return jsonify({
        'comparison': res,
        **res
    }), 200


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
    session_id = data.get('session_id') or data.get('sessionId')
    question_index = data.get('question_index') or data.get('questionIndex')
    candidate_answer = (
        data.get('candidate_answer') or 
        data.get('spoken_or_typed_answer') or 
        data.get('answer')
    )

    if not session_id or not candidate_answer:
        return jsonify({'error': 'session_id and candidate_answer are required'}), 400

    # If question_index not given, look up by question_id
    if not question_index:
        qid = data.get('question_id') or data.get('questionId')
        if qid:
            from models import InterviewQA
            qa_rec = InterviewQA.query.filter_by(id=int(qid), session_id=int(session_id)).first()
            if qa_rec:
                question_index = qa_rec.question_index
            else:
                question_index = 1
        else:
            question_index = 1

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
        'exported_at': datetime.now(timezone.utc).isoformat(),
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

    # Uploaded resume files live outside the database; collect them before the
    # cascade deletes the Resume rows, remove them after the commit succeeds.
    from utils.resume_files import delete_resume_files
    resume_files = [r.file_path for r in student.resumes if r.file_path]

    db.session.delete(student)
    db.session.commit()
    files_removed = delete_resume_files(resume_files)
    logout_user()

    return jsonify({
        'status': 'deleted',
        'resume_files_removed': files_removed,
        'message': 'Account, all associated private learning records and uploaded resume files '
                   'have been permanently erased.'
    }), 200


# ─────────────────────────────────────────────────────────────
# RESUME OPTIMIZER ENDPOINTS
# ─────────────────────────────────────────────────────────────

@student_bp.route('/resume_optimizer/careers', methods=['GET'])
@login_required
def get_resume_optimizer_careers():
    """Returns available predefined career tracks with required & preferred skills."""
    from data.career_requirements import CAREER_REQUIREMENTS
    careers = []
    for c_name, reqs in sorted(CAREER_REQUIREMENTS.items()):
        careers.append({
            'id': c_name,
            'title': c_name.title(),
            'required': reqs.get('required', []),
            'nice_to_have': reqs.get('nice_to_have', [])
        })
    return jsonify({'careers': careers}), 200


@student_bp.route('/resume_optimizer/my_resumes', methods=['GET'])
@login_required
def get_student_resumes_for_optimizer():
    """
    Returns the authenticated student's uploaded resumes.
    Strictly isolated to current_user.id for privacy protection.
    """
    resumes = Resume.query.filter_by(student_id=current_user.id).order_by(Resume.uploaded_on.desc()).all()
    return jsonify({
        'resumes': [{
            'id': r.id,
            'original_filename': r.original_filename or f"Resume #{r.id}",
            'uploaded_on': r.uploaded_on.isoformat() if r.uploaded_on else None,
            'is_latest': r.is_latest,
            'has_parsed_text': bool(r.parsed_text and len(r.parsed_text.strip()) > 30)
        } for r in resumes]
    }), 200


@student_bp.route('/resume_optimizer/analyze', methods=['POST'])
@login_required
def analyze_resume_for_optimization():
    """
    Analyzes a student resume against a target career or custom job description.
    Supports either direct file upload or selection of an existing resume record.
    Calculates deterministic job-match % and generates anti-hallucinatory AI improvements.
    """
    raw_text = None
    original_filename = "Resume"

    # Option A: Directly uploaded file
    if 'resume' in request.files and request.files['resume'].filename:
        file = request.files['resume']
        if not file.filename or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file format. Only PDF and DOCX documents are supported.'}), 400

        # Validate file size (10 MB max)
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        if size > 10 * 1024 * 1024:
            return jsonify({'error': 'File size exceeds maximum limit of 10MB.'}), 400

        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        raw_filename: str = file.filename or 'resume.pdf'
        orig_name = secure_filename(raw_filename)
        ext = orig_name.rsplit('.', 1)[1].lower()
        temp_name = f"temp_opt_{current_user.id}_{uuid.uuid4().hex}.{ext}"
        temp_path = os.path.join(UPLOAD_FOLDER, temp_name)
        try:
            file.save(temp_path)
            raw_text = parse_resume(temp_path)
            original_filename = orig_name
        except Exception as e:
            return jsonify({'error': f"Failed to extract text from file: {str(e)}"}), 400
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
    else:
        # Option B: Existing resume by ID or latest
        resume_id = request.form.get('resume_id') or (request.get_json(silent=True) or {}).get('resume_id')
        if not resume_id:
            latest_resume = Resume.query.filter_by(student_id=current_user.id, is_latest=True).first()
            if latest_resume:
                resume_id = latest_resume.id
            else:
                return jsonify({'error': 'Please upload a resume file (PDF/DOCX) or select an existing resume.'}), 400

        resume = Resume.query.filter_by(id=resume_id, student_id=current_user.id).first()
        if not resume:
            return jsonify({'error': 'Resume not found or unauthorized.'}), 404

        original_filename = resume.original_filename or f"Resume #{resume.id}"
        if resume.parsed_text and len(resume.parsed_text.strip()) > 30:
            raw_text = resume.parsed_text
        elif resume.file_path and os.path.exists(resume.file_path):
            try:
                raw_text = parse_resume(resume.file_path)
                resume.parsed_text = raw_text
                resume.parsed_on = datetime.now(timezone.utc)
                db.session.commit()
            except Exception as e:
                return jsonify({'error': f"Could not parse resume file: {str(e)}"}), 400
        else:
            return jsonify({'error': 'Resume file content could not be located on disk.'}), 404

    if not raw_text or len(raw_text.strip()) < 30:
        return jsonify({'error': 'Insufficient text extracted from resume. Please ensure the document is not an image scan.'}), 400

    target_career = request.form.get('target_career') or (request.get_json(silent=True) or {}).get('target_career') or ''
    job_description = request.form.get('job_description') or (request.get_json(silent=True) or {}).get('job_description') or ''

    if not target_career and not job_description:
        target_career = getattr(current_user, 'target_career', None) or 'Software Engineer'

    # Step 1: Structured parsing
    structured_sections = parse_resume_to_structured_json(raw_text)

    # Step 2: Deterministic Python Job-Match Analysis
    analysis = analyze_resume(structured_sections, target_career=target_career, job_description=job_description)

    # Step 3: AI Enhancement with strict anti-hallucination rules & deterministic fallback
    enhancement = enhance_resume_with_ai(structured_sections, analysis, target_career=target_career)

    return jsonify({
        'filename': original_filename,
        'target_career': target_career or "Custom Role",
        'has_custom_jd': bool(job_description),
        'match_analysis': analysis,
        'original_sections': structured_sections,
        'optimized_sections': enhancement['optimized_sections'],
        'suggestions': enhancement['suggestions'],
        'student_prompts': enhancement['student_prompts'],
        'ai_powered': enhancement['ai_powered']
    }), 200


@student_bp.route('/resume_optimizer/export_pdf', methods=['POST'])
@login_required
def export_optimized_resume_pdf():
    """Exports edited, finalized resume content to an ATS-ready PDF."""
    data = request.get_json(silent=True) or {}
    sections = data.get('sections')
    if not sections or not isinstance(sections, dict):
        return jsonify({'error': 'Missing or invalid sections payload'}), 400

    try:
        pdf_buffer = generate_resume_pdf(sections)
        filename = secure_filename(data.get('filename') or 'Optimized_Resume.pdf')
        if not filename.lower().endswith('.pdf'):
            filename += '.pdf'
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'error': f"Failed to generate PDF: {str(e)}"}), 500


@student_bp.route('/resume_optimizer/export_docx', methods=['POST'])
@login_required
def export_optimized_resume_docx():
    """Exports edited, finalized resume content to a clean Microsoft Word (.docx) document."""
    data = request.get_json(silent=True) or {}
    sections = data.get('sections')
    if not sections or not isinstance(sections, dict):
        return jsonify({'error': 'Missing or invalid sections payload'}), 400

    try:
        docx_buffer = generate_resume_docx(sections)
        filename = secure_filename(data.get('filename') or 'Optimized_Resume.docx')
        if not filename.lower().endswith('.docx'):
            filename += '.docx'
        return send_file(
            docx_buffer,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'error': f"Failed to generate DOCX: {str(e)}"}), 500

