import os
import logging
from sqlalchemy import select, delete
from app.core.database import AsyncSessionLocal
from app.models import Video, Job, Transcript, Candidate
from app.services.audio_extractor import get_audio_extractor
from app.services.asr import get_asr_provider
from app.services.window_generator import get_candidate_window_generator
from app.services.queue import get_job_queue

logger = logging.getLogger(__name__)


async def run_pipeline_stage1_and_2(job_id: str, video_id: str):
    """
    Executes Pipeline Stages 1, 2 and 3:
      Stage 1: Extract 16kHz mono audio via FFmpeg (Progress 50% -> 65%)
      Stage 2: Transcribe speech with word-level timestamps (Progress 65% -> 75%)
      Stage 3: Candidate Window Generator with sentence & pause snapping (Progress 75% -> 85%)
    """
    queue = get_job_queue()

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Video).where(Video.id == video_id))
        video = result.scalar_one_or_none()
        if not video:
            raise ValueError(f"Video {video_id} not found")
        if not video.storage_url or not os.path.exists(video.storage_url):
            raise FileNotFoundError(f"Video file missing on disk: {video.storage_url}")

    extractor = get_audio_extractor()
    asr = get_asr_provider()
    window_generator = get_candidate_window_generator()

    # -------------------------------------------------------------
    # STAGE 1: FFmpeg Audio Extraction (Progress 50% -> 65%)
    # -------------------------------------------------------------
    await queue.update_job_progress(job_id, stage="audio_extract", progress=55.0)
    audio_path = extractor.extract_audio(video.storage_url)
    duration_s = extractor.get_duration(audio_path)

    async with AsyncSessionLocal() as session:
        v_res = await session.execute(select(Video).where(Video.id == video_id))
        v = v_res.scalar_one_or_none()
        if v:
            v.duration_s = duration_s
            await session.commit()

    await queue.update_job_progress(job_id, stage="audio_extract", progress=65.0)

    # -------------------------------------------------------------
    # STAGE 2: Speech-to-Text Transcription (Progress 65% -> 75%)
    # -------------------------------------------------------------
    await queue.update_job_progress(job_id, stage="transcribe", progress=68.0)
    asr_result = await asr.transcribe(audio_path, language=video.language)

    # Store Transcript in Database
    async with AsyncSessionLocal() as session:
        t_res = await session.execute(select(Transcript).where(Transcript.video_id == video_id))
        existing_transcript = t_res.scalar_one_or_none()
        if existing_transcript:
            existing_transcript.words_json = asr_result.words_as_dict_list()
            existing_transcript.full_text = asr_result.text
            existing_transcript.version = asr_result.version
        else:
            new_transcript = Transcript(
                video_id=video_id,
                words_json=asr_result.words_as_dict_list(),
                full_text=asr_result.text,
                version=asr_result.version
            )
            session.add(new_transcript)

        v_res = await session.execute(select(Video).where(Video.id == video_id))
        v = v_res.scalar_one_or_none()
        if v:
            v.status = "transcribed"
            if asr_result.language:
                v.language = asr_result.language
            if duration_s > 0:
                v.duration_s = duration_s
        await session.commit()

    await queue.update_job_progress(job_id, stage="transcribe", progress=75.0)
    logger.info(f"Completed Stage 1-2 for Video {video_id} (Words: {len(asr_result.words)})")

    # -------------------------------------------------------------
    # STAGE 3: Candidate Window Generator (Progress 75% -> 85%)
    # -------------------------------------------------------------
    await queue.update_job_progress(job_id, stage="windowing", progress=78.0)
    words_dicts = asr_result.words_as_dict_list()
    windows = window_generator.generate_windows(words_dicts)

    # Persist Candidate Windows to Database
    async with AsyncSessionLocal() as session:
        # Clear any prior candidate records for this video
        await session.execute(delete(Candidate).where(Candidate.video_id == video_id))

        for idx, win in enumerate(windows):
            candidate = Candidate(
                video_id=video_id,
                start_s=win.start_s,
                end_s=win.end_s,
                text=win.text,
                features_json={
                    "duration_s": win.duration_s,
                    "word_count": len(win.words),
                },
                final_score=0.0,
                reason="Candidate window identified. Pending LLM rubric scoring.",
                prompt_version="scoring_v1",
                rank=None
            )
            session.add(candidate)

        v_res = await session.execute(select(Video).where(Video.id == video_id))
        v = v_res.scalar_one_or_none()
        if v:
            v.status = "candidates_generated"
        await session.commit()

    await queue.update_job_progress(job_id, stage="windowing", progress=85.0, status="completed")
    logger.info(f"Completed Stage 3 for Video {video_id} (Candidate Windows: {len(windows)})")
