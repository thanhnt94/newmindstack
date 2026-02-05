"""Add session_name and item_title to generation logs

Revision ID: 19611226b70b
Revises: 369d40d196e1
Create Date: 2026-02-05 13:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '19611226b70b'
down_revision = '369d40d196e1'
branch_labels = None
depends_on = None


def upgrade():
    # Only add columns to content_generator_logs
    with op.batch_alter_table('content_generator_logs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('session_name', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('item_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('item_title', sa.String(length=255), nullable=True))


def downgrade():
    with op.batch_alter_table('content_generator_logs', schema=None) as batch_op:
        batch_op.drop_column('item_title')
        batch_op.drop_column('item_id')
        batch_op.drop_column('session_name')