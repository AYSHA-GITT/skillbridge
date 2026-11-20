"""
Recruiter "request verification" of candidate skills.

Flow
  1. A recruiter of a verified organisation, with consent-scoped access to the
     candidate (utils.recruiting.access_for), asks for one or more skills to be
     verified. Only skills the candidate already shows that organisation, and
     that are not verified yet, can be requested; nothing hidden is revealed.
  2. The student sees the request in their employer updates and accepts or
     declines it. Accepting is the consent to report the outcome back.
  3. The student verifies the skill the normal way: the SkillBridge assessment
     or evidence accepted by a reviewer (the single passport rule,
     utils.skill_passport.skill_verification_states).
  4. sync_student_requests() marks accepted requests completed as soon as the
     skill is verified and flags them unread for the recruiter. Failed attempts
     are never reported. If the student stops sharing their profile with the
     organisation, open requests are closed.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from extensions import db
from models import Organisation, SkillVerificationRequest, Student
from utils.skill_passport import skill_verification_states
from utils.skill_taxonomy import normalize_skill_name

MAX_SKILLS_PER_REQUEST = 5
MAX_OPEN_PER_CANDIDATE = 15         # per organisation
DECLINE_COOLDOWN_DAYS = 30          # a declined skill cannot be requested again for this long

STATUS_LABELS = {
    'pending': 'Waiting for the candidate',
    'accepted': 'Accepted - candidate is verifying',
    'completed': 'Verified',
    'declined': 'Declined by the candidate',
    'cancelled': 'Cancelled by the recruiter',
    'closed': 'Closed',
}
STUDENT_STATUS_LABELS = {
    'pending': 'Awaiting your answer',
    'accepted': 'Accepted - verify the skill to complete it',
    'completed': 'Completed - the employer has been told the skill is verified',
    'declined': 'You declined',
    'cancelled': 'Withdrawn by the employer',
    'closed': 'Closed',
}
VIA_LABELS = {'assessment': 'passed the SkillBridge assessment',
              'reviewed_evidence': 'evidence accepted by a reviewer'}


def _now():
    return datetime.now(timezone.utc)


def _naive(dt):
    return dt.replace(tzinfo=None) if dt and dt.tzinfo else dt


def _iso(dt):
    if not dt:
        return None
    return (dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt).isoformat()


def _key(name: str) -> str:
    return (name or '').lower().strip()


def visible_skills(passport: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Skills the candidate shows this organisation, keyed by normalised name."""
    if 'skills' not in (passport.get('sections') or []):
        return {}
    return {normalize_skill_name(s['skill_name']): s for s in passport.get('skills') or []}


def open_requests(org_id: int, student_id: int) -> List[SkillVerificationRequest]:
    return (SkillVerificationRequest.query
            .filter(SkillVerificationRequest.organisation_id == org_id,
                    SkillVerificationRequest.student_id == student_id,
                    SkillVerificationRequest.status.in_(SkillVerificationRequest.OPEN_STATUSES)).all())


