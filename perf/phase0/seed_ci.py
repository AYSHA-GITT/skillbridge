"""
Prepares the THROW-AWAY PostgreSQL database of the Phase 0 CI run (never a real one).

Creates the schema (app import runs db.create_all), marks it as the current
Alembic head (running the migration chain on PostgreSQL is Phase 1's job), and
creates the administrator account e2e_check.py expects. The CI database exists
only for the duration of the workflow job.
"""
import os
import subprocess
import sys

if "localhost" not in os.environ.get("DATABASE_URL", "") and "127.0.0.1" not in os.environ.get("DATABASE_URL", ""):
    sys.exit("seed_ci.py only runs against the local CI database")

sys.path.insert(0, "/app")
from app import app  # noqa: E402
from extensions import db  # noqa: E402
from models import Student  # noqa: E402

with app.app_context():
    if not Student.query.filter_by(email="admin@skillbridge.edu").first():
        admin = Student(name="CI Admin", email="admin@skillbridge.edu", college="CI", course="CI", role="admin")
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
    print("tables:", len(db.metadata.tables), "| admin ready")

subprocess.run(["flask", "--app", "app", "db", "stamp", "head"], check=True, cwd="/app")
