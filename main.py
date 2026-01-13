"""VoxMind - Voice Assistant Integration"""
import argparse
import sys
import os
from time import sleep
import webbrowser
from datetime import datetime
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

# Import components
from Jalaj.speech_recognition_service import listen_for_command
from yash.wake_word_detector import listen_for_wake_word
from Priyapal.command_parser import parse_command

try:
    from minakshi.text_to_speech import speak_text
except:
    try:
        from yash.text_to_speech import speak_text
    except:
        import pyttsx3
        engine = pyttsx3.init()
        def speak_text(text):
            engine.say(text)
            engine.runAndWait()

def execute_command(parsed):
    """Execute the parsed command and return response."""
    cmd = parsed.get('command', 'unknown')
    params = parsed.get('params', {})
    
    if cmd == 'open_browser':
        browser = params.get('browser')
        webbrowser.open('https://www.google.com')
        return f"Opening {'Chrome' if not browser else browser}"
    
    elif cmd == 'search':
        query = params.get('query', '')
        if query:
            webbrowser.open(f'https://www.google.com/search?q={query}')
            return f"Searching for {query}"
        return "What would you like to search for?"
    
    elif cmd == 'get_time':
        now = datetime.now()
        return f"It's {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d')}"
    
    elif cmd == 'control_volume':
        action = params.get('action')
        level = params.get('level')
        if action == 'mute':
            os.system('nircmd mutesysvolume 1')
            return "Volume muted"
        elif action == 'unmute':
            os.system('nircmd mutesysvolume 0')
            return "Volume unmuted"
        elif action == 'up':
            os.system('nircmd changesysvolume 5000')
            return "Volume increased"
        elif action == 'down':
            os.system('nircmd changesysvolume -5000')
            return "Volume decreased"
        elif action == 'set' and level:
            os.system(f'nircmd setsysvolume {level * 655}')
            return f"Volume set to {level}%"
        return "Volume command received"
    
    elif cmd == 'control_app':
        app = params.get('app', '')
        action = params.get('action', 'open')
        if action == 'open':
            try:
                subprocess.Popen(app)
                return f"Opening {app}"
            except:
                return f"Could not open {app}"
        elif action == 'close':
            os.system(f'taskkill /f /im {app}.exe')
            return f"Closing {app}"
    
    elif cmd == 'system_power':
        mode = params.get('mode')
        if mode == 'shutdown':
            return "Shutting down system"
        elif mode == 'restart':
            return "Restarting system"
        elif mode == 'sleep':
            os.system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0')
            return "Putting system to sleep"
        elif mode == 'lock':
            os.system('rundll32.exe user32.dll,LockWorkStation')
            return "Locking screen"
    
    elif cmd == 'media_control':
        action = params.get('action')
        return f"Media {action} command received"
    
    elif cmd == 'assistant_help':
        help_text = (
            "I can help you with the following commands: "
            "Open browser or launch Chrome. "
            "Search for anything on Google. "
            "Tell you the current time and date. "
            "Control volume - mute, unmute, volume up, volume down. "
            "Open or close applications like notepad or calculator. "
            "System commands - shutdown, restart, sleep, or lock screen. "
            "Just say Hey Vox to activate me, and say shutdown when you're done."
        )
        print("\n=== VoxMind Commands ===")
        print("• Browser: 'open browser', 'launch chrome'")
        print("• Search: 'search for [topic]', 'what is [topic]'")
        print("• Time: 'what time is it', 'what's the date'")
        print("• Volume: 'mute', 'volume up', 'volume down', 'set volume to 50'")
        print("• Apps: 'open notepad', 'close chrome'")
        print("• System: 'shutdown', 'restart', 'sleep', 'lock screen'")
        print("• Help: 'help', 'what can you do'")
        print("========================\n")
        return help_text
    
    elif cmd == 'navigate':
        action = params.get('action')
        return f"Navigation {action} received"
    
    elif cmd == 'scroll':
        direction = params.get('direction')
        return f"Scrolling {direction}"
    
    return "I didn't understand that command"

def run_loop(simulate=False, no_tts=False, skip_wake=False):
    print("=" * 50)
    print("VoxMind Voice Assistant")
    print("=" * 50)
    print("Say 'Hey Vox' to start")
    print("Say 'shutdown' to exit")
    print("Press Ctrl-C to force exit\n")
    
    active = False
    
    while True:
        try:
            if simulate:
                if not active:
                    input("Press Enter to simulate 'Hey Vox'...")
                    active = True
                    print("✓ VoxMind activated! Listening for commands...\n")
                cmd_text = input("Command: ").strip()
            else:
                if not active:
                    print("Waiting for 'Hey Vox'...")
                    if listen_for_wake_word():
                        active = True
                        print("✓ VoxMind activated! Listening for commands...\n")
                        if not no_tts:
                            try:
                                speak_text("Yes, I'm listening")
                            except:
                                pass
                    continue
                
                print("Listening...")
                try:
                    cmd_text = listen_for_command(
                        timeout=5.0,
                        phrase_time_limit=8.0,
                        adjust_for_ambient=True,
                        ambient_duration=0.5
                    )
                except RuntimeError as e:
                    print(f"Error: {e}")
                    continue
            
            if not cmd_text:
                print("No command heard\n")
                continue
            
            print(f"Heard: '{cmd_text}'")
            
            parsed = parse_command(cmd_text)
            print(f"Command: {parsed['command']}")
            
            # Check for shutdown
            if parsed.get('command') == 'system_power':
                mode = parsed.get('params', {}).get('mode')
                if mode in ['shutdown', 'restart']:
                    response = "Goodbye!"
                    print(f"Response: {response}\n")
                    if not no_tts:
                        try:
                            speak_text(response)
                        except:
                            pass
                    break
            
            response = execute_command(parsed)
            print(f"Response: {response}\n")
            
            if not no_tts:
                try:
                    speak_text(response)
                except Exception as e:
                    print(f"TTS error: {e}")
            
            sleep(0.3)
            
        except KeyboardInterrupt:
            print("\nExiting VoxMind...")
            break
        except Exception as e:
            print(f"Error: {e}\n")

def main():
    parser = argparse.ArgumentParser(description='VoxMind Voice Assistant')
    parser.add_argument('--simulate', action='store_true', help='Keyboard mode')
    parser.add_argument('--no-tts', action='store_true', help='Disable TTS')
    args = parser.parse_args()
    
    run_loop(simulate=args.simulate, no_tts=args.no_tts)

if __name__ == '__main__':
    main()
