"""
wake_word_enhancement.py

Lightweight wake-word helper for a VoxMind-like assistant.

Responsibilities
----------------
- Decide WHEN to wake the assistant, not WHAT the command is.
- Provide a simple API to:
  - Check text transcripts for wake words ("hey vox", "vox").
  - (Optionally) process audio chunks for local wake detection.
- Handle multiple wake words and basic sensitivity/debounce logic.

Notes
-----
- This module is text/audio logic ONLY.
- It does NOT call command_parser or execute any actions.
- main.py (or another orchestrator) should:
  - Use this to decide when to run ASR and parse_command().
  - Pass the full ASR text into command_parser.parse_command()
    AFTER a wake word has been detected.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import List, Tuple, Optional


# Default wake phrases for the assistant
DEFAULT_WAKE_PHRASES: List[str] = [
    "hey vox",
    "vox",
    # you can add more, e.g. "hey voxmind", "voxmind"
]


@dataclass
class WakeConfig:
    """
    Configuration for wake-word detection.

    Attributes
    ----------
    phrases:
        List of wake phrases to detect (lowercased).
    sensitivity:
        0.0–1.0, higher is more sensitive. For text-based detection,
        this can be used to gate approximate matching (e.g., fuzzy match),
        but current implementation uses it mainly as a placeholder.
    debounce_seconds:
        Minimum number of seconds between two wake detections to avoid
        repeated triggers in quick succession.
    """

    phrases: List[str]
    sensitivity: float = 0.5
    debounce_seconds: float = 1.0


class WakeWordDetector:
    """
    Simple wake-word detector supporting text-based and stub audio detection.

    Typical usage (text-based):
    ---------------------------
    detector = WakeWordDetector()
    if detector.detect_in_text(transcript):
        # wake-word detected, pass transcript to command_parser

    For audio-based detection, implement detect_in_audio_chunk() later
    with a real wake-word engine (e.g., Porcupine) and reuse the same API.
    """

    def __init__(self, config: Optional[WakeConfig] = None) -> None:
        if config is None:
            config = WakeConfig(phrases=[p.lower() for p in DEFAULT_WAKE_PHRASES])
        else:
            config.phrases = [p.lower() for p in config.phrases]

        self.config = config
        self._last_trigger_time: float = 0.0

        # Precompile phrase regexes for performance
        self._phrase_patterns: List[Tuple[str, re.Pattern[str]]] = []
        for phrase in self.config.phrases:
            # word boundary-ish match, allowing punctuation after phrase
            escaped = re.escape(phrase)
            pattern = re.compile(r"\b" + escaped + r"\b", re.I)
            self._phrase_patterns.append((phrase, pattern))

    # --------------------------------------------------------
    # Public API
    # --------------------------------------------------------

    def set_sensitivity(self, level: float) -> None:
        """
        Set sensitivity between 0.0 and 1.0.

        Current implementation keeps exact-match semantics for text but
        stores this for future approximate/fuzzy matching.
        """
        level = max(0.0, min(1.0, level))
        self.config.sensitivity = level

    def reset_debounce(self) -> None:
        """
        Reset debounce timer (for tests or manual control).
        """
        self._last_trigger_time = 0.0

    def detect_in_text(self, text: str) -> bool:
        """
        Return True if any wake phrase is detected in the text AND
        debounce interval has passed.

        This is meant for ASR transcripts, e.g., "hey vox open the browser".
        """
        if not text:
            return False

        norm = self._normalize_text(text)

        if not self._passed_debounce():
            return False

        for phrase, pattern in self._phrase_patterns:
            if pattern.search(norm):
                self._mark_trigger()
                return True

        return False

    def detect_and_strip_wake(self, text: str) -> Tuple[bool, str]:
        """
        Detect wake word and return (detected: bool, stripped_text: str).

        If a wake phrase is found near the start of the text, it is removed
        and the remaining text is returned. Otherwise, text is returned unchanged.

        This mirrors what command_parser.parse_command() expects when it strips
        "jarvis"/"hey jarvis" internally, but now generalized for "hey vox"/"vox".
        """
        if not text:
            return False, ""

        norm = text.strip()
        low = norm.lower()

        if not self._passed_debounce():
            return False, norm

        # Find the first wake phrase near the start
        for phrase, pattern in self._phrase_patterns:
            m = pattern.search(low)
            if m and m.start() <= 5:
                # strip up to end of phrase
                end = m.end()
                stripped = norm[end:].lstrip(" ,.:")
                self._mark_trigger()
                return True, stripped

        return False, norm

    def detect_in_audio_chunk(self, audio_chunk: bytes) -> bool:
        """
        Stub for audio-based wake detection.

        In future, plug in Porcupine or similar here. For now, always False
        to avoid accidental triggers.

        main.py can choose to use this instead of text-based detection if/when
        a real audio detector is added.
        """
        _ = audio_chunk  # unused
        # TODO: integrate real wake-word engine here.
        return False

    # --------------------------------------------------------
    # Internal helpers
    # --------------------------------------------------------

    def _normalize_text(self, text: str) -> str:
        text = text.strip().lower()
        text = re.sub(r"\s+", " ", text)
        return text

    def _passed_debounce(self) -> bool:
        now = time.time()
        if now - self._last_trigger_time >= self.config.debounce_seconds:
            return True
        return False

    def _mark_trigger(self) -> None:
        self._last_trigger_time = time.time()
