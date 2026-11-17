"""
Recruiter portal domain logic: consent-scoped candidate access, the explainable
candidate-job compatibility report, candidate search and the hiring pipeline.

Access rules (enforced on every recruiter request that touches a student):

  application  the student applied, in SkillBridge, to a published job of the
               recruiter's organisation and agreed to share the passport sections
               chosen in that application. Withdrawing the application ends access.
  discovery    the student switched on "visible to verified employers" and the
               recruiter's organisation has been verified by an administrator.
               Switching it off ends access immediately.

Anything else is treated as "candidate not found" (404), so recruiters cannot
probe which students exist. Every profile a recruiter sees is built with
build_public_passport(), the same consent filter used by share links, so email,
phone, resume text, uploaded files and rejected evidence are never exposed.

Matching uses only skills and evidence the student shared. Name, college,
location, age and other personal characteristics are never part of a score.
"""
import json
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from extensions import db
from models import (CandidateDiscoverySetting, JobApplication, JobListing, Student, ApplicationEvent,
                    Organisation)
from utils.job_matcher import EVIDENCE_CREDIT, PREFERRED_WEIGHT, REQUIRED_WEIGHT, _quiz_credit
from utils.skill_passport import KIND_SECTION, build_public_passport, normalize_visibility
from utils.skill_taxonomy import normalize_skill_name

# ── Hiring pipeline ─────────────────────────────────────────────────────────
PIPELINE_STAGES = ['new', 'under_review', 'shortlisted', 'assessment', 'interview',
                   'selected', 'rejected', 'on_hold']
STAGE_LABELS = {
    'new': 'New applicant',
    'under_review': 'Under review',
    'shortlisted': 'Shortlisted',
    'assessment': 'Assessment',
    'interview': 'Interview',
    'selected': 'Selected',
    'rejected': 'Not selected',
    'on_hold': 'On hold',
}
# What the student is told when their application moves to a stage
STAGE_STUDENT_MESSAGES = {
    'new': 'Your application was received by the employer.',
    'under_review': 'The employer is reviewing your application.',
    'shortlisted': 'You have been shortlisted.',
    'assessment': 'The employer has moved you to the assessment stage.',
    'interview': 'The employer has moved you to the interview stage.',
    'selected': 'Congratulations - the employer has selected you.',
    'rejected': 'The employer has decided not to proceed with your application.',
    'on_hold': 'The employer has put your application on hold.',
}

EMPLOYER_PROVIDER = 'employer'
EMPLOYER_SOURCE_LABEL = 'Employer (posted on SkillBridge)'

# Credit for a shared skill, by passport status (mirrors utils.job_matcher's scale:
# verified > assessed/reviewed evidence > resume claims > self-declared).
STATUS_CREDIT = {'verified': 1.0, 'pending_verification': 0.6, 'evidence_submitted': 0.55,
                 'self_declared': 0.3}
PROFICIENCY_ORDER = {'beginner': 1, 'intermediate': 2, 'advanced': 3}


def _now():
    return datetime.now(timezone.utc)


def stage_label(stage):
    return STAGE_LABELS.get(stage, stage or '')


# ── Candidate references (recruiter URLs never contain database ids) ────────
def candidate_setting(student_id: int, create: bool = True) -> Optional[CandidateDiscoverySetting]:
    setting = CandidateDiscoverySetting.query.filter_by(student_id=student_id).first()
    if setting is None and create:
        setting = CandidateDiscoverySetting(student_id=student_id, candidate_ref=secrets.token_urlsafe(16)[:22],
                                            is_discoverable=False, visibility='{}', share_readiness=False)
        db.session.add(setting)
        db.session.flush()
    return setting


def candidate_ref(student_id: int) -> str:
    return candidate_setting(student_id).candidate_ref


def student_for_ref(ref: str) -> Optional[Student]:
    if not ref or len(ref) > 32:
        return None
    setting = CandidateDiscoverySetting.query.filter_by(candidate_ref=ref).first()
    if not setting:
        return None
    student = db.session.get(Student, setting.student_id)
    if not student or student.is_active is False or (student.role or 'student') != 'student':
        return None
    return student


