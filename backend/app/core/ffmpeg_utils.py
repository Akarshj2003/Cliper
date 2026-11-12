import os
import glob
import shutil
import logging

logger = logging.getLogger(__name__)


def find_ffmpeg_binary() -> str:
    """Find FFmpeg binary across PATH and standard install directories."""
    # 1. System PATH
    found = shutil.which("ffmpeg")
    if found:
        return found

    # 2. WinGet Packages
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        winget_pattern = os.path.join(
            local_app_data, "Microsoft", "WinGet", "Packages", "**", "ffmpeg.exe"
        )
        matches = glob.glob(winget_pattern, recursive=True)
        if matches and os.path.isfile(matches[0]):
            return matches[0]

        winget_links = os.path.join(local_app_data, "Microsoft", "WinGet", "Links", "ffmpeg.exe")
        if os.path.isfile(winget_links):
            return winget_links

    # 3. Common Windows Program Directories
    common_paths = [
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
    ]
    for p in common_paths:
        if os.path.isfile(p):
            return p

    return "ffmpeg"


def ensure_ffmpeg_in_path():
    """Ensure directory containing FFmpeg is in os.environ['PATH']."""
    binary_path = find_ffmpeg_binary()
    if binary_path and os.path.isfile(binary_path):
        bin_dir = os.path.dirname(binary_path)
        current_path = os.environ.get("PATH", "")
        if bin_dir not in current_path.split(os.pathsep):
            os.environ["PATH"] = f"{bin_dir}{os.pathsep}{current_path}"
            logger.info(f"Added FFmpeg directory to PATH: {bin_dir}")
    return binary_path
