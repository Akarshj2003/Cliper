import os
import subprocess
import json
import logging
from typing import Optional
from app.core.config import get_settings
from app.core.ffmpeg_utils import find_ffmpeg_binary

logger = logging.getLogger(__name__)
settings = get_settings()


class AudioExtractorService:
    def __init__(self, audio_dir: Optional[str] = None):
        self.audio_dir = audio_dir or os.path.join(settings.STORAGE_DIR, "audio")
        os.makedirs(self.audio_dir, exist_ok=True)
        self.ffmpeg_bin = find_ffmpeg_binary()

    def get_ffprobe_binary(self) -> str:
        ffprobe_candidate = self.ffmpeg_bin.replace("ffmpeg.exe", "ffprobe.exe")
        if os.path.isfile(ffprobe_candidate):
            return ffprobe_candidate
        return "ffprobe"

    def get_duration(self, file_path: str) -> float:
        """Get precise media duration in seconds using ffprobe."""
        ffprobe = self.get_ffprobe_binary()
        cmd = [
            ffprobe,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            file_path,
        ]

        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            info = json.loads(result.stdout)
            return float(info.get("format", {}).get("duration", 0.0))
        except Exception as e:
            logger.warning(f"Could not probe duration for {file_path}: {e}")
            return 0.0

    def extract_audio(self, video_path: str, output_path: Optional[str] = None) -> str:
        """
        Extract audio stream to 16kHz mono 16-bit PCM WAV (optimal for Whisper ASR).
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file does not exist: {video_path}")

        if not output_path:
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            output_path = os.path.join(self.audio_dir, f"{base_name}.wav")

        # ffmpeg -y -i <video> -vn -acodec pcm_s16le -ar 16000 -ac 1 <output.wav>
        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            output_path,
        ]

        logger.info(f"Extracting audio using FFmpeg: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg audio extraction failed: {e.stderr.decode('utf-8', errors='ignore')}")
            raise RuntimeError(f"FFmpeg audio extraction failed: {e.stderr.decode('utf-8', errors='ignore')}")

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError(f"FFmpeg audio extraction produced empty or missing file: {output_path}")

        return output_path


def get_audio_extractor() -> AudioExtractorService:
    return AudioExtractorService()
