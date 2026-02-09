from command_parser import parse_command

samples = [
    "VoxMind open the browser",
    "VoxMind launch chrome",
    "VoxMind search for quantum tunneling",
    "VoxMind what's the time",
    "VoxMind please shut down the computer",
    "VoxMind mute the volume",
    "VoxMind open vscode",
    "VoxMind open downloads folder",
    "VoxMind what can you do",
    "VoxMind go back",
    "VoxMind play next song",
    "VoxMind scroll down",
]

for s in samples:
    result = parse_command(s)
    print(f"INPUT: {s!r}")
    print("OUTPUT:", result)
    print("-" * 40)
