"""SQLAlchemy base declaration."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base ORM model type."""

