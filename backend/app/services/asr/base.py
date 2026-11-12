from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class WordTimestamp:
    word: str
    start: float  # seconds
    end: float    # seconds
    probability: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ASRResult:
    words: List[WordTimestamp]
    text: str
    language: str = "en"
    duration_s: float = 0.0
    version: str = "whisper-base-v1"

    def words_as_dict_list(self) -> List[Dict[str, Any]]:
        return [w.to_dict() for w in self.words]


class BaseASRProvider(ABC):
    @abstractmethod
    async def transcribe(
        self, audio_path: str, language: Optional[str] = None
    ) -> ASRResult:
        """
        Transcribe audio file into word-level timestamps.
        Must return ASRResult with individual words, start/end timestamps, and full text.
        """
        pass
