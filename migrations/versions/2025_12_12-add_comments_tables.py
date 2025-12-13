"""Add comments tables: comments, comment_mentions, comment_attachments

Revision ID: add_comments_tables
Revises: add_templates_tables
Create Date: 2025-12-12 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_comments_tables"
down_revision: Union[str, None] = "add_templates_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create comments table
    op.create_table(
        "comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_edited", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("edited_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["comments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comments_tenant_id", "comments", ["tenant_id"], unique=False)
    op.create_index("ix_comments_entity_type", "comments", ["entity_type"], unique=False)
    op.create_index("ix_comments_entity_id", "comments", ["entity_id"], unique=False)
    op.create_index("ix_comments_parent_id", "comments", ["parent_id"], unique=False)
    op.create_index("ix_comments_created_by", "comments", ["created_by"], unique=False)
    op.create_index("ix_comments_created_at", "comments", ["created_at"], unique=False)
    op.create_index("ix_comments_is_deleted", "comments", ["is_deleted"], unique=False)
    op.create_index("idx_comments_entity", "comments", ["entity_type", "entity_id"], unique=False)
    op.create_index("idx_comments_tenant_entity", "comments", ["tenant_id", "entity_type", "entity_id"], unique=False)
    op.create_index("idx_comments_parent", "comments", ["parent_id", "created_at"], unique=False)

    # Create comment_mentions table
    op.create_table(
        "comment_mentions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("comment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mentioned_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("notification_sent", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["comment_id"], ["comments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mentioned_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comment_mentions_tenant_id", "comment_mentions", ["tenant_id"], unique=False)
    op.create_index("ix_comment_mentions_comment_id", "comment_mentions", ["comment_id"], unique=False)
    op.create_index("ix_comment_mentions_mentioned_user_id", "comment_mentions", ["mentioned_user_id"], unique=False)
    op.create_index("idx_comment_mentions_comment", "comment_mentions", ["comment_id", "mentioned_user_id"], unique=False)
    op.create_index("idx_comment_mentions_user", "comment_mentions", ["mentioned_user_id", "notification_sent"], unique=False)

    # Create comment_attachments table
    op.create_table(
        "comment_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("comment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["comment_id"], ["comments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comment_attachments_tenant_id", "comment_attachments", ["tenant_id"], unique=False)
    op.create_index("ix_comment_attachments_comment_id", "comment_attachments", ["comment_id"], unique=False)
    op.create_index("ix_comment_attachments_file_id", "comment_attachments", ["file_id"], unique=False)
    op.create_index("idx_comment_attachments_comment", "comment_attachments", ["comment_id", "file_id"], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_comment_attachments_comment", table_name="comment_attachments")
    op.drop_index("ix_comment_attachments_file_id", table_name="comment_attachments")
    op.drop_index("ix_comment_attachments_comment_id", table_name="comment_attachments")
    op.drop_index("ix_comment_attachments_tenant_id", table_name="comment_attachments")
    op.drop_table("comment_attachments")

    op.drop_index("idx_comment_mentions_user", table_name="comment_mentions")
    op.drop_index("idx_comment_mentions_comment", table_name="comment_mentions")
    op.drop_index("ix_comment_mentions_mentioned_user_id", table_name="comment_mentions")
    op.drop_index("ix_comment_mentions_comment_id", table_name="comment_mentions")
    op.drop_index("ix_comment_mentions_tenant_id", table_name="comment_mentions")
    op.drop_table("comment_mentions")

    op.drop_index("idx_comments_parent", table_name="comments")
    op.drop_index("idx_comments_tenant_entity", table_name="comments")
    op.drop_index("idx_comments_entity", table_name="comments")
    op.drop_index("ix_comments_is_deleted", table_name="comments")
    op.drop_index("ix_comments_created_at", table_name="comments")
    op.drop_index("ix_comments_created_by", table_name="comments")
    op.drop_index("ix_comments_parent_id", table_name="comments")
    op.drop_index("ix_comments_entity_id", table_name="comments")
    op.drop_index("ix_comments_entity_type", table_name="comments")
    op.drop_index("ix_comments_tenant_id", table_name="comments")
    op.drop_table("comments")

