"""
Verified Skill Passport API.

  /api/passport/me/...           student's own passport (login required, scoped to current_user)
  /api/passport/public/<token>   recruiter view of a share link (no login; token-gated)
  /api/passport/admin/...        evidence review queue (administrators only)
"""
import json
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request, send_file, make_response
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from extensions import db
from models import (Skill, SkillVerification, PassportProfile, PassportEvidence, PassportShare,
                    PassportAccessLog, Student)
from routes.admin import admin_required
from utils.audit import audit
from utils.rate_limit import rate_limited
from utils.skill_passport import (
    build_owner_passport, build_public_passport, normalize_visibility, default_visibility,
    render_passport_pdf, make_qr_svg, hash_token, viewer_fingerprint, is_safe_url,
    latest_resume_structure, resume_import_candidates, evidence_dir, evidence_file_abspath,
    delete_evidence_files, file_matches_extension, EVIDENCE_FILE_EXTENSIONS,
)
from utils.skill_taxonomy import normalize_skill_name, skill_category, extract_skill_names

passport_bp = Blueprint('passport', __name__)


@passport_bp.before_request
def _block_recruiters_from_owner_api():
    # Recruiters only ever see passports through consent: share links or the recruiter portal
    if request.path.startswith('/api/passport/me') and current_user.is_authenticated \
            and getattr(current_user, 'is_recruiter', False):
        return jsonify({'error': 'Access denied: recruiter accounts do not have a Skill Passport.'}), 403

MAX_ACTIVE_SHARES = 20
MAX_EXPIRY_DAYS = 180
TOKEN_RE = re.compile(r'^[A-Za-z0-9_-]{32,64}$')
DATE_RANGE_SPLIT = re.compile(r'\s*(?:-|–|\bto\b)\s*', re.I)
GONE_MESSAGE = 'This Skill Passport link has expired or was revoked by the student.'
NOT_FOUND_MESSAGE = 'Skill Passport not found.'


def _now():
    return datetime.now(timezone.utc)


def _frontend_url():
    return os.environ.get('FRONTEND_URL', 'http://localhost:3000').rstrip('/')


def _text(data, key, max_len, required=False, label=None):
    """Returns (value, error)."""
    value = data.get(key)
    value = '' if value is None else str(value).strip()
    label = label or key.replace('_', ' ').capitalize()
    if required and not value:
        return None, f'{label} is required'
    if len(value) > max_len:
        return None, f'{label} cannot exceed {max_len} characters'
    return value, None


def _url(data, key, label):
    value = (data.get(key) or '').strip()
    if value and not is_safe_url(value):
        return None, f'{label} must be a full http(s) link (e.g. https://...)'
    return value, None


def _owned_evidence(evidence_id):
    return PassportEvidence.query.filter_by(id=evidence_id, student_id=current_user.id).first()


def _owned_skills(skill_ids):
    """Returns (skills, error). Only the student's own skills can be linked."""
    if skill_ids is None:
        return [], None
    if not isinstance(skill_ids, list) or len(skill_ids) > 50:
        return None, 'skill_ids must be a list (max 50)'
    try:
        ids = {int(i) for i in skill_ids}
    except (TypeError, ValueError):
        return None, 'skill_ids must be numbers'
    if not ids:
        return [], None
    skills = Skill.query.filter(Skill.id.in_(ids), Skill.student_id == current_user.id).all()
    if len(skills) != len(ids):
        return None, 'One or more skills do not exist in your profile'
    return skills, None


def _reset_review(ev):
    """Any change to evidence invalidates a previous review decision."""
    ev.review_status = 'not_requested'
    ev.review_requested_at = None
    ev.reviewed_at = None
    ev.reviewed_by = None
    ev.review_note = None


def _no_store(resp):
    resp.headers['Cache-Control'] = 'no-store'
    resp.headers['X-Robots-Tag'] = 'noindex, nofollow'
    resp.headers['Referrer-Policy'] = 'no-referrer'
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    return resp


# ─────────────────────────────────────────────────────────────────────────
# Student: passport & profile
# ─────────────────────────────────────────────────────────────────────────
@passport_bp.route('/me', methods=['GET'])
@login_required
def get_my_passport():
    data = build_owner_passport(current_user)
    data['shares'] = [s.to_dict() for s in
                      PassportShare.query.filter_by(student_id=current_user.id)
                      .order_by(PassportShare.created_at.desc()).all()]
    return _no_store(jsonify(data)), 200


