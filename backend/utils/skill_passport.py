"""
Verified Skill Passport.

Builds an evidence-backed profile from data SkillBridge already stores
(student profile, resume-extracted skills, quiz verifications, job preferences,
parsed resume) plus the passport tables (professional profile, submitted
evidence, share links).

Verification rules (one primary status per skill, strongest first):

    verified              latest SkillBridge assessment passed (>= PASS_THRESHOLD)
                          OR an administrator reviewed and accepted linked evidence
    assessment_completed  assessment taken, latest attempt below the pass mark
    pending_verification  linked evidence submitted for administrator review
    evidence_submitted    project / certificate / experience / challenge linked,
                          not (yet) submitted for review
    ai_extracted          found in the resume by the skill extractor, nothing more
    self_declared         added by the student, nothing more

A resume mention, an uploaded certificate or any other submitted evidence never
makes a skill "verified" on its own.
"""
import hashlib
import hmac
import io
import json
import logging
import os
import re
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from flask import current_app

from models import (Skill, SkillVerification, JobPreference, Resume, PassportProfile,
                    PassportEvidence)
from utils.skill_taxonomy import skill_category

logger = logging.getLogger("skillbridge.passport")

PASS_THRESHOLD = 70.0  # same pass mark as the Verified Skill Profile page

STATUS_ORDER = ['self_declared', 'ai_extracted', 'evidence_submitted',
                'pending_verification', 'assessment_completed', 'verified']
STATUS_LABELS = {
    'verified': 'Verified',
    'assessment_completed': 'Assessment completed',
    'pending_verification': 'Pending verification',
    'evidence_submitted': 'Evidence submitted',
    'ai_extracted': 'AI-extracted',
    'self_declared': 'Self-declared',
}
STATUS_DESCRIPTIONS = {
    'verified': 'Passed a SkillBridge assessment or has evidence accepted by a reviewer.',
    'assessment_completed': f'Assessment taken; latest score is below the {int(PASS_THRESHOLD)}% pass mark.',
    'pending_verification': 'Evidence has been submitted and is waiting for review.',
    'evidence_submitted': 'Supporting evidence is attached but has not been reviewed.',
    'ai_extracted': 'Detected in the resume by SkillBridge; not yet assessed.',
    'self_declared': 'Added by the student; no supporting evidence yet.',
}

GROUP_LABELS = {
    'languages_frameworks': 'Programming languages & frameworks',
    'ai_ml_data': 'AI/ML & data science',
    'technical': 'Technical skills',
    'soft_skills': 'Soft skills',
}
_CATEGORY_GROUP = {
    'Programming': 'languages_frameworks', 'Web': 'languages_frameworks',
    'Backend': 'languages_frameworks', 'Mobile': 'languages_frameworks',
    'ML/AI': 'ai_ml_data', 'Data': 'ai_ml_data',
    'Professional': 'soft_skills',
}

EVIDENCE_KIND_LABELS = {
    'project': 'Project',
    'certificate': 'Certificate',
    'experience': 'Experience',
    'practical_challenge': 'Practical challenge',
}
KIND_SECTION = {
    'project': 'projects',
    'certificate': 'certifications',
    'experience': 'experience',
    'practical_challenge': 'practical_challenges',
}

# Sections a student can show or hide on a share link / PDF.
SECTION_KEYS = ['profile', 'links', 'education', 'skills', 'projects', 'certifications',
                'experience', 'practical_challenges', 'assessments', 'career_interests']
SKILL_FILTERS = ('all', 'evidence', 'verified')
_EVIDENCE_OR_BETTER = {'evidence_submitted', 'pending_verification', 'assessment_completed', 'verified'}

EVIDENCE_FILE_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
_MAGIC = {'pdf': (b'%PDF',), 'png': (b'\x89PNG',), 'jpg': (b'\xff\xd8',), 'jpeg': (b'\xff\xd8',)}


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────
def _iso(dt):
    return dt.isoformat() if dt else None


