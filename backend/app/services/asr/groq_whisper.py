import os
import httpx
from typing import Optional
from app.core.config import get_settings
from app.services.asr.base import BaseASRProvider, ASRResult, WordTimestamp

settings = get_settings()


class GroqWhisperProvider(BaseASRProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.endpoint = "https://api.groq.com/openai/v1/audio/transcriptions"

    async def transcribe(
        self, audio_path: str, language: Optional[str] = None
    ) -> ASRResult:
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not configured in environment or .env file.")

        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        async with httpx.AsyncClient(timeout=180.0) as client:
            with open(audio_path, "rb") as f:
                files = {
                    "file": (os.path.basename(audio_path), f, "audio/wav")
                }
                data = {
                    "model": "whisper-large-v3",
                    "response_format": "verbose_json",
                    "timestamp_granularities[]": "word",
                }
                if language:
                    data["language"] = language

                response = await client.post(self.endpoint, headers=headers, files=files, data=data)
                response.raise_for_status()
                payload = response.json()

        words = []
        raw_words = payload.get("words", [])
        for item in raw_words:
            words.append(WordTimestamp(
                word=item.get("word", "").strip(),
                start=float(item.get("start", 0.0)),
                end=float(item.get("end", 0.0)),
                probability=0.98,
            ))

        return ASRResult(
            words=words,
            text=payload.get("text", ""),
            language=payload.get("language", language or "en"),
            duration_s=float(payload.get("duration", 0.0)),
            version="groq-whisper-large-v3"
        )
