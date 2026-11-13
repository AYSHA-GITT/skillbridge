from typing import Any
import json
from extensions import db
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

def utc_now():
    return datetime.now(timezone.utc)

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
    profile_photo = db.Column(db.String(300), nullable=True)
    readiness_score = db.Column(db.Float, default=0.0)
    role = db.Column(db.String(20), default='student', nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)
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
    applications = db.relationship('JobApplication', backref='student',
                                   lazy=True, cascade='all, delete-orphan')
    interviews = db.relationship('InterviewSession', backref='student',
                                  lazy=True, cascade='all, delete-orphan')
    job_preference = db.relationship('JobPreference', uselist=False, lazy=True,
                                     cascade='all, delete-orphan')
    job_alerts = db.relationship('JobAlert', lazy=True, cascade='all, delete-orphan')
    job_alert_matches = db.relationship('JobAlertMatch', lazy=True, cascade='all, delete-orphan',
                                        overlaps='matches')


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
            'profile_photo': self.profile_photo,
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
    uploaded_on = db.Column(db.DateTime, default=utc_now)
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
    # Rule-based certainty that the resume text refers to this skill (not a probability)
    extraction_confidence = db.Column(db.Float)
    proficiency = db.Column(db.String(50))  # inferred: Beginner/Intermediate/Advanced
    # How well the resume supports the skill: applied | supporting | listed_only | unclassified
    evidence_strength = db.Column(db.String(20))
    evidence = db.Column(db.Text)  # JSON list of {section, snippet}
    extraction_explanation = db.Column(db.String(400))
    category = db.Column(db.String(50))
    added_on = db.Column(db.DateTime, default=utc_now)

    def get_evidence(self):
        try:
            return json.loads(self.evidence) if self.evidence else []
        except Exception:
            return []

    def to_dict(self):
        return {
            'id': self.id,
            'skill_name': self.skill_name,
            'extraction_confidence': self.extraction_confidence,
            'evidence_strength': self.evidence_strength,
            'evidence': self.get_evidence(),
            'extraction_explanation': self.extraction_explanation,
            'category': self.category,
            'proficiency': self.proficiency,
            'added_on': self.added_on.isoformat() if self.added_on else None
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
    verified_on = db.Column(db.DateTime, default=utc_now)

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
    created_at = db.Column(db.DateTime, default=utc_now)

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
    date = db.Column(db.DateTime, default=utc_now)
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
    trained_on = db.Column(db.DateTime, default=utc_now)

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
    # Date the PROVIDER says the job was posted. NULL when the provider does not supply one;
    # never filled with the fetch time, so re-fetching cannot make an old job look new.
    posting_date = db.Column(db.DateTime, nullable=True)
    deadline = db.Column(db.DateTime, nullable=True)
    collected_at = db.Column(db.DateTime, default=utc_now)

    # ── Provenance & deduplication ───────────────────────────────────────
    source_provider = db.Column(db.String(50), index=True)    # adzuna | jooble | arbeitnow | curated_sample
    source_job_id = db.Column(db.String(200))                 # provider's own identifier
    original_url = db.Column(db.String(1000))                 # posting URL as given by provider
    canonical_url = db.Column(db.String(1000), index=True)    # normalized URL used for dedup
    fingerprint = db.Column(db.String(64), index=True)        # hash(title|company|city) for cross-provider dup detection
    content_hash = db.Column(db.String(64))                   # detects changed descriptions/metadata
    duplicate_of_id = db.Column(db.Integer, db.ForeignKey('job_listings.id'), nullable=True)

    # ── Location / structured metadata ───────────────────────────────────
    country = db.Column(db.String(60))
    state = db.Column(db.String(120))
    city = db.Column(db.String(120))
    career_category = db.Column(db.String(100), index=True)
    is_entry_level = db.Column(db.Boolean)
    experience_min_years = db.Column(db.Float)
    experience_max_years = db.Column(db.Float)
    skills_source = db.Column(db.String(30))  # provider_tags | description_text | curated | none

    # ── Salary (only what the provider states) ───────────────────────────
    salary_min = db.Column(db.Float)
    salary_max = db.Column(db.Float)
    salary_currency = db.Column(db.String(8))
    salary_period = db.Column(db.String(20))           # year | month | week | day | hour
    salary_is_estimated = db.Column(db.Boolean)        # True when the provider flags it as predicted

    # ── Freshness / lifecycle ────────────────────────────────────────────
    status = db.Column(db.String(20), default='active', index=True)  # active | stale | expired | sample
    first_seen_at = db.Column(db.DateTime, default=utc_now)
    last_seen_at = db.Column(db.DateTime)        # last time the provider returned this job
    last_verified_at = db.Column(db.DateTime)    # last evidence from source that the job is open
    last_synced_at = db.Column(db.DateTime)
    last_changed_at = db.Column(db.DateTime)
    expired_at = db.Column(db.DateTime)
    expiry_reason = db.Column(db.String(200))
    times_seen = db.Column(db.Integer, default=1)

    saved_by = db.relationship('SavedJob', back_populates='job', lazy=True, cascade='all, delete-orphan')
    applications = db.relationship('JobApplication', back_populates='job', lazy=True, cascade='all, delete-orphan')

    def freshness(self, now=None):
        """User-facing freshness labels derived from real timestamps only."""
        now = now or datetime.now(timezone.utc)

        def _aware(dt):
            if dt is None:
                return None
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

        posted = _aware(self.posting_date)
        verified = _aware(self.last_verified_at)
        posted_days = (now - posted).days if posted else None
        if self.is_sample or self.status == 'sample':
            verification = 'sample'
        elif self.status == 'expired':
            verification = 'expired'
        elif verified and (now - verified).total_seconds() <= 26 * 3600:
            verification = 'verified'
        elif verified:
            verification = 'unverified_recently'
        else:
            verification = 'unverified'
        return {
            'posted_days_ago': posted_days,
            'posted_label': (
                'Posting date not provided' if posted_days is None else
                'Posted today' if posted_days <= 0 else
                f'Posted {posted_days} day{"s" if posted_days != 1 else ""} ago'
            ),
            'is_recent': posted_days is not None and posted_days <= 3,
            'last_checked_at': verified.isoformat() if verified else None,
            'verification_status': verification,
        }

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
            'source_provider': self.source_provider,
            'original_url': self.original_url,
            'country': self.country,
            'state': self.state,
            'city': self.city,
            'career_category': self.career_category,
            'is_entry_level': self.is_entry_level,
            'experience_min_years': self.experience_min_years,
            'experience_max_years': self.experience_max_years,
            'skills_source': self.skills_source,
            'salary': {
                'min': self.salary_min,
                'max': self.salary_max,
                'currency': self.salary_currency,
                'period': self.salary_period,
                'is_estimated': self.salary_is_estimated,
                'label': (
                    None if (self.salary_min is None and self.salary_max is None) else
                    'Estimated by provider' if self.salary_is_estimated else 'Advertised by employer'
                ),
            },
            'status': self.status or 'active',
            'duplicate_of_id': self.duplicate_of_id,
            'first_seen_at': self.first_seen_at.isoformat() if self.first_seen_at else None,
            'last_seen_at': self.last_seen_at.isoformat() if self.last_seen_at else None,
            'last_verified_at': self.last_verified_at.isoformat() if self.last_verified_at else None,
            'last_synced_at': self.last_synced_at.isoformat() if self.last_synced_at else None,
            'expired_at': self.expired_at.isoformat() if self.expired_at else None,
            'expiry_reason': self.expiry_reason,
            'freshness': self.freshness(),
        }


