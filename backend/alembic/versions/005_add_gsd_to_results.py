"""add gsd_used_m_px to results

Revision ID: 005
Revises: 004
Create Date: 2026-06-13
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("results", sa.Column("gsd_used_m_px", sa.Float(), nullable=True))


def downgrade():
    op.drop_column("results", "gsd_used_m_px")
