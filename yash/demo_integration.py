"""Integration example showing enhanced command parser usage in VoxMind system."""
import logging
from typing import Dict, Any

# Configure logging for command parser
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def demo_enhanced_parser():
    """Demonstrate the enhanced command parser capabilities."""
    from command_parser import parse_command, get_supported_commands
    
    print("=== VoxMind Enhanced Command Parser Demo ===\n")
    
    # Show supported commands
    print("Supported Commands:")
    commands = get_supported_commands()
    for cmd_type, examples in commands.items():
        print(f"  {cmd_type}: {examples[0]} (+ {len(examples)-1} more variations)")
    print()
    
    # Interactive demo
    print("Try some commands (type 'quit' to exit):")
    print("Examples: 'open browser', 'what time is it', 'search for AI', 'play music'")
    print()
    
    while True:
        try:
            user_input = input("Command: ").strip()
            if user_input.lower() in ['quit', 'exit', 'stop']:
                break
            
            if not user_input:
                continue
            
            # Parse with logging enabled
            result = parse_command(user_input, log_matches=True)
            
            print(f"Parsed: {result}")
            
            # Show what action would be taken
            action = get_action_description(result)
            print(f"Action: {action}")
            print("-" * 50)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

def get_action_description(parsed_result: Dict[str, Any]) -> str:
    """Convert parsed result to human-readable action description."""
    cmd_type = parsed_result.get('type', 'unknown')
    
    if cmd_type == 'open_browser':
        return "Would open web browser"
    elif cmd_type == 'time':
        return "Would display current time/date"
    elif cmd_type == 'search':
        query = parsed_result.get('query', '')
        return f"Would search for: '{query}'"
    elif cmd_type == 'play_music':
        return "Would start music playback"
    elif cmd_type == 'shutdown':
        return "Would perform system shutdown/restart/sleep"
    elif cmd_type == 'volume':
        return "Would adjust system volume"
    elif cmd_type == 'app_control':
        app = parsed_result.get('app', 'application')
        return f"Would control application: {app}"
    elif cmd_type == 'help':
        return "Would show help information"
    else:
        return "Command not recognized"

def integration_example():
    """Show how to integrate enhanced parser into main VoxMind system."""
    print("\n=== Integration Example ===")
    print("Here's how to use the enhanced parser in main.py:")
    print()
    
    integration_code = '''
# In main.py, replace the basic parser import:
# from yash.command_parser import parse_command

# With enhanced version:
from yash.command_parser import parse_command

# Enable logging to see which patterns match:
import logging
logging.basicConfig(level=logging.INFO)

# In your main loop:
def process_voice_command(audio_text):
    # Parse with enhanced patterns and logging
    parsed = parse_command(audio_text, log_matches=True)
    
    # The result now includes matched_pattern for debugging
    if 'matched_pattern' in parsed:
        print(f"Matched pattern: {parsed['matched_pattern']}")
    
    # Handle the command based on type
    if parsed['type'] == 'open_browser':
        # Your browser opening logic
        pass
    elif parsed['type'] == 'search':
        query = parsed.get('query', '')
        # Your search logic with extracted query
        pass
    # ... handle other command types
    
    return parsed
'''
    
    print(integration_code)

if __name__ == "__main__":
    demo_enhanced_parser()
    integration_example()