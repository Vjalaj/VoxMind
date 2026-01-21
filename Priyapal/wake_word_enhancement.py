"""
wake_word_enhancement.py

Wake-word helper for a VoxMind-like assistant.

Design references
-----------------
- Assistants like Google Assistant use fixed wake phrases ("Hey Google",
  "Ok Google") that are long enough and phonetically rich to reduce
  false positives while being easy to say.[web:232][web:239]
- On-device wake-word engines (e.g., Porcupine) emphasize:
  - Choosing 2–4 syllable phrases.
  - Tuning sensitivity to balance false accepts vs false rejects.[web:249][web:259][web:261]
- ChatGPT-style assistants benefit from local wake detection for privacy
  and latency with natural phrases like "Hey ChatGPT".[web:234][web:249]

Goals
-----
- Provide a configurable wake-word detector for text transcripts.
- Support primary ("hey vox", "ok vox", "hey voxmind") and secondary
  ("vox") wake phrases, with sensitivity-aware fuzzy matching.
- Expose:
  - sensitivity (0.0–1.0)
  - debounce
  - configurable fuzzy thresholds
  - simple metrics and logging for QA.
- Keep implementation side-effect free and ready for future audio
  integration via detect_in_audio_chunk().
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field, asdict
from typing import List, Tuple, Optional, Dict, Any
from difflib import SequenceMatcher


# Primary and secondary wake phrases.
PRIMARY_WAKE_PHRASES: List[str] = [
    "hey vox",
    "ok vox",
    "hey voxmind",
]

SECONDARY_WAKE_PHRASES: List[str] = [
    "vox",
]


@dataclass
class WakeMetrics:
    """
    Metrics to support QA:

    - total_text_checks: number of detect_in_text / detect_and_strip_wake calls.
    - triggers: number of successful detections.
    - suppressed_by_debounce: detections that were ignored because
      debounce interval had not passed.
    - fuzzy_matches: detections relying on approximate matching at
      higher sensitivity.[web:249][web:259]
    """

    total_text_checks: int = 0
    triggers: int = 0
    suppressed_by_debounce: int = 0
    fuzzy_matches: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Return metrics as a plain dict (useful for tests or logging)."""
        return asdict(self)


@dataclass
class WakeConfig:
    """
    Configuration for wake-word detection.

    Attributes
    ----------
    primary_phrases:
        Main wake phrases (lowercased), e.g. "hey vox", "ok vox", "hey voxmind".
    secondary_phrases:
        Short forms like "vox" that are more prone to false positives.[web:239][web:249]
    sensitivity:
        0.0–1.0: Higher is more sensitive.
        - Low: rely mostly on primary phrases, no fuzzy matches.
        - Medium: allow secondary phrases carefully.
        - High: allow fuzzy matches and more liberal detection.[web:259]
    debounce_seconds:
        Minimum seconds between wake detections.
    primary_fuzzy_threshold:
        Similarity threshold (0–1) for fuzzy matching primary phrases.
    secondary_fuzzy_threshold:
        Similarity threshold (0–1) for fuzzy matching secondary phrases.
        Typically higher than primary to avoid false accepts from very
        short words.[web:239][web:249]
    """

    primary_phrases: List[str]
    secondary_phrases: List[str] = field(default_factory=list)
    sensitivity: float = 0.5
    debounce_seconds: float = 1.0
    primary_fuzzy_threshold: float = 0.8
    secondary_fuzzy_threshold: float = 0.9


