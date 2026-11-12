from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from models import Student

auth_bp = Blueprint('auth', __name__)


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

    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400

    email = str(data['email']).strip()
    student = Student.query.filter_by(email=email).first() or \
        Student.query.filter(db.func.lower(Student.email) == email.lower()).first()

    if not student or not student.check_password(data['password']):
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