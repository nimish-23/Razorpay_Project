from pathlib import Path

from sqlmodel import SQLModel, Session, create_engine

from app.models import Product, Order, AuditLog


# backend/
BASE_DIR = Path(__file__).resolve().parent.parent

# backend/merchant.db
DATABASE_PATH = BASE_DIR / "merchant.db"

# Convert Windows path to SQLite-compatible path
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    with engine.connect() as conn:
        cursor = conn.connection.cursor()
        # Migrate audit_log
        audit_cols = [
            c[1]
            for c in cursor.execute("PRAGMA table_info(audit_log)").fetchall()
        ]

        if audit_cols:
            if "order_id" not in audit_cols:
                cursor.execute(
                    "ALTER TABLE audit_log ADD COLUMN order_id VARCHAR"
                )

            if "session_id" not in audit_cols:
                cursor.execute(
                    "ALTER TABLE audit_log ADD COLUMN session_id VARCHAR DEFAULT ''"
                )

            cursor.execute(
                "CREATE INDEX IF NOT EXISTS ix_audit_log_order_id "
                "ON audit_log (order_id)"
            )

            cursor.execute(
                "CREATE INDEX IF NOT EXISTS ix_audit_log_session_id "
                "ON audit_log (session_id)"
            )


        # Migrate orders
        order_cols = [
            c[1]
            for c in cursor.execute("PRAGMA table_info(orders)").fetchall()
        ]

        if order_cols and "session_id" not in order_cols:
            cursor.execute(
                "ALTER TABLE orders ADD COLUMN session_id VARCHAR DEFAULT ''"
            )

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS ix_orders_session_id "
            "ON orders (session_id)"
        )

        conn.connection.commit()


def get_session():
    return Session(engine)