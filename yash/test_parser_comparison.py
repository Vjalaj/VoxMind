"""Comprehensive test comparing basic pattern matching vs NLP-enhanced parsing."""
import logging
import sys
import os

# Add the yash directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from command_parser import parse_command
from nlp_command_parser import parse_command_nlp, get_nlp_status

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_parser_comparison():
    """Compare basic pattern matching vs NLP-enhanced parsing."""
    
    # Test cases that might benefit from NLP understanding
    challenging_cases = [
        # Variations and synonyms
        "I want to browse the internet",
        "Can you tell me what time it currently is?",
        "Please find information about machine learning",
        "I'd like to listen to some tunes",
        "Could you please shut down my computer?",
        "Make the sound louder please",
        "I need to open my text editor",
        "What are your available functions?",
        
        # Natural language variations
        "I want to know the current time",
        "Help me search for restaurants nearby",
        "Can you start playing some music?",
        "I need to launch my browser",
        "Please increase the volume",
        
        # Ambiguous cases
        "open something",
        "play something",
        "find stuff",
        "help me out",
        
        # Edge cases
        "time to go online",
        "search and destroy",
        "music to my ears",
    ]
    
    print("=== PARSER COMPARISON TEST ===\n")
    print(f"NLP Status: {get_nlp_status()}\n")
    
    for i, test_input in enumerate(challenging_cases, 1):
        print(f"Test {i}: '{test_input}'")
        
        # Basic pattern matching
        basic_result = parse_command(test_input, log_matches=False)
        print(f"  Basic:  {basic_result['type']}")
        if 'query' in basic_result:
            print(f"          Query: '{basic_result['query']}'")
        
        # NLP-enhanced parsing
        nlp_result = parse_command_nlp(test_input, use_nlp=True, log_matches=False)
        print(f"  NLP:    {nlp_result['type']}")
        if 'confidence' in nlp_result:
            print(f"          Confidence: {nlp_result['confidence']:.3f}")
        if 'query' in nlp_result:
            print(f"          Query: '{nlp_result['query']}'")
        
        # Highlight differences
        if basic_result['type'] != nlp_result['type']:
            print(f"  >>> DIFFERENCE: Basic={basic_result['type']}, NLP={nlp_result['type']}")
        
        print("-" * 60)

def test_performance():
    """Test performance of both parsing methods."""
    import time
    
    test_phrases = [
        "open browser", "what time is it", "search for python",
        "play music", "shutdown computer", "help me"
    ] * 100  # 600 total tests
    
    print("\n=== PERFORMANCE TEST ===")
    
    # Test basic parser
    start_time = time.time()
    for phrase in test_phrases:
        parse_command(phrase)
    basic_time = time.time() - start_time
    
    # Test NLP parser
    start_time = time.time()
    for phrase in test_phrases:
        parse_command_nlp(phrase, use_nlp=True)
    nlp_time = time.time() - start_time
    
    print(f"Basic parser: {basic_time:.3f}s for {len(test_phrases)} phrases")
    print(f"NLP parser:   {nlp_time:.3f}s for {len(test_phrases)} phrases")
    print(f"NLP overhead: {((nlp_time - basic_time) / basic_time * 100):.1f}%")

if __name__ == "__main__":
    test_parser_comparison()
    test_performance()