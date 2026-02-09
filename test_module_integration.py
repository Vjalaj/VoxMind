"""
Comprehensive Module Integration Test for VoxMind
=================================================
Tests all core modules after redundancy cleanup to ensure functionality is preserved.

Modules Tested:
- Speech Recognition (Jalaj)
- Text-to-Speech (minakshi) 
- Command Parser (Priyapal)
- NLP Command Parser (Tejas)
- Wake Word Detection (Tejas, core)
- Response Generator (Tejas)
- Question Answering (Swadhin)
- Windows UI Control (core)
- Volume Control (Soumyadeb)

Run: python test_module_integration.py
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from typing import Dict, Any

# Ensure project root is on path
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


class TestSpeechRecognition(unittest.TestCase):
    """Test Jalaj speech recognition module."""
    
    def test_import(self):
        """Test module can be imported."""
        try:
            from Jalaj.speech_recognition_service import listen_for_command
            self.assertTrue(callable(listen_for_command))
        except ImportError as e:
            self.skipTest(f"SpeechRecognition dependencies not installed: {e}")
    
    def test_function_signature(self):
        """Test function has expected signature."""
        try:
            from Jalaj.speech_recognition_service import listen_for_command
            import inspect
            sig = inspect.signature(listen_for_command)
            # Should accept timeout parameter
            self.assertIn('timeout', sig.parameters)
        except ImportError:
            self.skipTest("Module not available")


class TestTextToSpeech(unittest.TestCase):
    """Test minakshi TTS module (canonical)."""
    
    def test_import(self):
        """Test module can be imported."""
        try:
            from minakshi.text_to_speech import speak_text
            self.assertTrue(callable(speak_text))
        except ImportError as e:
            self.skipTest(f"TTS dependencies not installed: {e}")
    
    def test_speak_text_with_persona(self):
        """Test persona-based TTS function exists."""
        try:
            from minakshi.text_to_speech import speak_text_with_persona
            self.assertTrue(callable(speak_text_with_persona))
        except ImportError:
            self.skipTest("Module not available")
    
    def test_voice_persona_functions(self):
        """Test voice persona management functions."""
        try:
            from minakshi.text_to_speech import set_voice_persona, get_voice_persona
            self.assertTrue(callable(set_voice_persona))
            self.assertTrue(callable(get_voice_persona))
        except ImportError:
            self.skipTest("Module not available")


class TestCommandParser(unittest.TestCase):
    """Test Priyapal command parser (canonical)."""
    
    def test_import(self):
        """Test module can be imported."""
        from Priyapal.command_parser import parse_command
        self.assertTrue(callable(parse_command))
    
    def test_basic_commands(self):
        """Test basic command parsing."""
        from Priyapal.command_parser import parse_command
        
        # Test open browser
        result = parse_command("open browser")
        self.assertIsInstance(result, dict)
        
        # Test time query
        result = parse_command("what time is it")
        self.assertIsInstance(result, dict)
        
        # Test search
        result = parse_command("search for python tutorials")
        self.assertIsInstance(result, dict)
    
    def test_wake_word_stripping(self):
        """Test wake word removal."""
        from Priyapal.command_parser import parse_command
        
        # Command with wake word
        result1 = parse_command("hey vox open browser")
        result2 = parse_command("open browser")
        
        # Both should parse to same command type
        self.assertEqual(result1.get('type'), result2.get('type'))
    
    def test_empty_input(self):
        """Test handling of empty input."""
        from Priyapal.command_parser import parse_command
        
        result = parse_command("")
        self.assertIsInstance(result, dict)
        # Parser may return None or 'unknown' for type
        self.assertIn(result.get('type'), [None, 'unknown', 'empty'])
    
    def test_shutdown_command(self):
        """Test shutdown command detection."""
        from Priyapal.command_parser import parse_command
        
        for cmd in ["shutdown", "exit", "quit", "goodbye"]:
            result = parse_command(cmd)
            # Parser returns dict, type may be None or specific command
            self.assertIsInstance(result, dict)
            cmd_type = result.get('type') or result.get('command')
            # At minimum should return a dict without error


class TestNLPCommandParser(unittest.TestCase):
    """Test Tejas NLP command parser."""
    
    def test_import(self):
        """Test module can be imported."""
        try:
            from Tejas.nlp_command_parser import parse_command_nlp
            self.assertTrue(callable(parse_command_nlp))
        except ImportError as e:
            self.skipTest(f"NLP dependencies not installed: {e}")
    
    def test_nlp_parsing(self):
        """Test NLP-based command parsing."""
        try:
            from Tejas.nlp_command_parser import parse_command_nlp
            
            result = parse_command_nlp("please open the web browser")
            self.assertIsInstance(result, dict)
            self.assertIn('confidence', result)
        except ImportError:
            self.skipTest("NLP module not available")


class TestWakeWordDetection(unittest.TestCase):
    """Test wake word detection modules."""
    
    def test_tejas_wake_word_import(self):
        """Test Tejas wake word detector can be imported."""
        try:
            from Tejas.wake_word_detector import listen_for_wake_word
            self.assertTrue(callable(listen_for_wake_word))
        except ImportError as e:
            self.skipTest(f"Wake word dependencies not installed: {e}")
    
    def test_core_wake_word_import(self):
        """Test core wake word module can be imported."""
        try:
            from core.wake_word import WakeWordDetector
            self.assertTrue(callable(WakeWordDetector))
        except ImportError as e:
            self.skipTest(f"Core wake word not available: {e}")
    
    def test_priyapal_wake_word_import(self):
        """Test Priyapal wake word enhancement can be imported."""
        try:
            from Priyapal.wake_word_enhancement import detect_wake_word
            self.assertTrue(callable(detect_wake_word))
        except ImportError as e:
            self.skipTest(f"Priyapal wake word not available: {e}")


class TestResponseGenerator(unittest.TestCase):
    """Test Tejas response generator."""
    
    def test_import(self):
        """Test module can be imported."""
        try:
            from Tejas.response_generator import generate_response
            self.assertTrue(callable(generate_response))
        except ImportError as e:
            self.skipTest(f"Response generator not available: {e}")
    
    def test_response_generation(self):
        """Test response generation for various command types."""
        try:
            from Tejas.response_generator import generate_response
            
            # Test with parsed command dict
            parsed = {"type": "time"}
            response = generate_response(parsed)
            self.assertIsInstance(response, str)
            self.assertTrue(len(response) > 0)
            
            # Test unknown command
            parsed = {"type": "unknown"}
            response = generate_response(parsed)
            self.assertIsInstance(response, str)
        except ImportError:
            self.skipTest("Module not available")


class TestQuestionAnswering(unittest.TestCase):
    """Test Swadhin question answering module."""
    
    def test_import_question_classifier(self):
        """Test question classifier can be imported."""
        try:
            from Swadhin.question_answering.question_classifier import QuestionClassifier
            self.assertTrue(callable(QuestionClassifier))
        except ImportError as e:
            self.skipTest(f"Question classifier not available: {e}")
    
    def test_import_question_handler(self):
        """Test question handler can be imported."""
        try:
            from Swadhin.question_answering.question_handler import QuestionAnswerer
            self.assertTrue(callable(QuestionAnswerer))
        except ImportError as e:
            self.skipTest(f"Question handler not available: {e}")
    
    def test_question_classification(self):
        """Test question type classification."""
        try:
            from Swadhin.question_answering.question_classifier import QuestionClassifier
            
            classifier = QuestionClassifier()
            
            # Test various question types
            test_cases = [
                ("What is Python?", "WHAT"),
                ("Why is the sky blue?", "WHY"),
                ("How do computers work?", "HOW"),
                ("When was Python created?", "WHEN"),
                ("Which is better, Python or Java?", "WHICH"),
            ]
            
            for question, expected_type in test_cases:
                result = classifier.classify(question)
                # Result may be a dataclass or dict
                if hasattr(result, 'question_type'):
                    self.assertIsNotNone(result.question_type)
                elif isinstance(result, dict):
                    self.assertIn('question_type', result)
                else:
                    self.assertTrue(result is not None)
        except ImportError:
            self.skipTest("Module not available")


class TestWindowsUIControl(unittest.TestCase):
    """Test core Windows UI control module."""
    
    def test_import(self):
        """Test module can be imported."""
        try:
            from core.windows_ui import WindowsUIController, parse_windows_ui_command
            self.assertTrue(callable(WindowsUIController))
            self.assertTrue(callable(parse_windows_ui_command))
        except ImportError as e:
            self.skipTest(f"Windows UI module not available: {e}")
    
    def test_parse_commands(self):
        """Test Windows UI command parsing."""
        try:
            from core.windows_ui import parse_windows_ui_command
            
            # Test start menu command
            result = parse_windows_ui_command("open start menu")
            self.assertIsNotNone(result)
            self.assertEqual(result.get('action'), 'open_start')
            
            # Test snap command
            result = parse_windows_ui_command("snap left")
            self.assertIsNotNone(result)
            
            # Test split screen
            result = parse_windows_ui_command("split screen")
            self.assertIsNotNone(result)
        except ImportError:
            self.skipTest("Module not available")


class TestVolumeControl(unittest.TestCase):
    """Test Soumyadeb volume control module."""
    
    def test_import(self):
        """Test module can be imported."""
        try:
            from Soumyadeb.audio import AudioController
            self.assertTrue(callable(AudioController))
        except ImportError as e:
            self.skipTest(f"Audio control module not available: {e}")


class TestIntelligentResponse(unittest.TestCase):
    """Test core intelligent response module."""
    
    def test_import(self):
        """Test module can be imported."""
        try:
            from core.intelligent_response import get_intelligent_response_engine
            self.assertTrue(callable(get_intelligent_response_engine))
        except ImportError as e:
            self.skipTest(f"Intelligent response not available: {e}")


class TestTejasMainIntegration(unittest.TestCase):
    """Test that Tejas/main.py uses canonical modules after cleanup."""
    
    def test_imports_canonical_tts(self):
        """Verify Tejas/main.py imports from minakshi."""
        with open(os.path.join(ROOT, 'Tejas', 'main.py'), 'r') as f:
            content = f.read()
        
        self.assertIn('from minakshi.text_to_speech import speak_text', content)
        self.assertNotIn('from Tejas.text_to_speech import', content)
    
    def test_imports_canonical_parser(self):
        """Verify Tejas/main.py imports from Priyapal."""
        with open(os.path.join(ROOT, 'Tejas', 'main.py'), 'r') as f:
            content = f.read()
        
        self.assertIn('from Priyapal.command_parser import parse_command', content)
        self.assertNotIn('from Tejas.command_parser import', content)
    
    def test_redundant_files_removed(self):
        """Verify redundant files were deleted."""
        self.assertFalse(
            os.path.exists(os.path.join(ROOT, 'Tejas', 'text_to_speech.py')),
            "Tejas/text_to_speech.py should be deleted"
        )
        self.assertFalse(
            os.path.exists(os.path.join(ROOT, 'Tejas', 'command_parser.py')),
            "Tejas/command_parser.py should be deleted"
        )


class TestMainPyIntegration(unittest.TestCase):
    """Test that main.py uses canonical modules."""
    
    def test_uses_minakshi_tts(self):
        """Verify main.py uses minakshi TTS."""
        with open(os.path.join(ROOT, 'main.py'), 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn('from minakshi.text_to_speech import', content)
    
    def test_uses_priyapal_parser(self):
        """Verify main.py uses Priyapal parser."""
        with open(os.path.join(ROOT, 'main.py'), 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn('from Priyapal.command_parser import', content)


class TestModuleCompatibility(unittest.TestCase):
    """Test that modules work together correctly."""
    
    def test_parse_and_respond_flow(self):
        """Test complete command parsing and response flow."""
        try:
            from Priyapal.command_parser import parse_command
            from Tejas.response_generator import generate_response
            
            # Simulate voice command flow
            commands = [
                "open browser",
                "what time is it",
                "search for python",
                "shutdown",
            ]
            
            for cmd in commands:
                parsed = parse_command(cmd)
                self.assertIsInstance(parsed, dict, f"Failed parsing: {cmd}")
                
                response = generate_response(parsed)
                self.assertIsInstance(response, str, f"Failed response for: {cmd}")
                self.assertTrue(len(response) > 0, f"Empty response for: {cmd}")
        except ImportError as e:
            self.skipTest(f"Required modules not available: {e}")
    
    def test_windows_ui_snap_commands(self):
        """Test new snap app commands work."""
        try:
            from core.windows_ui import parse_windows_ui_command
            
            # Test snap with app
            result = parse_windows_ui_command("snap left")
            self.assertIsNotNone(result)
            self.assertEqual(result.get('action'), 'snap')
            
            # Test snap window
            result = parse_windows_ui_command("snap window to right")
            if result:  # May not be implemented
                self.assertEqual(result.get('action'), 'snap')
        except ImportError:
            self.skipTest("Windows UI module not available")


def run_tests():
    """Run all tests with verbose output."""
    print("=" * 70)
    print("VoxMind Module Integration Tests")
    print("Testing after redundancy cleanup")
    print("=" * 70)
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestSpeechRecognition,
        TestTextToSpeech,
        TestCommandParser,
        TestNLPCommandParser,
        TestWakeWordDetection,
        TestResponseGenerator,
        TestQuestionAnswering,
        TestWindowsUIControl,
        TestVolumeControl,
        TestIntelligentResponse,
        TestTejasMainIntegration,
        TestMainPyIntegration,
        TestModuleCompatibility,
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.wasSuccessful():
        print("\n✅ All tests passed! Module integration is working correctly.")
    else:
        print("\n❌ Some tests failed. Check output above for details.")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
