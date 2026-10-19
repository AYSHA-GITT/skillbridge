from typing import Any
import json
from extensions import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class BaseModel(db.Model):
    __abstract__ = True
    __allow_unmapped__ = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


# ─────────────────────────────────────────
# STUDENT MODEL
# ─────────────────────────────────────────
class Student(BaseModel, UserMixin):
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    college = db.Column(db.String(200))
    course = db.Column(db.String(200))
    year = db.Column(db.String(20))
    target_career = db.Column(db.String(200))  # replaces target_company
    readiness_score = db.Column(db.Float, default=0.0)
    role = db.Column(db.String(20), default='student', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)


    resumes = db.relationship('Resume', backref='student',
                                lazy=True, cascade='all, delete-orphan')
    skills = db.relationship('Skill', backref='student',
                              lazy=True, cascade='all, delete-orphan')
    skill_gaps = db.relationship('SkillGap', backref='student',
                                  lazy=True, cascade='all, delete-orphan')
    progress = db.relationship('Progress', backref='student',
                                lazy=True, cascade='all, delete-orphan')
    study_plans = db.relationship('StudyPlan', backref='student',
                                   lazy=True, cascade='all, delete-orphan')
    verifications = db.relationship('SkillVerification', backref='student',
                                     lazy=True, cascade='all, delete-orphan')
    saved_jobs = db.relationship('SavedJob', backref='student',
                                  lazy=True, cascade='all, delete-orphan')
    interviews = db.relationship('InterviewSession', backref='student',
                                  lazy=True, cascade='all, delete-orphan')


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return (self.role or '').lower() == 'admin'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role or 'student',
            'college': self.college,
            'course': self.course,
            'year': self.year,
            'target_career': self.target_career,
            'readiness_score': self.readiness_score,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ─────────────────────────────────────────
# RESUME MODEL
# ─────────────────────────────────────────
class Resume(BaseModel):
    __tablename__ = 'resumes'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    original_filename = db.Column(db.String(200))
    parsed_text = db.Column(db.Text)  # raw extracted text
    parsed_on = db.Column(db.DateTime)
    uploaded_on = db.Column(db.DateTime, default=datetime.utcnow)
    is_latest = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'original_filename': self.original_filename,
            'uploaded_on': self.uploaded_on.isoformat(),
            'is_latest': self.is_latest
        }


# ─────────────────────────────────────────
# SKILL MODEL (now sourced from NLP extraction)
# ─────────────────────────────────────────
class Skill(BaseModel):
    __tablename__ = 'skills'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'))
    skill_name = db.Column(db.String(100), nullable=False)
    extraction_confidence = db.Column(db.Float)  # 0.0 to 1.0, from NLP
    proficiency = db.Column(db.String(50))  # inferred: Beginner/Intermediate/Advanced
    added_on = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'skill_name': self.skill_name,
            'extraction_confidence': self.extraction_confidence,
            'proficiency': self.proficiency,
            'added_on': self.added_on.isoformat()
        }


# ─────────────────────────────────────────
# SKILL VERIFICATION MODEL (confidence-based quiz)
# ─────────────────────────────────────────
class SkillVerification(BaseModel):
    __tablename__ = 'skill_verifications'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    skill_id = db.Column(db.Integer, db.ForeignKey('skills.id'), nullable=False)
    extraction_confidence = db.Column(db.Float)      # copied at verification time
    quiz_question_count = db.Column(db.Integer)       # 3-5 or 8-10 based on confidence
    quiz_correct_count = db.Column(db.Integer)
    quiz_score_percent = db.Column(db.Float)
    verification_score = db.Column(db.Float)  # weighted: resume evidence + quiz
    verified_on = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'skill_id': self.skill_id,
            'quiz_question_count': self.quiz_question_count,
            'quiz_correct_count': self.quiz_correct_count,
            'quiz_score_percent': self.quiz_score_percent,
            'verification_score': self.verification_score,
            'verified_on': self.verified_on.isoformat()
        }


# ─────────────────────────────────────────
# QUESTION BANK (kept, but tied to skill+difficulty tiering)
# ─────────────────────────────────────────
class QuestionBank(BaseModel):
    __tablename__ = 'question_bank'

    id = db.Column(db.Integer, primary_key=True)
    skill_name = db.Column(db.String(100), nullable=False)
    question = db.Column(db.String(500), nullable=False)
    option_a = db.Column(db.String(200))
    option_b = db.Column(db.String(200))
    option_c = db.Column(db.String(200))
    option_d = db.Column(db.String(200))
    correct_answer = db.Column(db.String(1))  # A/B/C/D
    difficulty = db.Column(db.String(20))     # Easy, Medium, Hard

    def to_dict(self):
        return {
            'id': self.id,
            'skill_name': self.skill_name,
            'question': self.question,
            'option_a': self.option_a,
            'option_b': self.option_b,
            'option_c': self.option_c,
            'option_d': self.option_d,
            'difficulty': self.difficulty
            # correct_answer intentionally excluded
        }


