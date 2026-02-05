"""Add content_generator module with session and delay

Revision ID: 369d40d196e1
Revises: 20260121_fsrs_native
Create Date: 2026-02-05 13:01:49.936024

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '369d40d196e1'
down_revision = '20260121_fsrs_native'
branch_labels = None
depends_on = None


def upgrade():
    # Only keep the creation of the new table for content_generator
    op.create_table('content_generator_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('task_id', sa.String(length=64), nullable=True),
    sa.Column('request_type', sa.String(length=20), nullable=False),
    sa.Column('requester_module', sa.String(length=50), nullable=True),
    sa.Column('session_id', sa.String(length=100), nullable=True),
    sa.Column('delay_seconds', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('input_payload', sa.Text(), nullable=True),
    sa.Column('output_result', sa.Text(), nullable=True),
    sa.Column('cost_tokens', sa.Integer(), nullable=True),
    sa.Column('execution_time_ms', sa.Integer(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('content_generator_logs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_content_generator_logs_session_id'), ['session_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_content_generator_logs_task_id'), ['task_id'], unique=False)


def downgrade():
    with op.batch_alter_table('content_generator_logs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_content_generator_logs_task_id'))
        batch_op.drop_index(batch_op.f('ix_content_generator_logs_session_id'))

    op.drop_table('content_generator_logs')