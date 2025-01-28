"""add ssh hostname and port

Revision ID: 003
Revises: 002
Create Date: 2024-01-28 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add new columns for SSH hostname and port
    with op.batch_alter_table('user_settings') as batch_op:
        batch_op.add_column(sa.Column('ssh_hostname', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('ssh_port', sa.Integer(), server_default='22', nullable=True))

def downgrade() -> None:
    # Remove the columns
    with op.batch_alter_table('user_settings') as batch_op:
        batch_op.drop_column('ssh_hostname')
        batch_op.drop_column('ssh_port') 