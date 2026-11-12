import os
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import AsyncSessionLocal
from app.models import Video, Job, Transcript
from app.services.audio_extractor import get_audio_extractor
from app.services.asr.mock_asr import MockASRProvider
from app.services.pipeline import run_pipeline_stage1_and_2


@pytest.fixture
def sample_video_path():
    path = os.path.abspath("storage/test_sample.mp4")
    assert os.path.exists(path), "test_sample.mp4 must exist for testing"
    return path


def test_ffmpeg_audio_extraction(sample_video_path):
    extractor = get_audio_extractor()
    audio_path = extractor.extract_audio(sample_video_path)
    assert os.path.exists(audio_path)
    assert audio_path.endswith(".wav")
    assert os.path.getsize(audio_path) > 0

    duration = extractor.get_duration(audio_path)
    assert duration > 0.0


@pytest.mark.asyncio
async def test_swappable_asr_word_timestamps(sample_video_path):
    extractor = get_audio_extractor()
    audio_path = extractor.extract_audio(sample_video_path)

    asr = MockASRProvider()
    result = await asr.transcribe(audio_path)

    assert result.text is not None
    assert len(result.words) > 0
    first_word = result.words[0]
    assert hasattr(first_word, "word")
    assert hasattr(first_word, "start")
    assert hasattr(first_word, "end")
    assert first_word.end >= first_word.start


@pytest.mark.asyncio
async def test_pipeline_stages_1_and_2_end_to_end(sample_video_path):
    async with AsyncSessionLocal() as session:
        video = Video(
            source_type="upload",
            storage_url=sample_video_path,
            title="Pipeline Test Video",
            status="uploaded"
        )
        session.add(video)
        await session.commit()
        await session.refresh(video)

        job = Job(
            video_id=video.id,
            stage="audio_extract",
            status="queued",
            progress=0.0
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)

    # Run stages 1 and 2
    await run_pipeline_stage1_and_2(job.id, video.id)

    # Verify database state
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        t_res = await session.execute(select(Transcript).where(Transcript.video_id == video.id))
        transcript = t_res.scalar_one_or_none()
        assert transcript is not None
        assert len(transcript.words_json) > 0
        assert "Welcome" in transcript.full_text

        j_res = await session.execute(select(Job).where(Job.id == job.id))
        updated_job = j_res.scalar_one_or_none()
        assert updated_job.stage in ("transcribe", "windowing")
        assert updated_job.progress >= 75.0

    # Verify transcript API endpoint
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(f"/api/videos/{video.id}/transcript")
        assert res.status_code == 200
        data = res.json()
        assert data["video_id"] == video.id
        assert data["word_count"] > 0
        assert "words" in data
