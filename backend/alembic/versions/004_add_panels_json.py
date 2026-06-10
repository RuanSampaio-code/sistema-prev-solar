"""add panels json to results

Revision ID: 004
Revises: 003
Create Date: 2026-06-09
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("results", sa.Column("panels", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("results", "panels")
