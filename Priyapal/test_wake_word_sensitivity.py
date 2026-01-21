# tests/test_wake_word_sensitivity.py

import pathlib
import statistics

import pytest

from wake_word_enhancement import WakeWordDetector, WakeConfig


DATA_DIR = pathlib.Path(__file__).parent / "data"


def load_lines(name: str):
    path = DATA_DIR / name
    with path.open("r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


SENSITIVITY_LEVELS = [0.2, 0.5, 0.8]


@pytest.fixture(scope="module")
def positive_samples():
    return load_lines("wake_positive.txt")


@pytest.fixture(scope="module")
def negative_samples():
    return load_lines("wake_negative.txt")


def make_detector(sensitivity: float) -> WakeWordDetector:
    config = WakeConfig(
        primary_phrases=["hey vox", "ok vox", "hey voxmind"],
        secondary_phrases=["vox"],
        sensitivity=sensitivity,
        debounce_seconds=0.0,  # disable debounce for offline evaluation
        primary_fuzzy_threshold=0.8,
        secondary_fuzzy_threshold=0.9,
    )
    return WakeWordDetector(config=config)


@pytest.mark.parametrize("sensitivity", SENSITIVITY_LEVELS)
def test_tpr_far_vs_sensitivity(positive_samples, negative_samples, sensitivity):
    detector = make_detector(sensitivity)
    detector.reset_metrics()

    # --- True positive rate (TPR) ---
    tp = 0
    for text in positive_samples:
        detected, _ = detector.detect_and_strip_wake(text)
        if detected:
            tp += 1
    tpr = tp / len(positive_samples)

    # --- False accept rate (FAR) on this small text set ---
    fp = 0
    for text in negative_samples:
        detected, _ = detector.detect_and_strip_wake(text)
        if detected:
            fp += 1
    far = fp / len(negative_samples)

    # Print metrics for debugging runs
    print(
        f"[wake-eval] sens={sensitivity:.2f} "
        f"TPR={tpr:.3f} FAR={far:.3f} metrics={detector.metrics.to_dict()}"
    )

    # Example expectations (tune these as you iterate):
    if sensitivity <= 0.3:
        # Very conservative: may miss some positives but should be almost no false positives
        assert far <= 0.10
    elif 0.3 < sensitivity < 0.8:
        # Balanced: require decent TPR with still low FAR
        assert tpr >= 0.7
        assert far <= 0.30
    else:
        # High sensitivity: higher TPR allowed at cost of some FAR, but still bounded
        assert tpr >= 0.9
        assert far <= 0.50


@pytest.mark.parametrize("sensitivity", [0.2, 0.8])
def test_primary_vs_secondary_behavior(positive_samples, sensitivity):
    """
    Check that at low sensitivity, long primary phrases work better than
    short 'vox', and at high sensitivity, both are usable.
    """
    # Separate “hey vox*” vs “vox ...”
    primary_texts = [s for s in positive_samples if s.lower().startswith(("hey vox", "ok vox", "hey voxmind"))]
    secondary_texts = [s for s in positive_samples if s.lower().startswith("vox")]

    detector = make_detector(sensitivity)
    detector.reset_metrics()

    # Evaluate primary
    primary_hits = sum(detector.detect_and_strip_wake(t)[0] for t in primary_texts)
    primary_tpr = primary_hits / max(1, len(primary_texts))

    # Evaluate secondary
    secondary_hits = sum(detector.detect_and_strip_wake(t)[0] for t in secondary_texts)
    secondary_tpr = secondary_hits / max(1, len(secondary_texts))

    print(
        f"[wake-primary-secondary] sens={sensitivity:.2f} "
        f"primary_TPR={primary_tpr:.3f} secondary_TPR={secondary_tpr:.3f}"
    )

    if sensitivity <= 0.3:
        # Low sensitivity: primary should be clearly more reliable than 'vox'
        assert primary_tpr >= secondary_tpr
        assert primary_tpr >= 0.6
    else:
        # High sensitivity: both should be good
        assert primary_tpr >= 0.8
        assert secondary_tpr >= 0.7
