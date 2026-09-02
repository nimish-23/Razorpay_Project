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


def get_session():
    return Session(engine)