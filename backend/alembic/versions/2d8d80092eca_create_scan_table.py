"""create_scan_table

Revision ID: 2d8d80092eca
Revises: 
Create Date: 2026-09-10 17:01:56.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2d8d80092eca'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('scans',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('session_id', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=True),
    sa.Column('risk_level', sa.String(), nullable=True),
    sa.Column('numerical_score', sa.Integer(), nullable=True),
    sa.Column('explanation', sa.Text(), nullable=True),
    sa.Column('mrz_status', sa.String(), nullable=True),
    sa.Column('tampering_status', sa.String(), nullable=True),
    sa.Column('face_status', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scans_id'), 'scans', ['id'], unique=False)
    op.create_index(op.f('ix_scans_session_id'), 'scans', ['session_id'], unique=True)

def downgrade() -> None:
    op.drop_index(op.f('ix_scans_session_id'), table_name='scans')
    op.drop_index(op.f('ix_scans_id'), table_name='scans')
    op.drop_table('scans')