@passport_bp.route('/me/profile', methods=['PUT'])
@login_required
def update_my_profile():
    data = request.get_json(silent=True) or {}
    headline, err = _text(data, 'headline', 160)
    if err:
        return jsonify({'error': err}), 400
    summary, err = _text(data, 'summary', 2000)
    if err:
        return jsonify({'error': err}), 400
    urls = {}
    for key, label in (('linkedin_url', 'LinkedIn URL'), ('github_url', 'GitHub URL'),
                       ('portfolio_url', 'Portfolio URL')):
        urls[key], err = _url(data, key, label)
        if err:
            return jsonify({'error': err}), 400

    profile = PassportProfile.query.filter_by(student_id=current_user.id).first()
    if not profile:
        profile = PassportProfile(student_id=current_user.id)
        db.session.add(profile)
    profile.headline = headline
    profile.summary = summary
    for k, v in urls.items():
        setattr(profile, k, v)
    profile.updated_at = _now()
    db.session.commit()
    return jsonify({'message': 'Professional profile saved', 'profile': profile.to_dict()}), 200


# ─────────────────────────────────────────────────────────────────────────
# Student: self-declared skills
# ─────────────────────────────────────────────────────────────────────────
@passport_bp.route('/me/skills', methods=['POST'])
@login_required
def add_self_declared_skill():
    data = request.get_json(silent=True) or {}
    raw, err = _text(data, 'skill_name', 60, required=True, label='Skill name')
    if err:
        return jsonify({'error': err}), 400
    if not re.match(r"^[\w .+#/&()'-]+$", raw):
        return jsonify({'error': 'Skill name contains unsupported characters'}), 400
    name = normalize_skill_name(raw)
    existing = next((s for s in Skill.query.filter_by(student_id=current_user.id).all()
                     if s.skill_name.lower().strip() == name), None)
    if existing:
        return jsonify({'error': f'"{existing.skill_name}" is already in your passport',
                        'skill_id': existing.id}), 409
    skill = Skill(student_id=current_user.id, skill_name=name, source='self_declared',
                  category=skill_category(name), extraction_confidence=None, proficiency=None)
    db.session.add(skill)
    db.session.commit()
    return jsonify({'message': 'Skill added as self-declared', 'skill': skill.to_dict()}), 201


@passport_bp.route('/me/skills/<int:skill_id>', methods=['DELETE'])
@login_required
def delete_self_declared_skill(skill_id):
    skill = Skill.query.filter_by(id=skill_id, student_id=current_user.id).first()
    if not skill:
        return jsonify({'error': 'Skill not found'}), 404
    if skill.source != 'self_declared' or skill.resume_id is not None:
        return jsonify({'error': 'Only self-declared skills can be removed here. '
                                 'Resume-extracted skills follow your latest resume.'}), 400
    if SkillVerification.query.filter_by(skill_id=skill.id).first():
        return jsonify({'error': 'This skill has assessment history and cannot be removed.'}), 400
    for ev in PassportEvidence.query.filter_by(student_id=current_user.id).all():
        if skill in ev.skills:
            ev.skills.remove(skill)
    db.session.delete(skill)
    db.session.commit()
    return jsonify({'message': 'Skill removed'}), 200


# ─────────────────────────────────────────────────────────────────────────
# Student: evidence
# ─────────────────────────────────────────────────────────────────────────
def _apply_evidence_payload(ev, data, creating):
    """Validates and applies fields. Returns (changed, error)."""
    changed = False
    if creating or 'kind' in data:
        kind = (data.get('kind') or '').strip()
        if kind not in PassportEvidence.KINDS:
            return False, f'kind must be one of: {", ".join(PassportEvidence.KINDS)}'
        changed |= ev.kind != kind
        ev.kind = kind
    specs = [('title', 200, True, 'Title'), ('organization', 200, False, 'Organization'),
             ('description', 2000, False, 'Description'), ('start_date', 20, False, 'Start date'),
             ('end_date', 20, False, 'End date')]
    for key, max_len, required, label in specs:
        if creating or key in data:
            value, err = _text(data, key, max_len, required=required, label=label)
            if err:
                return False, err
            changed |= (getattr(ev, key) or '') != value
            setattr(ev, key, value)
    if creating or 'url' in data:
        value, err = _url(data, 'url', 'Link')
        if err:
            return False, err
        changed |= (ev.url or '') != value
        ev.url = value
    if creating or 'skill_ids' in data:
        skills, err = _owned_skills(data.get('skill_ids') or [])
        if err:
            return False, err
        changed |= {s.id for s in ev.skills} != {s.id for s in skills}
        ev.skills = skills
    return changed, None


