"""Test script for NLP command parser enhancements."""
import logging
import sys
import os
import time

# Add the Tejas directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("NLPTest")

try:
    from nlp_command_parser import parse_command_nlp, get_nlp_status, NLPCommandParser
except ImportError as e:
    logger.error(f"Could not import nlp_command_parser: {e}")
    sys.exit(1)

def run_tests():
    print("="*60)
    print("NLP PARSER ENHANCEMENT TEST")
    print("="*60)

    # Check status
    status = get_nlp_status()
    print(f"NLP Available: {status['nlp_available']}")
    
    if not status['nlp_available']:
        print("Skipping tests because sentence-transformers is not available.")
        return

    # Trigger model load
    print("\nInitializing Parser (First run should load model)...")
    start_time = time.time()
    # This triggers the singleton initialization
    parser = NLPCommandParser()
    print(f"Initialization took: {time.time() - start_time:.4f}s")
    
    # Verify singleton
    print("\nVerifying Singleton Pattern...")
    start_time = time.time()
    parser2 = NLPCommandParser()
    print(f"Second instantiation took: {time.time() - start_time:.4f}s")
    if parser is parser2:
        print("✓ SUCCESS: Singleton pattern working (instances are storing the same object)")
    else:
        print("✗ FAILURE: Singleton pattern failed")

    test_cases = [
        # Wake word tests
        ("vox open chrome", "open_browser"),
        ("hey vox what time is it", "time"),
        ("search for neural networks", "search"),
        
        # Volume tests (Entity Extraction)
        ("turn volume to 50%", "volume"),
        ("mute the sound", "volume"),
        ("make it louder", "volume"),
        ("decrease volume", "volume"),
        
        # App Control
        ("launch notepad", "app_control"),
        ("close spotify", "app_control"),
        
        # Search Entity Extraction
        ("what is the capital of france", "search"),
        ("find python tutorials", "search")
    ]

    print("\nRunning Intent & Entity Extraction Tests:\n")
    print(f"{'Input Command':<35} | {'Intent':<15} | {'Extracted Entities'}")
    print("-" * 80)

    for text, expected_intent in test_cases:
        result = parse_command_nlp(text, use_nlp=True)
        
        intent = result.get("type", "unknown")
        # Filter out standard keys to show just extracted entities
        entities = {k: v for k, v in result.items() if k not in ['type', 'raw', 'confidence', 'method']}
        
        status_icon = "✓" if intent == expected_intent else "✗"
        
        print(f"{status_icon} {text:<33} | {intent:<15} | {entities}")

    print("\n" + "="*60)

if __name__ == "__main__":
    run_tests()