def requestable_skills(org_id: int, student_id: int, passport: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Shown, unverified skills without an open request from this organisation."""
    already = {normalize_skill_name(r.skill_name) for r in open_requests(org_id, student_id)}
    out = []
    for key, s in visible_skills(passport).items():
        if s['status'] != 'verified' and key not in already:
            out.append({'skill_name': s['skill_name'], 'status': s['status'], 'status_label': s['status_label']})
    return out


def create_requests(org: Organisation, recruiter_id: int, student: Student, passport: Dict[str, Any],
                    skills: List[str], job_id: Optional[int], message: Optional[str]):
    """Returns (created_requests, skipped [{skill, reason}], error)."""
    if not org.is_verified:
        return [], [], 'Verification requests can be sent once your organisation is verified.'
    if not skills:
        return [], [], 'Choose at least one skill'
    if len(skills) > MAX_SKILLS_PER_REQUEST:
        return [], [], f'Request at most {MAX_SKILLS_PER_REQUEST} skills at a time'
    shown = visible_skills(passport)
    if not shown:
        return [], [], 'The candidate does not share their skills with your organisation'
    states = skill_verification_states(student.id)
    open_now = open_requests(org.id, student.id)
    open_names = {normalize_skill_name(r.skill_name) for r in open_now}
    cooldown_from = _naive(_now() - timedelta(days=DECLINE_COOLDOWN_DAYS))
    created, skipped = [], []
    for raw in skills:
        key = normalize_skill_name(raw)
        s = shown.get(key)
        if s is None:
            # Not shown to this organisation: same answer whether or not the student has it
            skipped.append({'skill': raw, 'reason': 'Not shown in this candidate\'s profile'})
            continue
        if s['status'] == 'verified':
            skipped.append({'skill': s['skill_name'], 'reason': 'Already verified'})
            continue
        if key in open_names:
            skipped.append({'skill': s['skill_name'], 'reason': 'A request for this skill is already open'})
            continue
        declined = (SkillVerificationRequest.query
                    .filter(SkillVerificationRequest.organisation_id == org.id,
                            SkillVerificationRequest.student_id == student.id,
                            SkillVerificationRequest.status == 'declined',
                            SkillVerificationRequest.responded_at >= cooldown_from).all())
        if any(normalize_skill_name(r.skill_name) == key for r in declined):
            skipped.append({'skill': s['skill_name'],
                            'reason': f'The candidate declined this recently (within {DECLINE_COOLDOWN_DAYS} days)'})
            continue
        if len(open_now) + len(created) >= MAX_OPEN_PER_CANDIDATE:
            skipped.append({'skill': s['skill_name'],
                            'reason': f'At most {MAX_OPEN_PER_CANDIDATE} open requests per candidate'})
            continue
        st = states.get(_key(s['skill_name']))
        req = SkillVerificationRequest(organisation_id=org.id, recruiter_id=recruiter_id, student_id=student.id,
                                       job_id=job_id, skill_id=st['skill_id'] if st else None,
                                       skill_name=s['skill_name'], message=message or None, status='pending',
                                       created_at=_naive(_now()), seen_by_student=False, seen_by_recruiter=True)
        db.session.add(req)
        created.append(req)
        open_names.add(key)
    db.session.flush()
    return created, skipped, None


def sync_student_requests(student_id: int) -> int:
    """Complete accepted requests whose skill is now verified; close requests whose
    organisation lost access. Returns how many changed. Caller commits."""
    from utils.recruiting import access_for
    reqs = (SkillVerificationRequest.query
            .filter(SkillVerificationRequest.student_id == student_id,
                    SkillVerificationRequest.status.in_(SkillVerificationRequest.OPEN_STATUSES)).all())
    if not reqs:
        return 0
    student = db.session.get(Student, student_id)
    states = skill_verification_states(student_id)
    access_cache = {}
    changed = 0
    for r in reqs:
        if r.organisation_id not in access_cache:
            org = r.organisation
            access_cache[r.organisation_id] = bool(org and student and access_for(org, student))
        if not access_cache[r.organisation_id]:
            r.status = 'closed'
            r.close_reason = 'The candidate no longer shares their profile with this organisation.'
            r.closed_at = _naive(_now())
            r.seen_by_recruiter = False
            changed += 1
            continue
        if r.status != 'accepted':
            continue
        st = states.get(_key(r.skill_name))
        if st and st['verified']:
            r.status = 'completed'
            r.completed_via = ','.join(st['verified_via']) or None
            r.completed_at = _naive(_now())
            r.seen_by_recruiter = False
            r.seen_by_student = False
            changed += 1
    if changed:
        db.session.flush()
    return changed


def safe_sync(student_id: int) -> None:
    """Sync and commit; never breaks the caller (quiz submission, evidence review)."""
    try:
        if sync_student_requests(student_id):
            db.session.commit()
    except Exception:  # pragma: no cover - defensive
        db.session.rollback()


def _via(r: SkillVerificationRequest) -> List[str]:
    return [v for v in (r.completed_via or '').split(',') if v]


def recruiter_dict(r: SkillVerificationRequest, candidate_ref: Optional[str], candidate_name: Optional[str]):
    via = _via(r)
    return {
        'id': r.id,
        'skill_name': r.skill_name,
        'status': r.status,
        'status_label': STATUS_LABELS.get(r.status, r.status),
        'message': r.message or '',
        'student_note': (r.student_note or '') if r.status in ('accepted', 'declined', 'completed') else '',
        'completed_via': via,
        'completed_via_label': ' and '.join(VIA_LABELS.get(v, v) for v in via),
        'close_reason': r.close_reason or '',
        'job_id': r.job_id,
        'job_title': r.job.title if r.job else None,
        'candidate_ref': candidate_ref,
        'candidate_name': candidate_name,
        'created_at': _iso(r.created_at),
        'responded_at': _iso(r.responded_at),
        'completed_at': _iso(r.completed_at),
        'closed_at': _iso(r.closed_at),
        'unread': not r.seen_by_recruiter,
    }


def student_dict(r: SkillVerificationRequest, states: Dict[str, Any]) -> Dict[str, Any]:
    st = states.get(_key(r.skill_name))
    via = _via(r)
    return {
        'id': r.id,
        'type': 'verification_request',
        'skill_name': r.skill_name,
        'status': r.status,
        'status_label': STUDENT_STATUS_LABELS.get(r.status, r.status),
        'message': r.message or '',
        'student_note': r.student_note or '',
        'organisation': r.organisation.public_dict() if r.organisation else None,
        'job_id': r.job_id,
        'job_title': r.job.title if r.job else None,
        'skill_id': st['skill_id'] if st else None,
        'skill_status': st['status'] if st else None,
        'skill_verified': bool(st and st['verified']),
        'completed_via_label': ' and '.join(VIA_LABELS.get(v, v) for v in via),
        'close_reason': r.close_reason or '',
        'created_at': _iso(r.created_at),
        'responded_at': _iso(r.responded_at),
        'completed_at': _iso(r.completed_at),
        'seen': bool(r.seen_by_student),
        'what_is_shared': ('If you accept, this employer is told when the skill becomes verified and how '
                           '(assessment or reviewed evidence). Failed attempts and scores are not reported; '
                           'scores stay visible only if you share your assessments section.'),
    }
