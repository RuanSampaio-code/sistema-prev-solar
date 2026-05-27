"""remove consumer_unit from images

Revision ID: 003
Revises: 002
Create Date: 2026-05-27
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("images", "consumer_unit")


def downgrade():
    op.add_column("images", sa.Column("consumer_unit", sa.String(255), nullable=True))
