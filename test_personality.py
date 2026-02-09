"""Quick test for VoxMind personality."""
import sys
sys.path.insert(0, '.')

from personality import VoxPersonality as Vox

print("Testing VoxMind Personality Module")
print("=" * 40)

print("\n1. Startup message:")
print(f"   {Vox.get_startup_message()}")

print("\n2. Time-based greeting:")
print(f"   {Vox.get_greeting()}")

print("\n3. Listening message:")
print(f"   {Vox.get_listening_message()}")

print("\n4. Acknowledgments:")
for _ in range(3):
    print(f"   - {Vox.get_acknowledgment()}")

print("\n5. Responses:")
print(f"   Browser: {Vox.get_response('open_browser')}")
print(f"   Search: {Vox.get_response('search', query='weather')}")
print(f"   Volume: {Vox.get_response('volume_up')}")
print(f"   App: {Vox.get_response('app_open', app='Notepad')}")

print("\n6. Shutdown message:")
print(f"   {Vox.get_shutdown_message()}")

print("\n" + "=" * 40)
print("Personality module working correctly!")
