"""Initial ClipViral Schema with YouTube integration

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-12 15:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('plan', sa.String(length=50), nullable=False, server_default='free'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. videos
    op.create_table(
        'videos',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('storage_url', sa.Text(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('duration_s', sa.Float(), nullable=True),
        sa.Column('language', sa.String(length=10), nullable=False, server_default='en'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_videos_user_id'), 'videos', ['user_id'], unique=False)
    op.create_index(op.f('ix_videos_status'), 'videos', ['status'], unique=False)

    # 3. transcripts
    op.create_table(
        'transcripts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('video_id', sa.String(length=36), nullable=False),
        sa.Column('words_json', sa.JSON(), nullable=False),
        sa.Column('full_text', sa.Text(), nullable=True),
        sa.Column('version', sa.String(length=50), nullable=False, server_default='whisper-base-v1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transcripts_video_id'), 'transcripts', ['video_id'], unique=False)

    # 4. candidates
    op.create_table(
        'candidates',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('video_id', sa.String(length=36), nullable=False),
        sa.Column('start_s', sa.Float(), nullable=False),
        sa.Column('end_s', sa.Float(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('features_json', sa.JSON(), nullable=True),
        sa.Column('llm_scores_json', sa.JSON(), nullable=True),
        sa.Column('final_score', sa.Float(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('prompt_version', sa.String(length=50), nullable=False, server_default='scoring_v1'),
        sa.Column('rank', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_candidates_video_id'), 'candidates', ['video_id'], unique=False)
    op.create_index(op.f('ix_candidates_final_score'), 'candidates', ['final_score'], unique=False)
    op.create_index(op.f('ix_candidates_rank'), 'candidates', ['rank'], unique=False)

    # 5. clips
    op.create_table(
        'clips',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('candidate_id', sa.String(length=36), nullable=False),
        sa.Column('render_url', sa.Text(), nullable=True),
        sa.Column('aspect', sa.String(length=20), nullable=False, server_default='9:16'),
        sa.Column('caption_style', sa.String(length=50), nullable=False, server_default='word_highlight'),
        sa.Column('duration_s', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='queued'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_clips_candidate_id'), 'clips', ['candidate_id'], unique=False)

    # 6. feedback
    op.create_table(
        'feedback',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('clip_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('exported', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('posted', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('views', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('avg_watch_s', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('completion_rate', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['clip_id'], ['clips.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_feedback_clip_id'), 'feedback', ['clip_id'], unique=False)

    # 7. jobs
    op.create_table(
        'jobs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('video_id', sa.String(length=36), nullable=False),
        sa.Column('stage', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='queued'),
        sa.Column('progress', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('cost_estimate', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_jobs_video_id'), 'jobs', ['video_id'], unique=False)
    op.create_index(op.f('ix_jobs_status'), 'jobs', ['status'], unique=False)

    # 8. youtube_accounts
    op.create_table(
        'youtube_accounts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('channel_id', sa.String(length=100), nullable=False),
        sa.Column('channel_title', sa.String(length=255), nullable=False),
        sa.Column('channel_thumbnail', sa.Text(), nullable=True),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expiry', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_youtube_accounts_user_id'), 'youtube_accounts', ['user_id'], unique=False)

    # 9. youtube_publications
    op.create_table(
        'youtube_publications',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('clip_id', sa.String(length=36), nullable=False),
        sa.Column('youtube_account_id', sa.String(length=36), nullable=False),
        sa.Column('youtube_video_id', sa.String(length=100), nullable=True),
        sa.Column('youtube_video_url', sa.Text(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('privacy_status', sa.String(length=50), nullable=False, server_default='public'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='queued'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['clip_id'], ['clips.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['youtube_account_id'], ['youtube_accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_youtube_publications_clip_id'), 'youtube_publications', ['clip_id'], unique=False)


def downgrade() -> None:
    op.drop_table('youtube_publications')
    op.drop_table('youtube_accounts')
    op.drop_table('jobs')
    op.drop_table('feedback')
    op.drop_table('clips')
    op.drop_table('candidates')
    op.drop_table('transcripts')
    op.drop_table('videos')
    op.drop_table('users')
