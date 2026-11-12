import os
import asyncio
from typing import Optional
from app.services.asr.base import BaseASRProvider, ASRResult, WordTimestamp
from app.services.audio_extractor import get_audio_extractor


class MockASRProvider(BaseASRProvider):
    """
    Deterministic mock provider for unit tests, offline development,
    and verifying sentence/pause boundary windowing without requiring cloud API keys.
    """
    def __init__(self, sample_text: Optional[str] = None):
        self.sample_text = sample_text or (
            "Welcome back to the podcast. Today we are diving into why your brain gets addicted "
            "to cheap dopamine instead of hard tasks. The secret is dopamine reward prediction error. "
            "When you scroll social media, you get unpredictable spikes of dopamine. But when you study or build, "
            "the reward is delayed. If you learn to reset your baseline, you become unstoppable. "
            "Let's look at the three daily steps you must take to master your focus."
        )

    async def transcribe(
        self, audio_path: str, language: Optional[str] = None
    ) -> ASRResult:
        await asyncio.sleep(0.1)  # Simulate I/O

        audio_extractor = get_audio_extractor()
        duration = audio_extractor.get_duration(audio_path)
        if duration <= 0.0:
            duration = 30.0

        filename = os.path.basename(audio_path).replace(".wav", "").replace("audio_", "")
        mock_text = (
            f"Welcome to the speech processing pipeline for '{filename}' running in local Mock ASR mode. "
            "The speech pipeline successfully extracted the 16kHz audio track and mapped natural pause boundaries. "
            "To transcribe the real spoken audio word-for-word, please add your free Groq API key or OpenAI key in Settings or .env. "
            "Sentence-snapped candidate moment generator is fully operational and ready for viral scoring."
        )

        raw_words = mock_text.split()
        word_duration = min(duration / len(raw_words), 0.5)
        current_time = 0.5

        words = []
        for i, word in enumerate(raw_words):
            start = round(current_time, 2)
            pause = 0.4 if word.endswith((".", "!", "?", ",")) else 0.1
            end = round(start + word_duration, 2)
            words.append(WordTimestamp(
                word=word,
                start=start,
                end=end,
                probability=0.98
            ))
            current_time = end + pause

        return ASRResult(
            words=words,
            text=mock_text,
            language=language or "en",
            duration_s=duration,
            version="mock-whisper-demo"
        )
