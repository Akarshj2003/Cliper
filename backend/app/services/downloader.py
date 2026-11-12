import os
import uuid
import logging
from typing import Dict, Any, Optional
import yt_dlp
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class VideoDownloaderService:
    def __init__(self, download_dir: Optional[str] = None):
        self.download_dir = download_dir or settings.YT_DLP_STORAGE_PATH
        os.makedirs(self.download_dir, exist_ok=True)

    def extract_metadata(self, url: str) -> Dict[str, Any]:
        """Fetch video metadata without downloading the full payload."""
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                duration = info.get("duration", 0)
                title = info.get("title", "Untitled Video")

                if duration > settings.YT_DLP_MAX_DURATION_SECONDS:
                    raise ValueError(
                        f"Video duration ({duration}s) exceeds the maximum allowed limit of {settings.YT_DLP_MAX_DURATION_SECONDS}s."
                    )

                return {
                    "title": title,
                    "duration_s": duration,
                    "channel": info.get("uploader", "Unknown"),
                    "thumbnail": info.get("thumbnail"),
                    "description": info.get("description", "")[:500],
                    "webpage_url": info.get("webpage_url", url),
                }
            except Exception as e:
                logger.error(f"Error extracting metadata from {url}: {e}")
                raise

    def download_video(self, url: str) -> Dict[str, Any]:
        """Download video to local disk for pipeline processing."""
        file_prefix = f"dl_{uuid.uuid4().hex[:12]}"
        output_template = os.path.join(self.download_dir, f"{file_prefix}_%(title).50s.%(ext)s")

        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "merge_output_format": "mp4",
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
                downloaded_file = ydl.prepare_filename(info)
                # Ensure mp4 extension if merged
                if not os.path.exists(downloaded_file):
                    alt_path = os.path.splitext(downloaded_file)[0] + ".mp4"
                    if os.path.exists(alt_path):
                        downloaded_file = alt_path

                return {
                    "file_path": downloaded_file,
                    "title": info.get("title", "Downloaded Video"),
                    "duration_s": info.get("duration", 0),
                    "thumbnail": info.get("thumbnail"),
                }
            except Exception as e:
                logger.error(f"Error downloading video from {url}: {e}")
                raise


def get_downloader_service() -> VideoDownloaderService:
    return VideoDownloaderService()