# ─────────────────────────────────────────
# SAVED JOB MODEL
# ─────────────────────────────────────────
class SavedJob(BaseModel):
    __tablename__ = 'saved_jobs'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job_listings.id'), nullable=False)
    saved_at = db.Column(db.DateTime, default=utc_now)
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
# JOB APPLICATION MODEL
# ─────────────────────────────────────────
class JobApplication(BaseModel):
    __tablename__ = 'job_applications'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job_listings.id'), nullable=False)
    applied_at = db.Column(db.DateTime, default=utc_now)
    status = db.Column(db.String(50), default='Applied')  # Applied, Under Review, Interviewing, Offer, Rejected
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=True)
    cover_note = db.Column(db.Text, nullable=True)
    contact_email = db.Column(db.String(100), nullable=True)
    portfolio_url = db.Column(db.String(300), nullable=True)
    match_score = db.Column(db.Float, default=0.0)

    job = db.relationship('JobListing', back_populates='applications', foreign_keys=[job_id])
    resume = db.relationship('Resume', foreign_keys=[resume_id])

    def to_dict(self):
        job_data = None
        j = getattr(self, 'job', None)
        if j and hasattr(j, 'to_dict'):
            job_data = j.to_dict()

        resume_name = None
        r = getattr(self, 'resume', None)
        if r and hasattr(r, 'original_filename'):
            resume_name = r.original_filename

        return {
            'id': self.id,
            'application_id': self.id,
            'job_id': self.job_id,
            'student_id': self.student_id,
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'status': self.status,
            'resume_id': self.resume_id,
            'resume_name': resume_name,
            'cover_note': self.cover_note,
            'contact_email': self.contact_email,
            'portfolio_url': self.portfolio_url,
            'match_score': self.match_score,
            'job': job_data
        }



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
    created_at = db.Column(db.DateTime, default=utc_now)

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


