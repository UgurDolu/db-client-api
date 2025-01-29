"""Add started_at to queries

Revision ID: add_started_at
Revises: add_export_filename
Create Date: 2024-01-28 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_started_at'
down_revision = 'add_export_filename'
branch_labels = None
depends_on = None


def upgrade():
    # Add started_at column to queries table
    op.add_column('queries', sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    # Remove started_at column from queries table
    op.drop_column('queries', 'started_at') 