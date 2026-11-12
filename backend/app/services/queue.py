import asyncio
import logging
from datetime import datetime
from typing import Callable, Coroutine, Any, Dict, Optional
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models import Job, Video

logger = logging.getLogger(__name__)


class JobQueueEngine:
    _instance: Optional["JobQueueEngine"] = None

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._is_running = False
        self._worker_task: Optional[asyncio.Task] = None

    @classmethod
    def get_instance(cls) -> "JobQueueEngine":
        if cls._instance is None:
            cls._instance = JobQueueEngine()
        return cls._instance

    def start(self):
        if not self._is_running:
            self._is_running = True
            try:
                loop = asyncio.get_running_loop()
                self._worker_task = loop.create_task(self._process_queue())
            except RuntimeError:
                pass  # Loop will be created in app lifespan

    async def stop(self):
        self._is_running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    async def enqueue(
        self,
        job_id: str,
        handler: Callable[..., Coroutine[Any, Any, None]],
        *args,
        **kwargs
    ):
        await self._queue.put((job_id, handler, args, kwargs))
        logger.info(f"Enqueued job {job_id}")

    async def update_job_progress(
        self,
        job_id: str,
        stage: str,
        progress: float,
        status: str = "in_progress",
        error: Optional[str] = None
    ):
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if job:
                job.stage = stage
                job.progress = progress
                job.status = status
                if error:
                    job.error = error
                if status == "in_progress" and not job.started_at:
                    job.started_at = datetime.utcnow()
                elif status in ("completed", "failed"):
                    job.finished_at = datetime.utcnow()

                # Also sync video status
                video_res = await session.execute(select(Video).where(Video.id == job.video_id))
                video = video_res.scalar_one_or_none()
                if video:
                    if status == "failed":
                        video.status = "failed"
                    elif status == "completed" and stage == "render":
                        video.status = "ready"
                    else:
                        video.status = stage

                await session.commit()

    async def fail_job(self, job_id: str, error: str):
        """Mark a job as failed with a detailed error message."""
        await self.update_job_progress(
            job_id,
            stage="error",
            progress=0.0,
            status="failed",
            error=error
        )

    async def _process_queue(self):
        logger.info("JobQueueEngine background worker started.")
        while self._is_running:
            try:
                job_id, handler, args, kwargs = await self._queue.get()
                try:
                    await self.update_job_progress(job_id, stage="initializing", progress=5.0, status="in_progress")
                    await handler(job_id, *args, **kwargs)
                except Exception as e:
                    logger.exception(f"Job {job_id} failed: {e}")
                    await self.update_job_progress(
                        job_id,
                        stage="error",
                        progress=0.0,
                        status="failed",
                        error=str(e)
                    )
                finally:
                    self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected queue worker error: {e}")
                await asyncio.sleep(1)


def get_job_queue() -> JobQueueEngine:
    return JobQueueEngine.get_instance()
