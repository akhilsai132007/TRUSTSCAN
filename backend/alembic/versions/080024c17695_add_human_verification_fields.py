"""add human verification fields

Revision ID: 080024c17695
Revises: 2d8d80092eca
Create Date: 2026-09-11 10:07:29.282878

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '080024c17695'
down_revision: Union[str, Sequence[str], None] = '2d8d80092eca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('scans', sa.Column('human_verification_status', sa.String(), server_default='PENDING_REVIEW', nullable=True))
    op.add_column('scans', sa.Column('human_decision', sa.String(), nullable=True))
    op.add_column('scans', sa.Column('human_decision_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('scans', sa.Column('human_reviewer_id', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('scans', 'human_reviewer_id')
    op.drop_column('scans', 'human_decision_at')
    op.drop_column('scans', 'human_decision')
    op.drop_column('scans', 'human_verification_status')
