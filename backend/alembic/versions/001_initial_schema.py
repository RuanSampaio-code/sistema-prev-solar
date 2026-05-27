"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column(
            "role",
            sa.Enum("admin", "operator", name="userrole"),
            nullable=False,
            server_default="operator",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "images",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("consumer_unit", sa.String(255), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("filepath", sa.String(500), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("file_size_kb", sa.Float(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "processing", "done", "error", name="imagestatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("image_id", sa.Integer(), sa.ForeignKey("images.id"), nullable=False, unique=True),
        sa.Column("panel_count", sa.Integer(), nullable=False),
        sa.Column("detected_area_m2", sa.Float(), nullable=False),
        sa.Column("estimated_kwh_month", sa.Float(), nullable=False),
        sa.Column("mask_filepath", sa.String(500), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("results")
    op.drop_table("images")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS imagestatus")
    op.execute("DROP TYPE IF EXISTS userrole")
