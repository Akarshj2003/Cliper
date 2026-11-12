import yt_dlp
import os

url = "https://youtu.be/ijCrXHI1g2k?si=MVm2xAPFixER1ALW"

print("--- Testing download WITHOUT any cookie file ---")
ydl_opts = {
    "quiet": False,
    "ignore_no_formats_error": True,
    "js_runtimes": {"node": {}},
}

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        print("Success! Title:", info.get("title"))
        formats = info.get("formats", [])
        print("Formats available count:", len(formats))
        video_formats = [f for f in formats if f.get('vcodec') != 'none']
        print("Video formats:", len(video_formats))
except Exception as e:
    print("Failed without cookies:", e)
