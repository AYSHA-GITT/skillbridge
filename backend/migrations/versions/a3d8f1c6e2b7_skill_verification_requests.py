"""recruiter skill verification requests

Revision ID: a3d8f1c6e2b7
Revises: f7c2a9e4d1b3
Create Date: 2026-11-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3d8f1c6e2b7'
down_revision = 'f7c2a9e4d1b3'
branch_labels = None
depends_on = None


def _has_table(name):
    return name in sa.inspect(op.get_bind()).get_table_names()


def _has_index(table, name):
    return name in {i['name'] for i in sa.inspect(op.get_bind()).get_indexes(table)}


def upgrade():
    # app.py runs db.create_all() on import, so the table may already exist.
    if not _has_table('skill_verification_requests'):
        op.create_table(
            'skill_verification_requests',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('organisation_id', sa.Integer(), nullable=False),
            sa.Column('recruiter_id', sa.Integer(), nullable=True),
            sa.Column('student_id', sa.Integer(), nullable=False),
            sa.Column('job_id', sa.Integer(), nullable=True),
            sa.Column('skill_id', sa.Integer(), nullable=True),
            sa.Column('skill_name', sa.String(length=100), nullable=False),
            sa.Column('message', sa.String(length=500), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=False),
            sa.Column('student_note', sa.String(length=500), nullable=True),
            sa.Column('completed_via', sa.String(length=60), nullable=True),
            sa.Column('close_reason', sa.String(length=200), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('responded_at', sa.DateTime(), nullable=True),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('closed_at', sa.DateTime(), nullable=True),
            sa.Column('seen_by_student', sa.Boolean(), nullable=False),
            sa.Column('seen_by_recruiter', sa.Boolean(), nullable=False),
            sa.ForeignKeyConstraint(['organisation_id'], ['organisations.id']),
            sa.ForeignKeyConstraint(['student_id'], ['students.id']),
            sa.ForeignKeyConstraint(['job_id'], ['job_listings.id']),
            sa.PrimaryKeyConstraint('id'),
        )
    for col in ('organisation_id', 'student_id', 'status'):
        name = f'ix_skill_verification_requests_{col}'
        if not _has_index('skill_verification_requests', name):
            op.create_index(name, 'skill_verification_requests', [col], unique=False)


def downgrade():
    op.drop_table('skill_verification_requests')
