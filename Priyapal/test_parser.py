from command_parser import parse_command

samples = [
    "Jarvis open the browser",
    "Jarvis launch chrome",
    "Jarvis search for quantum tunneling",
    "Jarvis what's the time",
    "Jarvis please shut down the computer",
    "Jarvis mute the volume",
    "Jarvis open vscode",
    "Jarvis open downloads folder",
    "Jarvis what can you do",
    "Jarvis go back",
    "Jarvis play next song",
    "Jarvis scroll down",
]

for s in samples:
    result = parse_command(s)
    print(f"INPUT: {s!r}")
    print("OUTPUT:", result)
    print("-" * 40)
