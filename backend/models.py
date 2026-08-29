from extensions import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# ─────────────────────────────────────────
# STUDENT MODEL
# ─────────────────────────────────────────
class Student(db.Model, UserMixin):
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

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'college': self.college,
            'course': self.course,
            'year': self.year,
            'target_career': self.target_career,
            'readiness_score': self.readiness_score,
            'created_at': self.created_at.isoformat()
        }


# ─────────────────────────────────────────
# RESUME MODEL
# ─────────────────────────────────────────
class Resume(db.Model):
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
class Skill(db.Model):
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
class SkillVerification(db.Model):
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
class QuestionBank(db.Model):
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
class SkillGap(db.Model):
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
class StudyPlan(db.Model):
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
class Progress(db.Model):
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
class FLTrainingRound(db.Model):
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


class RoadmapTemplate(db.Model):
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