# ── Access decision ────────────────────────────────────────────────────────
def org_applications(org_id: int, student_id: int) -> List[JobApplication]:
    """In-app applications (with sharing consent) by this student to this organisation's jobs."""
    return (JobApplication.query.join(JobListing, JobApplication.job_id == JobListing.id)
            .filter(JobListing.organisation_id == org_id, JobApplication.student_id == student_id,
                    JobApplication.share_consent_at.isnot(None))
            .order_by(JobApplication.applied_at.desc()).all())


def access_for(org: Organisation, student: Student, job_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Returns {basis, visibility, share_readiness, applications} or None (no consent)."""
    if student is None or student.is_active is False or (student.role or 'student') != 'student':
        return None
    apps = org_applications(org.id, student.id)
    setting = candidate_setting(student.id, create=False)
    discoverable = bool(setting and setting.is_discoverable and org.is_verified)

    chosen = None
    if job_id is not None:
        chosen = next((a for a in apps if a.job_id == job_id), None)
    if chosen is not None:
        return {'basis': 'application', 'visibility': chosen.get_share_visibility(),
                'share_readiness': bool(chosen.share_readiness), 'applications': apps}
    if discoverable:
        return {'basis': 'discovery', 'visibility': setting.get_visibility(),
                'share_readiness': bool(setting.share_readiness), 'applications': apps}
    if apps:
        return {'basis': 'application', 'visibility': apps[0].get_share_visibility(),
                'share_readiness': bool(apps[0].share_readiness), 'applications': apps}
    return None


def readiness_info(student: Student) -> Dict[str, Any]:
    score = student.readiness_score
    if score is None:
        return {'score': None, 'label': 'Not calculated'}
    label = 'Job-ready' if score >= 70 else 'Developing' if score >= 40 else 'Foundation'
    return {'score': round(score, 1), 'label': label,
            'note': 'SkillBridge readiness for the student\'s own target career, computed from their '
                    'skills and assessments. It is not a hiring prediction.'}


def candidate_passport(student: Student, access: Dict[str, Any]) -> Dict[str, Any]:
    passport = build_public_passport(student, normalize_visibility(access['visibility']))
    if access.get('share_readiness'):
        passport['readiness'] = readiness_info(student)
    return passport


# ── Explainable compatibility report ───────────────────────────────────────
def _skill_credit(s: Dict[str, Any]) -> float:
    status = s.get('status')
    if status == 'assessment_completed':
        a = s.get('assessment')
        return _quiz_credit(a.get('score_percent')) if a else 0.4
    if status == 'ai_extracted':
        strength = (s.get('resume_evidence') or {}).get('evidence_strength')
        return EVIDENCE_CREDIT.get(strength, 0.4)
    return STATUS_CREDIT.get(status, 0.3)


def _norm_list(values) -> List[str]:
    out = []
    for v in values or []:
        n = normalize_skill_name(v)
        if n and n not in out:
            out.append(n)
    return out


def _evidence_note(s: Dict[str, Any]) -> List[str]:
    notes = []
    if s.get('verified_via'):
        via = {'assessment': 'passed a SkillBridge assessment', 'reviewed_evidence': 'evidence accepted by a reviewer'}
        notes.append('Verified: ' + ' and '.join(via.get(v, v) for v in s['verified_via']))
    a = s.get('assessment')
    if a:
        notes.append(f"Assessment {a['score_percent']:.0f}% ({a['correct']}/{a['total']})")
    if s.get('resume_evidence'):
        strength = (s['resume_evidence'].get('evidence_strength') or 'unclassified').replace('_', ' ')
        notes.append(f'Resume mention ({strength})')
    for e in s.get('evidence') or []:
        notes.append(f"{e['kind'].replace('_', ' ').capitalize()}: {e['title']} [{e['review_status'].replace('_', ' ')}]")
    return notes


def compatibility_report(passport: Dict[str, Any], job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare a consent-scoped passport (build_public_passport output) with a job's
    required / preferred skills. Every number comes with the per-skill evidence
    it was computed from; nothing the student did not share is used.
    """
    required = _norm_list(job.get('required_skills'))
    preferred = [p for p in _norm_list(job.get('preferred_skills')) if p not in required]
    skills_shared = 'skills' in (passport.get('sections') or [])
    by_name = {normalize_skill_name(s['skill_name']): s for s in (passport.get('skills') or [])}

    def row(skill, kind):
        s = by_name.get(skill)
        if not s:
            return {'skill': skill, 'kind': kind, 'matched': False, 'credit': 0.0,
                    'candidate_status': None, 'status_label': 'Not shown in profile', 'verified': False,
                    'needs_verification': False, 'evidence': []}
        verified = s['status'] == 'verified'
        return {'skill': skill, 'kind': kind, 'matched': True, 'credit': round(_skill_credit(s), 2),
                'candidate_status': s['status'], 'status_label': s['status_label'], 'verified': verified,
                'proficiency': s.get('proficiency'), 'last_verified_at': s.get('last_verified_at'),
                'needs_verification': not verified, 'evidence': _evidence_note(s)}

    req_rows = [row(s, 'required') for s in required]
    pref_rows = [row(s, 'preferred') for s in preferred]

    total_weight = REQUIRED_WEIGHT * len(required) + PREFERRED_WEIGHT * len(preferred)
    if not skills_shared or total_weight == 0:
        fit = None
        label = 'Not enough information'
    else:
        fit = round(100.0 * (REQUIRED_WEIGHT * sum(r['credit'] for r in req_rows) +
                             PREFERRED_WEIGHT * sum(r['credit'] for r in pref_rows)) / total_weight, 1)
        label = ('Strong match' if fit >= 70 else 'Moderate match' if fit >= 45
                 else 'Developing match' if fit >= 25 else 'Low match')

    job_skills = set(required) | set(preferred)
    relevant_projects = []
    for kind, key in KIND_SECTION.items():
        for e in passport.get(key) or []:
            hits = sorted({normalize_skill_name(x) for x in e.get('skills') or []} & job_skills)
            if hits:
                relevant_projects.append({'kind': kind, 'title': e['title'], 'organization': e.get('organization', ''),
                                          'review_status': e['review_status'], 'matching_skills': hits,
                                          'url': e.get('url', '')})
    relevant_assessments = [a for a in passport.get('assessments') or []
                            if normalize_skill_name(a['skill_name']) in job_skills]

    limitations = []
    if not skills_shared:
        limitations.append('The candidate has not shared their skills section, so no skill match can be calculated.')
    elif passport.get('skill_filter') == 'verified':
        limitations.append('The candidate shares only verified skills; other skills they hold are not shown.')
    elif passport.get('skill_filter') == 'evidence':
        limitations.append('The candidate shares only skills with evidence or an assessment; '
                           'resume-only and self-declared skills are not shown.')
    if total_weight == 0:
        limitations.append('This job lists no recognisable skills, so a skill match cannot be calculated.')
    if 'assessments' not in (passport.get('sections') or []):
        limitations.append('Assessment scores are not shared; assessed skills still show their verification status.')
    needs = [r['skill'] for r in req_rows + pref_rows if r['needs_verification']]
    if needs:
        limitations.append('Matched but not verified (confirm in interview or ask for an assessment): '
                           + ', '.join(needs) + '.')

    exp_min, exp_max = job.get('experience_min_years'), job.get('experience_max_years')
    exp_req = (f"{exp_min:g}-{exp_max:g} years" if exp_min is not None and exp_max is not None else
               f"{exp_min:g}+ years" if exp_min is not None else job.get('experience_level') or 'Not stated')
    edu = (passport.get('education') or {}).get('current') or {}

    return {
        'job': {'id': job.get('id'), 'title': job.get('title')},
        'skills_shared': skills_shared,
        'skill_fit_score': fit,
        'fit_label': label,
        'required': req_rows,
        'preferred': pref_rows,
        'summary': {
            'required_total': len(required),
            'required_matched': sum(1 for r in req_rows if r['matched']),
            'required_verified': sum(1 for r in req_rows if r['verified']),
            'preferred_total': len(preferred),
            'preferred_matched': sum(1 for r in pref_rows if r['matched']),
            'missing_mandatory': [r['skill'] for r in req_rows if not r['matched']],
            'matching_preferred': [r['skill'] for r in pref_rows if r['matched']],
            'needs_verification': needs,
        },
        'relevant_projects': relevant_projects,
        'relevant_assessments': relevant_assessments,
        'experience': {'job_requires': exp_req,
                       'candidate_entries': len(passport.get('experience') or []) if 'experience' in passport else None,
                       'note': 'Not scored: shared experience entries are listed for your judgement.'},
        'education': {'job_requires': job.get('eligibility') or 'Not stated',
                      'candidate': ' · '.join(x for x in (edu.get('program'), edu.get('institution'), edu.get('year')) if x)
                      if 'education' in passport else None,
                      'note': 'Not scored: compare against your requirement yourself.'},
        'limitations': limitations,
        'method': ('Skill fit = weighted credit of required (x3) and preferred (x1) skills. Credit per skill: '
                   'verified 1.0; assessed below the pass mark 0.6 or 0.2 by score; pending review 0.6; '
                   'evidence submitted 0.55; resume mention 0.40-0.70 by how strongly the resume supports it; '
                   'self-declared 0.3; not shown 0. Only information the candidate chose to share is used, and '
                   'no personal characteristic (name, college, location, gender, age) is part of the score.'),
        'disclaimer': 'An explainable indicator of skill alignment, not a prediction of job performance.',
    }


# ── Candidate search ────────────────────────────────────────────────────────
def _contains(haystack: List[str], needle: str) -> bool:
    n = needle.strip().lower()
    return any(n in (h or '').lower() for h in haystack)


def passes_filters(passport: Dict[str, Any], f: Dict[str, Any], readiness: Optional[float]) -> bool:
    skills = {normalize_skill_name(s['skill_name']): s for s in passport.get('skills') or []}
    wanted = f.get('skills') or []
    if wanted:
        if 'skills' not in passport['sections']:
            return False
        hits = [skills[w] for w in wanted if w in skills]
        if f.get('verified_only'):
            hits = [h for h in hits if h['status'] == 'verified']
        if f.get('match_all') and len(hits) < len(wanted):
            return False
        if not hits:
            return False
    else:
        hits = list(skills.values())
        if f.get('verified_only') and not any(h['status'] == 'verified' for h in hits):
            return False
    if f.get('min_proficiency'):
        need = PROFICIENCY_ORDER.get(f['min_proficiency'].lower(), 0)
        if not any(PROFICIENCY_ORDER.get((h.get('proficiency') or '').lower(), 0) >= need for h in hits):
            return False
    if f.get('min_assessment') is not None:
        pool = passport.get('assessments') or []
        if wanted:
            pool = [a for a in pool if normalize_skill_name(a['skill_name']) in wanted]
        if not any((a.get('score_percent') or 0) >= f['min_assessment'] for a in pool):
            return False
    if f.get('education'):
        edu = (passport.get('education') or {}).get('current') or {}
        if not _contains([edu.get('program'), edu.get('institution')], f['education']):
            return False
    ci = passport.get('career_interests') or {}
    if f.get('location'):
        from utils.job_discovery.normalizer import location_search_terms
        locs = ci.get('preferred_locations') or []
        if not any(_contains(locs, t) for t in location_search_terms(f['location'])):
            return False
    if f.get('role'):
        if not _contains((ci.get('preferred_roles') or []) + [ci.get('target_career') or ''], f['role']):
            return False
    if f.get('has_projects') and not passport.get('projects'):
        return False
    if f.get('has_experience') and not passport.get('experience'):
        return False
    if f.get('min_readiness') is not None and (readiness is None or readiness < f['min_readiness']):
        return False
    return True


def candidate_summary(student: Student, passport: Dict[str, Any], report: Optional[Dict[str, Any]],
                      access: Dict[str, Any]) -> Dict[str, Any]:
    skills = passport.get('skills') or []
    edu = (passport.get('education') or {}).get('current') or {}
    return {
        'candidate_ref': candidate_ref(student.id),
        'name': passport['name'],
        'headline': (passport.get('profile') or {}).get('headline', ''),
        'education': ' · '.join(x for x in (edu.get('program'), edu.get('institution')) if x),
        'basis': access['basis'],
        'skills_shared': 'skills' in passport['sections'],
        'skill_count': len(skills),
        'verified_count': sum(1 for s in skills if s['status'] == 'verified'),
        'top_skills': [{'skill_name': s['skill_name'], 'status': s['status'], 'status_label': s['status_label']}
                       for s in skills[:8]],
        'project_count': len(passport.get('projects') or []),
        'experience_count': len(passport.get('experience') or []),
        'readiness': passport.get('readiness'),
        'career_interests': passport.get('career_interests'),
        'report': report,
    }


def search_candidates(org: Organisation, f: Dict[str, Any], job: Optional[JobListing] = None,
                      limit: int = 50) -> Dict[str, Any]:
    """Discoverable candidates (opt-in) for a verified organisation, filtered and ranked
    by consent-scoped skill evidence."""
    settings = (CandidateDiscoverySetting.query.filter_by(is_discoverable=True)
                .order_by(CandidateDiscoverySetting.id.asc()).limit(1000).all())
    if job is not None:
        target = {'id': job.id, 'title': job.title, 'required_skills': job.get_required_skills(),
                  'preferred_skills': job.get_preferred_skills(), 'eligibility': job.eligibility,
                  'experience_min_years': job.experience_min_years,
                  'experience_max_years': job.experience_max_years, 'experience_level': job.experience_level}
    elif f.get('skills'):
        target = {'id': None, 'title': 'Search query', 'required_skills': f['skills'], 'preferred_skills': []}
    else:
        target = None

    results = []
    for setting in settings:
        student = db.session.get(Student, setting.student_id)
        access = access_for(org, student) if student else None
        if not access or access['basis'] != 'discovery':
            continue
        passport = candidate_passport(student, access)
        readiness = (passport.get('readiness') or {}).get('score')
        if not passes_filters(passport, f, readiness):
            continue
        report = compatibility_report(passport, target) if target else None
        results.append(candidate_summary(student, passport, report, access))

    def key(r):
        fit = (r['report'] or {}).get('skill_fit_score')
        return (fit is None, -(fit or 0), -r['verified_count'], -r['skill_count'])

    results.sort(key=key)
    return {'candidates': results[:limit], 'total': len(results),
            'ranked_by': ('Skill fit for the job / searched skills, then number of verified skills'
                          if target else 'Number of verified skills')}


# ── Pipeline ───────────────────────────────────────────────────────────────
def move_stage(app: JobApplication, to_stage: str, org_id: int, actor_id: Optional[int],
               message: Optional[str] = None) -> ApplicationEvent:
    ev = ApplicationEvent(application_id=app.id, organisation_id=org_id, actor_id=actor_id,
                          from_stage=app.stage, to_stage=to_stage, message=(message or None),
                          seen_by_student=False, created_at=_now())
    app.stage = to_stage
    app.stage_updated_at = _now()
    app.status = stage_label(to_stage)   # keeps the student's existing application tracker in sync
    db.session.add(ev)
    return ev


def email_domain_signal(recruiter_email: str, website: str) -> Dict[str, Any]:
    """A hint for the administrator reviewing an organisation. Not verification."""
    import re
    email_domain = (recruiter_email or '').rsplit('@', 1)[-1].lower().strip()
    m = re.match(r'^https?://(?:www\.)?([^/:?#]+)', (website or '').strip().lower())
    site = m.group(1) if m else ''
    free = email_domain in {'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'live.com',
                            'icloud.com', 'proton.me', 'protonmail.com', 'rediffmail.com', 'yahoo.co.in'}
    matches = bool(site) and (email_domain == site or email_domain.endswith('.' + site) or site.endswith('.' + email_domain))
    return {'recruiter_email_domain': email_domain, 'website_domain': site,
            'domains_match': matches, 'free_email_provider': free,
            'note': 'Automatic hint only. An administrator must still check the organisation.'}


def dumps(obj) -> str:
    return json.dumps(obj, default=str)
