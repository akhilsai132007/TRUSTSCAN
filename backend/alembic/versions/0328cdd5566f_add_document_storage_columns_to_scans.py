"""add document storage columns to scans

Revision ID: 0328cdd5566f
Revises: d4e19fb6d502
Create Date: 2026-09-11 10:41:40.974093

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0328cdd5566f'
down_revision: Union[str, Sequence[str], None] = 'd4e19fb6d502'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('scans', sa.Column('document_storage_id', sa.String(), nullable=True))
    op.add_column('scans', sa.Column('document_file_size', sa.Integer(), nullable=True))
    op.add_column('scans', sa.Column('document_content_type', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('scans', 'document_content_type')
    op.drop_column('scans', 'document_file_size')
    op.drop_column('scans', 'document_storage_id')
