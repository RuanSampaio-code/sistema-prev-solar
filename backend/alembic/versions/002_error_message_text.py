"""error_message to text

Revision ID: 002
Revises: 001
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("images", "error_message",
                    existing_type=sa.String(500),
                    type_=sa.Text(),
                    existing_nullable=True)


def downgrade():
    op.alter_column("images", "error_message",
                    existing_type=sa.Text(),
                    type_=sa.String(500),
                    existing_nullable=True)
