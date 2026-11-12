"""
Isolated test harness.

Every test module imports this FIRST. It points the app at a throw-away SQLite
database and disables real job providers, so tests never touch the developer
database (instance/skillbridge.db) and never call external APIs.
"""
import os
import sys
import tempfile

_TMP_DIR = tempfile.mkdtemp(prefix="skillbridge_tests_")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_TMP_DIR, "test.db").replace("\\", "/")
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["JOB_PROVIDERS"] = ""                 # no real providers
os.environ["JOB_INCLUDE_SAMPLE_LISTINGS"] = "0"
os.environ["RUN_JOB_SCHEDULER_IN_PROCESS"] = "0"
os.environ["YOUTUBE_API_KEY"] = ""               # resources fall back to search links (no network)
os.environ["FL_GLOBAL_MODEL_PATH"] = os.path.join(_TMP_DIR, "fl_global.npz")

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import app  # noqa: E402
from extensions import db  # noqa: E402

app.config["TESTING"] = True


def reset_db():
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()


def make_student(email, password="password123", role="student", **extra):
    from models import Student
    with app.app_context():
        s = Student(name=extra.pop("name", "Test User"), email=email, college="Test College",
                    course="B.Tech CSE", role=role, **extra)
        s.set_password(password)
        db.session.add(s)
        db.session.commit()
        return s.id


def login(client, email, password="password123"):
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.get_json()
    return res
