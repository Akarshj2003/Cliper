import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class CandidateWindow:
    start_s: float
    end_s: float
    duration_s: float
    text: str
    words: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_s": self.start_s,
            "end_s": self.end_s,
            "duration_s": self.duration_s,
            "text": self.text,
            "word_count": len(self.words),
        }


class CandidateWindowGenerator:
    """
    Stage 3: Candidate Window Generator
    Splits word-level transcripts into 20-90s candidate moments,
    snapping boundaries to sentence endings and pauses >= 0.4s,
    and filtering mid-thought beginnings.
    """
    def __init__(
        self,
        min_duration_s: float = 20.0,
        max_duration_s: float = 90.0,
        pause_threshold_s: float = 0.4,
        overlap_step_s: float = 15.0,
    ):
        self.min_duration_s = min_duration_s
        self.max_duration_s = max_duration_s
        self.pause_threshold_s = pause_threshold_s
        self.overlap_step_s = overlap_step_s
        self.banned_starters = {
            "and", "so", "but", "or", "because", "plus", "also", "then"
        }

    def _is_sentence_boundary(self, word: str) -> bool:
        """Check if a word ends with terminal punctuation."""
        return bool(re.search(r"[.!?][\"']?$", word.strip()))

    def _is_mid_thought(self, word: str) -> bool:
        """Check if a word is a mid-thought conjunction."""
        cleaned = re.sub(r"[^\w]", "", word).lower()
        return cleaned in self.banned_starters

    def generate_windows(
        self, words: List[Dict[str, Any]]
    ) -> List[CandidateWindow]:
        if not words:
            return []

        total_duration = words[-1].get("end", 0.0) - words[0].get("start", 0.0)
        if total_duration < self.min_duration_s:
            return []

        # Step 1: Identify all natural boundary split indices
        # A boundary index `i` means word `i` is the end of a sentence/pause segment
        # and word `i + 1` starts a new sentence/pause segment.
        boundary_indices = [0]
        for i in range(len(words)):
            w = words[i]
            is_punct = self._is_sentence_boundary(w.get("word", ""))
            
            # Check pause to next word
            is_pause = False
            if i < len(words) - 1:
                next_start = words[i + 1].get("start", 0.0)
                curr_end = w.get("end", 0.0)
                if (next_start - curr_end) >= self.pause_threshold_s:
                    is_pause = True

            if (is_punct or is_pause) and i < len(words) - 1:
                boundary_indices.append(i + 1)

        # Include the very last word index + 1 as terminating boundary
        if boundary_indices[-1] != len(words):
            boundary_indices.append(len(words))

        candidate_windows: List[CandidateWindow] = []
        last_window_start_time = -999.0

        # Step 2: Form candidate windows between boundaries
        for b_idx in range(len(boundary_indices) - 1):
            start_word_idx = boundary_indices[b_idx]
            if start_word_idx >= len(words):
                continue

            first_word_str = words[start_word_idx].get("word", "").strip()

            # Filter out windows that start mid-thought
            if self._is_mid_thought(first_word_str):
                continue

            start_time = float(words[start_word_idx].get("start", 0.0))

            # Respect overlap stepping
            if (start_time - last_window_start_time) < (self.overlap_step_s * 0.5):
                continue

            # Search forward for best matching boundary
            best_end_idx = None
            best_duration = 0.0

            for end_b_idx in range(b_idx + 1, len(boundary_indices)):
                end_word_idx = boundary_indices[end_b_idx]
                if end_word_idx <= start_word_idx:
                    continue

                candidate_end_time = float(words[end_word_idx - 1].get("end", 0.0))
                duration = candidate_end_time - start_time

                if duration > self.max_duration_s:
                    break  # Exceeded max duration limit

                if duration >= self.min_duration_s:
                    # Found a valid candidate window
                    window_words = words[start_word_idx:end_word_idx]
                    window_text = " ".join([w.get("word", "") for w in window_words]).strip()

                    candidate_windows.append(CandidateWindow(
                        start_s=round(start_time, 2),
                        end_s=round(candidate_end_time, 2),
                        duration_s=round(duration, 2),
                        text=window_text,
                        words=window_words
                    ))
                    best_duration = duration
                    last_window_start_time = start_time

                    # Only take 1 or 2 best lengths per starting hook to avoid over-clutter
                    if duration >= 45.0:
                        break

        # Remove duplicate or nearly identical windows (within 1 second)
        deduped: List[CandidateWindow] = []
        for cw in candidate_windows:
            is_dup = False
            for existing in deduped:
                if abs(existing.start_s - cw.start_s) < 1.0 and abs(existing.end_s - cw.end_s) < 1.0:
                    is_dup = True
                    break
            if not is_dup:
                deduped.append(cw)

        return deduped


def get_candidate_window_generator() -> CandidateWindowGenerator:
    return CandidateWindowGenerator()
