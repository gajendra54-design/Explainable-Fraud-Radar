from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "verified_labels",
        sa.Column("transaction_id", sa.String(100), sa.ForeignKey("transactions.id"), primary_key=True),
        sa.Column("label", sa.Integer, nullable=False),
        sa.Column("source", sa.String(120), nullable=False),
        sa.Column("evidence", sa.Text, nullable=False),
        sa.Column("verified_at", sa.String(50), nullable=False),
        sa.Column("recorded_at", sa.String(50), nullable=False),
        sa.Column("recorded_by", sa.String(80), sa.ForeignKey("users.username"), nullable=False),
        sa.CheckConstraint("label IN (0, 1)", name="ck_verified_label_binary"),
    )
    op.create_table(
        "monitoring_incidents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("report", sa.JSON, nullable=False),
        sa.Column("created_at", sa.String(50), nullable=False),
        sa.Column("created_by", sa.String(80), sa.ForeignKey("users.username"), nullable=False),
        sa.Column("updated_at", sa.String(50), nullable=False),
    )
    op.create_index("ix_monitoring_incidents_status", "monitoring_incidents", ["status"])
    op.create_table(
        "monitoring_incident_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("incident_id", sa.Integer, sa.ForeignKey("monitoring_incidents.id"), nullable=False),
        sa.Column("actor", sa.String(80), sa.ForeignKey("users.username"), nullable=False),
        sa.Column("note", sa.Text, nullable=False),
        sa.Column("previous_status", sa.String(30), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.String(50), nullable=False),
    )
    op.create_index("ix_monitoring_incident_events_incident_id", "monitoring_incident_events", ["incident_id"])


def downgrade():
    op.drop_table("monitoring_incident_events")
    op.drop_table("monitoring_incidents")
    op.drop_table("verified_labels")
