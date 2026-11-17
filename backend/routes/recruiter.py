"""
Recruiter portal API.

  /api/recruiter/...              recruiter accounts only (role='recruiter'), always scoped
                                  to the recruiter's own organisation
  /api/recruiter/admin/...        organisation verification review (administrators only)
  /api/candidate/...              student side: discovery consent, who viewed my profile,
                                  application updates and invitations (students only)

Authorization is enforced here on the server for every request; the frontend
only mirrors it. Records of another organisation are reported as "not found"
so their existence is not revealed.
"""
import json
import re
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import Blueprint, g, jsonify, request
from flask_login import current_user

from extensions import db
from models import (ApplicationEvent, CandidateDiscoverySetting, CandidateShortlist, JobApplication,
                    JobInvitation, JobListing, Organisation, RecruiterAccessLog, RecruiterProfile,
                    RecruitmentNote, ShortlistEntry, Student)
from routes.admin import admin_required
from utils.audit import audit
from utils.rate_limit import rate_limited
from utils.recruiting import (EMPLOYER_PROVIDER, EMPLOYER_SOURCE_LABEL, PIPELINE_STAGES, STAGE_LABELS,
                              STAGE_STUDENT_MESSAGES, access_for, candidate_passport, candidate_ref,
                              candidate_setting, candidate_summary, compatibility_report,
                              email_domain_signal, move_stage, readiness_info, search_candidates,
                              stage_label, student_for_ref)
from utils.skill_passport import SECTION_KEYS, SKILL_FILTERS, is_safe_url, normalize_visibility
from utils.skill_taxonomy import normalize_skill_name

recruiter_bp = Blueprint('recruiter', __name__)
candidate_bp = Blueprint('candidate', __name__)

JOB_TYPES = ('Full-time', 'Internship', 'Contract', 'Part-time')
WORK_MODES = ('Remote', 'Hybrid', 'Onsite')
CURRENCIES = ('INR', 'USD', 'EUR', 'GBP')
SALARY_PERIODS = ('year', 'month', 'hour')
NOT_FOUND = 'Not found'
CANDIDATE_NOT_FOUND = 'Candidate not found or no longer shares their profile with your organisation'


def _now():
    return datetime.now(timezone.utc)


def _naive(dt):
    return dt.replace(tzinfo=None) if dt and dt.tzinfo else dt


def _aware(dt):
    return dt.replace(tzinfo=timezone.utc) if dt and dt.tzinfo is None else dt


def _iso(dt):
    return _aware(dt).isoformat() if dt else None


def _text(data, key, max_len, required=False, label=None):
    value = data.get(key)
    value = '' if value is None else str(value).strip()
    label = label or key.replace('_', ' ').capitalize()
    if required and not value:
        return None, f'{label} is required'
    if len(value) > max_len:
        return None, f'{label} cannot exceed {max_len} characters'
    return value, None


def _no_store(resp):
    resp.headers['Cache-Control'] = 'no-store'
    return resp


def _bad(msg, code=400):
    return jsonify({'error': msg}), code


