"""verified skill passport: profile, evidence, share links, access log, skill source

Revision ID: e4a1c7d9b2f0
Revises: da08260c21b0
Create Date: 2026-11-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e4a1c7d9b2f0'
down_revision = 'da08260c21b0'
branch_labels = None
depends_on = None


def _has_table(name):
    return name in sa.inspect(op.get_bind()).get_table_names()


def _has_column(table, column):
    return column in {c['name'] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade():
    # app.py runs db.create_all() on import, so on an existing database the new
    # tables may already exist when this migration runs; only create what is missing.
    if not _has_column('skills', 'source'):
        with op.batch_alter_table('skills', schema=None) as batch_op:
            batch_op.add_column(sa.Column('source', sa.String(length=20), nullable=True))

    if not _has_table('passport_profiles'):
        op.create_table(
            'passport_profiles',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('student_id', sa.Integer(), nullable=False),
            sa.Column('headline', sa.String(length=160), nullable=True),
            sa.Column('summary', sa.Text(), nullable=True),
            sa.Column('linkedin_url', sa.String(length=300), nullable=True),
            sa.Column('github_url', sa.String(length=300), nullable=True),
            sa.Column('portfolio_url', sa.String(length=300), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['student_id'], ['students.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('student_id'),
        )

    if not _has_table('passport_evidence'):
        op.create_table(
            'passport_evidence',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('student_id', sa.Integer(), nullable=False),
            sa.Column('kind', sa.String(length=30), nullable=False),
            sa.Column('title', sa.String(length=200), nullable=False),
            sa.Column('organization', sa.String(length=200), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('url', sa.String(length=500), nullable=True),
            sa.Column('start_date', sa.String(length=20), nullable=True),
            sa.Column('end_date', sa.String(length=20), nullable=True),
            sa.Column('source', sa.String(length=20), nullable=True),
            sa.Column('file_path', sa.String(length=500), nullable=True),
            sa.Column('original_filename', sa.String(length=200), nullable=True),
            sa.Column('review_status', sa.String(length=20), nullable=False),
            sa.Column('review_requested_at', sa.DateTime(), nullable=True),
            sa.Column('reviewed_at', sa.DateTime(), nullable=True),
            sa.Column('reviewed_by', sa.Integer(), nullable=True),
            sa.Column('review_note', sa.String(length=500), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['student_id'], ['students.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        with op.batch_alter_table('passport_evidence', schema=None) as batch_op:
            batch_op.create_index('ix_passport_evidence_student_id', ['student_id'], unique=False)
            batch_op.create_index('ix_passport_evidence_review_status', ['review_status'], unique=False)

    if not _has_table('passport_evidence_skills'):
        op.create_table(
            'passport_evidence_skills',
            sa.Column('evidence_id', sa.Integer(), nullable=False),
            sa.Column('skill_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['evidence_id'], ['passport_evidence.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('evidence_id', 'skill_id'),
        )

    if not _has_table('passport_shares'):
        op.create_table(
            'passport_shares',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('student_id', sa.Integer(), nullable=False),
            sa.Column('token_hash', sa.String(length=64), nullable=False),
            sa.Column('token_hint', sa.String(length=8), nullable=True),
            sa.Column('label', sa.String(length=120), nullable=True),
            sa.Column('visibility', sa.Text(), nullable=False),
            sa.Column('allow_pdf', sa.Boolean(), nullable=True),
            sa.Column('consent_at', sa.DateTime(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.Column('revoked_at', sa.DateTime(), nullable=True),
            sa.Column('last_accessed_at', sa.DateTime(), nullable=True),
            sa.Column('access_count', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['student_id'], ['students.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        with op.batch_alter_table('passport_shares', schema=None) as batch_op:
            batch_op.create_index('ix_passport_shares_student_id', ['student_id'], unique=False)
            batch_op.create_index('ix_passport_shares_token_hash', ['token_hash'], unique=True)

    if not _has_table('passport_access_logs'):
        op.create_table(
            'passport_access_logs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('share_id', sa.Integer(), nullable=False),
            sa.Column('event', sa.String(length=30), nullable=False),
            sa.Column('viewer_hash', sa.String(length=16), nullable=True),
            sa.Column('user_agent', sa.String(length=200), nullable=True),
            sa.Column('accessed_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['share_id'], ['passport_shares.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        with op.batch_alter_table('passport_access_logs', schema=None) as batch_op:
            batch_op.create_index('ix_passport_access_logs_share_id', ['share_id'], unique=False)


def downgrade():
    op.drop_table('passport_access_logs')
    op.drop_table('passport_shares')
    op.drop_table('passport_evidence_skills')
    op.drop_table('passport_evidence')
    op.drop_table('passport_profiles')
    with op.batch_alter_table('skills', schema=None) as batch_op:
        batch_op.drop_column('source')
