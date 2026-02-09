"""Test the backend integration end-to-end."""
from main import backend_app

print("Testing VoxMind Backend...")
print("=" * 50)

tests = [
    "open chrome",
    "search for python tutorials", 
    "volume up",
    "what time is it",
    "set brightness to 50",
    "open notepad",
]

for t in tests:
    parsed, response, error = backend_app.handle(t)
    cmd = parsed.get("command", "unknown")
    conf = parsed.get("confidence", 0)
    method = parsed.get("method", "?")
    print(f"  '{t}'")
    print(f"    -> Command: {cmd} | Method: {method} | Confidence: {conf:.0%}")
    if response:
        print(f"    -> Response: {response[:60]}...")
    print()

print("=" * 50)
print("Telemetry Snapshot:")
snapshot = backend_app.telemetry_snapshot()
print(f"  Total Requests: {snapshot['total_requests']}")
print(f"  Command Counts: {snapshot['command_counts']}")
print(f"  Error Counts: {snapshot['error_counts']}")
print("=" * 50)
print("Backend OK!")