@passport_bp.route('/me/evidence', methods=['GET'])
@login_required
def list_my_evidence():
    items = (PassportEvidence.query.filter_by(student_id=current_user.id)
             .order_by(PassportEvidence.created_at.desc()).all())
    return jsonify({'evidence': [e.to_dict() for e in items]}), 200


@passport_bp.route('/me/evidence', methods=['POST'])
@login_required
def create_evidence():
    data = request.get_json(silent=True) or {}
    ev = PassportEvidence(student_id=current_user.id, source='student', review_status='not_requested')
    _, err = _apply_evidence_payload(ev, data, creating=True)
    if err:
        return jsonify({'error': err}), 400
    if PassportEvidence.query.filter_by(student_id=current_user.id).count() >= 200:
        return jsonify({'error': 'Evidence limit reached (200 items)'}), 400
    db.session.add(ev)
    db.session.commit()
    return jsonify({'message': 'Evidence added', 'evidence': ev.to_dict()}), 201


@passport_bp.route('/me/evidence/<int:evidence_id>', methods=['PUT', 'PATCH'])
@login_required
def update_evidence(evidence_id):
    ev = _owned_evidence(evidence_id)
    if not ev:
        return jsonify({'error': 'Evidence not found'}), 404
    data = request.get_json(silent=True) or {}
    changed, err = _apply_evidence_payload(ev, data, creating=False)
    if err:
        db.session.rollback()
        return jsonify({'error': err}), 400
    review_reset = False
    if changed and ev.review_status != 'not_requested':
        _reset_review(ev)
        review_reset = True
    db.session.commit()
    return jsonify({'message': 'Evidence updated' + (' - review status reset because the evidence changed'
                                                     if review_reset else ''),
                    'review_reset': review_reset, 'evidence': ev.to_dict()}), 200


@passport_bp.route('/me/evidence/<int:evidence_id>', methods=['DELETE'])
@login_required
def delete_evidence(evidence_id):
    ev = _owned_evidence(evidence_id)
    if not ev:
        return jsonify({'error': 'Evidence not found'}), 404
    path = ev.file_path
    db.session.delete(ev)
    db.session.commit()
    if path:
        delete_evidence_files([path])
    return jsonify({'message': 'Evidence deleted'}), 200


@passport_bp.route('/me/evidence/<int:evidence_id>/request_review', methods=['POST'])
@login_required
def request_evidence_review(evidence_id):
    ev = _owned_evidence(evidence_id)
    if not ev:
        return jsonify({'error': 'Evidence not found'}), 404
    if ev.review_status in ('pending', 'verified'):
        return jsonify({'error': f'Evidence is already {ev.review_status}'}), 400
    if not ev.skills:
        return jsonify({'error': 'Link at least one skill before requesting verification'}), 400
    if not (ev.url or ev.file_path or len(ev.description or '') >= 30):
        return jsonify({'error': 'Add a link, a file or a description (30+ characters) '
                                 'so a reviewer can check this evidence'}), 400
    ev.review_status = 'pending'
    ev.review_requested_at = _now()
    ev.reviewed_at = None
    ev.reviewed_by = None
    ev.review_note = None
    db.session.commit()
    return jsonify({'message': 'Submitted for verification', 'evidence': ev.to_dict()}), 200


@passport_bp.route('/me/evidence/<int:evidence_id>/file', methods=['POST'])
@login_required
def upload_evidence_file(evidence_id):
    ev = _owned_evidence(evidence_id)
    if not ev:
        return jsonify({'error': 'Evidence not found'}), 404
    f = request.files.get('file')
    if not f or not f.filename:
        return jsonify({'error': 'No file selected'}), 400
    original = secure_filename(f.filename) or 'evidence'
    ext = original.rsplit('.', 1)[-1].lower() if '.' in original else ''
    if ext not in EVIDENCE_FILE_EXTENSIONS:
        return jsonify({'error': 'Only PDF, PNG and JPG files are allowed'}), 400
    content = f.read()
    if not content:
        return jsonify({'error': 'The file is empty'}), 400
    if not file_matches_extension(content[:8], ext):
        return jsonify({'error': 'The file content does not match its extension'}), 400

    os.makedirs(evidence_dir(), exist_ok=True)
    stored = os.path.join('uploads', 'evidence', f"{current_user.id}_{uuid.uuid4().hex}.{ext}")
    with open(evidence_file_abspath(stored), 'wb') as out:
        out.write(content)
    old = ev.file_path
    ev.file_path = stored
    ev.original_filename = original[:200]
    if ev.review_status != 'not_requested':
        _reset_review(ev)
    db.session.commit()
    if old:
        delete_evidence_files([old])
    return jsonify({'message': 'File attached', 'evidence': ev.to_dict()}), 200


