"""FSRS Native Schema Migration (Refactored)

Revision ID: 20260121_fsrs_native
Revises: 
Create Date: 2026-01-21 04:36:08

This migration:
1. Renames FSRS columns to fsrs_* prefix (via batch_alter_table)
2. Preserves data during rename
3. Removes legacy columns/aliases if they exist
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = '20260121_fsrs_native'
down_revision = 'fa7e7651284c'
branch_labels = None
depends_on = None


def upgrade():
    """
    Upgrade to native FSRS schema with fsrs_* prefix.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # === 1. LearningProgress Migration ===
    lp_columns = [col['name'] for col in inspector.get_columns('learning_progress')]
    lp_indexes = [idx['name'] for idx in inspector.get_indexes('learning_progress')]
    
    with op.batch_alter_table('learning_progress', schema=None) as batch_op:
        # A. Rename compatible columns (DateTime)
        if 'fsrs_due' not in lp_columns and 'due_time' in lp_columns:
            batch_op.alter_column('due_time', new_column_name='fsrs_due')
        if 'fsrs_last_review' not in lp_columns and 'last_reviewed' in lp_columns:
            batch_op.alter_column('last_reviewed', new_column_name='fsrs_last_review')

        # B. Add new FSRS columns (Semantic changes prevented rename)
        if 'fsrs_state' not in lp_columns:
            batch_op.add_column(sa.Column('fsrs_state', sa.Integer(), nullable=True, default=0))
        if 'fsrs_stability' not in lp_columns:
            batch_op.add_column(sa.Column('fsrs_stability', sa.Float(), nullable=True, default=0.0))
        if 'fsrs_difficulty' not in lp_columns:
            batch_op.add_column(sa.Column('fsrs_difficulty', sa.Float(), nullable=True, default=5.0))
        
        # C. Add Legacy Mastery (to preserve mastery data)
        if 'legacy_mastery' not in lp_columns:
            batch_op.add_column(sa.Column('legacy_mastery', sa.Float(), nullable=True))

    # D. Data Migration (SQL)
    # Populate fsrs_state from status
    if 'status' in lp_columns:
        op.execute("UPDATE learning_progress SET fsrs_state = 0 WHERE status = 'new'")
        op.execute("UPDATE learning_progress SET fsrs_state = 1 WHERE status IN ('learning', 'relearning')")
        op.execute("UPDATE learning_progress SET fsrs_state = 2 WHERE status IN ('reviewing', 'mastered', 'hard')")
    
    # Populate legacy_mastery from mastery
    if 'mastery' in lp_columns:
        op.execute("UPDATE learning_progress SET legacy_mastery = mastery")
    
    # E. Drop Legacy Columns
    with op.batch_alter_table('learning_progress', schema=None) as batch_op:
        # Explicitly drop legacy indexes first (if they exist)
        if 'ix_learning_progress_status' in lp_indexes:
            batch_op.drop_index('ix_learning_progress_status')
            
        for col in ['status', 'mastery', 'easiness_factor', 'times_vague', 'vague_streak']:
            if col in lp_columns:
                batch_op.drop_column(col)

    # === 2. ReviewLogs Migration ===
    rl_columns = [col['name'] for col in inspector.get_columns('review_logs')]
    
    with op.batch_alter_table('review_logs', schema=None) as batch_op:
        if 'fsrs_stability' not in rl_columns and 'easiness_factor' in rl_columns:
            batch_op.alter_column('easiness_factor', new_column_name='fsrs_stability')


def downgrade():
    """
    Downgrade - Revert to simple names.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    lp_columns = [col['name'] for col in inspector.get_columns('learning_progress')]
    rl_columns = [col['name'] for col in inspector.get_columns('review_logs')]
    
    # 1. Revert LearningProgress
    with op.batch_alter_table('learning_progress', schema=None) as batch_op:
        # Revert renames
        if 'fsrs_due' in lp_columns:
            batch_op.alter_column('fsrs_due', new_column_name='due_time')
        if 'fsrs_last_review' in lp_columns:
            batch_op.alter_column('fsrs_last_review', new_column_name='last_reviewed')
            
        # Add back legacy columns
        if 'status' not in lp_columns:
            batch_op.add_column(sa.Column('status', sa.String(50), nullable=True))
        if 'mastery' not in lp_columns:
            batch_op.add_column(sa.Column('mastery', sa.Float(), nullable=True))
        if 'easiness_factor' not in lp_columns:
            batch_op.add_column(sa.Column('easiness_factor', sa.Float(), nullable=True))
            
        # Restore data (Inverse mapping - Lossy)
        # fsrs_state 0 -> new, 1 -> learning, 2 -> reviewing
        # legacy_mastery -> mastery
    
    if 'fsrs_state' in lp_columns:
        op.execute("UPDATE learning_progress SET status = 'new' WHERE fsrs_state = 0")
        op.execute("UPDATE learning_progress SET status = 'learning' WHERE fsrs_state IN (1, 3)")
        op.execute("UPDATE learning_progress SET status = 'reviewing' WHERE fsrs_state = 2")
        
    if 'legacy_mastery' in lp_columns:
        op.execute("UPDATE learning_progress SET mastery = legacy_mastery")

    with op.batch_alter_table('learning_progress', schema=None) as batch_op:
        for col in ['fsrs_state', 'fsrs_stability', 'fsrs_difficulty', 'legacy_mastery']:
            if col in lp_columns:
                batch_op.drop_column(col)

    # 2. Revert ReviewLogs
    with op.batch_alter_table('review_logs', schema=None) as batch_op:
        if 'fsrs_stability' in rl_columns:
            batch_op.alter_column('fsrs_stability', new_column_name='easiness_factor')