def _aware(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def skill_group(skill):
    cat = skill.category or skill_category(skill.skill_name)
    return _CATEGORY_GROUP.get(cat, 'technical')


def is_safe_url(url):
    """Only plain http(s) links are stored, so a shared page can never carry javascript: links."""
    return bool(re.match(r'^https?://[^\s<>"\']+$', url or '', re.I)) and len(url) <= 500


def default_visibility():
    return {'sections': {k: True for k in SECTION_KEYS}, 'skill_filter': 'all'}


def normalize_visibility(raw):
    """Whitelist the share settings: unknown sections are dropped, missing ones default to hidden
    only when the client sent an explicit sections object."""
    vis = default_visibility()
    if not isinstance(raw, dict):
        return vis
    sections = raw.get('sections')
    if isinstance(sections, dict):
        vis['sections'] = {k: bool(sections.get(k, False)) for k in SECTION_KEYS}
    if raw.get('skill_filter') in SKILL_FILTERS:
        vis['skill_filter'] = raw['skill_filter']
    return vis


def evidence_dir():
    return os.path.join(current_app.root_path, 'uploads', 'evidence')


def evidence_file_abspath(stored):
    if not stored:
        return ''
    path = stored if os.path.isabs(stored) else os.path.join(current_app.root_path, stored)
    root = os.path.abspath(evidence_dir())
    full = os.path.abspath(path)
    # Never resolve outside the evidence folder
    if os.path.commonpath([full, root]) != root:
        return ''
    return full


def delete_evidence_files(paths):
    removed = 0
    for p in paths:
        full = evidence_file_abspath(p)
        try:
            if full and os.path.isfile(full):
                os.remove(full)
                removed += 1
        except OSError as e:  # pragma: no cover
            logger.warning("Could not delete evidence file %s: %s", full, e)
    return removed


def file_matches_extension(head: bytes, ext: str) -> bool:
    return any(head.startswith(m) for m in _MAGIC.get(ext, ()))


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def viewer_fingerprint(ip: str) -> str:
    """Keyed hash of the requester IP: lets the student count distinct viewers
    without SkillBridge storing anyone's IP address."""
    key = (current_app.config.get('SECRET_KEY') or 'skillbridge').encode()
    return hmac.new(key, (ip or '').encode(), hashlib.sha256).hexdigest()[:16]


# ─────────────────────────────────────────────────────────────────────────
# Resume structure (re-uses the resume optimizer's section parser)
# ─────────────────────────────────────────────────────────────────────────
def latest_resume_structure(student_id):
    resume = (Resume.query.filter_by(student_id=student_id)
              .filter(Resume.parsed_text.isnot(None))
              .order_by(Resume.is_latest.desc(), Resume.uploaded_on.desc()).first())
    if not resume or not (resume.parsed_text or '').strip():
        return None, None
    try:
        from utils.resume_optimizer import parse_resume_to_structured_json
        return resume, parse_resume_to_structured_json(resume.parsed_text)
    except Exception as e:  # parsing is heuristic; never break the passport
        logger.warning("Resume structure parse failed for resume %s: %s", resume.id, e)
        return resume, None


def resume_import_candidates(structure):
    """Projects, certificates and experience found in the parsed resume, in a
    shape that can be imported as passport evidence."""
    if not structure:
        return {'project': [], 'certificate': [], 'experience': []}
    projects = []
    for p in structure.get('projects') or []:
        title = (p.get('name') or '').strip()
        if not title:
            continue
        desc = ' '.join(p.get('bullets') or [])
        if p.get('technologies'):
            desc = (f"Technologies: {p['technologies']}. " + desc).strip()
        projects.append({'title': title[:200], 'organization': '', 'description': desc[:2000],
                         'url': p.get('link') or ''})
    certs = [{'title': c.strip()[:200], 'organization': '', 'description': '', 'url': ''}
             for c in (structure.get('certifications') or []) if c and c.strip()]
    experience = []
    for e in structure.get('experience') or []:
        title = (e.get('title') or e.get('role') or e.get('position') or '').strip()
        org = (e.get('company') or e.get('organization') or '').strip()
        if not (title or org):
            continue
        experience.append({'title': (title or org)[:200], 'organization': org[:200],
                           'description': ' '.join(e.get('bullets') or [])[:2000],
                           'url': '', 'dates': (e.get('period') or '')[:40]})
    return {'project': projects, 'certificate': certs, 'experience': experience}


# ─────────────────────────────────────────────────────────────────────────
# Skill status
# ─────────────────────────────────────────────────────────────────────────
def _latest_verifications(student_id, skills):
    """Latest quiz attempt per skill (by skill id, falling back to skill name,
    the same matching the Assessments page uses)."""
    by_id = {}
    for v in (SkillVerification.query.filter_by(student_id=student_id)
              .order_by(SkillVerification.verified_on.asc(), SkillVerification.id.asc()).all()):
        by_id[v.skill_id] = v
    name_of = {s.id: s.skill_name.lower().strip() for s in skills}
    by_name = {}
    for sid, v in by_id.items():
        n = name_of.get(sid)
        if n and (n not in by_name or _aware(v.verified_on) >= _aware(by_name[n].verified_on)):
            by_name[n] = v
    return by_id, by_name


def skill_status(skill, latest_attempt, evidence_items):
    self_declared = (skill.source == 'self_declared')
    # Extracted from a resume: has a resume link, or is a legacy/resume-sourced row
    in_resume = skill.resume_id is not None or not self_declared
    passed = bool(latest_attempt and (latest_attempt.quiz_score_percent or 0) >= PASS_THRESHOLD)
    reviewed_ok = [e for e in evidence_items if e.review_status == 'verified']
    pending = [e for e in evidence_items if e.review_status == 'pending']
    submitted = [e for e in evidence_items if e.review_status != 'rejected']

    if passed or reviewed_ok:
        status = 'verified'
    elif latest_attempt:
        status = 'assessment_completed'
    elif pending:
        status = 'pending_verification'
    elif submitted:
        status = 'evidence_submitted'
    elif in_resume:
        status = 'ai_extracted'
    else:
        status = 'self_declared'

    verified_via = []
    if passed:
        verified_via.append('assessment')
    if reviewed_ok:
        verified_via.append('reviewed_evidence')

    dates = []
    if passed:
        dates.append(_aware(latest_attempt.verified_on))
    dates += [_aware(e.reviewed_at) for e in reviewed_ok if e.reviewed_at]
    last_verified = max(dates) if dates else None

    signals = []
    if self_declared:
        signals.append('self_declared')
    if in_resume:
        signals.append('ai_extracted')
    if submitted:
        signals.append('evidence_submitted')
    if pending:
        signals.append('pending_verification')
    if latest_attempt:
        signals.append('assessment_completed')
    if status == 'verified':
        signals.append('verified')
    return status, verified_via, last_verified, signals


# ─────────────────────────────────────────────────────────────────────────
# Passport builder
# ─────────────────────────────────────────────────────────────────────────
def _career_interests(student):
    pref = JobPreference.query.filter_by(student_id=student.id).first()
    p = pref.to_dict() if pref else {}
    return {
        'target_career': student.target_career or '',
        'preferred_roles': p.get('preferred_roles', []),
        'preferred_locations': p.get('preferred_locations', []),
        'work_modes': p.get('work_modes', []),
        'job_types': p.get('job_types', []),
        'open_to_relocation': p.get('open_to_relocation', False),
    }


def build_owner_passport(student):
    """Everything the student sees about their own passport (never served publicly)."""
    skills_rows = Skill.query.filter_by(student_id=student.id).order_by(Skill.id.asc()).all()
    # One entry per skill name (older data can contain duplicates)
    skills, seen = [], set()
    for s in skills_rows:
        key = s.skill_name.lower().strip()
        if key not in seen:
            seen.add(key)
            skills.append(s)

    evidence = (PassportEvidence.query.filter_by(student_id=student.id)
                .order_by(PassportEvidence.created_at.desc(), PassportEvidence.id.desc()).all())
    ev_by_skill = {}
    for e in evidence:
        for sk in e.skills:
            ev_by_skill.setdefault(sk.skill_name.lower().strip(), []).append(e)

    latest_by_id, latest_by_name = _latest_verifications(student.id, skills_rows)

    skill_items = []
    for s in skills:
        key = s.skill_name.lower().strip()
        attempt = latest_by_id.get(s.id) or latest_by_name.get(key)
        linked = ev_by_skill.get(key, [])
        status, via, last_verified, signals = skill_status(s, attempt, linked)
        resume_ev = None
        if 'ai_extracted' in signals:
            resume_ev = {
                'evidence_strength': s.evidence_strength or 'unclassified',
                'sections': sorted({(x.get('section') or '').strip() for x in s.get_evidence()
                                    if isinstance(x, dict) and x.get('section')}),
                'snippets': [x for x in s.get_evidence() if isinstance(x, dict)][:3],
                'explanation': s.extraction_explanation,
            }
        skill_items.append({
            'id': s.id,
            'skill_name': s.skill_name,
            'group': skill_group(s),
            'category': s.category or skill_category(s.skill_name),
            'source': s.source or 'resume',
            'proficiency': s.proficiency if attempt else 'Not assessed',
            'status': status,
            'status_label': STATUS_LABELS[status],
            'signals': signals,
            'verified_via': via,
            'last_verified_at': _iso(last_verified),
            'resume_evidence': resume_ev,
            'assessment': {
                'score_percent': attempt.quiz_score_percent,
                'correct': attempt.quiz_correct_count,
                'total': attempt.quiz_question_count,
                'passed': (attempt.quiz_score_percent or 0) >= PASS_THRESHOLD,
                'taken_at': _iso(attempt.verified_on),
            } if attempt else None,
            'evidence': [{'id': e.id, 'kind': e.kind, 'title': e.title,
                          'review_status': e.review_status} for e in linked],
            # Only signals the system actually computes, each with what it means
            'confidence': {
                'resume_mention_confidence': s.extraction_confidence if 'ai_extracted' in signals else None,
                'resume_evidence_strength': s.evidence_strength if 'ai_extracted' in signals else None,
                'verification_score': attempt.verification_score if attempt else None,
            },
        })
    skill_items.sort(key=lambda x: (-STATUS_ORDER.index(x['status']), x['skill_name']))

    assessments = []
    for s in skills:
        a = next((i['assessment'] for i in skill_items if i['id'] == s.id), None)
        if a:
            assessments.append({'skill_name': s.skill_name, **a})
    assessments.sort(key=lambda a: a['taken_at'] or '', reverse=True)

    profile = PassportProfile.query.filter_by(student_id=student.id).first()
    resume, structure = latest_resume_structure(student.id)
    contact = (structure or {}).get('contact') or {}
    suggestions = {
        'summary': (structure or {}).get('summary', '')[:2000],
        'linkedin_url': _as_url(contact.get('linkedin')),
        'github_url': _as_url(contact.get('github')),
        'portfolio_url': _as_url(contact.get('portfolio')),
    }
    candidates = resume_import_candidates(structure)
    existing = {(e.kind, e.title.lower().strip()) for e in evidence}
    for kind, items in candidates.items():
        for idx, item in enumerate(items):
            item['index'] = idx
            item['already_added'] = (kind, item['title'].lower().strip()) in existing

    counts = {st: 0 for st in STATUS_ORDER}
    for i in skill_items:
        counts[i['status']] += 1

    return {
        'student': {
            'name': student.name,
            'college': student.college or '',
            'course': student.course or '',
            'year': student.year or '',
        },
        'profile': profile.to_dict() if profile else PassportProfile().to_dict(),
        'profile_saved': profile is not None,
        'suggestions': suggestions,
        'education': {
            'current': {'institution': student.college or '', 'program': student.course or '',
                        'year': student.year or ''},
            'from_resume': [e for e in (structure or {}).get('education') or []
                            if (e.get('degree') or e.get('institution'))],
        },
        'skills': skill_items,
        'skill_groups': GROUP_LABELS,
        'status_labels': STATUS_LABELS,
        'status_descriptions': STATUS_DESCRIPTIONS,
        'status_counts': counts,
        'evidence': [e.to_dict() for e in evidence],
        'assessments': assessments,
        'career_interests': _career_interests(student),
        'resume': {'id': resume.id, 'filename': resume.original_filename,
                   'uploaded_on': _iso(resume.uploaded_on)} if resume else None,
        'resume_import_candidates': candidates,
        'pass_threshold': PASS_THRESHOLD,
        'section_keys': SECTION_KEYS,
        'generated_at': datetime.now(timezone.utc).isoformat(),
    }


def _as_url(value):
    v = (value or '').strip()
    if not v:
        return ''
    if not re.match(r'^https?://', v, re.I):
        v = 'https://' + v
    return v if is_safe_url(v) else ''


def build_public_passport(student, visibility):
    """
    Recruiter-facing view: only the sections the student selected, no internal ids,
    no email/phone, no resume text, no uploaded files, no review notes,
    no rejected evidence.
    """
    vis = normalize_visibility(visibility)
    sec = vis['sections']
    owner = build_owner_passport(student)

    skills = owner['skills']
    if vis['skill_filter'] == 'verified':
        skills = [s for s in skills if s['status'] == 'verified']
    elif vis['skill_filter'] == 'evidence':
        skills = [s for s in skills if s['status'] in _EVIDENCE_OR_BETTER]
    visible_skill_names = {s['skill_name'].lower() for s in skills}

    out = {
        'name': student.name,
        'sections': [k for k in SECTION_KEYS if sec.get(k)],
        'skill_filter': vis['skill_filter'],
        'status_labels': STATUS_LABELS,
        'status_descriptions': STATUS_DESCRIPTIONS,
        'skill_groups': GROUP_LABELS,
        'pass_threshold': PASS_THRESHOLD,
        'generated_at': owner['generated_at'],
    }
    prof = owner['profile']
    if sec.get('profile'):
        out['profile'] = {'headline': prof['headline'], 'summary': prof['summary']}
    if sec.get('links'):
        out['links'] = {k: prof[k] for k in ('linkedin_url', 'github_url', 'portfolio_url')
                        if prof.get(k) and is_safe_url(prof[k])}
    if sec.get('education'):
        # Only what the student entered; resume-parsed entries are heuristic and are
        # shown to the student alone (like other resume content until they import it).
        out['education'] = {'current': owner['education']['current'], 'from_resume': []}
    if sec.get('skills'):
        out['skills'] = [{
            'skill_name': s['skill_name'],
            'group': s['group'],
            'proficiency': s['proficiency'],
            'status': s['status'],
            'status_label': s['status_label'],
            'verified_via': s['verified_via'],
            'last_verified_at': s['last_verified_at'],
            'resume_evidence': ({'evidence_strength': s['resume_evidence']['evidence_strength'],
                                 'sections': s['resume_evidence']['sections']}
                                if s['resume_evidence'] else None),
            'assessment': s['assessment'] if sec.get('assessments') else None,
            'evidence': [{'kind': e['kind'], 'title': e['title'], 'review_status': e['review_status']}
                         for e in s['evidence'] if e['review_status'] != 'rejected'
                         and sec.get(KIND_SECTION.get(e['kind'], ''))],
        } for s in skills]

    for kind, key in KIND_SECTION.items():
        if not sec.get(key):
            continue
        out[key] = [{
            'kind': e['kind'],
            'title': e['title'],
            'organization': e['organization'],
            'description': e['description'],
            'url': e['url'] if is_safe_url(e['url']) else '',
            'start_date': e['start_date'],
            'end_date': e['end_date'],
            'review_status': e['review_status'],
            'skills': [x['skill_name'] for x in e['skills'] if x['skill_name'].lower() in visible_skill_names],
        } for e in owner['evidence'] if e['kind'] == kind and e['review_status'] != 'rejected']

    if sec.get('assessments'):
        out['assessments'] = [a for a in owner['assessments']
                              if a['skill_name'].lower() in visible_skill_names]
    if sec.get('career_interests'):
        out['career_interests'] = owner['career_interests']
    return out


# ─────────────────────────────────────────────────────────────────────────
# QR code & PDF (reportlab, already a dependency)
# ─────────────────────────────────────────────────────────────────────────
def make_qr_svg(data: str, size: int = 220) -> str:
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics import renderSVG
    widget = QrCodeWidget(data)
    x0, y0, x1, y1 = widget.getBounds()
    drawing = Drawing(size, size, transform=[size / (x1 - x0), 0, 0, size / (y1 - y0), 0, 0])
    drawing.add(widget)
    return renderSVG.drawToString(drawing)


def _p(text):
    return escape(str(text or ''))


def render_passport_pdf(passport: dict, share_url: str = None) -> bytes:
    """Render a public-shaped passport dict (see build_public_passport) to PDF bytes."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
                            topMargin=14 * mm, bottomMargin=14 * mm,
                            title=f"Skill Passport - {passport.get('name', '')}", author='SkillBridge')
    ss = getSampleStyleSheet()
    teal = colors.HexColor('#0d9488')
    h1 = ParagraphStyle('h1', parent=ss['Title'], alignment=0, fontSize=20, spaceAfter=2)
    h2 = ParagraphStyle('h2', parent=ss['Heading2'], textColor=teal, fontSize=12.5, spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle('body', parent=ss['BodyText'], fontSize=9.5, leading=13)
    small = ParagraphStyle('small', parent=body, fontSize=8, leading=10.5, textColor=colors.HexColor('#555555'))
    cell = ParagraphStyle('cell', parent=body, fontSize=8.5, leading=11)

    story = [Paragraph(_p(passport.get('name')), h1),
             Paragraph('SkillBridge Verified Skill Passport', small)]
    prof = passport.get('profile') or {}
    if prof.get('headline'):
        story.append(Paragraph(f"<b>{_p(prof['headline'])}</b>", body))
    if prof.get('summary'):
        story.append(Spacer(1, 3))
        story.append(Paragraph(_p(prof['summary']), body))
    links = passport.get('links') or {}
    if links:
        story.append(Spacer(1, 3))
        story.append(Paragraph(' &nbsp;|&nbsp; '.join(_p(v) for v in links.values()), small))

    edu = passport.get('education')
    if edu:
        story.append(Paragraph('Education', h2))
        cur = edu.get('current') or {}
        if cur.get('institution') or cur.get('program'):
            story.append(Paragraph(_p(' - '.join(x for x in (cur.get('program'), cur.get('institution'),
                                                              cur.get('year')) if x)), body))
        for e in edu.get('from_resume') or []:
            story.append(Paragraph(_p(' - '.join(x for x in (e.get('degree'), e.get('institution'),
                                                              e.get('year'), e.get('score')) if x)) +
                                   ' <font color="#777777">(from resume)</font>', body))

    skills = passport.get('skills')
    if skills is not None:
        story.append(Paragraph('Skills', h2))
        if not skills:
            story.append(Paragraph('No skills match the selected filter.', small))
        groups = passport.get('skill_groups') or GROUP_LABELS
        for gkey, glabel in groups.items():
            rows = [s for s in skills if s['group'] == gkey]
            if not rows:
                continue
            story.append(Paragraph(f"<b>{_p(glabel)}</b>", body))
            data = [[Paragraph('<b>Skill</b>', cell), Paragraph('<b>Status</b>', cell),
                     Paragraph('<b>Proficiency</b>', cell), Paragraph('<b>Assessment</b>', cell),
                     Paragraph('<b>Evidence</b>', cell)]]
            for s in rows:
                a = s.get('assessment')
                ev = [EVIDENCE_KIND_LABELS.get(e['kind'], e['kind']) + ': ' + e['title'] for e in s.get('evidence') or []]
                if s.get('resume_evidence'):
                    ev.insert(0, 'Resume (' + (s['resume_evidence'].get('evidence_strength') or '').replace('_', ' ') + ')')
                verified = (' (' + s['last_verified_at'][:10] + ')') if s.get('last_verified_at') else ''
                data.append([
                    Paragraph(_p(s['skill_name']), cell),
                    Paragraph(_p(s['status_label'] + verified), cell),
                    Paragraph(_p(s['proficiency']), cell),
                    Paragraph(_p(f"{a['score_percent']:.0f}% ({a['correct']}/{a['total']})") if a and a.get('score_percent') is not None else '-', cell),
                    Paragraph(_p('; '.join(ev)) or '-', cell),
                ])
            t = Table(data, colWidths=[30 * mm, 34 * mm, 26 * mm, 24 * mm, 64 * mm], repeatRows=1)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e6f7f5')),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#cccccc')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story += [t, Spacer(1, 5)]

    for kind, key in KIND_SECTION.items():
        items = passport.get(key)
        if items is None:
            continue
        story.append(Paragraph({'projects': 'Projects', 'certifications': 'Certifications',
                                'experience': 'Experience',
                                'practical_challenges': 'Practical challenges'}[key], h2))
        if not items:
            story.append(Paragraph('None added yet.', small))
        for e in items:
            head = f"<b>{_p(e['title'])}</b>"
            if e.get('organization'):
                head += f" - {_p(e['organization'])}"
            dates = ' - '.join(x for x in (e.get('start_date'), e.get('end_date')) if x)
            if dates:
                head += f" <font color='#777777'>({_p(dates)})</font>"
            head += f" <font color='#0d9488'>[{_p(_review_label(e['review_status']))}]</font>"
            story.append(Paragraph(head, body))
            if e.get('description'):
                story.append(Paragraph(_p(e['description'][:900]), small))
            meta = []
            if e.get('skills'):
                meta.append('Skills: ' + ', '.join(e['skills']))
            if e.get('url'):
                meta.append(e['url'])
            if meta:
                story.append(Paragraph(_p(' | '.join(meta)), small))
            story.append(Spacer(1, 3))

    ci = passport.get('career_interests')
    if ci:
        story.append(Paragraph('Career interests', h2))
        parts = []
        if ci.get('target_career'):
            parts.append(f"<b>Target career:</b> {_p(ci['target_career'])}")
        for label, k in (('Preferred roles', 'preferred_roles'), ('Locations', 'preferred_locations'),
                         ('Work modes', 'work_modes'), ('Job types', 'job_types')):
            if ci.get(k):
                parts.append(f"<b>{label}:</b> {_p(', '.join(ci[k]))}")
        story.append(Paragraph('<br/>'.join(parts) or 'Not specified.', body))

    story.append(Spacer(1, 10))
    story.append(Paragraph(
        'Verification statuses reflect SkillBridge records at the time this document was generated '
        f"({_p(passport.get('generated_at', '')[:16].replace('T', ' '))} UTC). \"Verified\" means the "
        f"student passed a SkillBridge assessment (pass mark {int(passport.get('pass_threshold', PASS_THRESHOLD))}%) "
        'or a reviewer accepted the linked evidence. Resume mentions and submitted evidence alone are not '
        'treated as verification.', small))
    if share_url:
        story.append(Paragraph(f"Live version: {_p(share_url)}", small))

    doc.build(story)
    return buf.getvalue()


def _review_label(status):
    return {'verified': 'Reviewed & accepted', 'pending': 'Pending review',
            'not_requested': 'Not reviewed', 'rejected': 'Rejected'}.get(status, status)
