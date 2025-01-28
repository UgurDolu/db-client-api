"""add transferring status

Revision ID: 002
Revises: 001
Create Date: 2024-01-28 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from app.schemas.query import QueryStatus as QueryStatusEnum

# revision identifiers, used by Alembic
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Update the status column to accept the new value
    # SQLite doesn't support ALTER COLUMN, so we need to use batch operations
    with op.batch_alter_table('queries') as batch_op:
        batch_op.alter_column('status',
                            existing_type=sa.String(),
                            type_=sa.String(),
                            existing_nullable=True,
                            nullable=False,
                            server_default=QueryStatusEnum.pending.value)

def downgrade() -> None:
    # Convert any 'transferring' status to 'running' before downgrading
    op.execute("UPDATE queries SET status = 'running' WHERE status = 'transferring'") 
