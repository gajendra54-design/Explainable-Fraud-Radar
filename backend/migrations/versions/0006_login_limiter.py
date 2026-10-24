"""Cross-process failed-login rolling windows."""

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "login_attempt_buckets",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("failed_at", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.Float(), nullable=False),
    )
    op.create_index("ix_login_attempt_buckets_expires_at", "login_attempt_buckets", ["expires_at"])
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])


def downgrade():
    op.drop_index("ix_auth_sessions_expires_at", table_name="auth_sessions")
    op.drop_index("ix_login_attempt_buckets_expires_at", table_name="login_attempt_buckets")
    op.drop_table("login_attempt_buckets")
