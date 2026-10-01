"""review history and administrator authentication

Revision ID: 0007_review_and_auth
Revises: 0006_content_packs
Create Date: 2026-09-25
"""

import sqlalchemy as sa
from alembic import op

revision = "0007_review_and_auth"
down_revision = "0006_content_packs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.add_column("content_packs", sa.Column("team_profile_version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("content_packs", sa.Column("revised_from_id", sa.Uuid(), nullable=True))
    op.add_column("content_packs", sa.Column("revision_reason", sa.String(length=80), nullable=True))
    op.add_column("content_packs", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("content_packs", sa.Column("reviewed_by_id", sa.Uuid(), nullable=True))
    op.add_column("content_packs", sa.Column("review_note", sa.Text(), nullable=True))
    op.add_column("content_packs", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("content_packs", sa.Column("approved_by_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_content_packs_revised_from", "content_packs", "content_packs", ["revised_from_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_content_packs_reviewed_by", "content_packs", "users", ["reviewed_by_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_content_packs_approved_by", "content_packs", "users", ["approved_by_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_content_packs_revised_from_id", "content_packs", ["revised_from_id"])


def downgrade() -> None:
    op.drop_index("ix_content_packs_revised_from_id", table_name="content_packs")
    op.drop_constraint("fk_content_packs_approved_by", "content_packs", type_="foreignkey")
    op.drop_constraint("fk_content_packs_reviewed_by", "content_packs", type_="foreignkey")
    op.drop_constraint("fk_content_packs_revised_from", "content_packs", type_="foreignkey")
    for column in ("approved_by_id", "approved_at", "review_note", "reviewed_by_id", "reviewed_at", "revision_reason", "revised_from_id", "team_profile_version"):
        op.drop_column("content_packs", column)
    op.drop_table("users")
