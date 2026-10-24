"""Durable pipeline queue, fenced leases and bounded retries."""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("pipeline_runs", sa.Column("job_type", sa.String(30), nullable=False, server_default="training"))
    op.add_column("pipeline_runs", sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("pipeline_runs", sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"))
    for name, size in [("lease_owner", 100), ("lease_expires_at", 50), ("heartbeat_at", 50), ("next_attempt_at", 50)]:
        op.add_column("pipeline_runs", sa.Column(name, sa.String(size), nullable=True))
    op.create_index("ix_pipeline_queue", "pipeline_runs", ["status", "lease_expires_at"])


def downgrade():
    op.drop_index("ix_pipeline_queue", table_name="pipeline_runs")
    for name in ["next_attempt_at", "heartbeat_at", "lease_expires_at", "lease_owner", "max_attempts", "attempts", "job_type"]:
        op.drop_column("pipeline_runs", name)