# ─────────────────────────────────────────
# SKILL GAP MODEL
# ─────────────────────────────────────────
class SkillGap(BaseModel):
    __tablename__ = 'skill_gaps'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    missing_skill = db.Column(db.String(100))
    importance = db.Column(db.String(50))  # High, Medium, Low
    estimated_days = db.Column(db.Integer)
    category = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'missing_skill': self.missing_skill,
            'importance': self.importance,
            'estimated_days': self.estimated_days,
            'category': self.category
        }


# ─────────────────────────────────────────
# STUDY PLAN / LEARNING ROADMAP MODEL
# ─────────────────────────────────────────
class StudyPlan(BaseModel):
    __tablename__ = 'study_plans'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    skill_name = db.Column(db.String(100))

    day_number = db.Column(db.Integer)
    topic = db.Column(db.String(200))
    description = db.Column(db.String(500))
    resource_link = db.Column(db.String(500))
    resource_type = db.Column(db.String(50))  # YouTube, Course, Article
    duration_hours = db.Column(db.Float)
    is_completed = db.Column(db.Boolean, default=False)
    completed_on = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'skill_name': self.skill_name,
            'day_number': self.day_number,
            'topic': self.topic,
            'description': self.description,
            'resource_link': self.resource_link,
            'resource_type': self.resource_type,
            'duration_hours': self.duration_hours,
            'is_completed': self.is_completed
        }


# ─────────────────────────────────────────
# PROGRESS MODEL
# ─────────────────────────────────────────
class Progress(BaseModel):
    __tablename__ = 'progress'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    readiness_score = db.Column(db.Float)
    skill_count = db.Column(db.Integer)
    verified_skill_count = db.Column(db.Integer)
    skill_gap_count = db.Column(db.Integer)

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'readiness_score': self.readiness_score,
            'skill_count': self.skill_count,
            'verified_skill_count': self.verified_skill_count,
            'skill_gap_count': self.skill_gap_count
        }


# ─────────────────────────────────────────
# FEDERATED LEARNING TRAINING LOG
# (tracks simulated institution partitions, not real orgs)
# ─────────────────────────────────────────
class FLTrainingRound(BaseModel):
    __tablename__ = 'fl_training_rounds'

    id = db.Column(db.Integer, primary_key=True)
    round_number = db.Column(db.Integer)
    partition_id = db.Column(db.String(50))  # e.g. "Institution_A"
    local_accuracy = db.Column(db.Float)
    global_accuracy_after_round = db.Column(db.Float)
    trained_on = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'round_number': self.round_number,
            'partition_id': self.partition_id,
            'local_accuracy': self.local_accuracy,
            'global_accuracy_after_round': self.global_accuracy_after_round,
            'trained_on': self.trained_on.isoformat()
        }


class RoadmapTemplate(BaseModel):
    __tablename__ = 'roadmap_templates'

    id = db.Column(db.Integer, primary_key=True)
    skill_name = db.Column(db.String(100), nullable=False)
    day_number = db.Column(db.Integer, nullable=False)
    topic = db.Column(db.String(200))
    description = db.Column(db.String(500))
    resource_hint = db.Column(db.String(300))
    duration_hours = db.Column(db.Float)

    def to_dict(self):
        return {
            'day_number': self.day_number,
            'topic': self.topic,
            'description': self.description,
            'resource_hint': self.resource_hint,
            'duration_hours': self.duration_hours,
        }


