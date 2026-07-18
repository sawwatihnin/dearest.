"""Post API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from ..ai import UnsafeContentError
from ..schemas import (
    ArchiveExplorerResponse,
    EchoesResponse,
    JobStatusResponse,
    PostCreate,
    PostCreateResponse,
    PostSummary,
    SimilarPostsResponse,
)
from .deps import get_post_service, get_processing_service
from ..services import PostService, ProcessingService
from ..tasks import process_post_job

router = APIRouter(prefix="/api")


@router.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@router.get("/posts", response_model=list[PostSummary])
def list_posts(post_service: PostService = Depends(get_post_service)) -> list[PostSummary]:
    """List all posts."""
    return post_service.list_posts()


@router.get("/posts/{post_id}", response_model=PostSummary)
def get_post(post_id: int, post_service: PostService = Depends(get_post_service)) -> PostSummary:
    """Fetch one post by id."""
    post = post_service.get_post(post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.post("/posts", response_model=PostCreateResponse)
def create_post(
    payload: PostCreate,
    response: Response,
    processing_service: ProcessingService = Depends(get_processing_service),
) -> PostCreateResponse:
    """Create a new post asynchronously with idempotent caching."""
    try:
        status_code, result = processing_service.submit_post(payload)
        if status_code == status.HTTP_202_ACCEPTED and result.job_id:
            process_post_job.delay(result.job_id)
        response.status_code = status_code
        return result
    except UnsafeContentError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: str,
    processing_service: ProcessingService = Depends(get_processing_service),
) -> JobStatusResponse:
    """Get async job status and result payload when available."""
    result = processing_service.get_job_status(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return result


@router.get("/posts/{post_id}/similar", response_model=SimilarPostsResponse)
def find_similar_posts(
    post_id: int,
    limit: int = 5,
    post_service: PostService = Depends(get_post_service),
) -> SimilarPostsResponse:
    """Get similar posts for one post."""
    response = post_service.get_similar_posts(post_id, limit=limit)
    if response is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return response


@router.get("/posts/{post_id}/echoes", response_model=EchoesResponse)
def get_echoes(
    post_id: int,
    depth: int = 5,
    post_service: PostService = Depends(get_post_service),
) -> EchoesResponse:
    """Get a semantic chain of connected writings."""
    response = post_service.get_echoes(post_id, depth=depth)
    if response is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return response


@router.get("/archive/explorer", response_model=ArchiveExplorerResponse)
def archive_explorer(
    theme: str | None = None,
    emotion: str | None = None,
    tone: str | None = None,
    author: str | None = None,
    year: str | None = None,
    content_type: str | None = None,
    collection: str | None = None,
    content_note: str | None = None,
    avoid_theme: str | None = None,
    avoid_content_note: str | None = None,
    sort: str = "newest",
    semantic_to_post_id: int | None = None,
    post_service: PostService = Depends(get_post_service),
) -> ArchiveExplorerResponse:
    """Browse archive content with semantic-friendly filters."""
    return post_service.list_archive_explorer_posts(
        theme=theme,
        emotion=emotion,
        tone=tone,
        author=author,
        year=year,
        content_type=content_type,
        collection=collection,
        content_note=content_note,
        avoid_theme=avoid_theme,
        avoid_content_note=avoid_content_note,
        sort=sort,
        semantic_to_post_id=semantic_to_post_id,
    )