class WakeWordDetector:
    """
    Wake-word detector for text transcripts.

    Features
    --------
    - Primary/secondary phrases.
    - Sensitivity-aware fuzzy matching with configurable thresholds.
    - Debounce to avoid repeated triggers.
    - Metrics and logging for QA.

    API
    ---
    - detect_in_text(text) -> bool
    - detect_and_strip_wake(text) -> (bool, stripped_text)
    - detect_in_audio_chunk(audio_chunk) -> bool  (stub for future engines)
    - metrics, metrics.to_dict()
    - log_metrics(prefix: str = "") -> None
    """

    def __init__(self, config: Optional[WakeConfig] = None) -> None:
        if config is None:
            config = WakeConfig(
                primary_phrases=[p.lower() for p in PRIMARY_WAKE_PHRASES],
                secondary_phrases=[p.lower() for p in SECONDARY_WAKE_PHRASES],
            )
        else:
            config.primary_phrases = [p.lower() for p in config.primary_phrases]
            config.secondary_phrases = [p.lower() for p in config.secondary_phrases]

        self.config = config
        self._last_trigger_time: float = 0.0
        self.metrics = WakeMetrics()

        # Precompile patterns
        self._primary_patterns: List[Tuple[str, re.Pattern[str]]] = []
        self._secondary_patterns: List[Tuple[str, re.Pattern[str]]] = []

        for phrase in self.config.primary_phrases:
            escaped = re.escape(phrase)
            pattern = re.compile(r"\b" + escaped + r"\b", re.I)
            self._primary_patterns.append((phrase, pattern))

        for phrase in self.config.secondary_phrases:
            escaped = re.escape(phrase)
            pattern = re.compile(r"\b" + escaped + r"\b", re.I)
            self._secondary_patterns.append((phrase, pattern))

    # --------------------------------------------------------
    # Public API
    # --------------------------------------------------------

    def set_sensitivity(self, level: float) -> None:
        """
        Set detection sensitivity between 0.0 and 1.0.[web:259]

        Guidance:
        - 0.0–0.3: low sensitivity (primary phrases only, no fuzzy).
        - 0.4–0.7: balanced.
        - 0.8–1.0: high sensitivity (enable fuzzy matching).
        """
        level = max(0.0, min(1.0, level))
        self.config.sensitivity = level

    def set_fuzzy_thresholds(self, primary: float, secondary: float) -> None:
        """
        Configure fuzzy thresholds (0.0–1.0) for primary and secondary phrases.[web:249]

        Typical values:
        - primary: 0.75–0.85
        - secondary: 0.85–0.95
        """
        self.config.primary_fuzzy_threshold = max(0.0, min(1.0, primary))
        self.config.secondary_fuzzy_threshold = max(0.0, min(1.0, secondary))

    def reset_debounce(self) -> None:
        """Reset debounce timer (useful for tests)."""
        self._last_trigger_time = 0.0

    def reset_metrics(self) -> None:
        """Reset QA metrics."""
        self.metrics = WakeMetrics()

    def log_metrics(self, prefix: str = "") -> None:
        """
        Print metrics in a compact form for debugging/QA runs.

        Example:
            detector.log_metrics("[wake-test] ")
        """
        data = self.metrics.to_dict()
        if prefix:
            print(prefix, end="")
        print(
            f"WakeMetrics(total_text_checks={data['total_text_checks']}, "
            f"triggers={data['triggers']}, "
            f"suppressed_by_debounce={data['suppressed_by_debounce']}, "
            f"fuzzy_matches={data['fuzzy_matches']})"
        )

    def detect_in_text(self, text: str) -> bool:
        """
        Return True if any wake phrase is detected in the text AND
        debounce interval has passed.
        """
        if not text:
            return False

        self.metrics.total_text_checks += 1
        norm = self._normalize_text(text)

        if not self._passed_debounce():
            self.metrics.suppressed_by_debounce += 1
            return False

        # Primary phrases first
        if self._match_any_phrase(norm, primary=True):
            self._mark_trigger()
            return True

        # Secondary phrases (short forms) only if sensitivity is not too low
        if self.config.sensitivity >= 0.4 and self._match_any_phrase(norm, primary=False):
            self._mark_trigger()
            return True

        return False

    def detect_and_strip_wake(self, text: str) -> Tuple[bool, str]:
        """
        Detect wake word and return (detected: bool, stripped_text: str).

        If a wake phrase is found near the start, remove it and return
        the remaining text as the candidate command. Otherwise, return
        the original text unchanged.
        """
        if not text:
            return False, ""

        self.metrics.total_text_checks += 1
        raw = text.strip()
        low = raw.lower()

        if not self._passed_debounce():
            self.metrics.suppressed_by_debounce += 1
            return False, raw

        # Primary phrases near the start
        m, phrase_len, fuzzy_used = self._find_phrase_near_start(
            low,
            self._primary_patterns,
            self.config.primary_fuzzy_threshold,
        )
        if m:
            end = m.start() + phrase_len
            stripped = raw[end:].lstrip(" ,.:")
            self._mark_trigger(fuzzy_used=fuzzy_used)
            return True, stripped

        # Secondary phrases (short forms) near the start at moderate+ sensitivity
        if self.config.sensitivity >= 0.4:
            m2, phrase_len2, fuzzy_used2 = self._find_phrase_near_start(
                low,
                self._secondary_patterns,
                self.config.secondary_fuzzy_threshold,
            )
            if m2:
                end = m2.start() + phrase_len2
                stripped = raw[end:].lstrip(" ,.:")
                self._mark_trigger(fuzzy_used=fuzzy_used2)
                return True, stripped

        return False, raw

    def detect_in_audio_chunk(self, audio_chunk: bytes) -> bool:
        """
        Stub for audio-based wake detection.

        Future integration:
        - Attach an engine like Porcupine, feed it audio frames, and map
          its sensitivity parameter to config.sensitivity and fuzzy
          thresholds.[web:249][web:251][web:261]
        """
        _ = audio_chunk
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
        return (now - self._last_trigger_time) >= self.config.debounce_seconds

    def _mark_trigger(self, fuzzy_used: bool = False) -> None:
        self._last_trigger_time = time.time()
        self.metrics.triggers += 1
        if fuzzy_used:
            self.metrics.fuzzy_matches += 1

    def _match_any_phrase(self, norm: str, primary: bool) -> bool:
        """
        Check if any primary/secondary phrase matches in the text.
        Uses exact boundary match first, then fuzzy at high sensitivity.
        """
        patterns = self._primary_patterns if primary else self._secondary_patterns

        # Exact match
        for _, pattern in patterns:
            if pattern.search(norm):
                return True

        # Fuzzy at high sensitivity only
        if self.config.sensitivity >= 0.8:
            threshold = (
                self.config.primary_fuzzy_threshold
                if primary
                else self.config.secondary_fuzzy_threshold
            )
            for phrase, _ in patterns:
                if self._fuzzy_contains(norm, phrase, threshold=threshold):
                    return True

        return False

    def _find_phrase_near_start(
        self,
        low_text: str,
        patterns: List[Tuple[str, re.Pattern[str]]],
        threshold: float,
    ) -> Tuple[Optional[re.Match[str]], int, bool]:
        """
        Find a phrase near the start (index <= 5) via exact or fuzzy detection.

        Returns (match_obj, phrase_length, fuzzy_used).
        """
        # Exact match
        for phrase, pattern in patterns:
            m = pattern.search(low_text)
            if m and m.start() <= 5:
                return m, len(phrase), False

        # Fuzzy at high sensitivity
        if self.config.sensitivity >= 0.8:
            for phrase, _ in patterns:
                if self._fuzzy_startswith(low_text, phrase, threshold=threshold):
                    class _DummyMatch:
                        def __init__(self, start: int) -> None:
                            self._start = start

                        def start(self) -> int:
                            return self._start

                    return _DummyMatch(0), len(phrase), True

        return None, 0, False

    def _fuzzy_contains(self, text: str, phrase: str, threshold: float) -> bool:
        """
        Check whether phrase is approximately contained in text.
        Uses a sliding window and SequenceMatcher.[web:249]
        """
        if phrase in text:
            return True

        n = len(phrase)
        for i in range(max(1, len(text) - n + 1)):
            window = text[i:i + n + 2]
            ratio = SequenceMatcher(None, window, phrase).ratio()
            if ratio >= threshold:
                return True
        return False

    def _fuzzy_startswith(self, text: str, phrase: str, threshold: float) -> bool:
        """
        Fuzzy "starts with" check for phrase at the beginning of text,
        useful for ASR variations like "hey box" vs "hey vox".[web:249]
        """
        n = len(phrase)
        window = text[: n + 2]
        ratio = SequenceMatcher(None, window, phrase).ratio()
        return ratio >= threshold
