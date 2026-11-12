"""Job sync pipeline, job freshness/provenance, alerts, audit log, skill evidence

Revision ID: c9f1e2a7b3d4
Revises: b18d3c5f2026
Create Date: 2026-11-12 22:30:00

Idempotent: every column / table / index is only added if it is missing, so the
migration is safe both on fresh databases and on databases whose tables were
created by db.create_all().
"""
from alembic import op
import sqlalchemy as sa


revision = 'c9f1e2a7b3d4'
down_revision = 'b18d3c5f2026'
branch_labels = None
depends_on = None


def _insp():
    return sa.inspect(op.get_bind())


def _tables():
    return set(_insp().get_table_names())


def _columns(table):
    return {c['name'] for c in _insp().get_columns(table)}


def _indexes(table):
    return {i['name'] for i in _insp().get_indexes(table)}


def _add_columns(table, columns):
    if table not in _tables():
        return
    existing = _columns(table)
    missing = [c for c in columns if c.name not in existing]
    if not missing:
        return
    with op.batch_alter_table(table, schema=None) as batch_op:
        for col in missing:
            batch_op.add_column(col)


def _create_index(name, table, cols):
    if table in _tables() and name not in _indexes(table):
        op.create_index(name, table, cols)


SKILL_COLUMNS = [
    sa.Column('evidence_strength', sa.String(length=20), nullable=True),
    sa.Column('evidence', sa.Text(), nullable=True),
    sa.Column('extraction_explanation', sa.String(length=400), nullable=True),
    sa.Column('category', sa.String(length=50), nullable=True),
]

