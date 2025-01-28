"""add ssh hostname to queries

Revision ID: 004
Revises: 003
Create Date: 2024-01-28 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add ssh_hostname column to queries table
    with op.batch_alter_table('queries') as batch_op:
        batch_op.add_column(sa.Column('ssh_hostname', sa.String(), nullable=True))

def downgrade() -> None:
    # Remove ssh_hostname column from queries table
    with op.batch_alter_table('queries') as batch_op:
        batch_op.drop_column('ssh_hostname') 