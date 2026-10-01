"""content performance snapshots and editorial tags

Revision ID: 0008_content_performance
Revises: 0007_review_and_auth
Create Date: 2026-09-25
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008_content_performance"
down_revision = "0007_review_and_auth"
branch_labels = None
depends_on = None


def _json_type() -> sa.types.TypeEngine[object]:
    return sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.add_column(
        "content_packs",
        sa.Column("editorial_tags", _json_type(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_table(
        "content_performance",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("content_pack_id", sa.Uuid(), sa.ForeignKey("content_packs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(length=40), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("engaged_views", sa.Integer(), nullable=True),
        sa.Column("average_watch_seconds", sa.Float(), nullable=True),
        sa.Column("average_percentage_viewed", sa.Float(), nullable=True),
        sa.Column("likes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("shares", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("saves", sa.Integer(), nullable=True),
        sa.Column("followers_gained", sa.Integer(), nullable=True),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False, server_default="manual"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("views >= 0", name="ck_content_performance_views"),
        sa.CheckConstraint("likes >= 0", name="ck_content_performance_likes"),
        sa.CheckConstraint("comments >= 0", name="ck_content_performance_comments"),
        sa.CheckConstraint("shares >= 0", name="ck_content_performance_shares"),
        sa.CheckConstraint("average_percentage_viewed IS NULL OR average_percentage_viewed BETWEEN 0 AND 100", name="ck_content_performance_percentage"),
        sa.UniqueConstraint("content_pack_id", "platform", "measured_at", name="uq_content_performance_measurement"),
    )
    op.create_index("ix_content_performance_content_pack_id", "content_performance", ["content_pack_id"])
    op.create_index("ix_content_performance_platform", "content_performance", ["platform"])
    op.create_index("ix_content_performance_measured_at", "content_performance", ["measured_at"])


def downgrade() -> None:
    op.drop_table("content_performance")
    op.drop_column("content_packs", "editorial_tags")
