from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from flask_migrate import Migrate
import os

from extensions import db, login_manager

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(
    app, origins=["http://localhost:3000"], supports_credentials=True)
# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads', 'resumes')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

# Bind extensions to this app
db.init_app(app)
login_manager.init_app(app)
migrate = Migrate(app, db)

with app.app_context():
    import models
    db.create_all()

@login_manager.user_loader
def load_user(student_id):
    from models import Student
    return Student.query.get(int(student_id))

# Import and register routes
from routes.auth import auth_bp
from routes.student import student_bp
from routes.admin import admin_bp

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(student_bp, url_prefix='/api/student')
app.register_blueprint(admin_bp, url_prefix='/api/admin')

@app.route('/')
def home():
    return {
        'message': 'SkillBridge API is running!',
        'version': '1.0.0',
        'status': 'success'
    }



if __name__ == '__main__':
    app.run(debug=True, port=5000)