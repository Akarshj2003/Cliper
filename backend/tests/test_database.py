import uuid
import pytest
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models import (
    User,
    Video,
    Transcript,
    Candidate,
    Clip,
    Feedback,
    Job,
    YouTubeAccount,
    YouTubePublication
)


@pytest.mark.asyncio
async def test_create_and_query_user_and_video():
    unique_email = f"clipper_{uuid.uuid4().hex[:8]}@test.com"
    async with AsyncSessionLocal() as session:
        # Create user
        user = User(email=unique_email, plan="clipper")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        assert user.id is not None
        assert user.email == unique_email

        # Create YouTube Link Video
        video = Video(
            user_id=user.id,
            source_type="youtube_url",
            source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            title="Sample Viral Podcast",
            duration_s=1800.0,
            status="pending"
        )
        session.add(video)
        await session.commit()
        await session.refresh(video)
        assert video.id is not None
        assert video.source_type == "youtube_url"

        # Query video
        result = await session.execute(select(Video).where(Video.id == video.id))
        queried_video = result.scalar_one_or_none()
        assert queried_video is not None
        assert queried_video.title == "Sample Viral Podcast"


@pytest.mark.asyncio
async def test_pipeline_entities_and_scoring():
    async with AsyncSessionLocal() as session:
        # Create video
        video = Video(source_type="upload", title="Interview Episode 1", status="transcribing")
        session.add(video)
        await session.commit()
        await session.refresh(video)

        # Create transcript
        transcript = Transcript(
            video_id=video.id,
            words_json=[
                {"word": "Welcome", "start": 0.0, "end": 0.5, "probability": 0.98},
                {"word": "everyone", "start": 0.5, "end": 1.0, "probability": 0.99}
            ],
            full_text="Welcome everyone",
            version="whisper-base-v1"
        )
        session.add(transcript)

        # Create Candidate
        candidate = Candidate(
            video_id=video.id,
            start_s=0.0,
            end_s=35.0,
            text="Welcome everyone, today we uncover the greatest secret.",
            features_json={"audio_energy": 0.85, "speech_rate": 3.2},
            llm_scores_json={"hook": 9.0, "emotion": 8.5, "clarity": 9.0},
            final_score=88.5,
            reason="High hook energy and clear premise in first 3 seconds.",
            rank=1
        )
        session.add(candidate)
        await session.commit()
        await session.refresh(candidate)
        assert candidate.final_score == 88.5

        # Create Clip
        clip = Clip(
            candidate_id=candidate.id,
            render_url="/storage/clips/clip_001.mp4",
            aspect="9:16",
            caption_style="word_highlight",
            duration_s=35.0,
            status="ready"
        )
        session.add(clip)

        # Create Job
        job = Job(
            video_id=video.id,
            stage="scoring",
            status="completed",
            progress=100.0,
            cost_estimate=0.015
        )
        session.add(job)
        await session.commit()

        # Query Clip
        res = await session.execute(select(Clip).where(Clip.id == clip.id))
        queried_clip = res.scalar_one_or_none()
        assert queried_clip is not None
        assert queried_clip.aspect == "9:16"


@pytest.mark.asyncio
async def test_youtube_integration_models():
    unique_email = f"youtube_creator_{uuid.uuid4().hex[:8]}@test.com"
    async with AsyncSessionLocal() as session:
        user = User(email=unique_email, plan="pro")
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # YouTube Account
        yt_account = YouTubeAccount(
            user_id=user.id,
            channel_id=f"UC_{uuid.uuid4().hex[:10]}",
            channel_title="Clipper Shorts Official",
            access_token="fake_access_token",
            refresh_token="fake_refresh_token"
        )
        session.add(yt_account)
        await session.commit()
        await session.refresh(yt_account)
        assert yt_account.user_id == user.id

        # Video & Candidate & Clip
        video = Video(source_type="upload", title="Podcast Clip Source")
        session.add(video)
        await session.commit()

        candidate = Candidate(
            video_id=video.id,
            start_s=10.0,
            end_s=40.0,
            text="Unbelievable moment",
            final_score=92.0,
            reason="Huge plot twist"
        )
        session.add(candidate)
        await session.commit()

        clip = Clip(candidate_id=candidate.id, status="ready")
        session.add(clip)
        await session.commit()

        # YouTube Publication
        pub = YouTubePublication(
            clip_id=clip.id,
            youtube_account_id=yt_account.id,
            youtube_video_id="dQw4w9WgXcQ",
            youtube_video_url="https://youtube.com/shorts/dQw4w9WgXcQ",
            title="You won't believe this moment! #Shorts",
            description="Viral podcast excerpt clipped with ClipViral",
            tags=["shorts", "viral", "podcast"],
            privacy_status="public",
            status="published"
        )
        session.add(pub)
        await session.commit()
        await session.refresh(pub)
        assert pub.youtube_video_id == "dQw4w9WgXcQ"
        assert pub.status == "published"
