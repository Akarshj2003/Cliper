import pytest
from app.services.window_generator import CandidateWindowGenerator, CandidateWindow


@pytest.fixture
def sample_word_timestamps():
    """
    Generate synthetic transcript words over 120 seconds with sentences and pauses.
    """
    words = []
    current_time = 0.0

    sentences = [
        "Welcome to the ultimate podcast on neuroscience.",  # ~3.0s
        "Have you ever wondered why social media is so addictive?",  # ~4.0s
        "It turns out that dopamine is not about pleasure at all, but anticipation.",  # ~5.5s
        "When you expect a reward, your brain releases a massive spike of dopamine.",  # ~5.0s
        "And so you keep scrolling for hours.",  # connector start
        "Here is the single most important rule: do the hardest task first thing in the morning.",  # ~6.5s
        "If you do that, your dopamine baseline resets completely.",  # ~4.0s
        "You will feel incredible focus and energy throughout the day.",  # ~4.5s
        "Most people never figure this out and stay trapped forever.",  # ~4.0s
        "Thank you for watching, and remember to subscribe for more insights.",  # ~4.5s
    ]

    for sentence in sentences:
        tokens = sentence.split()
        for i, token in enumerate(tokens):
            start = round(current_time, 2)
            duration = 0.35
            end = round(start + duration, 2)
            words.append({
                "word": token,
                "start": start,
                "end": end,
                "probability": 0.99
            })
            current_time = end + 0.08  # small inter-word gap

        # Add pause after each sentence (0.6s > 0.4s pause threshold)
        current_time += 0.6

    return words


def test_window_duration_constraints(sample_word_timestamps):
    generator = CandidateWindowGenerator(min_duration_s=20.0, max_duration_s=90.0)
    windows = generator.generate_windows(sample_word_timestamps)

    assert len(windows) > 0, "Should generate candidate windows"
    for w in windows:
        assert 20.0 <= w.duration_s <= 90.0, f"Window duration {w.duration_s}s must be between 20s and 90s"
        assert w.end_s > w.start_s
        assert len(w.text) > 0


def test_sentence_and_pause_snapping(sample_word_timestamps):
    generator = CandidateWindowGenerator(min_duration_s=20.0, max_duration_s=90.0)
    windows = generator.generate_windows(sample_word_timestamps)

    for w in windows:
        # Check that window start starts at a clean capitalized word or sentence boundary
        first_char = w.text.strip()[0]
        assert first_char.isupper() or first_char in ('"', "'"), f"Window should start cleanly: '{w.text[:20]}'"

        # Check that window end ends with punctuation or natural pause
        last_char = w.text.strip()[-1]
        assert last_char in (".", "!", "?", ",", '"', "'"), f"Window should end at punctuation: '{w.text[-20:]}'"


def test_mid_thought_connector_rejection(sample_word_timestamps):
    generator = CandidateWindowGenerator(min_duration_s=20.0, max_duration_s=90.0)
    windows = generator.generate_windows(sample_word_timestamps)

    banned_starts = ["and", "so", "but", "or", "because"]
    for w in windows:
        first_word = w.text.strip().split()[0].lower().rstrip(",.!?")
        # Ensure windows do not start with a dangling mid-thought connector
        assert first_word not in banned_starts, f"Window started with banned mid-thought connector: {first_word}"


def test_short_transcript_handling():
    short_words = [
        {"word": "Hello", "start": 0.0, "end": 0.5, "probability": 0.99},
        {"word": "world.", "start": 0.6, "end": 1.0, "probability": 0.99},
    ]
    generator = CandidateWindowGenerator(min_duration_s=20.0, max_duration_s=90.0)
    windows = generator.generate_windows(short_words)
    # Under 20s audio should return empty or gracefully handled list without crashing
    assert isinstance(windows, list)
    assert len(windows) == 0


def test_overlap_and_candidate_coverage(sample_word_timestamps):
    generator = CandidateWindowGenerator(min_duration_s=20.0, max_duration_s=90.0, overlap_step_s=15.0)
    windows = generator.generate_windows(sample_word_timestamps)

    # In a multi-minute video, multiple overlapping candidate windows should be discovered
    assert len(windows) >= 2
    # Check that candidate start times advance progressively
    starts = [w.start_s for w in windows]
    assert starts == sorted(starts)