def _send_evidence_file(ev):
    full = evidence_file_abspath(ev.file_path)
    if not full or not os.path.isfile(full):
        return jsonify({'error': 'File not found'}), 404
    resp = send_file(full, as_attachment=True, download_name=ev.original_filename or os.path.basename(full))
    return _no_store(resp)


@passport_bp.route('/me/evidence/<int:evidence_id>/file', methods=['GET'])
@login_required
def download_evidence_file(evidence_id):
    ev = _owned_evidence(evidence_id)
    if not ev or not ev.file_path:
        return jsonify({'error': 'File not found'}), 404
    return _send_evidence_file(ev)


@passport_bp.route('/me/evidence/import', methods=['POST'])
@login_required
def import_evidence_from_resume():
    """Adds projects / certificates / experience found in the latest parsed resume.
    Items are re-read from the server-side resume, never taken from the request body."""
    data = request.get_json(silent=True) or {}
    items = data.get('items')
    if not isinstance(items, list) or not items or len(items) > 50:
        return jsonify({'error': 'items must be a non-empty list of {kind, index}'}), 400
    _, structure = latest_resume_structure(current_user.id)
    candidates = resume_import_candidates(structure)
    own_skills = {s.skill_name.lower().strip(): s for s in Skill.query.filter_by(student_id=current_user.id).all()}
    existing = {(e.kind, e.title.lower().strip())
                for e in PassportEvidence.query.filter_by(student_id=current_user.id).all()}

    created, skipped = [], 0
    for it in items:
        kind = (it or {}).get('kind') if isinstance(it, dict) else None
        try:
            idx = int(it.get('index'))
        except (TypeError, ValueError, AttributeError):
            return jsonify({'error': 'Each item needs a kind and a numeric index'}), 400
        pool = candidates.get(kind)
        if pool is None or not (0 <= idx < len(pool)):
            return jsonify({'error': f'No {kind} #{idx} in your latest resume'}), 400
        c = pool[idx]
        key = (kind, c['title'].lower().strip())
        if key in existing:
            skipped += 1
            continue
        existing.add(key)
        dates = c.get('dates') or ''
        start, end = (DATE_RANGE_SPLIT.split(dates, maxsplit=1) + [''])[:2]
        text = ' '.join([c['title'], c.get('description') or ''])
        linked = [own_skills[n] for n in extract_skill_names(text) if n in own_skills]
        ev = PassportEvidence(student_id=current_user.id, kind=kind, title=c['title'],
                              organization=c.get('organization') or '', description=c.get('description') or '',
                              url=c.get('url') if is_safe_url(c.get('url') or '') else '',
                              start_date=start.strip()[:20], end_date=end.strip()[:20],
                              source='resume', review_status='not_requested')
        ev.skills = linked
        db.session.add(ev)
        created.append(ev)
    db.session.commit()
    return jsonify({'message': f'{len(created)} item(s) imported from your resume',
                    'skipped_existing': skipped,
                    'evidence': [e.to_dict() for e in created]}), 201


# ─────────────────────────────────────────────────────────────────────────
# Student: PDF export & share links
# ─────────────────────────────────────────────────────────────────────────
def _visibility_from_query():
    sections = request.args.get('sections')
    raw = {}
    if sections is not None:
        chosen = {s.strip() for s in sections.split(',') if s.strip()}
        raw['sections'] = {k: True for k in chosen}
    if request.args.get('skill_filter'):
        raw['skill_filter'] = request.args.get('skill_filter')
    return normalize_visibility(raw) if raw else default_visibility()


def _pdf_response(pdf_bytes, student_name):
    safe = re.sub(r'[^A-Za-z0-9]+', '_', student_name or 'student').strip('_') or 'student'
    resp = make_response(pdf_bytes)
    resp.headers['Content-Type'] = 'application/pdf'
    resp.headers['Content-Disposition'] = f'attachment; filename="SkillPassport_{safe}.pdf"'
    return _no_store(resp)


@passport_bp.route('/me/pdf', methods=['GET'])
@login_required
def export_my_pdf():
    passport = build_public_passport(current_user, _visibility_from_query())
    return _pdf_response(render_passport_pdf(passport), current_user.name)