# ─────────────────────────────────────────
# JOB SYNCHRONIZATION BOOKKEEPING
# ─────────────────────────────────────────
class JobSyncRun(BaseModel):
    """One execution of the job synchronization pipeline (scheduled, manual or CLI)."""
    __tablename__ = 'job_sync_runs'

    id = db.Column(db.Integer, primary_key=True)
    trigger = db.Column(db.String(20), nullable=False)          # scheduled | manual | cli
    triggered_by = db.Column(db.Integer, nullable=True)         # student id of admin (no FK: survives deletion)
    status = db.Column(db.String(20), nullable=False, default='running', index=True)
    # running | success | partial | failed | skipped
    started_at = db.Column(db.DateTime, default=utc_now, index=True)
    finished_at = db.Column(db.DateTime)
    fetched_count = db.Column(db.Integer, default=0)
    inserted_count = db.Column(db.Integer, default=0)
    updated_count = db.Column(db.Integer, default=0)
    unchanged_count = db.Column(db.Integer, default=0)
    duplicate_count = db.Column(db.Integer, default=0)
    invalid_count = db.Column(db.Integer, default=0)
    expired_count = db.Column(db.Integer, default=0)
    stale_count = db.Column(db.Integer, default=0)
    alerts_created = db.Column(db.Integer, default=0)
    provider_results = db.Column(db.Text, default='{}')  # JSON {provider: {...}}
    error = db.Column(db.Text)

    def get_provider_results(self):
        try:
            return json.loads(self.provider_results) if self.provider_results else {}
        except Exception:
            return {}

    def to_dict(self):
        return {
            'id': self.id,
            'trigger': self.trigger,
            'triggered_by': self.triggered_by,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'fetched_count': self.fetched_count,
            'inserted_count': self.inserted_count,
            'updated_count': self.updated_count,
            'unchanged_count': self.unchanged_count,
            'duplicate_count': self.duplicate_count,
            'invalid_count': self.invalid_count,
            'expired_count': self.expired_count,
            'stale_count': self.stale_count,
            'alerts_created': self.alerts_created,
            'provider_results': self.get_provider_results(),
            'error': self.error,
        }


class SchedulerLease(BaseModel):
    """
    Database lease that guarantees only ONE sync runs at a time, across
    processes, workers and machines. A lease expires automatically so a
    crashed worker cannot block synchronization forever.
    """
    __tablename__ = 'scheduler_leases'

    name = db.Column(db.String(64), primary_key=True)
    owner = db.Column(db.String(128))
    acquired_at = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime)


# ─────────────────────────────────────────
# STUDENT JOB PREFERENCES & ALERTS
# ─────────────────────────────────────────
def _json_list(value):
    try:
        data = json.loads(value) if value else []
        return data if isinstance(data, list) else []
    except Exception:
        return []


