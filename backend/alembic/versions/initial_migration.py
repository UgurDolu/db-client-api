"""initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-23

"""
from alembic import op
import sqlalchemy as sa
from app.db.models import QueryStatus

# revision identifiers, used by Alembic
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Create user_settings table
    op.create_table(
        'user_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('export_location', sa.String(), nullable=True),
        sa.Column('export_type', sa.String(), nullable=True),
        sa.Column('max_parallel_queries', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_settings_id', 'user_settings', ['id'])

    # Create queries table
    op.create_table(
        'queries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('db_username', sa.String(), nullable=False),
        sa.Column('db_password', sa.String(), nullable=False),
        sa.Column('db_tns', sa.String(), nullable=False),
        sa.Column('query_text', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, default=QueryStatus.PENDING.value),
        sa.Column('export_location', sa.String(), nullable=True),
        sa.Column('export_type', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('result_metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_queries_id', 'queries', ['id'])
    op.create_index('ix_queries_user_id', 'queries', ['user_id'])

def downgrade() -> None:
    op.drop_index('ix_queries_id', 'queries')
    op.drop_table('queries')
    op.drop_index('ix_user_settings_id', 'user_settings')
    op.drop_table('user_settings')
    op.drop_index('ix_users_email', 'users')
    op.drop_index('ix_users_id', 'users')
    op.drop_table('users') 