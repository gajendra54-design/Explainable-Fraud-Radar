"""Protect audit history against ordinary SQL UPDATE and DELETE operations."""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None
TABLES = ("audit_events", "verified_labels", "monitoring_incident_events")


def upgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
            CREATE FUNCTION radar_reject_audit_mutation() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN
              RAISE EXCEPTION 'Evidence tables are append-only';
            END $$
        """)
        for table in TABLES:
            op.execute(f"""
                CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE OR TRUNCATE
                ON {table} FOR EACH STATEMENT EXECUTE FUNCTION radar_reject_audit_mutation()
            """)
    else:
        for table in TABLES:
            for operation in ("UPDATE", "DELETE"):
                op.execute(f"""
                    CREATE TRIGGER {table}_no_{operation.lower()}
                    BEFORE {operation} ON {table} BEGIN
                      SELECT RAISE(ABORT, 'Evidence tables are append-only');
                    END
                """)


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        for table in TABLES:
            op.execute(f"DROP TRIGGER {table}_append_only ON {table}")
        op.execute("DROP FUNCTION radar_reject_audit_mutation()")
    else:
        for table in TABLES:
            for operation in ("update", "delete"):
                op.execute(f"DROP TRIGGER {table}_no_{operation}")
