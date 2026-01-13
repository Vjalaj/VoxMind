"""Test script for enhanced command parser with logging."""
import logging
import sys
import os

# Add the yash directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from command_parser import parse_command, get_supported_commands

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_enhanced_parser():
    """Test the enhanced command parser with various inputs."""
    
    test_cases = [
        # Browser commands
        "open browser",
        "launch chrome", 
        "start firefox",
        "go online",
        "open google chrome",
        
        # Time queries
        "what time is it",
        "current time",
        "what's the date",
        "tell me the time",
        "what day is it",
        
        # Search queries
        "search for python programming",
        "google machine learning",
        "what is artificial intelligence",
        "find restaurants near me",
        "lookup weather forecast",
        
        # Music commands
        "play music",
        "start music", 
        "play a song",
        "next track",
        "pause music",
        "stop music",
        
        # System commands
        "shutdown computer",
        "restart system",
        "sleep mode",
        "lock screen",
        
        # Volume commands
        "mute",
        "volume up",
        "turn volume to 50",
        "louder",
        "quieter",
        
        # App control
        "open notepad",
        "launch vscode",
        "close chrome",
        "start calculator",
        
        # Help commands
        "help",
        "what can you do",
        "who are you",
        
        # Wake word tests
        "jarvis open browser",
        "hey jarvis what time is it",
        "ok jarvis search for cats",
        
        # Edge cases
        "unknown command xyz",
        "",
        "just some random text"
    ]
    
    print("=== ENHANCED COMMAND PARSER TESTS ===\n")
    
    for i, test_input in enumerate(test_cases, 1):
        print(f"Test {i}: '{test_input}'")
        result = parse_command(test_input, log_matches=True)
        print(f"Result: {result}")
        print("-" * 50)
    
    print("\n=== SUPPORTED COMMANDS ===")
    commands = get_supported_commands()
    for cmd_type, examples in commands.items():
        print(f"{cmd_type}: {examples}")

if __name__ == "__main__":
    test_enhanced_parser()