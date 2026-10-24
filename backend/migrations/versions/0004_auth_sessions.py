"""Persistent, revocable authentication sessions."""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.String(50), nullable=False),
        sa.Column("expires_at", sa.String(50), nullable=False),
        sa.Column("revoked_at", sa.String(50), nullable=True),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])


def downgrade():
    op.drop_index("ix_auth_sessions_user_id", table_name="auth_sessions")
    op.drop_table("auth_sessions")