@passport_bp.route('/me/shares', methods=['GET'])
@login_required
def list_shares():
    shares = (PassportShare.query.filter_by(student_id=current_user.id)
              .order_by(PassportShare.created_at.desc()).all())
    return jsonify({'shares': [s.to_dict() for s in shares]}), 200


@passport_bp.route('/me/shares', methods=['POST'])
@login_required
def create_share():
    data = request.get_json(silent=True) or {}
    if data.get('consent') is not True:
        return jsonify({'error': 'Please confirm that you consent to sharing the selected information'}), 400
    try:
        days = int(data.get('expires_in_days', 30))
    except (TypeError, ValueError):
        return jsonify({'error': 'expires_in_days must be a number'}), 400
    if not 1 <= days <= MAX_EXPIRY_DAYS:
        return jsonify({'error': f'Link expiry must be between 1 and {MAX_EXPIRY_DAYS} days'}), 400
    label, err = _text(data, 'label', 120, label='Label')
    if err:
        return jsonify({'error': err}), 400
    visibility = normalize_visibility(data.get('visibility'))
    if not any(visibility['sections'].values()):
        return jsonify({'error': 'Select at least one section to share'}), 400

    active = [s for s in PassportShare.query.filter_by(student_id=current_user.id).all()
              if s.status() == 'active']
    if len(active) >= MAX_ACTIVE_SHARES:
        return jsonify({'error': f'You can have at most {MAX_ACTIVE_SHARES} active links. '
                                 'Revoke one first.'}), 400

    token = secrets.token_urlsafe(32)   # 256 bits of randomness
    now = _now()
    share = PassportShare(student_id=current_user.id, token_hash=hash_token(token), token_hint=token[-6:],
                          label=label, visibility=json.dumps(visibility),
                          allow_pdf=bool(data.get('allow_pdf', True)), consent_at=now,
                          created_at=now, expires_at=now + timedelta(days=days), access_count=0)
    db.session.add(share)
    db.session.commit()
    audit('passport.share_created', actor_id=current_user.id, target=f'share:{share.id}',
          details={'expires_in_days': days, 'sections': [k for k, v in visibility['sections'].items() if v],
                   'skill_filter': visibility['skill_filter']})
    url = f"{_frontend_url()}/passport/{token}"
    return _no_store(jsonify({
        'message': 'Share link created. Copy it now: for security it cannot be shown again.',
        'share': share.to_dict(),
        'url': url,
        'qr_svg': make_qr_svg(url),
    })), 201


@passport_bp.route('/me/shares/<int:share_id>/revoke', methods=['POST'])
@login_required
def revoke_share(share_id):
    share = PassportShare.query.filter_by(id=share_id, student_id=current_user.id).first()
    if not share:
        return jsonify({'error': 'Share link not found'}), 404
    if not share.revoked_at:
        share.revoked_at = _now()
        db.session.commit()
        audit('passport.share_revoked', actor_id=current_user.id, target=f'share:{share.id}')
    return jsonify({'message': 'Link revoked. It no longer gives access to your passport.',
                    'share': share.to_dict()}), 200


@passport_bp.route('/me/shares/<int:share_id>/access_log', methods=['GET'])
@login_required
def share_access_log(share_id):
    share = PassportShare.query.filter_by(id=share_id, student_id=current_user.id).first()
    if not share:
        return jsonify({'error': 'Share link not found'}), 404
    logs = PassportAccessLog.query.filter_by(share_id=share.id).order_by(PassportAccessLog.id.desc()).limit(200).all()
    return jsonify({
        'share': share.to_dict(),
        'unique_viewers': len({l.viewer_hash for l in logs if l.event in ('view', 'pdf')}),
        'access_log': [l.to_dict() for l in logs],
        'note': 'Viewers are identified by an anonymous code; SkillBridge does not store IP addresses.',
    }), 200


# ─────────────────────────────────────────────────────────────────────────
# Public (recruiter) access
# ─────────────────────────────────────────────────────────────────────────
def _resolve_share(token):
    """Returns (share, student, error_response)."""
    if not token or not TOKEN_RE.match(token):
        return None, None, (jsonify({'error': NOT_FOUND_MESSAGE}), 404)
    share = PassportShare.query.filter_by(token_hash=hash_token(token)).first()
    if not share:
        return None, None, (jsonify({'error': NOT_FOUND_MESSAGE}), 404)
    student = db.session.get(Student, share.student_id)
    status = share.status()
    if status != 'active' or not student or student.is_active is False:
        _log_access(share, f'denied_{status if status != "active" else "inactive"}')
        return None, None, (jsonify({'error': GONE_MESSAGE}), 410)
    return share, student, None


