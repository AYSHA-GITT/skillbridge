"""recruiter portal: organisations, recruiter profiles, candidate discovery consent,
employer-posted jobs, application pipeline, shortlists, notes, invitations, access log

Revision ID: f7c2a9e4d1b3
Revises: e4a1c7d9b2f0
Create Date: 2026-11-16 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f7c2a9e4d1b3'
down_revision = 'e4a1c7d9b2f0'
branch_labels = None
depends_on = None


def _has_table(name):
    return name in sa.inspect(op.get_bind()).get_table_names()


def _has_column(table, column):
    return column in {c['name'] for c in sa.inspect(op.get_bind()).get_columns(table)}


def _has_index(table, name):
    return name in {i['name'] for i in sa.inspect(op.get_bind()).get_indexes(table)}


def _is_sqlite():
    return op.get_bind().dialect.name == 'sqlite'


def upgrade():
    # app.py runs db.create_all() on import, so on an existing database the new
    # tables may already exist when this migration runs; only create what is missing.
    if not _has_table('organisations'):
        op.create_table(
            'organisations',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('industry', sa.String(length=120), nullable=True),
            sa.Column('website', sa.String(length=300), nullable=True),
            sa.Column('contact_email', sa.String(length=120), nullable=True),
            sa.Column('contact_phone', sa.String(length=40), nullable=True),
            sa.Column('location', sa.String(length=200), nullable=True),
            sa.Column('size', sa.String(length=40), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('verification_status', sa.String(length=20), nullable=False),
            sa.Column('verification_details', sa.Text(), nullable=True),
            sa.Column('verification_requested_at', sa.DateTime(), nullable=True),
            sa.Column('verified_at', sa.DateTime(), nullable=True),
            sa.Column('verified_by', sa.Integer(), nullable=True),
            sa.Column('verification_note', sa.String(length=500), nullable=True),
            sa.Column('created_by', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_organisations_name', 'organisations', ['name'])
        op.create_index('ix_organisations_verification_status', 'organisations', ['verification_status'])

    # Employer-posted jobs live in job_listings
    if not _has_column('job_listings', 'organisation_id'):
        op.add_column('job_listings', sa.Column('organisation_id', sa.Integer(), nullable=True))
        if not _is_sqlite():  # SQLite cannot add a FK constraint to an existing table
            op.create_foreign_key('fk_job_listings_organisation', 'job_listings', 'organisations',
                                  ['organisation_id'], ['id'])
    if not _has_index('job_listings', 'ix_job_listings_organisation_id'):
        op.create_index('ix_job_listings_organisation_id', 'job_listings', ['organisation_id'])
    if not _has_column('job_listings', 'posted_by'):
        op.add_column('job_listings', sa.Column('posted_by', sa.Integer(), nullable=True))

    # Applications to employer jobs carry a pipeline stage and the student's consent
    for name, col in (('stage', sa.String(length=30)), ('stage_updated_at', sa.DateTime()),
                      ('share_consent_at', sa.DateTime()), ('share_visibility', sa.Text()),
                      ('share_readiness', sa.Boolean())):
        if not _has_column('job_applications', name):
            op.add_column('job_applications', sa.Column(name, col, nullable=True))

    if not _has_table('recruiter_profiles'):
        op.create_table(
            'recruiter_profiles',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('organisation_id', sa.Integer(), nullable=False),
            sa.Column('job_title', sa.String(length=120), nullable=True),
            sa.Column('phone', sa.String(length=40), nullable=True),
            sa.Column('org_role', sa.String(length=20), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['students.id']),
            sa.ForeignKeyConstraint(['organisation_id'], ['organisations.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id'),
        )
        op.create_index('ix_recruiter_profiles_organisation_id', 'recruiter_profiles', ['organisation_id'])

    if not _has_table('candidate_discovery_settings'):
        op.create_table(
            'candidate_discovery_settings',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('student_id', sa.Integer(), nullable=False),
            sa.Column('candidate_ref', sa.String(length=32), nullable=False),
            sa.Column('is_discoverable', sa.Boolean(), nullable=False),
            sa.Column('visibility', sa.Text(), nullable=True),
            sa.Column('share_readiness', sa.Boolean(), nullable=True),
            sa.Column('consent_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['student_id'], ['students.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('student_id'),
        )
        op.create_index('ix_candidate_discovery_settings_candidate_ref', 'candidate_discovery_settings',
                        ['candidate_ref'], unique=True)

    if not _has_table('recruiter_access_logs'):
        op.create_table(
            'recruiter_access_logs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('student_id', sa.Integer(), nullable=False),
            sa.Column('organisation_id', sa.Integer(), nullable=False),
            sa.Column('recruiter_id', sa.Integer(), nullable=True),
            sa.Column('job_id', sa.Integer(), nullable=True),
            sa.Column('basis', sa.String(length=20), nullable=False),
            sa.Column('action', sa.String(length=30), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['student_id'], ['students.id']),
            sa.ForeignKeyConstraint(['organisation_id'], ['organisations.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_recruiter_access_logs_student_id', 'recruiter_access_logs', ['student_id'])
        op.create_index('ix_recruiter_access_logs_organisation_id', 'recruiter_access_logs', ['organisation_id'])
        op.create_index('ix_recruiter_access_logs_created_at', 'recruiter_access_logs', ['created_at'])

    if not _has_table('application_events'):
        op.create_table(
            'application_events',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('application_id', sa.Integer(), nullable=False),
            sa.Column('organisation_id', sa.Integer(), nullable=False),
            sa.Column('actor_id', sa.Integer(), nullable=True),
            sa.Column('from_stage', sa.String(length=30), nullable=True),
            sa.Column('to_stage', sa.String(length=30), nullable=False),
            sa.Column('message', sa.String(length=500), nullable=True),
            sa.Column('seen_by_student', sa.Boolean(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['application_id'], ['job_applications.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_application_events_application_id', 'application_events', ['application_id'])

    if not _has_table('recruitment_notes'):
        op.create_table(
            'recruitment_notes',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('organisation_id', sa.Integer(), nullable=False),
            sa.Column('student_id', sa.Integer(), nullable=False),
            sa.Column('application_id', sa.Integer(), nullable=True),
            sa.Column('author_id', sa.Integer(), nullable=True),
            sa.Column('kind', sa.String(length=20), nullable=False),
            sa.Column('interview_round', sa.String(length=80), nullable=True),
            sa.Column('outcome', sa.String(length=20), nullable=True),
            sa.Column('body', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['organisation_id'], ['organisations.id']),
            sa.ForeignKeyConstraint(['student_id'], ['students.id']),
            sa.ForeignKeyConstraint(['application_id'], ['job_applications.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_recruitment_notes_organisation_id', 'recruitment_notes', ['organisation_id'])
        op.create_index('ix_recruitment_notes_student_id', 'recruitment_notes', ['student_id'])
        op.create_index('ix_recruitment_notes_application_id', 'recruitment_notes', ['application_id'])

    if not _has_table('candidate_shortlists'):
        op.create_table(
            'candidate_shortlists',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('organisation_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=120), nullable=False),
            sa.Column('description', sa.String(length=300), nullable=True),
            sa.Column('job_id', sa.Integer(), nullable=True),
            sa.Column('created_by', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['organisation_id'], ['organisations.id']),
            sa.ForeignKeyConstraint(['job_id'], ['job_listings.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_candidate_shortlists_organisation_id', 'candidate_shortlists', ['organisation_id'])

    if not _has_table('shortlist_entries'):
        op.create_table(
            'shortlist_entries',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('shortlist_id', sa.Integer(), nullable=False),
            sa.Column('student_id', sa.Integer(), nullable=False),
            sa.Column('added_by', sa.Integer(), nullable=True),
            sa.Column('note', sa.String(length=500), nullable=True),
            sa.Column('added_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['shortlist_id'], ['candidate_shortlists.id']),
            sa.ForeignKeyConstraint(['student_id'], ['students.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('shortlist_id', 'student_id', name='uq_shortlist_student'),
        )
        op.create_index('ix_shortlist_entries_shortlist_id', 'shortlist_entries', ['shortlist_id'])
        op.create_index('ix_shortlist_entries_student_id', 'shortlist_entries', ['student_id'])

    if not _has_table('job_invitations'):
        op.create_table(
            'job_invitations',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('job_id', sa.Integer(), nullable=False),
            sa.Column('organisation_id', sa.Integer(), nullable=False),
            sa.Column('student_id', sa.Integer(), nullable=False),
            sa.Column('invited_by', sa.Integer(), nullable=True),
            sa.Column('message', sa.String(length=500), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('seen_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['job_id'], ['job_listings.id']),
            sa.ForeignKeyConstraint(['organisation_id'], ['organisations.id']),
            sa.ForeignKeyConstraint(['student_id'], ['students.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('job_id', 'student_id', name='uq_invitation_job_student'),
        )
        op.create_index('ix_job_invitations_job_id', 'job_invitations', ['job_id'])
        op.create_index('ix_job_invitations_organisation_id', 'job_invitations', ['organisation_id'])
        op.create_index('ix_job_invitations_student_id', 'job_invitations', ['student_id'])


def downgrade():
    for table in ('job_invitations', 'shortlist_entries', 'candidate_shortlists', 'recruitment_notes',
                  'application_events', 'recruiter_access_logs', 'candidate_discovery_settings',
                  'recruiter_profiles'):
        op.drop_table(table)
    with op.batch_alter_table('job_applications', schema=None) as batch_op:
        for col in ('share_readiness', 'share_visibility', 'share_consent_at', 'stage_updated_at', 'stage'):
            batch_op.drop_column(col)
    op.drop_index('ix_job_listings_organisation_id', table_name='job_listings')
    with op.batch_alter_table('job_listings', schema=None) as batch_op:
        batch_op.drop_column('posted_by')
        batch_op.drop_column('organisation_id')
    op.drop_table('organisations')
