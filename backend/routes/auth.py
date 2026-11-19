import os
import secrets
from werkzeug.utils import secure_filename
from flask import Blueprint, request, jsonify, send_from_directory, current_app
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from models import Student, PasswordResetToken
from utils.rate_limit import hit, blocked_for, too_many, rate_limited
from utils import password_reset as pr

auth_bp = Blueprint('auth', __name__)

# Failed logins allowed per (client IP, email) in the window, before a cool-down
LOGIN_FAILURE_LIMIT = 10
LOGIN_FAILURE_WINDOW = 15 * 60
PORTAL_ROLES = {'admin': 'admin', 'recruiter': 'recruiter'}

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@auth_bp.route('/register', methods=['POST'])
@rate_limited('register', 10, 3600)
def register():
    data = request.get_json(silent=True) or {}

    required_fields = ['name', 'email', 'password', 'college', 'course']
    for field in required_fields:
        if not data.get(field) or not isinstance(data.get(field), str):
            return jsonify({'error': f'{field} is required'}), 400

    email = data['email'].strip().lower()
    if '@' not in email or '.' not in email.split('@')[-1] or len(email) > 100:
        return jsonify({'error': 'Please enter a valid email address'}), 400
    if len(data['password']) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    existing_student = Student.query.filter(db.func.lower(Student.email) == email).first()
    if existing_student:
        return jsonify({'error': 'An account with this email already exists'}), 409

    # SECURITY: role is never taken from the request - self-registration always
    # creates a student. Admins are created with `flask --app app users make-admin`.
    new_student = Student(
        name=data['name'].strip()[:100],
        email=email,
        college=data['college'].strip()[:200],
        course=data['course'].strip()[:200],
        year=data.get('year'),
        target_career=data.get('target_career'),
        role='student'
    )
    new_student.set_password(data['password'])

    db.session.add(new_student)
    db.session.commit()

    login_user(new_student)

    return jsonify({
        'message': 'Registration successful',
        'student': new_student.to_dict()
    }), 201


