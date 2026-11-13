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
    app,
    origins=[o.strip() for o in os.getenv('FRONTEND_ORIGINS', 'http://localhost:3000').split(',') if o.strip()],
    supports_credentials=True)
# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads', 'resumes')
app.config['AVATAR_UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads', 'avatars')
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
    return db.session.get(Student, int(student_id))

@login_manager.unauthorized_handler
def unauthorized():
    return {'error': 'Authentication required. Please log in.'}, 401

# Import and register routes
from routes.auth import auth_bp
from routes.student import student_bp
from routes.admin import admin_bp

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(student_bp, url_prefix='/api/student')
app.register_blueprint(admin_bp, url_prefix='/api/admin')

from cli import jobs_cli, skills_cli, users_cli, resumes_cli
app.cli.add_command(jobs_cli)
app.cli.add_command(skills_cli)
app.cli.add_command(users_cli)
app.cli.add_command(resumes_cli)

# Optional in-process scheduler (single-instance/dev). Production: use job_worker.py or cron.
if os.getenv('RUN_JOB_SCHEDULER_IN_PROCESS', '0').lower() in ('1', 'true', 'yes'):
    from utils.job_discovery.scheduler import start_in_process_scheduler
    start_in_process_scheduler(app)

@app.route('/')
@app.route('/api/health')
def home():
    return {
        'message': 'SkillBridge API is running!',
        'version': '1.0.0',
        'status': 'healthy'
    }



if __name__ == '__main__':
    # `python app.py` is the development entry point.
    #  - The auto-reloader is OFF by default: file activity (OneDrive, editors) restarts the
    #    server mid-request. Set FLASK_USE_RELOADER=1 to turn it back on.
    #  - The two-hour job scheduler runs in-process unless RUN_JOB_SCHEDULER_IN_PROCESS is set
    #    explicitly (1 = started above at import time, 0 = never; use job_worker.py or cron).
    _use_reloader = os.getenv('FLASK_USE_RELOADER', '0').lower() in ('1', 'true', 'yes')
    if os.getenv('RUN_JOB_SCHEDULER_IN_PROCESS') is None and             (not _use_reloader or os.environ.get('WERKZEUG_RUN_MAIN') == 'true'):
        from utils.job_discovery.scheduler import start_in_process_scheduler
        start_in_process_scheduler(app)
    app.run(debug=True, port=5000, use_reloader=_use_reloader)