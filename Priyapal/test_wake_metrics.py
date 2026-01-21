from wake_word_enhancement import WakeWordDetector

detector = WakeWordDetector()

samples = [
    "hey vox",
    "hey vox open chrome",
    "hey vox open edge",
    "this should not trigger",
    "vox, what's the time",
]

for s in samples:
    detected, stripped = detector.detect_and_strip_wake(s)
    print(f"INPUT: {s!r} -> detected={detected}, stripped={stripped!r}")

# Print metrics summary
detector.log_metrics("[wake-test] ")