class JobPreference(BaseModel):
    __tablename__ = 'job_preferences'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, unique=True)
    preferred_roles = db.Column(db.Text, default='[]')
    preferred_locations = db.Column(db.Text, default='[]')
    work_modes = db.Column(db.Text, default='[]')        # Remote / Hybrid / Onsite
    job_types = db.Column(db.Text, default='[]')         # Full-time / Internship / Contract ...
    experience_years = db.Column(db.Float, default=0.0)
    open_to_relocation = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    def to_dict(self):
        return {
            'preferred_roles': _json_list(self.preferred_roles),
            'preferred_locations': _json_list(self.preferred_locations),
            'work_modes': _json_list(self.work_modes),
            'job_types': _json_list(self.job_types),
            'experience_years': self.experience_years or 0.0,
            'open_to_relocation': bool(self.open_to_relocation),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class JobAlert(BaseModel):
    __tablename__ = 'job_alerts'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    roles = db.Column(db.Text, default='[]')
    locations = db.Column(db.Text, default='[]')
    skills = db.Column(db.Text, default='[]')
    job_types = db.Column(db.Text, default='[]')
    work_modes = db.Column(db.Text, default='[]')
    min_match_score = db.Column(db.Float, default=50.0)
    frequency = db.Column(db.String(20), default='daily')   # instant | daily | weekly
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    last_evaluated_at = db.Column(db.DateTime)
    last_notified_at = db.Column(db.DateTime)

    matches = db.relationship('JobAlertMatch', lazy=True, cascade='all, delete-orphan',
                              overlaps='job_alert_matches')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'roles': _json_list(self.roles),
            'locations': _json_list(self.locations),
            'skills': _json_list(self.skills),
            'job_types': _json_list(self.job_types),
            'work_modes': _json_list(self.work_modes),
            'min_match_score': self.min_match_score,
            'frequency': self.frequency,
            'is_active': bool(self.is_active),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_evaluated_at': self.last_evaluated_at.isoformat() if self.last_evaluated_at else None,
            'last_notified_at': self.last_notified_at.isoformat() if self.last_notified_at else None,
        }


class JobAlertMatch(BaseModel):
    """A job surfaced to a student by an alert. Unique per (student, job) so the
    same job is never alerted twice, even if several alerts match it."""
    __tablename__ = 'job_alert_matches'
    __table_args__ = (db.UniqueConstraint('student_id', 'job_id', name='uq_alert_match_student_job'),)

    id = db.Column(db.Integer, primary_key=True)
    alert_id = db.Column(db.Integer, db.ForeignKey('job_alerts.id'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job_listings.id'), nullable=False)
    match_score = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=utc_now)
    released_at = db.Column(db.DateTime)   # when it became visible (respects alert frequency)
    is_read = db.Column(db.Boolean, default=False)

    job = db.relationship('JobListing', foreign_keys=[job_id])

    def to_dict(self):
        return {
            'id': self.id,
            'alert_id': self.alert_id,
            'job_id': self.job_id,
            'match_score': self.match_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'released_at': self.released_at.isoformat() if self.released_at else None,
            'is_read': bool(self.is_read),
            'job': self.job.to_dict() if self.job else None,
        }


# ─────────────────────────────────────────
# AUDIT LOG
# ─────────────────────────────────────────
class AuditLog(BaseModel):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, nullable=True, index=True)   # no FK: entries survive account deletion
    action = db.Column(db.String(80), nullable=False, index=True)
    target = db.Column(db.String(200))
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utc_now, index=True)

    def to_dict(self):
        try:
            details = json.loads(self.details) if self.details else None
        except Exception:
            details = self.details
        return {
            'id': self.id,
            'actor_id': self.actor_id,
            'action': self.action,
            'target': self.target,
            'details': details,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# ─────────────────────────────────────────
# PASSWORD RESET TOKEN
# ─────────────────────────────────────────
class PasswordResetToken(BaseModel):
    __tablename__ = 'password_reset_tokens'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    token = db.Column(db.String(128), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    student = db.relationship('Student', backref=db.backref('reset_tokens', lazy=True, cascade='all, delete-orphan'))

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'token': self.token,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'used': self.used,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