# ─────────────────────────────────────────
# JOB & INTERNSHIP OPPORTUNITY MODEL
# ─────────────────────────────────────────
class JobListing(BaseModel):
    __tablename__ = 'job_listings'

    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String(150), unique=True, index=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    company = db.Column(db.String(200), nullable=False, index=True)
    location = db.Column(db.String(200), default='Remote')
    job_type = db.Column(db.String(50), default='Full-time')  # Internship, Full-time, Contract, Co-op
    work_arrangement = db.Column(db.String(50), default='Remote')  # Remote, Hybrid, Onsite
    domain = db.Column(db.String(100), default='Software Engineering')  # Software Engineering, Data Science, etc.
    experience_level = db.Column(db.String(50), default='Entry-Level')  # Entry-Level, 0-2 yrs, Mid, Senior
    description = db.Column(db.Text)
    required_skills = db.Column(db.Text, default='[]')  # JSON array
    preferred_skills = db.Column(db.Text, default='[]')  # JSON array
    eligibility = db.Column(db.String(300))  # e.g., "B.Tech/BE in CS/IT/Data or equivalent degree"
    application_url = db.Column(db.String(500))
    source = db.Column(db.String(100), default='SkillBridge Verified Index')
    is_sample = db.Column(db.Boolean, default=False)  # Clearly labels demo vs live scraped
    posting_date = db.Column(db.DateTime, default=datetime.utcnow)
    deadline = db.Column(db.DateTime, nullable=True)
    collected_at = db.Column(db.DateTime, default=datetime.utcnow)

    saved_by = db.relationship('SavedJob', back_populates='job', lazy=True, cascade='all, delete-orphan')



    def get_required_skills(self):
        try:
            return json.loads(self.required_skills) if self.required_skills else []
        except Exception:
            return []

    def get_preferred_skills(self):
        try:
            return json.loads(self.preferred_skills) if self.preferred_skills else []
        except Exception:
            return []

    def to_dict(self):
        from utils.job_discovery.location_prioritizer import get_location_region_label, get_location_rank
        return {
            'id': self.id,
            'external_id': self.external_id,
            'title': self.title,
            'company': self.company,
            'location': self.location,
            'region_badge': get_location_region_label(self.location, self.title, self.company),
            'location_rank': get_location_rank(self.location, self.title, self.company),
            'job_type': self.job_type,
            'work_arrangement': self.work_arrangement,
            'domain': self.domain,
            'experience_level': self.experience_level,
            'description': self.description,
            'required_skills': self.get_required_skills(),
            'preferred_skills': self.get_preferred_skills(),
            'eligibility': self.eligibility,
            'application_url': self.application_url,
            'source': self.source,
            'is_sample': bool(self.is_sample),
            'posting_date': self.posting_date.isoformat() if self.posting_date else None,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'collected_at': self.collected_at.isoformat() if self.collected_at else None,
        }


# ─────────────────────────────────────────
# SAVED JOB MODEL
# ─────────────────────────────────────────
class SavedJob(BaseModel):
    __tablename__ = 'saved_jobs'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job_listings.id'), nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)

    job = db.relationship('JobListing', back_populates='saved_by', foreign_keys=[job_id])


    def to_dict(self):
        job_data = None
        j = getattr(self, 'job', None)
        if j and hasattr(j, 'to_dict'):
            job_data = j.to_dict()
        res = {
            'id': self.job_id,
            'job_id': self.job_id,
            'saved_id': self.id,
            'student_id': self.student_id,
            'saved_at': self.saved_at.isoformat() if self.saved_at else None,
            'notes': self.notes,
            'job': job_data
        }
        if job_data:
            for k, v in job_data.items():
                if k not in res:
                    res[k] = v
        return res



# ─────────────────────────────────────────
# INTERVIEW PREPARATION SESSION & QUESTIONS
# ─────────────────────────────────────────
class InterviewSession(BaseModel):
    __tablename__ = 'interview_sessions'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job_listings.id'), nullable=True)
    job_title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200), default='Target Company')
    overall_score = db.Column(db.Float, default=0.0)
    feedback_summary = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='in_progress')  # in_progress, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    qa_records = db.relationship('InterviewQA', backref='session', lazy=True, cascade='all, delete-orphan', order_by='InterviewQA.question_index')


    def to_dict(self):
        qa_list = []
        records = getattr(self, 'qa_records', None)
        if records:
            for q in records:
                qa_list.append(q.to_dict())
        return {
            'id': self.id,
            'session_id': self.id,
            'student_id': self.student_id,
            'job_id': self.job_id,
            'job_title': self.job_title,
            'company': self.company,
            'overall_score': self.overall_score,
            'feedback_summary': self.feedback_summary,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'questions': qa_list
        }



class InterviewQA(BaseModel):
    __tablename__ = 'interview_qa'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('interview_sessions.id'), nullable=False)
    question_index = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(100), default='Technical Fundamentals')
    question_text = db.Column(db.Text, nullable=False)
    candidate_answer = db.Column(db.Text, nullable=True)
    rubric_score = db.Column(db.Float, default=0.0)
    conceptual_accuracy = db.Column(db.Float, default=0.0)
    completeness = db.Column(db.Float, default=0.0)
    clarity = db.Column(db.Float, default=0.0)
    feedback = db.Column(db.Text, nullable=True)
    missing_points = db.Column(db.Text, default='[]')
    sample_answer = db.Column(db.Text, nullable=True)
    answered_at = db.Column(db.DateTime, nullable=True)

    def get_missing_points(self):
        try:
            return json.loads(self.missing_points) if self.missing_points else []
        except Exception:
            return []

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'question_index': self.question_index,
            'category': self.category,
            'question_text': self.question_text,
            'candidate_answer': self.candidate_answer,
            'rubric_score': self.rubric_score,
            'conceptual_accuracy': self.conceptual_accuracy,
            'completeness': self.completeness,
            'clarity': self.clarity,
            'feedback': self.feedback,
            'missing_points': self.get_missing_points(),
            'sample_answer': self.sample_answer,
            'answered_at': self.answered_at.isoformat() if self.answered_at else None,
        }