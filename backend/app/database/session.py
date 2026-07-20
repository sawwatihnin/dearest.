"""Database session and engine configuration."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import event
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .base import Base

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "dearest.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@event.listens_for(engine, "connect")
def _configure_sqlite(connection, _record) -> None:
    """Keep SQLite reads stable on low-disk local dev machines."""
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=MEMORY")
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


def get_db():
    """Yield a request-scoped SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
