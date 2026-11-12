from app.core.config import get_settings
from app.services.asr.base import BaseASRProvider, ASRResult, WordTimestamp
from app.services.asr.mock_asr import MockASRProvider
from app.services.asr.openai_whisper import OpenAIWhisperProvider
from app.services.asr.groq_whisper import GroqWhisperProvider

settings = get_settings()


def get_asr_provider(provider_name: str = None) -> BaseASRProvider:
    provider = provider_name or settings.ASR_PROVIDER

    if provider == "openai":
        return OpenAIWhisperProvider()
    elif provider == "groq":
        return GroqWhisperProvider()
    elif provider == "mock":
        return MockASRProvider()
    else:
        # Default fallback: if keys are present use OpenAI/Groq, else Mock
        if settings.GROQ_API_KEY:
            return GroqWhisperProvider()
        elif settings.OPENAI_API_KEY:
            return OpenAIWhisperProvider()
        return MockASRProvider()
