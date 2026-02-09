"""Debug NLP confidence scores for various commands."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from nlp_command_parser import NLPCommandParser, NLP_AVAILABLE

if not NLP_AVAILABLE:
    print("NLP not available!")
    sys.exit(1)

parser = NLPCommandParser()

test_phrases = [
    "search for python tutorials",
    "what is machine learning",
    "google the weather",
    "find restaurants nearby",
    "look up information about AI",
    "open browser",
    "what time is it",
    "mute",
    "help",
]

print("Intent Confidence Analysis")
print("="*70)
print(f"{'Phrase':<35} | {'Best Intent':<15} | {'Score':<6}")
print("-"*70)

for phrase in test_phrases:
    intent, confidence = parser._classify_with_nlp(phrase, threshold=0.0)  # No threshold for debug
    status = "✓" if confidence >= 0.6 else "✗"
    print(f"{status} {phrase:<33} | {intent:<15} | {confidence:.2%}")

print("\n" + "="*70)
print("✓ = passes 0.6 threshold, ✗ = would fall back to basic parser")
