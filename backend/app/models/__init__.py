import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    plan = Column(String(50), default="free", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    videos = relationship("Video", back_populates="user", cascade="all, delete-orphan")
    youtube_accounts = relationship("YouTubeAccount", back_populates="user", cascade="all, delete-orphan")


class Video(Base):
    __tablename__ = "videos"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    source_type = Column(String(50), nullable=False)  # "upload", "youtube_url", "stream_url"
    source_url = Column(Text, nullable=True)          # Original URL if source_type == link
    storage_url = Column(Text, nullable=True)         # Local disk path or S3 key
    title = Column(String(255), nullable=True)
    duration_s = Column(Float, nullable=True)
    language = Column(String(10), default="en", nullable=False)
    status = Column(String(50), default="pending", nullable=False, index=True)  # pending, transcribing, ready, failed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="videos")
    transcripts = relationship("Transcript", back_populates="video", cascade="all, delete-orphan")
    candidates = relationship("Candidate", back_populates="video", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="video", cascade="all, delete-orphan")


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    video_id = Column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    words_json = Column(JSON, nullable=False)   # Word-level timestamps: [{word, start, end, probability}]
    full_text = Column(Text, nullable=True)
    version = Column(String(50), default="whisper-base-v1", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    video = relationship("Video", back_populates="transcripts")


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    video_id = Column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    start_s = Column(Float, nullable=False)
    end_s = Column(Float, nullable=False)
    text = Column(Text, nullable=False)
    features_json = Column(JSON, nullable=True)      # Audio energy, speech rate, visual interest
    llm_scores_json = Column(JSON, nullable=True)    # hook, emotion, clarity, novelty, title, etc.
    final_score = Column(Float, nullable=False, index=True)  # 0 to 100
    reason = Column(Text, nullable=False)
    prompt_version = Column(String(50), default="scoring_v1", nullable=False)
    rank = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    video = relationship("Video", back_populates="candidates")
    clips = relationship("Clip", back_populates="candidate", cascade="all, delete-orphan")


class Clip(Base):
    __tablename__ = "clips"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    candidate_id = Column(String(36), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    render_url = Column(Text, nullable=True)          # Rendered 1080x1920 MP4 path
    aspect = Column(String(20), default="9:16", nullable=False)
    caption_style = Column(String(50), default="word_highlight", nullable=False)
    duration_s = Column(Float, nullable=True)
    status = Column(String(50), default="queued", nullable=False)  # queued, rendering, ready, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    candidate = relationship("Candidate", back_populates="clips")
    feedback = relationship("Feedback", back_populates="clip", cascade="all, delete-orphan")
    publications = relationship("YouTubePublication", back_populates="clip", cascade="all, delete-orphan")


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    clip_id = Column(String(36), ForeignKey("clips.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    rating = Column(Integer, nullable=False)  # +1 (good) or -1 (bad)
    exported = Column(Boolean, default=False, nullable=False)
    posted = Column(Boolean, default=False, nullable=False)
    views = Column(Integer, default=0, nullable=False)
    avg_watch_s = Column(Float, default=0.0, nullable=False)
    completion_rate = Column(Float, default=0.0, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    clip = relationship("Clip", back_populates="feedback")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    video_id = Column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    stage = Column(String(50), nullable=False)  # "download", "transcribe", "windowing", "scoring", "render"
    status = Column(String(50), default="queued", nullable=False, index=True)  # queued, running, completed, failed
    progress = Column(Float, default=0.0, nullable=False)
    error = Column(Text, nullable=True)
    cost_estimate = Column(Float, default=0.0, nullable=False)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    video = relationship("Video", back_populates="jobs")


class YouTubeAccount(Base):
    __tablename__ = "youtube_accounts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    channel_id = Column(String(100), nullable=False)
    channel_title = Column(String(255), nullable=False)
    channel_thumbnail = Column(Text, nullable=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_expiry = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="youtube_accounts")
    publications = relationship("YouTubePublication", back_populates="account", cascade="all, delete-orphan")


class YouTubePublication(Base):
    __tablename__ = "youtube_publications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    clip_id = Column(String(36), ForeignKey("clips.id", ondelete="CASCADE"), nullable=False, index=True)
    youtube_account_id = Column(String(36), ForeignKey("youtube_accounts.id", ondelete="CASCADE"), nullable=False)
    youtube_video_id = Column(String(100), nullable=True)
    youtube_video_url = Column(Text, nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    privacy_status = Column(String(50), default="public", nullable=False)  # public, unlisted, private
    status = Column(String(50), default="queued", nullable=False)          # queued, uploading, published, failed
    error_message = Column(Text, nullable=True)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    clip = relationship("Clip", back_populates="publications")
    account = relationship("YouTubeAccount", back_populates="publications")
