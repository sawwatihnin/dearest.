from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from time import perf_counter
from collections import defaultdict, deque
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect
from starlette.responses import Response

from .api import router
from .api.deps import build_services
from .database import SessionLocal, engine
from .repositories import PostRepository
from .request_context import set_client_ip, set_correlation_id
from .seed import seed_posts
from .settings import get_settings
from .telemetry import registry

logger = logging.getLogger("dearest.api")
_rate_limit_state: dict[str, deque[float]] = defaultdict(deque)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if "posts" not in inspect(engine).get_table_names():
        raise RuntimeError("Database schema missing. Run Alembic migrations before starting Dearest.")
    with SessionLocal() as session:
        seed_posts(session)
        repository = PostRepository(session)
        post_service = build_services(session)["post_service"]
        repaired = 0
        for post in repository.all_posts():
            if post.content_type != "community":
                continue
            post_service.reindex_post(post.id)  # type: ignore[attr-defined]
            repaired += 1
        if repaired:
            logger.info("privacy.repair completed community_posts=%s", repaired)
    yield


app = FastAPI(title="Dearest. API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    settings = get_settings()
    request_id = request.headers.get("x-correlation-id") or request.headers.get("x-request-id") or str(uuid4())
    client_ip = request.client.host if request.client else "unknown"
    set_correlation_id(request_id)
    set_client_ip(client_ip)
    now = perf_counter()
    history = _rate_limit_state[client_ip]
    while history and (now - history[0]) > settings.rate_limit_window_seconds:
        history.popleft()
    if len(history) >= settings.rate_limit_requests:
        registry.increment("dearest_rate_limit_blocks_total")
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please slow down.")
    history.append(now)
    started = perf_counter()
    response: Response = await call_next(request)
    latency_ms = round((perf_counter() - started) * 1000, 3)
    response.headers["X-Request-Id"] = request_id
    response.headers["X-Correlation-Id"] = request_id
    registry.observe_latency(f"dearest_http_{request.method.lower()}_{request.url.path.strip('/').replace('/', '_') or 'root'}", latency_ms)
    logger.info(
        "request.complete method=%s path=%s status=%s latency_ms=%s request_id=%s client_ip=%s",
        request.method,
        request.url.path,
        response.status_code,
        latency_ms,
        request_id,
        client_ip,
    )
    return response

app.include_router(router)