# ─────────────────────────────────────────────────────────────────────────
# Access decorators
# ─────────────────────────────────────────────────────────────────────────
def recruiter_required(f):
    """Logged-in recruiter with an organisation; sets g.org and g.profile."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return _bad('Authentication required. Please log in.', 401)
        if not getattr(current_user, 'is_recruiter', False) or current_user.is_active is False:
            return _bad('Access denied: this area is for recruiter accounts.', 403)
        profile = RecruiterProfile.query.filter_by(user_id=current_user.id).first()
        if not profile or not profile.organisation:
            return _bad('Your recruiter account is not linked to an organisation.', 403)
        g.profile = profile
        g.org = profile.organisation
        return f(*args, **kwargs)
    return wrapper


def student_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return _bad('Authentication required. Please log in.', 401)
        if (current_user.role or 'student') != 'student':
            return _bad('Access denied: this area is for student accounts.', 403)
        return f(*args, **kwargs)
    return wrapper


def _org_job(job_id):
    return JobListing.query.filter_by(id=job_id, organisation_id=g.org.id).first()


def _org_application(app_id):
    return (JobApplication.query.join(JobListing, JobApplication.job_id == JobListing.id)
            .filter(JobApplication.id == app_id, JobListing.organisation_id == g.org.id,
                    JobApplication.share_consent_at.isnot(None)).first())


# ─────────────────────────────────────────────────────────────────────────
# Recruiter account & organisation
# ─────────────────────────────────────────────────────────────────────────
ORG_FIELDS = [('name', 200, True, 'Organisation name'), ('industry', 120, False, 'Industry'),
              ('contact_email', 120, False, 'Contact email'), ('contact_phone', 40, False, 'Contact phone'),
              ('location', 200, False, 'Location'), ('size', 40, False, 'Organisation size'),
              ('description', 3000, False, 'Description')]


def apply_org_payload(org, data, creating):
    """Validates organisation fields. Returns (identity_changed, error)."""
    identity_changed = False
    for key, max_len, required, label in ORG_FIELDS:
        if creating or key in data:
            value, err = _text(data, key, max_len, required=required, label=label)
            if err:
                return False, err
            if key == 'contact_email' and value and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', value):
                return False, 'Contact email is not a valid email address'
            if key == 'name' and (org.name or '') != value:
                identity_changed = True
            setattr(org, key, value)
    if creating or 'website' in data:
        website = (data.get('website') or '').strip()
        if website and not is_safe_url(website):
            return False, 'Website must be a full http(s) link (e.g. https://example.com)'
        if (org.website or '') != website:
            identity_changed = True
        org.website = website
    return identity_changed, None


def _me_payload():
    org = g.org
    return {
        'user': {'id': current_user.id, 'name': current_user.name, 'email': current_user.email,
                 'role': current_user.role},
        'profile': g.profile.to_dict(),
        'organisation': org.to_dict(),
        'can_publish_jobs': org.is_verified,
        'can_search_candidates': org.is_verified,
        'pipeline_stages': [{'key': s, 'label': STAGE_LABELS[s]} for s in PIPELINE_STAGES],
    }


@recruiter_bp.route('/me', methods=['GET'])
@recruiter_required
def recruiter_me():
    return jsonify(_me_payload()), 200


@recruiter_bp.route('/me/profile', methods=['PUT'])
@recruiter_required
def update_recruiter_profile():
    data = request.get_json(silent=True) or {}
    name, err = _text(data, 'name', 100, required=True, label='Name')
    if err:
        return _bad(err)
    job_title, err = _text(data, 'job_title', 120, label='Job title')
    if err:
        return _bad(err)
    phone, err = _text(data, 'phone', 40, label='Phone')
    if err:
        return _bad(err)
    current_user.name = name
    g.profile.job_title = job_title
    g.profile.phone = phone
    db.session.commit()
    return jsonify({'message': 'Profile saved', **_me_payload()}), 200


@recruiter_bp.route('/organisation', methods=['PUT'])
@recruiter_required
def update_organisation():
    data = request.get_json(silent=True) or {}
    org = g.org
    identity_changed, err = apply_org_payload(org, data, creating=False)
    if err:
        db.session.rollback()
        return _bad(err)
    reset = False
    if identity_changed and org.verification_status in ('verified', 'pending'):
        # The verified identity changed: it must be checked again
        org.verification_status = 'unverified'
        org.verified_at = None
        org.verified_by = None
        org.verification_note = 'Verification reset because the organisation name or website changed.'
        reset = True
    db.session.commit()
    if reset:
        audit('recruiter.org_verification_reset', actor_id=current_user.id, target=f'organisation:{org.id}')
    return jsonify({'message': 'Organisation saved' + (' - verification reset because the name or website '
                                                       'changed; please submit it again' if reset else ''),
                    'verification_reset': reset, **_me_payload()}), 200


@recruiter_bp.route('/organisation/verification', methods=['POST'])
@recruiter_required
def request_org_verification():
    org = g.org
    if org.verification_status in ('pending', 'verified'):
        return _bad(f'Organisation is already {org.verification_status}')
    data = request.get_json(silent=True) or {}
    reg_id, err = _text(data, 'registration_id', 80, label='Registration number')
    if err:
        return _bad(err)
    linkedin, err = _text(data, 'linkedin_url', 300, label='LinkedIn page')
    if err:
        return _bad(err)
    if linkedin and not is_safe_url(linkedin):
        return _bad('LinkedIn page must be a full http(s) link')
    proof_url, err = _text(data, 'proof_url', 300, label='Proof link')
    if err:
        return _bad(err)
    if proof_url and not is_safe_url(proof_url):
        return _bad('Proof link must be a full http(s) link')
    notes, err = _text(data, 'notes', 1000, label='Notes')
    if err:
        return _bad(err)
    if not org.website:
        return _bad('Add your organisation website before requesting verification')
    if not (reg_id or linkedin or proof_url):
        return _bad('Provide at least a registration number (CIN / GSTIN / LLPIN), a LinkedIn page or a proof link')
    org.verification_details = json.dumps({
        'registration_id': reg_id, 'linkedin_url': linkedin, 'proof_url': proof_url, 'notes': notes,
        'submitted_by': current_user.id, 'signals': email_domain_signal(current_user.email, org.website),
    })
    org.verification_status = 'pending'
    org.verification_requested_at = _naive(_now())
    org.verification_note = None
    db.session.commit()
    audit('recruiter.org_verification_requested', actor_id=current_user.id, target=f'organisation:{org.id}')
    return jsonify({'message': 'Verification requested. An administrator will review your organisation.',
                    **_me_payload()}), 200


@recruiter_bp.route('/dashboard', methods=['GET'])
@recruiter_required
def recruiter_dashboard():
    jobs = JobListing.query.filter_by(organisation_id=g.org.id).all()
    job_ids = [j.id for j in jobs]
    by_status = {}
    for j in jobs:
        by_status[j.status] = by_status.get(j.status, 0) + 1
    apps = (JobApplication.query.filter(JobApplication.job_id.in_(job_ids),
                                        JobApplication.share_consent_at.isnot(None)).all() if job_ids else [])
    by_stage = {s: 0 for s in PIPELINE_STAGES}
    for a in apps:
        by_stage[a.stage or 'new'] = by_stage.get(a.stage or 'new', 0) + 1
    recent = sorted(apps, key=lambda a: a.applied_at or datetime.min, reverse=True)[:8]
    title = {j.id: j.title for j in jobs}
    return jsonify({
        **_me_payload(),
        'jobs_by_status': by_status,
        'applications_total': len(apps),
        'applications_by_stage': by_stage,
        'recent_applications': [{'application_id': a.id, 'candidate_ref': candidate_ref(a.student_id),
                                 'name': a.student.name if a.student else '', 'job_title': title.get(a.job_id),
                                 'stage': a.stage, 'stage_label': stage_label(a.stage),
                                 'applied_at': _iso(a.applied_at)} for a in recent],
        'discoverable_candidates': (CandidateDiscoverySetting.query.filter_by(is_discoverable=True).count()
                                    if g.org.is_verified else None),
    }), 200


# ─────────────────────────────────────────────────────────────────────────
# Jobs (stored in job_listings with source_provider='employer')
# ─────────────────────────────────────────────────────────────────────────
def _skill_list(value, label, max_items=25):
    if value is None:
        return [], None
    if isinstance(value, str):
        value = [v for v in value.split(',')]
    if not isinstance(value, list):
        return None, f'{label} must be a list'
    out = []
    for v in value:
        if not isinstance(v, str) or not v.strip():
            continue
        if len(v.strip()) > 60:
            return None, f'{label}: each skill must be at most 60 characters'
        n = normalize_skill_name(v)
        if n not in out:
            out.append(n)
    if len(out) > max_items:
        return None, f'{label}: at most {max_items} skills'
    return out, None


def _number(data, key, label, lo, hi):
    v = data.get(key)
    if v in (None, ''):
        return None, None
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None, f'{label} must be a number'
    if not lo <= v <= hi:
        return None, f'{label} must be between {lo:g} and {hi:g}'
    return v, None


def _parse_deadline(value):
    if value in (None, ''):
        return None, None
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        return None, 'Deadline must be a date (YYYY-MM-DD)'
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if len(str(value)) <= 10:  # a plain date means "open until the end of that day"
        dt = dt + timedelta(hours=23, minutes=59)
    return dt, None


def apply_job_payload(job, data, creating):
    from utils.job_discovery.normalizer import infer_career_category, make_fingerprint, split_location
    if creating or 'title' in data:
        v, err = _text(data, 'title', 200, required=True, label='Job title')
        if err:
            return err
        job.title = v
    if creating or 'description' in data:
        v, err = _text(data, 'description', 10000, required=True, label='Description')
        if err:
            return err
        if len(v) < 30:
            return 'Description must be at least 30 characters'
        job.description = v
    if creating or 'location' in data:
        v, err = _text(data, 'location', 200, required=True, label='Location')
        if err:
            return err
        job.location = v
        parts = split_location(v)
        job.city, job.state, job.country = parts['city'], parts['state'], parts['country']
    if creating or 'work_arrangement' in data:
        v = data.get('work_arrangement') or 'Onsite'
        if v not in WORK_MODES:
            return f'Work arrangement must be one of: {", ".join(WORK_MODES)}'
        job.work_arrangement = v
    if creating or 'job_type' in data:
        v = data.get('job_type') or 'Full-time'
        if v not in JOB_TYPES:
            return f'Employment type must be one of: {", ".join(JOB_TYPES)}'
        job.job_type = v
    if creating or 'required_skills' in data:
        v, err = _skill_list(data.get('required_skills'), 'Required skills')
        if err:
            return err
        if not v:
            return 'List at least one required skill'
        job.required_skills = json.dumps(v)
    if creating or 'preferred_skills' in data:
        v, err = _skill_list(data.get('preferred_skills'), 'Preferred skills')
        if err:
            return err
        req = json.loads(job.required_skills or '[]')
        job.preferred_skills = json.dumps([s for s in v if s not in req])
    if creating or 'education' in data:
        v, err = _text(data, 'education', 300, label='Education requirement')
        if err:
            return err
        job.eligibility = v
    for key, attr, label, hi in (('experience_min_years', 'experience_min_years', 'Minimum experience', 40),
                                 ('experience_max_years', 'experience_max_years', 'Maximum experience', 40)):
        if creating or key in data:
            v, err = _number(data, key, label, 0, hi)
            if err:
                return err
            setattr(job, attr, v)
    if job.experience_min_years is not None and job.experience_max_years is not None \
            and job.experience_min_years > job.experience_max_years:
        return 'Minimum experience cannot exceed maximum experience'
    for key, label in (('salary_min', 'Minimum salary'), ('salary_max', 'Maximum salary')):
        if creating or key in data:
            v, err = _number(data, key, label, 0, 1e9)
            if err:
                return err
            setattr(job, key, v)
    if job.salary_min is not None and job.salary_max is not None and job.salary_min > job.salary_max:
        return 'Minimum salary cannot exceed maximum salary'
    if creating or 'salary_currency' in data:
        v = (data.get('salary_currency') or 'INR').upper()
        if v not in CURRENCIES:
            return f'Currency must be one of: {", ".join(CURRENCIES)}'
        job.salary_currency = v
    if creating or 'salary_period' in data:
        v = data.get('salary_period') or 'year'
        if v not in SALARY_PERIODS:
            return f'Salary period must be one of: {", ".join(SALARY_PERIODS)}'
        job.salary_period = v
    job.salary_is_estimated = False if (job.salary_min is not None or job.salary_max is not None) else None
    if creating or 'deadline' in data:
        dt, err = _parse_deadline(data.get('deadline'))
        if err:
            return err
        if dt and dt <= _now() and (creating or job.status == 'active'):
            return 'Application deadline must be in the future'
        job.deadline = _naive(dt)

    # Derived fields, so employer jobs search, filter and match like aggregated ones
    mn = job.experience_min_years
    if job.job_type == 'Internship':
        job.experience_level, job.is_entry_level = 'Internship', True
    elif mn is None:
        job.experience_level, job.is_entry_level = 'Not specified', None
    elif mn <= 1:
        job.experience_level, job.is_entry_level = 'Entry-Level', True
    elif mn >= 5:
        job.experience_level, job.is_entry_level = 'Senior', False
    else:
        job.experience_level, job.is_entry_level = 'Mid-Level', False
    job.career_category = infer_career_category(job.title, job.description)
    job.domain = job.career_category
    job.company = g.org.name
    job.fingerprint = make_fingerprint(job.title, job.company, job.city or job.location)
    return None


def _job_dict(job, with_counts=True):
    d = job.to_dict()
    if with_counts:
        apps = JobApplication.query.filter(JobApplication.job_id == job.id,
                                           JobApplication.share_consent_at.isnot(None)).all()
        d['applicant_count'] = len(apps)
        d['applicants_by_stage'] = {s: sum(1 for a in apps if (a.stage or 'new') == s) for s in PIPELINE_STAGES}
    return d


@recruiter_bp.route('/jobs', methods=['GET'])
@recruiter_required
def list_org_jobs():
    jobs = (JobListing.query.filter_by(organisation_id=g.org.id)
            .order_by(JobListing.collected_at.desc(), JobListing.id.desc()).all())
    return jsonify({'jobs': [_job_dict(j) for j in jobs]}), 200


@recruiter_bp.route('/jobs', methods=['POST'])
@recruiter_required
def create_org_job():
    import uuid
    if JobListing.query.filter_by(organisation_id=g.org.id).count() >= 200:
        return _bad('Job limit reached (200 per organisation)')
    data = request.get_json(silent=True) or {}
    now = _naive(_now())
    job = JobListing(external_id=f'employer:{uuid.uuid4().hex}', source_provider=EMPLOYER_PROVIDER,
                     source=EMPLOYER_SOURCE_LABEL, skills_source='employer', is_sample=False, status='draft',
                     organisation_id=g.org.id, posted_by=current_user.id, collected_at=now, first_seen_at=now,
                     times_seen=1, company=g.org.name)
    err = apply_job_payload(job, data, creating=True)
    if err:
        return _bad(err)
    db.session.add(job)
    db.session.commit()
    audit('recruiter.job_created', actor_id=current_user.id, target=f'job:{job.id}',
          details={'organisation_id': g.org.id})
    return jsonify({'message': 'Job saved as a draft. Publish it to make it visible to students.',
                    'job': _job_dict(job)}), 201


@recruiter_bp.route('/jobs/<int:job_id>', methods=['GET'])
@recruiter_required
def get_org_job(job_id):
    job = _org_job(job_id)
    if not job:
        return _bad(NOT_FOUND, 404)
    return jsonify({'job': _job_dict(job)}), 200


@recruiter_bp.route('/jobs/<int:job_id>', methods=['PUT', 'PATCH'])
@recruiter_required
def update_org_job(job_id):
    job = _org_job(job_id)
    if not job:
        return _bad(NOT_FOUND, 404)
    if job.status == 'expired':
        return _bad('This job has expired. Close it, or create a new posting.')
    err = apply_job_payload(job, request.get_json(silent=True) or {}, creating=False)
    if err:
        db.session.rollback()
        return _bad(err)
    job.last_changed_at = _naive(_now())
    db.session.commit()
    audit('recruiter.job_updated', actor_id=current_user.id, target=f'job:{job.id}')
    return jsonify({'message': 'Job updated', 'job': _job_dict(job)}), 200


@recruiter_bp.route('/jobs/<int:job_id>/publish', methods=['POST'])
@recruiter_required
def publish_org_job(job_id):
    job = _org_job(job_id)
    if not job:
        return _bad(NOT_FOUND, 404)
    if not g.org.is_verified:
        return _bad('Jobs can be published once an administrator has verified your organisation. '
                    'Request verification from the Organisation page.', 403)
    if job.status == 'active':
        return _bad('Job is already published')
    if job.deadline and _aware(job.deadline) <= _now():
        return _bad('The application deadline has passed. Update it before publishing.')
    now = _naive(_now())
    first_publish = job.posting_date is None
    job.status = 'active'
    job.expired_at = None
    job.expiry_reason = None
    job.posting_date = job.posting_date or now
    job.last_verified_at = now
    job.last_seen_at = now
    job.last_synced_at = now
    db.session.commit()
    created = 0
    if first_publish:
        # Same path as newly synced jobs: notify students whose alerts match
        try:
            from utils.job_alerts import evaluate_alerts_for_new_jobs, release_due_alert_matches
            created = evaluate_alerts_for_new_jobs([job.id], _now())
            release_due_alert_matches(_now())
        except Exception:  # alerts must never block publishing
            db.session.rollback()
    audit('recruiter.job_published', actor_id=current_user.id, target=f'job:{job.id}',
          details={'alert_matches': created})
    return jsonify({'message': 'Job published. Students can now find it on the Jobs page.',
                    'alert_matches_created': created, 'job': _job_dict(job)}), 200


@recruiter_bp.route('/jobs/<int:job_id>/close', methods=['POST'])
@recruiter_required
def close_org_job(job_id):
    job = _org_job(job_id)
    if not job:
        return _bad(NOT_FOUND, 404)
    if job.status != 'closed':
        job.status = 'closed'
        job.expired_at = _naive(_now())
        job.expiry_reason = 'Closed by the employer'
        db.session.commit()
        audit('recruiter.job_closed', actor_id=current_user.id, target=f'job:{job.id}')
    return jsonify({'message': 'Job closed. Existing applications are kept.', 'job': _job_dict(job)}), 200


@recruiter_bp.route('/jobs/<int:job_id>', methods=['DELETE'])
@recruiter_required
def delete_org_job(job_id):
    job = _org_job(job_id)
    if not job:
        return _bad(NOT_FOUND, 404)
    if job.status != 'draft' or job.posting_date is not None:
        return _bad('Only drafts that were never published can be deleted. Close the job instead.')
    JobInvitation.query.filter_by(job_id=job.id).delete()
    CandidateShortlist.query.filter_by(job_id=job.id).update({'job_id': None})
    db.session.delete(job)
    db.session.commit()
    audit('recruiter.job_deleted', actor_id=current_user.id, target=f'job:{job_id}')
    return jsonify({'message': 'Draft deleted'}), 200


def _job_target(job):
    return {'id': job.id, 'title': job.title, 'required_skills': job.get_required_skills(),
            'preferred_skills': job.get_preferred_skills(), 'eligibility': job.eligibility,
            'experience_min_years': job.experience_min_years, 'experience_max_years': job.experience_max_years,
            'experience_level': job.experience_level}


@recruiter_bp.route('/jobs/<int:job_id>/applicants', methods=['GET'])
@recruiter_required
def job_applicants(job_id):
    job = _org_job(job_id)
    if not job:
        return _bad(NOT_FOUND, 404)
    stage = request.args.get('stage')
    q = JobApplication.query.filter(JobApplication.job_id == job.id, JobApplication.share_consent_at.isnot(None))
    if stage:
        if stage not in PIPELINE_STAGES:
            return _bad('Unknown stage')
        q = q.filter(JobApplication.stage == stage)
    target = _job_target(job)
    out = []
    for a in q.order_by(JobApplication.applied_at.asc()).all():
        student = a.student
        access = access_for(g.org, student, job_id=job.id)
        if not access:
            continue
        passport = candidate_passport(student, access)
        report = compatibility_report(passport, target)
        item = candidate_summary(student, passport, report, access)
        item.update({'application_id': a.id, 'stage': a.stage, 'stage_label': stage_label(a.stage),
                     'applied_at': _iso(a.applied_at), 'stage_updated_at': _iso(a.stage_updated_at)})
        out.append(item)
    db.session.commit()  # candidate refs created on first use
    out.sort(key=lambda r: ((r['report'] or {}).get('skill_fit_score') is None,
                            -((r['report'] or {}).get('skill_fit_score') or 0)))
    return _no_store(jsonify({'job': _job_dict(job, with_counts=False), 'applicants': out,
                              'ranked_by': 'Skill fit for this job (see each report for the evidence)'})), 200


@recruiter_bp.route('/jobs/<int:job_id>/matches', methods=['GET'])
@recruiter_required
@rate_limited('recruiter_search', 60, 60, per_user=True)
def job_matches(job_id):
    job = _org_job(job_id)
    if not job:
        return _bad(NOT_FOUND, 404)
    if not g.org.is_verified:
        return _bad('Candidate discovery is available once your organisation is verified.', 403)
    res = search_candidates(g.org, {'skills': []}, job=job, limit=50)
    db.session.commit()
    return _no_store(jsonify({'job': _job_dict(job, with_counts=False), **res})), 200


# ─────────────────────────────────────────────────────────────────────────
# Candidate discovery & profiles
# ─────────────────────────────────────────────────────────────────────────
def _flag(name):
    return (request.args.get(name) or '').lower() in ('1', 'true', 'yes')


def _float_arg(name, lo, hi):
    v = request.args.get(name)
    if v in (None, ''):
        return None
    try:
        v = float(v)
    except ValueError:
        return None
    return max(lo, min(hi, v))


@recruiter_bp.route('/candidates/search', methods=['GET'])
@recruiter_required
@rate_limited('recruiter_search', 60, 60, per_user=True)
def candidate_search():
    if not g.org.is_verified:
        return _bad('Candidate discovery is available once your organisation is verified.', 403)
    skills, err = _skill_list(request.args.get('skills') or '', 'Skills', max_items=15)
    if err:
        return _bad(err)
    prof = request.args.get('min_proficiency') or None
    if prof and prof.lower() not in ('beginner', 'intermediate', 'advanced'):
        return _bad('min_proficiency must be Beginner, Intermediate or Advanced')
    filters = {
        'skills': skills,
        'verified_only': _flag('verified_only'),
        'match_all': _flag('match_all'),
        'min_proficiency': prof,
        'min_assessment': _float_arg('min_assessment', 0, 100),
        'education': (request.args.get('education') or '').strip()[:100] or None,
        'location': (request.args.get('location') or '').strip()[:100] or None,
        'role': (request.args.get('role') or '').strip()[:100] or None,
        'has_projects': _flag('has_projects'),
        'has_experience': _flag('has_experience'),
        'min_readiness': _float_arg('min_readiness', 0, 100),
    }
    job = None
    if request.args.get('job_id'):
        try:
            job = _org_job(int(request.args['job_id']))
        except ValueError:
            job = None
        if not job:
            return _bad(NOT_FOUND, 404)
    res = search_candidates(g.org, filters, job=job, limit=50)
    db.session.commit()
    return _no_store(jsonify({**res, 'filters': filters,
                              'note': 'Only students who chose to be visible to verified employers appear here, '
                                      'and only with the information they chose to share.'})), 200


def _resolve_candidate(ref, job_id=None):
    student = student_for_ref(ref)
    access = access_for(g.org, student, job_id=job_id) if student else None
    return student, access


def _profile_payload(student, access, job):
    passport = candidate_passport(student, access)
    report = compatibility_report(passport, _job_target(job)) if job else None
    apps = []
    for a in access['applications']:
        apps.append({'application_id': a.id, 'job_id': a.job_id, 'job_title': a.job.title if a.job else '',
                     'stage': a.stage, 'stage_label': stage_label(a.stage), 'applied_at': _iso(a.applied_at),
                     'cover_note': a.cover_note or '', 'contact_email': a.contact_email or '',
                     'portfolio_url': a.portfolio_url if is_safe_url(a.portfolio_url or '') else '',
                     'events': [e.to_dict() for e in a.events]})
    notes = (RecruitmentNote.query.filter_by(organisation_id=g.org.id, student_id=student.id)
             .order_by(RecruitmentNote.created_at.desc()).all())
    shortlists = (db.session.query(CandidateShortlist.id).join(ShortlistEntry)
                  .filter(CandidateShortlist.organisation_id == g.org.id,
                          ShortlistEntry.student_id == student.id).all())
    open_jobs = JobListing.query.filter_by(organisation_id=g.org.id, status='active').all()
    invited = {i.job_id for i in JobInvitation.query.filter_by(organisation_id=g.org.id,
                                                               student_id=student.id).all()}
    applied = {a.job_id for a in access['applications']}
    return {
        'candidate_ref': candidate_ref(student.id),
        'basis': access['basis'],
        'basis_label': ('Applied to your job and agreed to share this profile' if access['basis'] == 'application'
                        else 'Chose to be visible to verified employers'),
        'passport': passport,
        'report': report,
        'applications': apps,
        'notes': [n.to_dict() for n in notes],
        'shortlist_ids': [s[0] for s in shortlists],
        'invitable_jobs': [{'id': j.id, 'title': j.title, 'invited': j.id in invited}
                           for j in open_jobs if j.id not in applied] if access['basis'] == 'discovery' else [],
        'privacy': 'Shown with the student\'s consent. Contact details appear only in applications the student '
                   'submitted to you. Do not copy this information outside your hiring process.',
    }


@recruiter_bp.route('/candidates/<ref>', methods=['GET'])
@recruiter_required
@rate_limited('recruiter_profile', 120, 60, per_user=True)
def candidate_profile(ref):
    job = None
    job_id = request.args.get('job_id')
    if job_id:
        try:
            job = _org_job(int(job_id))
        except ValueError:
            job = None
        if not job:
            return _bad(NOT_FOUND, 404)
    student, access = _resolve_candidate(ref, job_id=job.id if job else None)
    if not access:
        return _bad(CANDIDATE_NOT_FOUND, 404)
    payload = _profile_payload(student, access, job)
    db.session.add(RecruiterAccessLog(student_id=student.id, organisation_id=g.org.id,
                                      recruiter_id=current_user.id, job_id=job.id if job else None,
                                      basis=access['basis'], action='profile_view'))
    db.session.commit()
    return _no_store(jsonify(payload)), 200


@recruiter_bp.route('/candidates/<ref>/notes', methods=['POST'])
@recruiter_required
def add_candidate_note(ref):
    student, access = _resolve_candidate(ref)
    if not access:
        return _bad(CANDIDATE_NOT_FOUND, 404)
    data = request.get_json(silent=True) or {}
    kind = data.get('kind') or 'note'
    if kind not in RecruitmentNote.KINDS:
        return _bad('kind must be "note" or "interview"')
    body, err = _text(data, 'body', 4000, required=(kind == 'note'), label='Note')
    if err:
        return _bad(err)
    app_id = data.get('application_id')
    if app_id not in (None, ''):
        try:
            app_id = int(app_id)
        except (TypeError, ValueError):
            return _bad('application_id must be a number')
        if app_id not in {a.id for a in access['applications']}:
            return _bad('Application not found', 404)
    else:
        app_id = None
    note = RecruitmentNote(organisation_id=g.org.id, student_id=student.id, application_id=app_id,
                           author_id=current_user.id, kind=kind, body=body)
    if kind == 'interview':
        rnd, err = _text(data, 'interview_round', 80, required=True, label='Interview round')
        if err:
            return _bad(err)
        outcome = data.get('outcome') or 'pending'
        if outcome not in RecruitmentNote.OUTCOMES:
            return _bad(f'outcome must be one of: {", ".join(RecruitmentNote.OUTCOMES)}')
        note.interview_round, note.outcome = rnd, outcome
    db.session.add(note)
    db.session.commit()
    audit('recruiter.note_added', actor_id=current_user.id, target=f'note:{note.id}',
          details={'organisation_id': g.org.id, 'kind': kind})
    return jsonify({'message': 'Saved (internal - the candidate cannot see it)', 'note': note.to_dict()}), 201


@recruiter_bp.route('/notes/<int:note_id>', methods=['DELETE'])
@recruiter_required
def delete_candidate_note(note_id):
    note = RecruitmentNote.query.filter_by(id=note_id, organisation_id=g.org.id).first()
    if not note:
        return _bad(NOT_FOUND, 404)
    db.session.delete(note)
    db.session.commit()
    return jsonify({'message': 'Note deleted'}), 200


@recruiter_bp.route('/candidates/<ref>/invite', methods=['POST'])
@recruiter_required
def invite_candidate(ref):
    student, access = _resolve_candidate(ref)
    if not access or access['basis'] != 'discovery':
        return _bad(CANDIDATE_NOT_FOUND, 404)
    data = request.get_json(silent=True) or {}
    try:
        job = _org_job(int(data.get('job_id')))
    except (TypeError, ValueError):
        job = None
    if not job or job.status != 'active':
        return _bad('Choose one of your published jobs')
    message, err = _text(data, 'message', 500, label='Message')
    if err:
        return _bad(err)
    if JobInvitation.query.filter_by(job_id=job.id, student_id=student.id).first():
        return _bad('This candidate has already been invited to this job', 409)
    if JobApplication.query.filter_by(job_id=job.id, student_id=student.id).first():
        return _bad('This candidate has already applied to this job', 409)
    inv = JobInvitation(job_id=job.id, organisation_id=g.org.id, student_id=student.id,
                        invited_by=current_user.id, message=message or None)
    db.session.add(inv)
    db.session.commit()
    audit('recruiter.candidate_invited', actor_id=current_user.id, target=f'invitation:{inv.id}',
          details={'organisation_id': g.org.id, 'job_id': job.id})
    return jsonify({'message': 'Invitation sent. The candidate decides whether to apply.'}), 201


# ─────────────────────────────────────────────────────────────────────────
# Shortlists
# ─────────────────────────────────────────────────────────────────────────
def _org_shortlist(sid):
    return CandidateShortlist.query.filter_by(id=sid, organisation_id=g.org.id).first()


def _shortlist_dict(sl, with_entries=False):
    d = {'id': sl.id, 'name': sl.name, 'description': sl.description or '', 'job_id': sl.job_id,
         'created_at': _iso(sl.created_at), 'count': len(sl.entries)}
    if with_entries:
        items = []
        for e in sl.entries:
            student = db.session.get(Student, e.student_id)
            access = access_for(g.org, student) if student else None
            if not access:
                items.append({'entry_id': e.id, 'available': False, 'note': e.note or '',
                              'added_at': _iso(e.added_at),
                              'message': 'This candidate no longer shares their profile with you.'})
                continue
            passport = candidate_passport(student, access)
            report = None
            if sl.job_id:
                job = _org_job(sl.job_id)
                report = compatibility_report(passport, _job_target(job)) if job else None
            items.append({'entry_id': e.id, 'available': True, 'note': e.note or '', 'added_at': _iso(e.added_at),
                          **candidate_summary(student, passport, report, access)})
        d['entries'] = items
    return d


@recruiter_bp.route('/shortlists', methods=['GET'])
@recruiter_required
def list_shortlists():
    lists = (CandidateShortlist.query.filter_by(organisation_id=g.org.id)
             .order_by(CandidateShortlist.created_at.desc()).all())
    return jsonify({'shortlists': [_shortlist_dict(s) for s in lists]}), 200


@recruiter_bp.route('/shortlists', methods=['POST'])
@recruiter_required
def create_shortlist():
    data = request.get_json(silent=True) or {}
    name, err = _text(data, 'name', 120, required=True, label='Name')
    if err:
        return _bad(err)
    desc, err = _text(data, 'description', 300, label='Description')
    if err:
        return _bad(err)
    job_id = data.get('job_id')
    if job_id not in (None, ''):
        try:
            job = _org_job(int(job_id))
        except (TypeError, ValueError):
            job = None
        if not job:
            return _bad('Job not found', 404)
        job_id = job.id
    else:
        job_id = None
    if CandidateShortlist.query.filter_by(organisation_id=g.org.id).count() >= 100:
        return _bad('Shortlist limit reached (100)')
    sl = CandidateShortlist(organisation_id=g.org.id, name=name, description=desc, job_id=job_id,
                            created_by=current_user.id)
    db.session.add(sl)
    db.session.commit()
    return jsonify({'message': 'Shortlist created', 'shortlist': _shortlist_dict(sl)}), 201


@recruiter_bp.route('/shortlists/<int:sid>', methods=['GET'])
@recruiter_required
def get_shortlist(sid):
    sl = _org_shortlist(sid)
    if not sl:
        return _bad(NOT_FOUND, 404)
    payload = _shortlist_dict(sl, with_entries=True)
    db.session.commit()
    return _no_store(jsonify({'shortlist': payload})), 200


@recruiter_bp.route('/shortlists/<int:sid>', methods=['DELETE'])
@recruiter_required
def delete_shortlist(sid):
    sl = _org_shortlist(sid)
    if not sl:
        return _bad(NOT_FOUND, 404)
    db.session.delete(sl)
    db.session.commit()
    return jsonify({'message': 'Shortlist deleted'}), 200


@recruiter_bp.route('/shortlists/<int:sid>/entries', methods=['POST'])
@recruiter_required
def add_shortlist_entry(sid):
    sl = _org_shortlist(sid)
    if not sl:
        return _bad(NOT_FOUND, 404)
    data = request.get_json(silent=True) or {}
    student, access = _resolve_candidate(str(data.get('candidate_ref') or ''))
    if not access:
        return _bad(CANDIDATE_NOT_FOUND, 404)
    note, err = _text(data, 'note', 500, label='Note')
    if err:
        return _bad(err)
    if ShortlistEntry.query.filter_by(shortlist_id=sl.id, student_id=student.id).first():
        return _bad('Candidate is already on this shortlist', 409)
    db.session.add(ShortlistEntry(shortlist_id=sl.id, student_id=student.id, added_by=current_user.id,
                                  note=note or None))
    db.session.commit()
    audit('recruiter.shortlist_added', actor_id=current_user.id, target=f'shortlist:{sl.id}',
          details={'organisation_id': g.org.id})
    return jsonify({'message': f'Added to "{sl.name}"'}), 201


@recruiter_bp.route('/shortlists/<int:sid>/entries/<int:entry_id>', methods=['DELETE'])
@recruiter_required
def remove_shortlist_entry(sid, entry_id):
    sl = _org_shortlist(sid)
    entry = ShortlistEntry.query.filter_by(id=entry_id, shortlist_id=sid).first() if sl else None
    if not entry:
        return _bad(NOT_FOUND, 404)
    db.session.delete(entry)
    db.session.commit()
    return jsonify({'message': 'Removed from shortlist'}), 200


# ─────────────────────────────────────────────────────────────────────────
# Recruitment pipeline
# ─────────────────────────────────────────────────────────────────────────
@recruiter_bp.route('/pipeline', methods=['GET'])
@recruiter_required
def pipeline():
    q = (JobApplication.query.join(JobListing, JobApplication.job_id == JobListing.id)
         .filter(JobListing.organisation_id == g.org.id, JobApplication.share_consent_at.isnot(None)))
    job_id = request.args.get('job_id')
    if job_id:
        try:
            q = q.filter(JobListing.id == int(job_id))
        except ValueError:
            return _bad('job_id must be a number')
    columns = {s: [] for s in PIPELINE_STAGES}
    for a in q.order_by(JobApplication.stage_updated_at.desc()).all():
        columns.setdefault(a.stage or 'new', []).append({
            'application_id': a.id, 'candidate_ref': candidate_ref(a.student_id),
            'name': a.student.name if a.student else '', 'job_id': a.job_id, 'job_title': a.job.title,
            'stage': a.stage or 'new', 'applied_at': _iso(a.applied_at), 'stage_updated_at': _iso(a.stage_updated_at),
            'match_score': a.match_score})
    db.session.commit()
    return _no_store(jsonify({'stages': [{'key': s, 'label': STAGE_LABELS[s], 'applications': columns[s]}
                                         for s in PIPELINE_STAGES]})), 200


@recruiter_bp.route('/applications/<int:app_id>/stage', methods=['POST'])
@recruiter_required
def change_application_stage(app_id):
    app = _org_application(app_id)
    if not app:
        return _bad(NOT_FOUND, 404)
    data = request.get_json(silent=True) or {}
    stage = data.get('stage')
    if stage not in PIPELINE_STAGES:
        return _bad(f'stage must be one of: {", ".join(PIPELINE_STAGES)}')
    if stage == app.stage:
        return _bad(f'Application is already at "{stage_label(stage)}"')
    message, err = _text(data, 'message', 500, label='Message to the candidate')
    if err:
        return _bad(err)
    prev = app.stage
    ev = move_stage(app, stage, g.org.id, current_user.id, message)
    db.session.commit()
    audit('recruiter.stage_changed', actor_id=current_user.id, target=f'application:{app.id}',
          details={'organisation_id': g.org.id, 'from': prev, 'to': stage})
    return jsonify({'message': f'Moved to "{stage_label(stage)}". The candidate will see this update.',
                    'event': ev.to_dict(), 'stage': stage, 'stage_label': stage_label(stage)}), 200


# ─────────────────────────────────────────────────────────────────────────
# Administrator: organisation verification
# ─────────────────────────────────────────────────────────────────────────
@recruiter_bp.route('/admin/organisations', methods=['GET'])
@admin_required
def admin_list_organisations():
    status = request.args.get('status', 'pending')
    if status not in Organisation.VERIFICATION_STATUSES and status != 'all':
        return _bad('Unknown status')
    q = Organisation.query
    if status != 'all':
        q = q.filter_by(verification_status=status)
    out = []
    for org in q.order_by(Organisation.verification_requested_at.asc(), Organisation.id.asc()).limit(200).all():
        d = org.to_dict()
        d['recruiters'] = [{'name': p.user.name if p.user else '', 'email': p.user.email if p.user else '',
                            'job_title': p.job_title or ''}
                           for p in RecruiterProfile.query.filter_by(organisation_id=org.id).all()]
        d['job_count'] = JobListing.query.filter_by(organisation_id=org.id).count()
        out.append(d)
    return jsonify({'organisations': out, 'count': len(out)}), 200


@recruiter_bp.route('/admin/organisations/<int:org_id>/review', methods=['POST'])
@admin_required
def admin_review_organisation(org_id):
    org = db.session.get(Organisation, org_id)
    if not org:
        return _bad(NOT_FOUND, 404)
    data = request.get_json(silent=True) or {}
    decision = data.get('decision')
    note, err = _text(data, 'note', 500, label='Note')
    if err:
        return _bad(err)
    if decision in ('verified', 'rejected'):
        if org.verification_status != 'pending':
            return _bad('Only organisations pending verification can be decided')
        if decision == 'rejected' and not note:
            return _bad('Please give the recruiter a reason for rejecting the verification')
    elif decision == 'revoked':
        if org.verification_status != 'verified':
            return _bad('Only verified organisations can be revoked')
        if not note:
            return _bad('Please give a reason for revoking the verification')
    else:
        return _bad('decision must be "verified", "rejected" or "revoked"')

    org.verification_status = 'verified' if decision == 'verified' else 'rejected'
    org.verified_at = _naive(_now()) if decision == 'verified' else None
    org.verified_by = current_user.id
    org.verification_note = note or None
    closed = 0
    if decision == 'revoked':
        # An employer that is no longer verified must not keep collecting applications
        for job in JobListing.query.filter_by(organisation_id=org.id, status='active').all():
            job.status = 'closed'
            job.expired_at = _naive(_now())
            job.expiry_reason = 'Closed: employer verification revoked'
            closed += 1
    db.session.commit()
    audit('admin.organisation_reviewed', actor_id=current_user.id, target=f'organisation:{org.id}',
          details={'decision': decision, 'jobs_closed': closed})
    return jsonify({'message': f'Organisation {decision}', 'jobs_closed': closed, 'organisation': org.to_dict()}), 200


# ─────────────────────────────────────────────────────────────────────────
# Student side
# ─────────────────────────────────────────────────────────────────────────
def _discovery_dict(setting):
    vis = normalize_visibility(setting.get_visibility()) if setting and setting.visibility not in (None, '', '{}') \
        else {'sections': {k: k in ('profile', 'education', 'skills', 'projects', 'certifications',
                                    'assessments', 'career_interests') for k in SECTION_KEYS},
              'skill_filter': 'all'}
    return {
        'is_discoverable': bool(setting and setting.is_discoverable),
        'visibility': vis,
        'share_readiness': bool(setting and setting.share_readiness),
        'consent_at': _iso(setting.consent_at) if setting else None,
        'updated_at': _iso(setting.updated_at) if setting else None,
        'section_keys': SECTION_KEYS,
        'skill_filters': list(SKILL_FILTERS),
        'explanation': {
            'who': 'Recruiters from organisations an administrator has verified. Unverified organisations cannot '
                   'search for you.',
            'what': 'Only the sections you select. Your email address, phone number, resume file and uploaded '
                    'evidence files are never shown in search.',
            'why': 'So employers can find you for roles that match your verified skills and invite you to apply.',
            'how_long': 'Until you switch this off. Switching it off removes you from search immediately; '
                        'employers you applied to keep access to what you shared in that application until you '
                        'withdraw it.',
        },
    }


@candidate_bp.route('/discovery', methods=['GET'])
@student_required
def get_discovery():
    return jsonify(_discovery_dict(candidate_setting(current_user.id, create=False))), 200


@candidate_bp.route('/discovery', methods=['PUT'])
@student_required
def update_discovery():
    data = request.get_json(silent=True) or {}
    enable = bool(data.get('is_discoverable'))
    visibility = normalize_visibility(data.get('visibility'))
    if enable:
        if data.get('consent') is not True:
            return _bad('Please confirm that you consent to verified employers seeing the selected information')
        if not any(visibility['sections'].values()):
            return _bad('Select at least one section to share')
    setting = candidate_setting(current_user.id)
    was = setting.is_discoverable
    setting.is_discoverable = enable
    setting.visibility = json.dumps(visibility)
    setting.share_readiness = bool(data.get('share_readiness'))
    if enable:
        setting.consent_at = _naive(_now())
    setting.updated_at = _naive(_now())
    db.session.commit()
    if was != enable:
        audit('candidate.discovery_' + ('enabled' if enable else 'disabled'), actor_id=current_user.id,
              target=f'student:{current_user.id}')
    return jsonify({'message': ('You are now visible to verified employers.' if enable else
                                'You are hidden from employer search.'),
                    **_discovery_dict(setting)}), 200


@candidate_bp.route('/access', methods=['GET'])
@student_required
def my_recruiter_access():
    """Who can see my profile, and who has looked."""
    logs = (RecruiterAccessLog.query.filter_by(student_id=current_user.id)
            .order_by(RecruiterAccessLog.created_at.desc()).limit(200).all())
    titles = {}
    log_items = []
    for l in logs:
        if l.job_id and l.job_id not in titles:
            j = db.session.get(JobListing, l.job_id)
            titles[l.job_id] = j.title if j else None
        log_items.append({'organisation': l.organisation.name if l.organisation else 'Deleted organisation',
                          'organisation_verified': bool(l.organisation and l.organisation.is_verified),
                          'basis': l.basis, 'action': l.action, 'job_title': titles.get(l.job_id),
                          'at': _iso(l.created_at)})
    apps = (JobApplication.query.join(JobListing, JobApplication.job_id == JobListing.id)
            .filter(JobApplication.student_id == current_user.id, JobApplication.share_consent_at.isnot(None))
            .all())
    by_org = {}
    for a in apps:
        org = a.job.organisation
        if not org:
            continue
        entry = by_org.setdefault(org.id, {'organisation': org.name, 'verified': org.is_verified,
                                            'basis': 'application', 'jobs': []})
        entry['jobs'].append({'job_title': a.job.title, 'application_id': a.id, 'job_id': a.job_id,
                              'stage_label': stage_label(a.stage),
                              'shared_sections': [k for k, v in normalize_visibility(
                                  a.get_share_visibility())['sections'].items() if v],
                              'shared_at': _iso(a.share_consent_at)})
    setting = candidate_setting(current_user.id, create=False)
    return jsonify({
        'discoverable': bool(setting and setting.is_discoverable),
        'organisations_with_application_access': list(by_org.values()),
        'access_log': log_items,
        'how_to_revoke': 'Switch off employer visibility to leave search; withdraw an application to remove '
                         'that employer\'s access to what you shared with it.',
    }), 200


@candidate_bp.route('/updates', methods=['GET'])
@student_required
def my_updates():
    events = (ApplicationEvent.query.join(JobApplication, ApplicationEvent.application_id == JobApplication.id)
              .filter(JobApplication.student_id == current_user.id)
              .order_by(ApplicationEvent.created_at.desc()).limit(100).all())
    ev_items = []
    for e in events:
        app = db.session.get(JobApplication, e.application_id)
        job = app.job if app else None
        ev_items.append({**e.to_dict(), 'type': 'application_update', 'application_id': e.application_id,
                         'job_id': app.job_id if app else None, 'job_title': job.title if job else '',
                         'company': job.company if job else '', 'stage_label': stage_label(e.to_stage),
                         'text': STAGE_STUDENT_MESSAGES.get(e.to_stage, '')})
    invitations = (JobInvitation.query.filter_by(student_id=current_user.id)
                   .order_by(JobInvitation.created_at.desc()).limit(50).all())
    inv_items = []
    for i in invitations:
        applied = JobApplication.query.filter_by(student_id=current_user.id, job_id=i.job_id).first() is not None
        inv_items.append({'id': i.id, 'type': 'invitation', 'job_id': i.job_id,
                          'job_title': i.job.title if i.job else '', 'job_status': i.job.status if i.job else None,
                          'organisation': i.organisation.public_dict() if i.organisation else None,
                          'message': i.message or '', 'created_at': _iso(i.created_at),
                          'seen': i.seen_at is not None, 'applied': applied})
    unread = sum(1 for e in ev_items if not e['seen']) + sum(1 for i in inv_items if not i['seen'])
    return jsonify({'application_updates': ev_items, 'invitations': inv_items, 'unread_count': unread}), 200


@candidate_bp.route('/updates/read', methods=['POST'])
@student_required
def mark_updates_read():
    app_ids = [a.id for a in JobApplication.query.filter_by(student_id=current_user.id).all()]
    n = 0
    if app_ids:
        n += ApplicationEvent.query.filter(ApplicationEvent.application_id.in_(app_ids),
                                           ApplicationEvent.seen_by_student.is_(False)) \
            .update({'seen_by_student': True}, synchronize_session=False)
    n += JobInvitation.query.filter(JobInvitation.student_id == current_user.id, JobInvitation.seen_at.is_(None)) \
        .update({'seen_at': _naive(_now())}, synchronize_session=False)
    db.session.commit()
    return jsonify({'updated': n}), 200


@candidate_bp.route('/readiness_preview', methods=['GET'])
@student_required
def readiness_preview():
    """What 'share readiness' would show, so the student can decide."""
    return jsonify(readiness_info(current_user)), 200
