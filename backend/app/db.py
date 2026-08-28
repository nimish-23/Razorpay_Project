"""
SQLite database setup via SQLModel.
Fastest option for hackathon — zero infra, single file DB.
"""

from sqlmodel import SQLModel, Session, create_engine

DATABASE_URL = "sqlite:///./trust_layer.db"

engine = create_engine(DATABASE_URL, echo=False)


def create_db_and_tables():
    """Create all SQLModel tables. Called once at app startup."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency — yields a DB session per request."""
    with Session(engine) as session:
        yield session
