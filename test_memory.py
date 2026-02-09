"""Test the unified memory system for pronoun resolution."""

from core.unified_memory import get_memory

def test_memory():
    print("=" * 50)
    print("Testing Unified Memory System")
    print("=" * 50)
    
    # Get memory instance and clear it
    memory = get_memory()
    memory.clear()
    print("\n1. Memory cleared")
    
    # Test 1: Record "open chrome" command
    memory.record(
        user_input="open chrome",
        response="Opening Chrome browser",
        command="app_control",
        entities={"app": "chrome", "action": "open"}
    )
    print("\n2. Recorded: 'open chrome' with entities {'app': 'chrome'}")
    
    # Test 2: Resolve "close it"
    resolved = memory.resolve_pronouns("close it", {})
    print(f"\n3. Resolving 'close it':")
    print(f"   Result: {resolved}")
    
    # Test 3: Check last entity
    last_app = memory.get_last_entity("app")
    print(f"\n4. Last app entity: {last_app}")
    
    # Test 4: Record another command
    memory.record(
        user_input="open notepad",
        response="Opening Notepad",
        command="app_control",
        entities={"app": "notepad", "action": "open"}
    )
    print("\n5. Recorded: 'open notepad' with entities {'app': 'notepad'}")
    
    # Test 5: Now "close it" should refer to notepad
    resolved2 = memory.resolve_pronouns("close it", {})
    print(f"\n6. Resolving 'close it' again:")
    print(f"   Result: {resolved2}")
    
    # Test 6: Check follow-up detection
    is_followup = memory.is_follow_up("minimize that")
    print(f"\n7. Is 'minimize that' a follow-up? {is_followup}")
    
    # Test 7: Check context summary
    context = memory.get_context_summary()
    print(f"\n8. Context summary:\n{context}")
    
    # Test 8: Check last command
    last_cmd = memory.get_last_command()
    if last_cmd:
        print(f"\n9. Last command:")
        print(f"   Input: {last_cmd.user_input}")
        print(f"   Entities: {last_cmd.entities}")
    
    # Test 9: Pronoun in complex sentence
    resolved3 = memory.resolve_pronouns("search for more information about it", {})
    print(f"\n10. Resolving 'search for more information about it':")
    print(f"    Result: {resolved3}")
    
    print("\n" + "=" * 50)
    print("Memory test complete!")
    print("=" * 50)


def test_parse_command_integration():
    """Test that parse_command properly resolves pronouns."""
    print("\n" + "=" * 50)
    print("Testing parse_command() Integration")
    print("=" * 50)
    
    from core.unified_memory import get_memory
    
    # Clear and set up memory
    memory = get_memory()
    memory.clear()
    
    # Simulate opening Chrome
    memory.record(
        user_input="open chrome",
        response="Opening Chrome",
        command="app_control",
        entities={"app": "chrome", "action": "open"}
    )
    print("\n1. Recorded: 'open chrome'")
    
    # Now import and test parse_command
    from main import parse_command
    
    # Test pronoun resolution in parse_command
    result = parse_command("close it")
    print(f"\n2. parse_command('close it'):")
    print(f"   Command: {result.get('command')}")
    print(f"   Params: {result.get('params')}")
    
    # The parsed command should recognize 'chrome' as the app
    if 'params' in result and result['params'].get('app') == 'chrome':
        print("\n   ✅ Pronoun 'it' correctly resolved to 'chrome'!")
    elif result.get('command') == 'app_control':
        print("\n   ⚠️ Command recognized but check params for 'chrome'")
    else:
        print("\n   ❌ Pronoun resolution may not be working correctly")
    
    # Test with another app
    memory.record(
        user_input="open calculator",
        response="Opening Calculator",
        command="app_control",
        entities={"app": "calculator", "action": "open"}
    )
    print("\n3. Recorded: 'open calculator'")
    
    result2 = parse_command("minimize that")
    print(f"\n4. parse_command('minimize that'):")
    print(f"   Command: {result2.get('command')}")
    print(f"   Params: {result2.get('params')}")
    
    # Check for success
    if 'params' in result2 and result2['params'].get('app') == 'calculator':
        print("\n   ✅ Pronoun 'that' correctly resolved to 'calculator'!")
    elif result2.get('command') in ['app_control', 'windows_ui']:
        print("\n   ⚠️ Command recognized, checking app resolution...")
    else:
        print("\n   ❌ Pronoun resolution needs work")
    
    print("\n" + "=" * 50)
    print("Integration test complete!")
    print("=" * 50)


if __name__ == "__main__":
    test_memory()
    test_parse_command_integration()
