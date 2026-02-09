"""
Test suite for VoxMind Screen Context (Screen Sharing with Vox)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.screen_context import (
    ScreenCapture,
    TextExtractor,
    SemanticAnalyzer,
    ScreenContextEngine,
    get_screen_engine,
    ScreenContext,
    ScreenRegion,
)


def test_screen_capture():
    """Test screen capture functionality."""
    print("\n[Testing Screen Capture]")
    
    capture = ScreenCapture()
    
    # Full screen capture
    screenshot = capture.capture_full_screen()
    assert screenshot is not None, "Failed to capture screen"
    print(f"  ✓ Full screen captured: {screenshot.size}")
    
    # Active window capture
    window_shot = capture.capture_active_window()
    assert window_shot is not None, "Failed to capture active window"
    print(f"  ✓ Active window captured: {window_shot.size}")
    
    # Region capture
    region = ScreenRegion(x=100, y=100, width=200, height=200)
    region_shot = capture.capture_region(region)
    assert region_shot is not None, "Failed to capture region"
    print(f"  ✓ Region captured: {region_shot.size}")
    
    return True


def test_text_extractor():
    """Test OCR text extraction."""
    print("\n[Testing Text Extractor]")
    
    extractor = TextExtractor()
    
    print(f"  OCR Backend: {extractor._ocr_backend or 'None'}")
    print(f"  OCR Available: {extractor.available}")
    
    if not extractor.available:
        print("  ⚠ OCR not available - skipping text extraction test")
        return True
    
    # Capture and extract
    capture = ScreenCapture()
    screenshot = capture.capture_full_screen()
    
    text = extractor.extract_text(screenshot)
    print(f"  ✓ Extracted {len(text)} characters of text")
    
    blocks = extractor.extract_text_with_positions(screenshot)
    print(f"  ✓ Found {len(blocks)} text blocks with positions")
    
    return True


def test_semantic_analyzer():
    """Test semantic analysis of text."""
    print("\n[Testing Semantic Analyzer]")
    
    analyzer = SemanticAnalyzer()
    
    # Test with sample text
    sample_text = """
    Welcome to VoxMind - Your AI Assistant
    
    Visit https://github.com/voxmind/voxmind for more info.
    Contact: support@voxmind.ai
    Phone: (555) 123-4567
    
    Price: $99.99 USD
    Date: January 31, 2026
    
    def hello_world():
        print("Hello, World!")
    
    Error: Connection refused
    """
    
    context = analyzer.analyze(sample_text)
    
    print(f"  ✓ Detected app: {context.detected_app}")
    print(f"  ✓ URLs found: {len(context.urls)}")
    print(f"  ✓ Emails found: {len(context.emails)}")
    print(f"  ✓ Phone numbers: {len(context.phone_numbers)}")
    print(f"  ✓ Prices found: {len(context.prices)}")
    print(f"  ✓ Keywords: {context.keywords[:5]}")
    print(f"  ✓ Suggested actions: {context.suggested_actions}")
    
    # Verify extractions
    assert len(context.urls) > 0, "Should find URLs"
    assert len(context.emails) > 0, "Should find emails"
    assert len(context.phone_numbers) > 0, "Should find phone numbers"
    assert len(context.prices) > 0, "Should find prices"
    
    return True


def test_screen_context_engine():
    """Test the full screen context engine."""
    print("\n[Testing Screen Context Engine]")
    
    engine = get_screen_engine()
    
    print(f"  OCR Available: {engine.ocr_available}")
    
    if not engine.ocr_available:
        print("  ⚠ OCR not available - limited testing")
        return True
    
    # Full analysis
    print("  Analyzing screen...")
    context = engine.capture_and_analyze()
    
    print(f"  ✓ Detected app: {context.detected_app or 'Unknown'}")
    print(f"  ✓ Page title: {context.page_title or 'Unknown'}")
    print(f"  ✓ Text extracted: {len(context.all_text)} chars")
    print(f"  ✓ Text blocks: {len(context.text_blocks)}")
    print(f"  ✓ Keywords: {context.keywords[:5] if context.keywords else 'None'}")
    
    # Quick context
    quick = engine.get_quick_context()
    print(f"  ✓ Quick context keys: {list(quick.keys())}")
    
    # Description
    description = engine.describe_screen()
    print(f"  ✓ Description length: {len(description)} chars")
    
    return True


def test_command_parsing():
    """Test that screen commands are recognized."""
    print("\n[Testing Command Parsing]")
    
    from main import parse_command
    
    screen_commands = [
        "what's on my screen",
        "describe the screen",
        "what am I looking at",
        "read the screen",
        "help me with this",
        "what do you see",
    ]
    
    passed = 0
    for cmd in screen_commands:
        result = parse_command(cmd)
        if result.get('command') == 'screen_context':
            print(f"  ✓ '{cmd}' -> screen_context")
            passed += 1
        else:
            print(f"  ✗ '{cmd}' -> {result.get('command')} (expected screen_context)")
    
    print(f"\n  Passed: {passed}/{len(screen_commands)}")
    return passed == len(screen_commands)


def main():
    print("=" * 60)
    print("VoxMind Screen Context Test Suite")
    print("=" * 60)
    
    results = []
    
    results.append(("Screen Capture", test_screen_capture()))
    results.append(("Text Extractor", test_text_extractor()))
    results.append(("Semantic Analyzer", test_semantic_analyzer()))
    results.append(("Screen Context Engine", test_screen_context_engine()))
    results.append(("Command Parsing", test_command_parsing()))
    
    print("\n" + "=" * 60)
    print("Results Summary:")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {name}: {status}")
    
    all_passed = all(r[1] for r in results)
    print("\n" + ("All tests passed!" if all_passed else "Some tests failed."))
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
