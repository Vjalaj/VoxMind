"""Test wake word detector."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from wake_word_detector import listen_for_wake_word

print("=== Wake Word Detector Test ===")
print("Wake word: 'Hey Vox'")
print("Alternatives: 'Vox', 'hey box', 'a vox'")
print("\nListening for wake word (or press Enter for keyboard fallback)...\n")

for i in range(5):
    print(f"Attempt {i+1}/5...")
    detected = listen_for_wake_word()
    if detected:
        print("✅ Wake word detected!")
    else:
        print("❌ Wake word not detected")
    print()
