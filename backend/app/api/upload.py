import os
import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models import Video, Job
from app.services.storage import get_storage_service, LocalStorageService
from app.services.downloader import get_downloader_service
from app.services.queue import get_job_queue

router = APIRouter(tags=["Ingestion & Uploads"])


# Pydantic Schemas
class SignedUrlRequest(BaseModel):
    filename: str
    content_type: str = "video/mp4"


class UrlIngestRequest(BaseModel):
    url: str
    user_id: Optional[str] = None


@router.post("/upload/signed-url")
async def generate_signed_upload_url(
    payload: SignedUrlRequest,
    storage: LocalStorageService = Depends(get_storage_service),
):
    """Generate signed upload parameters for direct file upload."""
    return storage.generate_signed_upload_url(payload.filename, payload.content_type)


@router.post("/upload/file")
async def upload_video_file(
    file: UploadFile = File(...),
    file_id: Optional[str] = Query(None),
    expires: Optional[int] = Query(None),
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    storage: LocalStorageService = Depends(get_storage_service),
    queue = Depends(get_job_queue),
):
    """Upload video directly via multipart form data."""
    # If signed token query params were passed, verify them
    if file_id and expires and token:
        if not storage.verify_token(file_id, expires, token):
            raise HTTPException(status_code=403, detail="Invalid or expired upload token")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    storage_path = storage.save_uploaded_file(content, file.filename or "video.mp4")

    # Create Video record
    video = Video(
        source_type="upload",
        storage_url=storage_path,
        title=file.filename,
        status="uploaded",
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    # Create Job record
    job = Job(
        video_id=video.id,
        stage="audio_extract",
        status="queued",
        progress=0.0,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # In Step 3, we simulate job pipeline start
    async def sample_pipeline_handler(job_id: str, vid_id: str):
        await asyncio.sleep(1)
        await queue.update_job_progress(job_id, stage="audio_extract", progress=25.0)
        await asyncio.sleep(1)
        await queue.update_job_progress(job_id, stage="transcribing", progress=50.0)

    await queue.enqueue(job.id, sample_pipeline_handler, video.id)

    return {
        "status": "success",
        "video_id": video.id,
        "job_id": job.id,
        "storage_url": storage_path,
        "filename": file.filename,
        "size_bytes": len(content),
    }


@router.post("/ingest/url")
async def ingest_video_url(
    payload: UrlIngestRequest,
    db: AsyncSession = Depends(get_db),
    downloader = Depends(get_downloader_service),
    queue = Depends(get_job_queue),
):
    """Ingest a video stream or YouTube URL using yt-dlp."""
    if not payload.url or not payload.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid video URL")

    # Extract metadata before queuing
    try:
        # Run in threadpool so yt-dlp doesn't block the async event loop
        meta = await asyncio.to_thread(downloader.extract_metadata, payload.url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch video information: {str(e)}")

    video = Video(
        user_id=payload.user_id,
        source_type="youtube_url",
        source_url=payload.url,
        title=meta.get("title"),
        duration_s=meta.get("duration_s"),
        status="queued",
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    job = Job(
        video_id=video.id,
        stage="download",
        status="queued",
        progress=0.0,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Async worker task for downloading video
    async def download_handler(job_id: str, url: str, vid_id: str):
        await queue.update_job_progress(job_id, stage="download", progress=20.0)
        dl_info = await asyncio.to_thread(downloader.download_video, url)
        
        # Update video record with downloaded file path
        async with AsyncSessionLocal() as s:
            res = await s.execute(select(Video).where(Video.id == vid_id))
            v = res.scalar_one_or_none()
            if v:
                v.storage_url = dl_info["file_path"]
                v.status = "downloaded"
                await s.commit()

        await queue.update_job_progress(job_id, stage="audio_extract", progress=50.0)

    from app.core.database import AsyncSessionLocal
    await queue.enqueue(job.id, download_handler, payload.url, video.id)

    return {
        "status": "success",
        "video_id": video.id,
        "job_id": job.id,
        "title": meta.get("title"),
        "duration_s": meta.get("duration_s"),
        "channel": meta.get("channel"),
    }


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str, db: AsyncSession = Depends(get_db)):
    """Poll job progress, status, stage, and error."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "id": job.id,
        "video_id": job.video_id,
        "stage": job.stage,
        "status": job.status,
        "progress": job.progress,
        "error": job.error,
        "cost_estimate": job.cost_estimate,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }


@router.get("/videos/{video_id}")
async def get_video_details(video_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve video details and status."""
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    return {
        "id": video.id,
        "title": video.title,
        "source_type": video.source_type,
        "source_url": video.source_url,
        "storage_url": video.storage_url,
        "duration_s": video.duration_s,
        "language": video.language,
        "status": video.status,
        "created_at": video.created_at,
    }
