import os
import secrets
import smtplib
from typing import Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from werkzeug.utils import secure_filename
from flask import Blueprint, request, jsonify, send_from_directory, current_app
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from models import Student, PasswordResetToken

auth_bp = Blueprint('auth', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def send_password_reset_email(to_email: str, reset_url: str):
    mail_server = (os.environ.get('MAIL_SERVER') or '').strip()
    mail_port = int(os.environ.get('MAIL_PORT', 587))
    mail_username = (os.environ.get('MAIL_USERNAME') or '').strip()
    mail_password = (os.environ.get('MAIL_PASSWORD') or '').strip()
    mail_use_tls = os.environ.get('MAIL_USE_TLS', 'true').lower() in ('true', '1')
    mail_from = (os.environ.get('MAIL_FROM') or mail_username or 'noreply@skillbridge.edu').strip()

    if not mail_server or not mail_username or not mail_password:
        print(f"\n=======================================================")
        print(f"[DEVELOPMENT MODE] Password Reset Requested")
        print(f"Recipient: {to_email}")
        print(f"Reset Link: {reset_url}")
        print(f"=======================================================\n")
        return False, "Email service not configured. Reset link logged to console."

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'SkillBridge - Password Reset Request'
        msg['From'] = mail_from
        msg['To'] = to_email

        text_content = f"""Hello,

We received a request to reset your password for your SkillBridge account.
Please visit the following link to choose a new password:

{reset_url}

This link is valid for 1 hour. If you did not request this, you can safely ignore this email.

Best regards,
The SkillBridge Team
"""
        html_content = f"""
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; background-color: #0b0f19; color: #ffffff; padding: 30px;">
  <div style="max-width: 540px; margin: 0 auto; background: #131b2e; border: 1px solid #1e293b; border-radius: 16px; padding: 32px;">
    <h2 style="color: #2dd4bf; margin-top: 0;">SkillBridge</h2>
    <h3 style="color: #f1f5f9; margin-bottom: 12px;">Password Reset Request</h3>
    <p style="color: #94a3b8; font-size: 14px; line-height: 1.6;">
      We received a request to reset the password associated with your email address. Click the button below to set a new password:
    </p>
    <div style="text-align: center; margin: 30px 0;">
      <a href="{reset_url}" style="background-color: #0d9488; color: #ffffff; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 14px; display: inline-block;">
        Reset My Password
      </a>
    </div>
    <p style="color: #64748b; font-size: 12px; line-height: 1.5;">
      Or copy and paste this link into your browser:<br>
      <a href="{reset_url}" style="color: #2dd4bf;">{reset_url}</a>
    </p>
    <hr style="border: none; border-top: 1px solid #1e293b; margin: 24px 0;" />
    <p style="color: #64748b; font-size: 11px;">
      This password reset link is time-limited and expires in 1 hour.<br>
      If you did not request a password reset, no action is needed.
    </p>
  </div>
</body>
</html>
"""
        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))

        with smtplib.SMTP(mail_server, mail_port, timeout=10) as server:
            if mail_use_tls:
                server.starttls()
            if mail_username and mail_password:
                server.login(mail_username, mail_password)
            server.send_message(msg)

        return True, "Email sent successfully"
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send email to {to_email}: {e}")
        return False, str(e)


@auth_bp.route('/register', methods=['POST'])
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


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}

    email = (data.get('email') or '').strip().lower()
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    email = str(data.get('email') or '').strip()
    student = Student.query.filter_by(email=email).first() or \
        Student.query.filter(db.func.lower(Student.email) == email.lower()).first()

    if not student or not student.check_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401

    # Optional portal restriction check
    portal = data.get('portal')
    if portal == 'admin' and student.role != 'admin':
        return jsonify({
            'error': 'Access denied: This account does not possess institutional administrator privileges'
        }), 403

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

    if len(new_password) < 8:
        return jsonify({'error': 'New password must be at least 8 characters long'}), 400

    if new_password != confirm_password:
        return jsonify({'error': 'New password and confirmation do not match'}), 400

    student.set_password(new_password)
    db.session.commit()

    return jsonify({'message': 'Password changed successfully'}), 200


@auth_bp.route('/forgot_password', methods=['POST'])
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()

    if not email:
        return jsonify({'error': 'Email address is required'}), 400

    student = Student.query.filter(db.func.lower(Student.email) == email).first()

    generic_msg = 'If an account exists with this email, a password reset link has been sent.'
    dev_info = None

    if student:
        # Invalidate existing unused tokens
        PasswordResetToken.query.filter_by(student_id=student.id, used=False).update({'used': True})

        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        reset_token = PasswordResetToken(
            student_id=student.id,
            token=token,
            expires_at=expires_at,
            used=False
        )
        db.session.add(reset_token)
        db.session.commit()

        frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000').rstrip('/')
        reset_url = f"{frontend_url}/reset-password?token={token}"

        sent, msg = send_password_reset_email(student.email, reset_url)
        if not sent:
            dev_info = {
                'dev_reset_link': reset_url,
                'note': 'SMTP not configured in local environment; link generated for testing.'
            }

    resp: dict[str, Any] = {'message': generic_msg}
    if dev_info:
        resp['dev_info'] = dev_info

    return jsonify(resp), 200


@auth_bp.route('/verify_reset_token/<token>', methods=['GET'])
def verify_reset_token(token):
    token_record = PasswordResetToken.query.filter_by(token=token).first()
    if not token_record or token_record.used:
        return jsonify({'valid': False, 'error': 'Invalid or already used password reset link'}), 400

    expires = token_record.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        return jsonify({'valid': False, 'error': 'This password reset link has expired'}), 400

    student = db.session.get(Student, token_record.student_id)
    return jsonify({
        'valid': True,
        'email': student.email if student else ''
    }), 200


@auth_bp.route('/reset_password', methods=['POST'])
def reset_password():
    data = request.get_json(silent=True) or {}
    token = (data.get('token') or '').strip()
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')

    if not token:
        return jsonify({'error': 'Reset token is required'}), 400
    if not new_password or not confirm_password:
        return jsonify({'error': 'New password and confirmation are required'}), 400
    if len(new_password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters long'}), 400
    if new_password != confirm_password:
        return jsonify({'error': 'Passwords do not match'}), 400

    token_record = PasswordResetToken.query.filter_by(token=token).first()
    if not token_record or token_record.used:
        return jsonify({'error': 'Invalid or already used reset token'}), 400

    expires = token_record.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        return jsonify({'error': 'Reset token has expired'}), 400

    student = db.session.get(Student, token_record.student_id)
    if not student:
        return jsonify({'error': 'Student account not found'}), 404

    student.set_password(new_password)
    token_record.used = True
    db.session.commit()

    return jsonify({'message': 'Password has been reset successfully! You can now log in.'}), 200

