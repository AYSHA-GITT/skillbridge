"""add profile_photo and password reset token

Revision ID: da08260c21b0
Revises: c9f1e2a7b3d4
Create Date: 2026-11-13 22:03:20.137309

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'da08260c21b0'
down_revision = 'c9f1e2a7b3d4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('students', schema=None) as batch_op:
        batch_op.add_column(sa.Column('profile_photo', sa.String(length=300), nullable=True))

    op.create_table('password_reset_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=128), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('password_reset_tokens', schema=None) as batch_op:
        batch_op.create_index('ix_password_reset_tokens_student_id', ['student_id'], unique=False)
        batch_op.create_index('ix_password_reset_tokens_token', ['token'], unique=True)


def downgrade():
    with op.batch_alter_table('password_reset_tokens', schema=None) as batch_op:
        batch_op.drop_index('ix_password_reset_tokens_token')
        batch_op.drop_index('ix_password_reset_tokens_student_id')
    op.drop_table('password_reset_tokens')

    with op.batch_alter_table('students', schema=None) as batch_op:
        batch_op.drop_column('profile_photo')
