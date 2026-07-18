from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response

from .api import router
from .database import Base, SessionLocal, ensure_schema, engine
from .seed import seed_posts

logger = logging.getLogger("dearest.api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_schema()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        seed_posts(session)
    yield


app = FastAPI(title="Dearest. API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid4())
    started = perf_counter()
    response: Response = await call_next(request)
    latency_ms = round((perf_counter() - started) * 1000, 3)
    response.headers["X-Request-Id"] = request_id
    logger.info(
        "request.complete method=%s path=%s status=%s latency_ms=%s request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        latency_ms,
        request_id,
    )
    return response

app.include_router(router)
