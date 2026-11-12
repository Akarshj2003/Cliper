import io
import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.storage import get_storage_service


@pytest.mark.asyncio
async def test_generate_signed_upload_url():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/upload/signed-url",
            json={"filename": "my_podcast.mp4", "content_type": "video/mp4"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "upload_url" in data
        assert "file_id" in data
        assert data["storage_type"] == "local"
        assert "expires_at" in data


@pytest.mark.asyncio
async def test_direct_file_upload_and_job_creation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        fake_video_content = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42mp41"
        files = {
            "file": ("test_interview.mp4", fake_video_content, "video/mp4")
        }

        response = await client.post("/api/upload/file", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "video_id" in data
        assert "job_id" in data
        assert data["filename"] == "test_interview.mp4"

        # Check job status endpoint
        job_res = await client.get(f"/api/jobs/{data['job_id']}")
        assert job_res.status_code == 200
        job_data = job_res.json()
        assert job_data["id"] == data["job_id"]
        assert job_data["video_id"] == data["video_id"]

        # Check video details endpoint
        vid_res = await client.get(f"/api/videos/{data['video_id']}")
        assert vid_res.status_code == 200
        vid_data = vid_res.json()
        assert vid_data["id"] == data["video_id"]
        assert vid_data["title"] == "test_interview.mp4"
        assert vid_data["source_type"] == "upload"


@pytest.mark.asyncio
async def test_signed_token_verification():
    storage = get_storage_service()
    signed_info = storage.generate_signed_upload_url("secure_clip.mp4", "video/mp4", expires_in=300)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Valid token upload
        files = {"file": ("secure_clip.mp4", b"dummy content", "video/mp4")}
        res = await client.post(signed_info["upload_url"], files=files)
        assert res.status_code == 200

        # Invalid/forged token upload should be rejected
        tampered_url = signed_info["upload_url"].replace("token=", "token=tampered_signature")
        bad_res = await client.post(tampered_url, files=files)
        assert bad_res.status_code == 403


@pytest.mark.asyncio
async def test_url_ingest_endpoint_with_mock():
    transport = ASGITransport(app=app)
    mock_metadata = {
        "title": "Lex Fridman Podcast #400",
        "duration_s": 3600.0,
        "channel": "Lex Fridman",
        "thumbnail": "https://example.com/thumb.jpg",
        "webpage_url": "https://www.youtube.com/watch?v=mock123"
    }

    with patch("app.services.downloader.VideoDownloaderService.extract_metadata", return_value=mock_metadata):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/ingest/url",
                json={"url": "https://www.youtube.com/watch?v=mock123"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["title"] == "Lex Fridman Podcast #400"
            assert data["duration_s"] == 3600.0
            assert "job_id" in data
            assert "video_id" in data