JOB_COLUMNS = [
    sa.Column('source_provider', sa.String(length=50), nullable=True),
    sa.Column('source_job_id', sa.String(length=200), nullable=True),
    sa.Column('original_url', sa.String(length=1000), nullable=True),
    sa.Column('canonical_url', sa.String(length=1000), nullable=True),
    sa.Column('fingerprint', sa.String(length=64), nullable=True),
    sa.Column('content_hash', sa.String(length=64), nullable=True),
    sa.Column('duplicate_of_id', sa.Integer(), nullable=True),
    sa.Column('country', sa.String(length=60), nullable=True),
    sa.Column('state', sa.String(length=120), nullable=True),
    sa.Column('city', sa.String(length=120), nullable=True),
    sa.Column('career_category', sa.String(length=100), nullable=True),
    sa.Column('is_entry_level', sa.Boolean(), nullable=True),
    sa.Column('experience_min_years', sa.Float(), nullable=True),
    sa.Column('experience_max_years', sa.Float(), nullable=True),
    sa.Column('skills_source', sa.String(length=30), nullable=True),
    sa.Column('salary_min', sa.Float(), nullable=True),
    sa.Column('salary_max', sa.Float(), nullable=True),
    sa.Column('salary_currency', sa.String(length=8), nullable=True),
    sa.Column('salary_period', sa.String(length=20), nullable=True),
    sa.Column('salary_is_estimated', sa.Boolean(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=True, server_default='active'),
    sa.Column('first_seen_at', sa.DateTime(), nullable=True),
    sa.Column('last_seen_at', sa.DateTime(), nullable=True),
    sa.Column('last_verified_at', sa.DateTime(), nullable=True),
    sa.Column('last_synced_at', sa.DateTime(), nullable=True),
    sa.Column('last_changed_at', sa.DateTime(), nullable=True),
    sa.Column('expired_at', sa.DateTime(), nullable=True),
    sa.Column('expiry_reason', sa.String(length=200), nullable=True),
    sa.Column('times_seen', sa.Integer(), nullable=True, server_default='1'),
]


def upgrade():
    _add_columns('skills', SKILL_COLUMNS)
    _add_columns('job_listings', JOB_COLUMNS)

    for name, cols in [
        ('ix_job_listings_source_provider', ['source_provider']),
        ('ix_job_listings_canonical_url', ['canonical_url']),
        ('ix_job_listings_fingerprint', ['fingerprint']),
        ('ix_job_listings_career_category', ['career_category']),
        ('ix_job_listings_status', ['status']),
    ]:
        _create_index(name, 'job_listings', cols)

    tables = _tables()

    if 'job_sync_runs' not in tables:
        op.create_table(
            'job_sync_runs',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('trigger', sa.String(length=20), nullable=False),
            sa.Column('triggered_by', sa.Integer(), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=False),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('finished_at', sa.DateTime(), nullable=True),
            sa.Column('fetched_count', sa.Integer(), nullable=True),
            sa.Column('inserted_count', sa.Integer(), nullable=True),
            sa.Column('updated_count', sa.Integer(), nullable=True),
            sa.Column('unchanged_count', sa.Integer(), nullable=True),
            sa.Column('duplicate_count', sa.Integer(), nullable=True),
            sa.Column('invalid_count', sa.Integer(), nullable=True),
            sa.Column('expired_count', sa.Integer(), nullable=True),
            sa.Column('stale_count', sa.Integer(), nullable=True),
            sa.Column('alerts_created', sa.Integer(), nullable=True),
            sa.Column('provider_results', sa.Text(), nullable=True),
            sa.Column('error', sa.Text(), nullable=True),
        )
        op.create_index('ix_job_sync_runs_status', 'job_sync_runs', ['status'])
        op.create_index('ix_job_sync_runs_started_at', 'job_sync_runs', ['started_at'])

    if 'scheduler_leases' not in tables:
        op.create_table(
            'scheduler_leases',
            sa.Column('name', sa.String(length=64), primary_key=True),
            sa.Column('owner', sa.String(length=128), nullable=True),
            sa.Column('acquired_at', sa.DateTime(), nullable=True),
            sa.Column('expires_at', sa.DateTime(), nullable=True),
        )

    if 'job_preferences' not in tables:
        op.create_table(
            'job_preferences',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('student_id', sa.Integer(), sa.ForeignKey('students.id'), nullable=False, unique=True),
            sa.Column('preferred_roles', sa.Text(), nullable=True),
            sa.Column('preferred_locations', sa.Text(), nullable=True),
            sa.Column('work_modes', sa.Text(), nullable=True),
            sa.Column('job_types', sa.Text(), nullable=True),
            sa.Column('experience_years', sa.Float(), nullable=True),
            sa.Column('open_to_relocation', sa.Boolean(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )

    if 'job_alerts' not in tables:
        op.create_table(
            'job_alerts',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('student_id', sa.Integer(), sa.ForeignKey('students.id'), nullable=False),
            sa.Column('name', sa.String(length=120), nullable=False),
            sa.Column('roles', sa.Text(), nullable=True),
            sa.Column('locations', sa.Text(), nullable=True),
            sa.Column('skills', sa.Text(), nullable=True),
            sa.Column('job_types', sa.Text(), nullable=True),
            sa.Column('work_modes', sa.Text(), nullable=True),
            sa.Column('min_match_score', sa.Float(), nullable=True),
            sa.Column('frequency', sa.String(length=20), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('last_evaluated_at', sa.DateTime(), nullable=True),
            sa.Column('last_notified_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_job_alerts_student_id', 'job_alerts', ['student_id'])

    if 'job_alert_matches' not in tables:
        op.create_table(
            'job_alert_matches',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('alert_id', sa.Integer(), sa.ForeignKey('job_alerts.id'), nullable=False),
            sa.Column('student_id', sa.Integer(), sa.ForeignKey('students.id'), nullable=False),
            sa.Column('job_id', sa.Integer(), sa.ForeignKey('job_listings.id'), nullable=False),
            sa.Column('match_score', sa.Float(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('released_at', sa.DateTime(), nullable=True),
            sa.Column('is_read', sa.Boolean(), nullable=True),
            sa.UniqueConstraint('student_id', 'job_id', name='uq_alert_match_student_job'),
        )
        op.create_index('ix_job_alert_matches_alert_id', 'job_alert_matches', ['alert_id'])
        op.create_index('ix_job_alert_matches_student_id', 'job_alert_matches', ['student_id'])

    if 'audit_logs' not in tables:
        op.create_table(
            'audit_logs',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('actor_id', sa.Integer(), nullable=True),
            sa.Column('action', sa.String(length=80), nullable=False),
            sa.Column('target', sa.String(length=200), nullable=True),
            sa.Column('details', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_audit_logs_actor_id', 'audit_logs', ['actor_id'])
        op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
        op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])

    # ── Honest backfill for listings collected before this migration ─────
    if 'job_listings' in _tables():
        op.execute("""
            UPDATE job_listings SET source_provider = CASE
                WHEN source LIKE 'Arbeitnow%' THEN 'arbeitnow'
                WHEN is_sample = 1 OR is_sample = TRUE THEN 'curated_sample'
                ELSE 'unknown' END
            WHERE source_provider IS NULL
        """ if op.get_bind().dialect.name == 'sqlite' else """
            UPDATE job_listings SET source_provider = CASE
                WHEN source LIKE 'Arbeitnow%%' THEN 'arbeitnow'
                WHEN is_sample = TRUE THEN 'curated_sample'
                ELSE 'unknown' END
            WHERE source_provider IS NULL
        """)
        # Sample rows are labelled as samples, never as live listings.
        op.execute("UPDATE job_listings SET status = 'sample' WHERE is_sample = "
                   + ("1" if op.get_bind().dialect.name == 'sqlite' else "TRUE"))
        op.execute("UPDATE job_listings SET status = 'active' WHERE status IS NULL")
        # The only evidence we have for old rows is the time they were collected.
        op.execute("UPDATE job_listings SET first_seen_at = collected_at WHERE first_seen_at IS NULL")
        op.execute("UPDATE job_listings SET last_seen_at = collected_at WHERE last_seen_at IS NULL")
        op.execute("UPDATE job_listings SET last_verified_at = collected_at "
                   "WHERE last_verified_at IS NULL AND status = 'active'")
        op.execute("UPDATE job_listings SET original_url = application_url WHERE original_url IS NULL")
        op.execute("UPDATE job_listings SET times_seen = 1 WHERE times_seen IS NULL")


def downgrade():
    for t in ['audit_logs', 'job_alert_matches', 'job_alerts', 'job_preferences',
              'scheduler_leases', 'job_sync_runs']:
        if t in _tables():
            op.drop_table(t)
    for table, cols in [('job_listings', JOB_COLUMNS), ('skills', SKILL_COLUMNS)]:
        if table not in _tables():
            continue
        existing = _columns(table)
        with op.batch_alter_table(table, schema=None) as batch_op:
            for col in cols:
                if col.name in existing:
                    batch_op.drop_column(col.name)