@auth_bp.route('/register_recruiter', methods=['POST'])
@rate_limited('register_recruiter', 5, 3600)
def register_recruiter():
    """Creates a recruiter account and its organisation. The organisation starts
    'unverified': it cannot publish jobs or search candidates until an
    administrator verifies it."""
    from models import Organisation, RecruiterProfile
    from routes.recruiter import apply_org_payload
    from utils.audit import audit

    data = request.get_json(silent=True) or {}
    for field in ('name', 'email', 'password'):
        if not data.get(field) or not isinstance(data.get(field), str):
            return jsonify({'error': f'{field} is required'}), 400
    email = data['email'].strip().lower()
    if '@' not in email or '.' not in email.split('@')[-1] or len(email) > 100:
        return jsonify({'error': 'Please enter a valid email address'}), 400
    if len(data['password']) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    name = data['name'].strip()[:100]
    job_title = (data.get('job_title') or '').strip()
    if len(job_title) > 120:
        return jsonify({'error': 'Job title cannot exceed 120 characters'}), 400
    org_data = data.get('organisation')
    if not isinstance(org_data, dict):
        return jsonify({'error': 'organisation details are required'}), 400
    if Student.query.filter(db.func.lower(Student.email) == email).first():
        return jsonify({'error': 'An account with this email already exists'}), 409

    org = Organisation(verification_status='unverified')
    _, err = apply_org_payload(org, org_data, creating=True)
    if err:
        return jsonify({'error': err}), 400

    # SECURITY: the role is fixed by this endpoint, never read from the request
    user = Student(name=name, email=email, role='recruiter', college=None, course=None)
    user.set_password(data['password'])
    db.session.add_all([org, user])
    db.session.flush()
    org.created_by = user.id
    db.session.add(RecruiterProfile(user_id=user.id, organisation_id=org.id, job_title=job_title,
                                    org_role='owner'))
    db.session.commit()
    audit('recruiter.registered', actor_id=user.id, target=f'organisation:{org.id}')
    login_user(user)
    return jsonify({'message': 'Recruiter account created. Request organisation verification to start '
                               'publishing jobs and searching candidates.',
                    'student': user.to_dict(), 'organisation': org.to_dict()}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}

    email = (data.get('email') or '').strip().lower()
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    # Brute-force protection: only failed attempts count, per client IP + email
    bucket = f"login_fail:{request.remote_addr or 'unknown'}:{email}"
    wait = blocked_for(bucket, LOGIN_FAILURE_LIMIT, LOGIN_FAILURE_WINDOW)
    if wait:
        return too_many(wait)

    email = str(data.get('email') or '').strip()
    student = Student.query.filter_by(email=email).first() or \
        Student.query.filter(db.func.lower(Student.email) == email.lower()).first()

    if not student or not student.check_password(password):
        hit(bucket, LOGIN_FAILURE_LIMIT, LOGIN_FAILURE_WINDOW)
        return jsonify({'error': 'Invalid email or password'}), 401
    if student.is_active is False:
        return jsonify({'error': 'This account has been deactivated'}), 403

    # Optional portal restriction check
    portal = data.get('portal')
    if portal == 'admin' and student.role != 'admin':
        return jsonify({
            'error': 'Access denied: This account does not possess institutional administrator privileges'
        }), 403
    if portal == 'recruiter' and student.role != 'recruiter':
        return jsonify({'error': 'Access denied: this is not a recruiter account. '
                                 'Students sign in through the Student Portal.'}), 403
    if portal == 'student' and student.role == 'recruiter':
        return jsonify({'error': 'This is a recruiter account. Please sign in through the Recruiter Portal.'}), 403

    login_user(student)

    return jsonify({
        'message': 'Login successful',
        'student': student.to_dict()
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out successfully'}), 200


@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_student():
    return jsonify({'student': current_user.to_dict()}), 200


# ─────────────────────────────────────────
# PROFILE SETTINGS & PHOTO MANAGEMENT
# ─────────────────────────────────────────
@auth_bp.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    data = request.get_json(silent=True) or {}

    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    if len(name) > 100:
        return jsonify({'error': 'Name cannot exceed 100 characters'}), 400

    college = (data.get('college') or '').strip()
    if len(college) > 200:
        return jsonify({'error': 'College cannot exceed 200 characters'}), 400

    course = (data.get('course') or '').strip()
    if len(course) > 200:
        return jsonify({'error': 'Course cannot exceed 200 characters'}), 400

    year = (data.get('year') or '').strip()
    if len(year) > 20:
        return jsonify({'error': 'Academic year cannot exceed 20 characters'}), 400

    target_career = (data.get('target_career') or '').strip()
    if len(target_career) > 200:
        return jsonify({'error': 'Target career cannot exceed 200 characters'}), 400

    student = db.session.get(Student, current_user.id)
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    student.name = name
    student.college = college
    student.course = course
    student.year = year
    if target_career:
        student.target_career = target_career

    db.session.commit()

    return jsonify({
        'message': 'Profile updated successfully',
        'student': student.to_dict()
    }), 200


@auth_bp.route('/profile/photo', methods=['POST'])
@login_required
def upload_profile_photo():
    if 'photo' not in request.files:
        return jsonify({'error': 'No photo file provided'}), 400

    file = request.files['photo']
    orig_filename = file.filename or ''
    if not orig_filename:
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(orig_filename):
        return jsonify({'error': 'Invalid file format. Allowed: PNG, JPG, JPEG, WEBP, GIF'}), 400

    student = db.session.get(Student, current_user.id)
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    ext = orig_filename.rsplit('.', 1)[1].lower()
    filename = f"avatar_{student.id}_{secrets.token_hex(8)}.{ext}"

    avatar_dir = os.path.join(current_app.root_path, 'uploads', 'avatars')
    os.makedirs(avatar_dir, exist_ok=True)

    # Delete existing old photo if present
    if student.profile_photo:
        old_filename = os.path.basename(student.profile_photo)
        old_path = os.path.join(avatar_dir, old_filename)
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass

    save_path = os.path.join(avatar_dir, filename)
    file.save(save_path)

    student.profile_photo = f"/api/auth/profile/photo/{filename}"
    db.session.commit()

    return jsonify({
        'message': 'Profile photo uploaded successfully',
        'profile_photo': student.profile_photo,
        'student': student.to_dict()
    }), 200


@auth_bp.route('/profile/photo/<path:filename>', methods=['GET'])
def get_profile_photo(filename):
    avatar_dir = os.path.join(current_app.root_path, 'uploads', 'avatars')
    safe_name = secure_filename(filename)
    return send_from_directory(avatar_dir, safe_name)


# ─────────────────────────────────────────
# PASSWORD MANAGEMENT
# ─────────────────────────────────────────
@auth_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    data = request.get_json(silent=True) or {}
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')

    if not current_password or not new_password or not confirm_password:
        return jsonify({'error': 'Current password, new password, and confirmation are all required'}), 400

    student = db.session.get(Student, current_user.id)
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    if not student.check_password(current_password):
        return jsonify({'error': 'Current password is incorrect'}), 401

    problem = pr.password_problem(new_password, confirm_password)
    if problem:
        return jsonify({'error': problem}), 400

    student.set_password(new_password)
    PasswordResetToken.query.filter_by(student_id=student.id, used=False).update({'used': True})
    db.session.commit()
    # The session identifier includes a password fingerprint (Student.get_id), so every
    # other session is now signed out; refresh this one so the user stays signed in.
    login_user(student)

    return jsonify({'message': 'Password changed successfully'}), 200


# Limits: per client IP for every reset endpoint, and per e-mail address for new links.
FORGOT_IP_LIMIT, FORGOT_IP_WINDOW = 5, 15 * 60
FORGOT_EMAIL_LIMIT, FORGOT_EMAIL_WINDOW = 3, 60 * 60
TOKEN_IP_LIMIT, TOKEN_IP_WINDOW = 20, 15 * 60
GENERIC_RESET_MESSAGE = ('If an account exists for this email address, we have sent it a password '
                         'reset link. The link expires in 60 minutes.')
INVALID_LINK_MESSAGE = ('This password reset link is invalid, has expired or has already been used. '
                        'Request a new link to continue.')


def _usable_token(raw_token):
    """Returns the PasswordResetToken row for a valid, unused, unexpired token, else None."""
    if not isinstance(raw_token, str) or not (20 <= len(raw_token) <= 128):
        return None
    record = PasswordResetToken.query.filter_by(token=pr.hash_token(raw_token)).first()
    if not record or record.used:
        return None
    if pr.utc_aware(record.expires_at) <= pr.now_utc():
        return None
    student = db.session.get(Student, record.student_id)
    if not student or student.is_active is False:
        return None
    return record


@auth_bp.route('/forgot_password', methods=['POST'])
@rate_limited('forgot_password', FORGOT_IP_LIMIT, FORGOT_IP_WINDOW)
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = str(data.get('email') or '').strip().lower()

    if not email or '@' not in email or len(email) > 254:
        return jsonify({'error': 'Please enter a valid email address'}), 400

    # Same response, status and (because mail is sent in the background) timing whether or
    # not the address has an account, so the form cannot be used to discover accounts.
    response = jsonify({'message': GENERIC_RESET_MESSAGE})

    # Per-address limit: stops someone flooding a user's inbox. Over the limit, nothing is
    # sent but the response is unchanged.
    if hit(f'forgot_password_email:{email}', FORGOT_EMAIL_LIMIT, FORGOT_EMAIL_WINDOW):
        return response, 200

    student = Student.query.filter(db.func.lower(Student.email) == email).first()
    if student and student.is_active is not False:
        # Only the newest link works.
        PasswordResetToken.query.filter_by(student_id=student.id, used=False).update({'used': True})
        raw_token, token_hash = pr.new_token()
        db.session.add(PasswordResetToken(
            student_id=student.id,
            token=token_hash,
            expires_at=pr.now_utc() + pr.RESET_TOKEN_TTL,
            used=False,
        ))
        db.session.commit()
        # Delivered only to the address stored on the account, never the one typed in.
        pr.deliver_in_background(current_app._get_current_object(), student.email, raw_token)

    return response, 200


@auth_bp.route('/verify_reset_token', methods=['POST'])
@rate_limited('reset_token', TOKEN_IP_LIMIT, TOKEN_IP_WINDOW)
def verify_reset_token():
    """Lets the reset page show "link expired" before the user types a password.
    POST with the token in the body, so it never appears in a URL or access log."""
    data = request.get_json(silent=True) or {}
    record = _usable_token(data.get('token'))
    if not record:
        return jsonify({'valid': False, 'error': INVALID_LINK_MESSAGE}), 400
    student = db.session.get(Student, record.student_id)
    return jsonify({'valid': True, 'email': pr.mask_email(student.email)}), 200


@auth_bp.route('/reset_password', methods=['POST'])
@rate_limited('reset_token', TOKEN_IP_LIMIT, TOKEN_IP_WINDOW)
def reset_password():
    data = request.get_json(silent=True) or {}
    raw_token = data.get('token')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')

    if not raw_token or not isinstance(raw_token, str):
        return jsonify({'error': INVALID_LINK_MESSAGE, 'code': 'invalid_token'}), 400
    problem = pr.password_problem(new_password, confirm_password)
    if problem:
        return jsonify({'error': problem}), 400

    record = _usable_token(raw_token.strip())
    if not record:
        return jsonify({'error': INVALID_LINK_MESSAGE, 'code': 'invalid_token'}), 400

    # Consume the token atomically: if two requests race, only one UPDATE matches.
    consumed = PasswordResetToken.query.filter_by(id=record.id, used=False) \
        .update({'used': True}, synchronize_session=False)
    if consumed != 1:
        db.session.rollback()
        return jsonify({'error': INVALID_LINK_MESSAGE, 'code': 'invalid_token'}), 400

    student = db.session.get(Student, record.student_id)
    student.set_password(new_password)
    # Any other outstanding links for this account stop working too.
    PasswordResetToken.query.filter_by(student_id=student.id, used=False) \
        .update({'used': True}, synchronize_session=False)
    db.session.commit()

    # Changing the password changes Student.get_id(), which signs out every existing
    # session of this account (student, recruiter or admin).
    if current_user.is_authenticated:
        logout_user()
    current_app.logger.info('Password reset completed for account %s', student.id)
    return jsonify({'message': 'Your password has been changed. Sign in with your new password. '
                               'Any other signed-in sessions have been signed out.'}), 200

