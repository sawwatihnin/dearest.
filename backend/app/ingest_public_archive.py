"""CLI for ingesting verified public-domain archive entries."""

from __future__ import annotations

from .database import SessionLocal, ensure_schema
from .seed import seed_posts


def main() -> None:
    ensure_schema()
    with SessionLocal() as session:
        seed_posts(session)


if __name__ == "__main__":
    main()
