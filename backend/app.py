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
if (app.config['SQLALCHEMY_DATABASE_URI'] or '').startswith('sqlite'):
    # SQLite allows one writer at a time. Wait up to 30 s for the lock (default 5 s) so a
    # request that writes while the background job sync is committing is delayed, not failed
    # with "database is locked".
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'connect_args': {'timeout': 30}}
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# Production (SKILLBRIDGE_ENV=production): HTTPS-only cookies, real client IPs behind the
# reverse proxy (rate limits and login lockouts are keyed on the IP), and no weak secrets.
if os.getenv('SKILLBRIDGE_ENV', '').lower() == 'production':
    from werkzeug.middleware.proxy_fix import ProxyFix
    if not app.config['SECRET_KEY'] or len(app.config['SECRET_KEY']) < 32:
        raise RuntimeError('SECRET_KEY must be set to a random value of at least 32 characters in production.')
    if not (app.config['SQLALCHEMY_DATABASE_URI'] or '').startswith('postgresql'):
        raise RuntimeError('DATABASE_URL must point to PostgreSQL in production.')
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        REMEMBER_COOKIE_SECURE=True,
        REMEMBER_COOKIE_HTTPONLY=True,
        PREFERRED_URL_SCHEME='https',
    )
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True, 'pool_recycle': 1800}
    from utils.password_reset import mail_configured
    if not mail_configured():
        import logging
        logging.getLogger('skillbridge').error(
            'E-mail is not configured (MAIL_SERVER/MAIL_USERNAME/MAIL_PASSWORD/MAIL_FROM): '
            'password reset links cannot be delivered. Check with: flask users test-email <address>')

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
def load_user(session_id):
    # session_id is "<id>:<password fingerprint>" (Student.get_id). A session created before
    # the password was reset or changed no longer matches, so it is signed out.
    import hmac
    from models import Student
    user_id, _, fingerprint = str(session_id).partition(':')
    if not user_id.isdigit() or not fingerprint:
        return None
    user = db.session.get(Student, int(user_id))
    if not user or user.is_active is False:
        return None
    if not hmac.compare_digest(user.session_fingerprint(), fingerprint):
        return None
    return user

@login_manager.unauthorized_handler
def unauthorized():
    return {'error': 'Authentication required. Please log in.'}, 401

# Import and register routes
from routes.auth import auth_bp
from routes.student import student_bp
from routes.admin import admin_bp
from routes.passport import passport_bp

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(student_bp, url_prefix='/api/student')
app.register_blueprint(admin_bp, url_prefix='/api/admin')
app.register_blueprint(passport_bp, url_prefix='/api/passport')

from routes.recruiter import recruiter_bp, candidate_bp
app.register_blueprint(recruiter_bp, url_prefix='/api/recruiter')
app.register_blueprint(candidate_bp, url_prefix='/api/candidate')

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