"""add model_name to results

Revision ID: 006
Revises: 005
Create Date: 2026-06-23
"""

from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("results", sa.Column("model_name", sa.String(50), nullable=True))


def downgrade():
    op.drop_column("results", "model_name")
