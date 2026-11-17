"""
Regression: "database is locked" (HTTP 500) when a request writes while the
background job sync is writing.

Seen live on 2026-11-17: student registrations failed for ~10 s after start-up
because the scheduler's first sync wrote ~490 jobs in one transaction, holding
SQLite's single write lock longer than the 5 s that other writers waited.
Fixed by (1) a 30 s SQLite busy timeout and (2) committing the sync in chunks.
"""
from tests.base import app, db, reset_db, make_student, login  # must be first

import sqlite3
import threading
import time
import unittest
from unittest import mock

from tests.test_job_system import FakeAdapter, raw_job, sync
from utils.job_discovery import sync_service as S


def _db_file():
    return app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '', 1)


class SqliteLockingTests(unittest.TestCase):
    def setUp(self):
        reset_db()

    def test_engine_waits_longer_than_sqlite_default(self):
        self.assertEqual(app.config['SQLALCHEMY_ENGINE_OPTIONS']['connect_args']['timeout'], 30)

    def test_registration_waits_for_a_busy_writer_instead_of_failing(self):
        with app.app_context():
            db.session.remove()
            db.engine.dispose()            # fresh connections pick up the timeout
        blocker = sqlite3.connect(_db_file(), timeout=1, check_same_thread=False)
        blocker.execute('BEGIN IMMEDIATE')  # take the write lock, like a long sync transaction
        release = threading.Timer(6.5, blocker.commit)   # longer than SQLite's old 5 s default
        release.start()
        try:
            started = time.monotonic()
            res = app.test_client().post('/api/auth/register', json={
                'name': 'Lock Test', 'email': 'lock.test@example.com', 'password': 'password123',
                'college': 'Test College', 'course': 'B.Tech'})
            waited = time.monotonic() - started
        finally:
            release.join()
            blocker.close()
        self.assertEqual(res.status_code, 201, res.get_json())
        self.assertGreater(waited, 5.0)    # it really waited for the lock

    def test_sync_commits_in_chunks(self):
        jobs = [raw_job(i, title=f'Python Developer {i}') for i in range(1, 8)]

        def commits_during_sync(every):
            reset_db()
            with app.app_context(), mock.patch.object(S, 'SYNC_COMMIT_EVERY', every):
                real = db.session.commit
                count = {'n': 0}

                def counting():
                    count['n'] += 1
                    return real()
                with mock.patch.object(db.session, 'commit', side_effect=counting):
                    result = sync([FakeAdapter(jobs=jobs)])
                self.assertEqual(result['inserted_count'], 7, result)
                return count['n']

        self.assertEqual(commits_during_sync(2) - commits_during_sync(1000), 3)   # after jobs 2, 4, 6


if __name__ == '__main__':
    unittest.main()
