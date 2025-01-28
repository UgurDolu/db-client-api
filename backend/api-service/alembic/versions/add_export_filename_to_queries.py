"""Add export_filename to queries

Revision ID: add_export_filename
Revises: 004
Create Date: 2024-01-28 21:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_export_filename'
down_revision = '004'  # Updated to use the current head revision
branch_labels = None
depends_on = None


def upgrade():
    # Add export_filename column to queries table
    op.add_column('queries', sa.Column('export_filename', sa.String(), nullable=True))


def downgrade():
    # Remove export_filename column from queries table
    op.drop_column('queries', 'export_filename') 
