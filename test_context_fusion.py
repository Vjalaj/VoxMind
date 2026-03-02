"""
Test for VoxMind Multi-Modal Context Fusion (Phase 1.1)
=======================================================
Tests for the context fusion module.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_import():
    """Test that context_fusion module can be imported."""
    try:
        from core.context_fusion import ContextFusion, get_context_fusion
        print("✓ ContextFusion imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import: {e}")
        return False


def test_singleton():
    """Test that get_context_fusion returns singleton."""
    from core.context_fusion import get_context_fusion
    
    fusion1 = get_context_fusion()
    fusion2 = get_context_fusion()
    
    assert fusion1 is fusion2, "Should return same instance"
    print("✓ Singleton pattern works")


def test_ambiguous_detection():
    """Test detection of ambiguous commands."""
    from core.context_fusion import ContextFusion
    
    fusion = ContextFusion()
    
    # Test ambiguous patterns
    ambiguous = [
        "open that",
        "click that",
        "close it",
        "show this",
        "open that file",
    ]
    
    for text in ambiguous:
        result = fusion._is_ambiguous(text)
        assert result == True, f"Should detect '{text}' as ambiguous"
    
    # Test non-ambiguous patterns
    clear = [
        "open chrome",
        "close notepad",
        "click the button",
    ]
    
    for text in clear:
        result = fusion._is_ambiguous(text)
        assert result == False, f"Should detect '{text}' as clear"
    
    print("✓ Ambiguous command detection works")


def test_voice_context_update():
    """Test updating voice context."""
    from core.context_fusion import ContextFusion
    
    fusion = ContextFusion()
    fusion.update_voice_context(
        "open that file",
        "app_control",
        {"target": "that"},
        confidence=0.8
    )
    
    assert fusion._voice_context is not None
    assert fusion._voice_context.raw_text == "open that file"
    assert fusion._voice_context.parsed_command == "app_control"
    assert fusion._voice_context.is_ambiguous == True
    
    print("✓ Voice context update works")


def test_screen_context_capture():
    """Test screen context capture (may fail if OCR not available)."""
    from core.context_fusion import ContextFusion
    
    fusion = ContextFusion()
    fusion.update_screen_context()
    
    # Should not raise exception even if OCR unavailable
    print("✓ Screen context capture doesn't crash")


def test_context_fusion():
    """Test full context fusion."""
    from core.context_fusion import ContextFusion
    
    fusion = ContextFusion()
    
    # Update contexts
    fusion.update_voice_context(
        "open that",
        "control_app",
        {"target": "that"}
    )
    fusion.update_screen_context()
    
    # Fuse contexts
    unified = fusion.fuse_context()
    
    # Check unified context has expected fields
    assert unified.voice is not None
    assert unified.disambiguated_entities is not None
    
    print("✓ Context fusion works")


def test_resolve_ambiguous():
    """Test ambiguous command resolution."""
    from core.context_fusion import ContextFusion
    
    fusion = ContextFusion()
    fusion.update_screen_context()
    
    resolved = fusion.resolve_ambiguous_command(
        "open that",
        "control_app",
        {"target": "that"}
    )
    
    # Should return a dictionary
    assert isinstance(resolved, dict)
    
    print("✓ Ambiguous command resolution works")


def test_get_screen_description():
    """Test screen description generation."""
    from core.context_fusion import ContextFusion
    
    fusion = ContextFusion()
    desc = fusion.get_screen_description()
    
    # Should return a string
    assert isinstance(desc, str)
    
    print("✓ Screen description works")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("VoxMind Phase 1.1 - Context Fusion Tests")
    print("=" * 60)
    
    tests = [
        test_import,
        test_singleton,
        test_ambiguous_detection,
        test_voice_context_update,
        test_screen_context_capture,
        test_context_fusion,
        test_resolve_ambiguous,
        test_get_screen_description,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
