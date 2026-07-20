"""Request-scoped correlation context utilities."""

from __future__ import annotations

from contextvars import ContextVar

_correlation_id: ContextVar[str | None] = ContextVar("dearest_correlation_id", default=None)
_client_ip: ContextVar[str | None] = ContextVar("dearest_client_ip", default=None)


def set_correlation_id(value: str | None) -> None:
    _correlation_id.set(value)


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def set_client_ip(value: str | None) -> None:
    _client_ip.set(value)


def get_client_ip() -> str | None:
    return _client_ip.get()
