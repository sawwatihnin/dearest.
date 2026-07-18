"""Public archive ingestion helpers for verified public-domain texts."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field, HttpUrl

PUBLIC_ARCHIVE_PATH = Path(__file__).resolve().parent.parent / "data" / "public_archive_entries.json"


class PublicArchiveEntry(BaseModel):
    """One verified public-domain or otherwise permitted archive item."""

    ingestion_key: str = Field(min_length=3, max_length=255)
    title: str = Field(min_length=3, max_length=255)
    text: str = Field(min_length=20, max_length=20000)
    mood: str | None = Field(default=None, max_length=64)
    author: str = Field(min_length=2, max_length=255)
    work: str | None = Field(default=None, max_length=255)
    year: str | None = Field(default=None, max_length=64)
    source: str | None = Field(default=None, max_length=255)
    source_url: HttpUrl | None = None
    rights_status: str = Field(min_length=3, max_length=255)
    rights_notes: str | None = Field(default=None, max_length=1000)
    themes: list[str] = Field(default_factory=list)
    emotions: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    tone: str | None = Field(default=None, max_length=64)


def load_public_archive_entries(path: Path = PUBLIC_ARCHIVE_PATH) -> list[PublicArchiveEntry]:
    """Load vetted public archive entries from a local JSON file."""
    if not path.exists():
        return []

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Public archive file must contain a JSON array.")
    entries = [PublicArchiveEntry.model_validate(item) for item in payload]
    validate_public_archive_entries(entries)
    return entries


def validate_public_archive_entries(entries: list[PublicArchiveEntry]) -> None:
    """Raise if the public archive dataset has structural issues."""
    ingestion_keys = [entry.ingestion_key for entry in entries]
    if len(ingestion_keys) != len(set(ingestion_keys)):
        raise ValueError("Public archive ingestion keys must be unique.")
