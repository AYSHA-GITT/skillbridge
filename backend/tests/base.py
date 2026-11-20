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
# Optional: run the suite against PostgreSQL (as in production) instead of SQLite.
# The suite drops every table, so only a database whose name ends in "_test" is accepted.
_PG_TEST_URL = os.environ.get("SKILLBRIDGE_TEST_DATABASE_URL", "").strip()
if _PG_TEST_URL:
    if not _PG_TEST_URL.startswith("postgresql") or not _PG_TEST_URL.rsplit("/", 1)[-1].split("?")[0].endswith("_test"):
        raise SystemExit("SKILLBRIDGE_TEST_DATABASE_URL must be a PostgreSQL database whose name ends in _test")
    os.environ["DATABASE_URL"] = _PG_TEST_URL
else:
    os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_TMP_DIR, "test.db").replace("\\", "/")
IS_POSTGRES = bool(_PG_TEST_URL)
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["JOB_PROVIDERS"] = ""                 # no real providers
os.environ["JOB_INCLUDE_SAMPLE_LISTINGS"] = "0"
os.environ["RUN_JOB_SCHEDULER_IN_PROCESS"] = "0"
os.environ["YOUTUBE_API_KEY"] = ""               # resources fall back to search links (no network)
os.environ["FL_GLOBAL_MODEL_PATH"] = os.path.join(_TMP_DIR, "fl_global.npz")
os.environ["MARKET_DEMAND_PATH"] = os.path.join(_TMP_DIR, "market_demand.json")

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import app  # noqa: E402
from extensions import db  # noqa: E402

if not IS_POSTGRES:
    # SQLite ignores foreign keys unless asked; PostgreSQL always enforces them. Enforcing
    # them in the SQLite test database catches PostgreSQL-only failures (e.g. delete order).
    from sqlalchemy import event as _sa_event

    with app.app_context():
        @_sa_event.listens_for(db.engine, "connect")
        def _sqlite_foreign_keys_on(dbapi_conn, _record):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()
        db.engine.dispose()   # connections made during app import reconnect with the pragma

app.config["TESTING"] = True
# Tests log in many times from one client; rate limiting has its own dedicated test.
app.config["RATELIMIT_ENABLED"] = False


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
