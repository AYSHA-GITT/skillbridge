from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from models import Student

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    required_fields = ['name', 'email', 'password', 'college', 'course']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    existing_student = Student.query.filter_by(email=data['email']).first()
    if existing_student:
        return jsonify({'error': 'An account with this email already exists'}), 409

    new_student = Student(
        name=data['name'],
        email=data['email'],
        college=data['college'],
        course=data['course'],
        year=data.get('year'),
        target_career=data.get('target_career')
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
    data = request.get_json()

    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400

    student = Student.query.filter_by(email=data['email']).first()

    if not student or not student.check_password(data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401

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