"""Non-interactive test of VoxMind main loop with NLP parser."""
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Import the main module components
from main import parse_command, execute_command

def test_main_loop_integration():
    print("="*60)
    print("VoxMind Main Loop Integration Test")
    print("="*60)
    
    test_commands = [
        # Browser commands
        "open browser",
        "launch chrome",
        
        # Time queries
        "what time is it",
        "what's the date today",
        
        # Search commands
        "search for python tutorials",
        "what is machine learning",
        "google the weather in New York",
        
        # Volume commands
        "mute",
        "turn volume to 75",
        "make it louder",
        "decrease volume",
        
        # App control
        "open notepad",
        "close chrome",
        
        # Help
        "help",
        "what can you do",
        
        # Shutdown (will be parsed but not executed for safety)
        "shutdown",
    ]
    
    print(f"\nTesting {len(test_commands)} commands:\n")
    print(f"{'Command':<35} | {'Intent':<20} | {'Method':<6} | {'Conf':<5}")
    print("-" * 80)
    
    for cmd_text in test_commands:
        parsed = parse_command(cmd_text)
        
        command = parsed.get('command', 'unknown')
        method = parsed.get('method', '?')
        confidence = parsed.get('confidence', 0)
        params = parsed.get('params', {})
        
        conf_str = f"{confidence:.0%}" if method == 'nlp' else "N/A"
        
        # Show extracted params for search
        extra = ""
        if command == 'search' and 'query' in params:
            extra = f" → '{params['query'][:20]}...'" if len(params.get('query', '')) > 20 else f" → '{params.get('query', '')}'"
        
        # Get response (but don't actually execute system commands or app commands)
        if command not in ['system_power', 'control_app']:
            response = execute_command(parsed)
        else:
            response = "[Skipped for safety]"
        
        print(f"{cmd_text:<35} | {command:<20} | {method:<6} | {conf_str:<5}{extra}")
    
    print("\n" + "="*60)
    print("Integration test complete!")
    print("="*60)

if __name__ == "__main__":
    test_main_loop_integration()