def _log_access(share, event):
    db.session.add(PassportAccessLog(
        share_id=share.id, event=event,
        viewer_hash=viewer_fingerprint(request.remote_addr or ''),
        user_agent=(request.headers.get('User-Agent') or '')[:200]))
    if event in ('view', 'pdf'):
        share.access_count = (share.access_count or 0) + 1
        share.last_accessed_at = _now()
    db.session.commit()


@passport_bp.route('/public/<token>', methods=['GET'])
@rate_limited('public_passport', 60, 60)
def public_passport(token):
    share, student, err = _resolve_share(token)
    if err:
        resp, code = err
        return _no_store(resp), code
    passport = build_public_passport(student, share.get_visibility())
    passport['link'] = {'expires_at': share.expires_at.isoformat() if share.expires_at else None,
                        'allow_pdf': bool(share.allow_pdf)}
    _log_access(share, 'view')
    return _no_store(jsonify(passport)), 200


@passport_bp.route('/public/<token>/pdf', methods=['GET'])
@rate_limited('public_passport_pdf', 20, 60)
def public_passport_pdf(token):
    share, student, err = _resolve_share(token)
    if err:
        resp, code = err
        return _no_store(resp), code
    if not share.allow_pdf:
        return _no_store(jsonify({'error': 'The student has not enabled PDF download for this link.'})), 403
    passport = build_public_passport(student, share.get_visibility())
    _log_access(share, 'pdf')
    return _pdf_response(render_passport_pdf(passport, share_url=f"{_frontend_url()}/passport/{token}"),
                         student.name)


# ─────────────────────────────────────────────────────────────────────────
# Administrator evidence review
# ─────────────────────────────────────────────────────────────────────────
@passport_bp.route('/admin/evidence', methods=['GET'])
@admin_required
def admin_list_evidence():
    status = request.args.get('status', 'pending')
    if status not in PassportEvidence.REVIEW_STATUSES:
        return jsonify({'error': 'Unknown status'}), 400
    items = (PassportEvidence.query.filter_by(review_status=status)
             .order_by(PassportEvidence.review_requested_at.asc()).limit(200).all())
    out = []
    for e in items:
        d = e.to_dict()
        st = db.session.get(Student, e.student_id)
        d['student'] = {'id': e.student_id, 'name': st.name if st else None,
                        'college': st.college if st else None}
        out.append(d)
    return jsonify({'evidence': out, 'count': len(out)}), 200


@passport_bp.route('/admin/evidence/<int:evidence_id>/review', methods=['POST'])
@admin_required
def admin_review_evidence(evidence_id):
    ev = db.session.get(PassportEvidence, evidence_id)
    if not ev:
        return jsonify({'error': 'Evidence not found'}), 404
    if ev.review_status != 'pending':
        return jsonify({'error': 'Only evidence that is pending review can be decided'}), 400
    if ev.student_id == current_user.id:
        return jsonify({'error': 'You cannot review your own evidence'}), 403
    data = request.get_json(silent=True) or {}
    decision = data.get('decision')
    if decision not in ('verified', 'rejected'):
        return jsonify({'error': 'decision must be "verified" or "rejected"'}), 400
    note, err = _text(data, 'note', 500, label='Note')
    if err:
        return jsonify({'error': err}), 400
    if decision == 'rejected' and not note:
        return jsonify({'error': 'Please give the student a reason for rejecting the evidence'}), 400
    ev.review_status = decision
    ev.reviewed_at = _now()
    ev.reviewed_by = current_user.id
    ev.review_note = note or None
    db.session.commit()
    if decision == 'verified':
        # Accepted evidence may complete an employer's verification request the student accepted
        from utils.verification_requests import safe_sync
        safe_sync(ev.student_id)
    audit('passport.evidence_reviewed', actor_id=current_user.id, target=f'evidence:{ev.id}',
          details={'decision': decision, 'student_id': ev.student_id})
    return jsonify({'message': f'Evidence {decision}', 'evidence': ev.to_dict()}), 200


@passport_bp.route('/admin/evidence/<int:evidence_id>/file', methods=['GET'])
@admin_required
def admin_download_evidence_file(evidence_id):
    ev = db.session.get(PassportEvidence, evidence_id)
    if not ev or not ev.file_path:
        return jsonify({'error': 'File not found'}), 404
    return _send_evidence_file(ev)
