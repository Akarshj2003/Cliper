import os
import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import get_db, AsyncSessionLocal
from app.models import Video, Job, Transcript, Candidate
from app.services.storage import get_storage_service, LocalStorageService
from app.services.downloader import get_downloader_service
from app.services.queue import get_job_queue
from app.services.pipeline import run_pipeline_stage1_and_2

router = APIRouter(tags=["Ingestion & Pipeline Stages 1-2"])
settings = get_settings()


# Pydantic Schemas
class SignedUrlRequest(BaseModel):
    filename: str
    content_type: str = "video/mp4"


class UrlIngestRequest(BaseModel):
    url: str
    user_id: Optional[str] = None


class CookiePayload(BaseModel):
    cookies_content: str


@router.get("/auth/cookies/status")
async def get_cookie_status():
    """Check if YouTube cookies are configured on the server."""
    cookie_paths = [
        os.path.abspath("cookies.txt"),
        os.path.join(settings.STORAGE_DIR, "cookies.txt"),
    ]
    for p in cookie_paths:
        if os.path.isfile(p) and os.path.getsize(p) > 0:
            return {
                "has_cookies": True,
                "cookie_file": p,
                "size_bytes": os.path.getsize(p),
            }
    return {
        "has_cookies": False,
        "cookie_file": None,
        "size_bytes": 0,
    }


@router.post("/auth/cookies")
async def save_youtube_cookies(payload: CookiePayload):
    """Save user-provided YouTube cookies to bypass bot checks."""
    content = payload.cookies_content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Cookies content cannot be empty")

    cookie_paths = [
        os.path.abspath("cookies.txt"),
        os.path.join(settings.STORAGE_DIR, "cookies.txt"),
    ]
    for path in cookie_paths:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    return {
        "status": "success",
        "message": "YouTube cookies successfully saved and active for downloads.",
        "size_bytes": len(content),
    }


@router.post("/auth/cookies/upload")
async def upload_youtube_cookies_file(file: UploadFile = File(...)):
    """Upload a cookies.txt file directly."""
    content = (await file.read()).decode("utf-8", errors="ignore").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded cookie file is empty")

    cookie_paths = [
        os.path.abspath("cookies.txt"),
        os.path.join(settings.STORAGE_DIR, "cookies.txt"),
    ]
    for path in cookie_paths:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    return {
        "status": "success",
        "message": f"Cookie file '{file.filename}' uploaded and active.",
        "size_bytes": len(content),
    }


@router.delete("/auth/cookies")
async def delete_youtube_cookies():
    """Remove saved YouTube cookies."""
    cookie_paths = [
        os.path.abspath("cookies.txt"),
        os.path.join(settings.STORAGE_DIR, "cookies.txt"),
    ]
    deleted = False
    for path in cookie_paths:
        if os.path.isfile(path):
            try:
                os.remove(path)
                deleted = True
            except Exception:
                pass
    return {"status": "success", "deleted": deleted}


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
    """Upload video directly via multipart form data and run audio extraction & ASR."""
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

    # Enqueue pipeline stages 1 and 2
    await queue.enqueue(job.id, run_pipeline_stage1_and_2, video.id)

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
    """Ingest a video stream or YouTube URL using yt-dlp and chain into ASR pipeline."""
    if not payload.url or not payload.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid video URL")

    # Extract metadata before queuing
    try:
        meta = await asyncio.to_thread(downloader.extract_metadata, payload.url)
    except Exception as e:
        err_msg = str(e)
        if "confirm you’re not a bot" in err_msg or "Sign in to confirm" in err_msg or "Sign in to confirm you're not a bot" in err_msg:
            raise HTTPException(
                status_code=400,
                detail="YouTube requires authentication ('Sign in to confirm you’re not a bot'). Click 'YouTube Sign-in' at the top right to configure your cookies, or switch to the 'Upload File' tab to process your video directly without restrictions."
            )
        raise HTTPException(status_code=400, detail=f"Failed to fetch video information: {err_msg}")

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

    # Async worker task for downloading video and continuing to ASR
    async def download_and_process_handler(job_id: str, url: str, vid_id: str):
        await queue.update_job_progress(job_id, stage="download", progress=20.0)
        dl_info = await asyncio.to_thread(downloader.download_video, url)

        async with AsyncSessionLocal() as s:
            res = await s.execute(select(Video).where(Video.id == vid_id))
            v = res.scalar_one_or_none()
            if v:
                v.storage_url = dl_info["file_path"]
                v.status = "downloaded"
                await s.commit()

        # Chain immediately into stage 1 & 2
        await run_pipeline_stage1_and_2(job_id, vid_id)

    await queue.enqueue(job.id, download_and_process_handler, payload.url, video.id)

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


@router.get("/videos/{video_id}/transcript")
async def get_video_transcript(video_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve transcribed text and word-level timestamps."""
    result = await db.execute(select(Transcript).where(Transcript.video_id == video_id))
    transcript = result.scalar_one_or_none()
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not ready or not found")

    return {
        "id": transcript.id,
        "video_id": transcript.video_id,
        "version": transcript.version,
        "full_text": transcript.full_text,
        "words": transcript.words_json,
        "word_count": len(transcript.words_json) if transcript.words_json else 0,
    }


@router.get("/videos/{video_id}/candidates")
async def get_video_candidates(video_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve generated candidate window segments for a video."""
    result = await db.execute(
        select(Candidate).where(Candidate.video_id == video_id).order_by(Candidate.start_s)
    )
    candidates = result.scalars().all()
    return [
        {
            "id": c.id,
            "video_id": c.video_id,
            "start_s": c.start_s,
            "end_s": c.end_s,
            "duration_s": round(c.end_s - c.start_s, 2),
            "text": c.text,
            "final_score": c.final_score,
            "reason": c.reason,
            "rank": c.rank,
        }
        for c in candidates
    ]
