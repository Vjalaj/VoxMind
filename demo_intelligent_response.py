"""
VoxMind Intelligent Voice Response Demo
========================================
Demonstrates the ChatGPT-like features:

1. 'Did you mean...?' disambiguation for ambiguous commands
2. Varied response templates (avoids robotic repetition)
3. Context awareness for follow-up questions
4. Streaming responses for low-latency feel

This makes VoxMind feel more intelligent and responsive than Gemini.
"""

import sys
import os

# Add project paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.intelligent_response import (
    IntelligentResponseEngine,
    StreamingResponse,
    ResponseVariation,
    DisambiguationEngine
)


def demo_disambiguation():
    """Demo: 'Did you mean...?' for ambiguous commands."""
    print("\n" + "="*60)
    print("DEMO 1: Disambiguation ('Did you mean...?')")
    print("="*60)
    
    engine = IntelligentResponseEngine()
    disambig = DisambiguationEngine()
    
    # Test cases: (text, intent, confidence, alternatives)
    test_cases = [
        # Clear command - no disambiguation needed
        ("open chrome", "app_control", 0.85, []),
        
        # Ambiguous - single suggestion
        ("play", "play_music", 0.38, [("search", 0.32)]),
        
        # Very ambiguous - multiple suggestions
        ("go", "open_browser", 0.28, [
            ("app_control", 0.27),
            ("search", 0.25),
            ("help", 0.22)
        ]),
        
        # Unclear audio scenario
        ("mmm...", "unknown", 0.15, []),
    ]
    
    for text, intent, confidence, alternatives in test_cases:
        print(f"\n  Input: '{text}'")
        print(f"  Top intent: {intent} (confidence: {confidence:.0%})")
        
        needs_disambig = disambig.needs_disambiguation(confidence, alternatives)
        
        if confidence < 0.25:
            print(f"  → Too unclear. Response: \"{engine.get_clarification_response()}\"")
        elif needs_disambig:
            result = disambig.generate_disambiguation_response(text, intent, confidence, alternatives)
            print(f"  → Needs clarification!")
            print(f"  → Message: \"{result['message']}\"")
            print(f"  → Options:")
            for i, opt in enumerate(result['options']):
                print(f"       {i+1}. {opt['description']} ({opt['confidence']:.0%})")
        else:
            print(f"  → Clear! Executing directly.")


def demo_response_variation():
    """Demo: Varied responses (no robotic repetition)."""
    print("\n" + "="*60)
    print("DEMO 2: Response Variation (avoids robotic repetition)")
    print("="*60)
    
    variation = ResponseVariation()
    
    print("\n  Same command 'what time is it?' - different responses each time:")
    from datetime import datetime
    time_str = datetime.now().strftime('%I:%M %p')
    
    for i in range(5):
        response = variation.get_response('time', time=time_str)
        print(f"    {i+1}. \"{response}\"")
    
    print("\n  Same command 'search for cats' - different responses:")
    for i in range(4):
        response = variation.get_response('search', query='cats')
        print(f"    {i+1}. \"{response}\"")
    
    print("\n  Error/unclear responses (also varied):")
    for i in range(4):
        response = variation.get_response('error_unclear')
        print(f"    {i+1}. \"{response}\"")


def demo_context_memory():
    """Demo: Context awareness for follow-up questions."""
    print("\n" + "="*60)
    print("DEMO 3: Context Memory (follow-up understanding)")
    print("="*60)
    
    engine = IntelligentResponseEngine()
    
    # Simulate a conversation
    conversation = [
        # First command - opens Chrome
        ("open chrome", {"type": "app_control", "app": "chrome", "confidence": 0.9}),
        # Follow-up - "close it" should resolve to Chrome
        ("now close it", {"type": "app_control", "action": "close", "confidence": 0.85}),
        # Another conversation
        ("search for python tutorials", {"type": "search", "query": "python tutorials", "confidence": 0.92}),
        # Follow-up - "search for more" or similar
        ("what about machine learning", {"type": "search", "confidence": 0.7}),
    ]
    
    print("\n  Conversation flow:")
    for text, parsed in conversation:
        result = engine.process_command(text, parsed)
        
        print(f"\n  User: \"{text}\"")
        if result.get('context_used'):
            print(f"  [Context used! Resolved entity: {result.get('entities', {})}]")
        print(f"  VoxMind: \"{result['response']}\"")


def demo_streaming():
    """Demo: Streaming responses (low-latency feel)."""
    print("\n" + "="*60)
    print("DEMO 4: Streaming Response (ChatGPT-like)")
    print("="*60)
    
    response_text = "I'm searching for python tutorials. This will just take a moment. Here are some great resources I found for you!"
    
    print(f"\n  Full response: \"{response_text}\"")
    print("\n  Streaming (word by word):")
    print("  ", end="")
    
    stream = StreamingResponse(response_text, delay=0.05)
    for chunk in stream.stream():
        print(chunk, end="", flush=True)
    
    print("\n\n  This streaming approach is what makes ChatGPT voice feel so responsive!")


def demo_full_integration():
    """Demo: Full integration with parsing."""
    print("\n" + "="*60)
    print("DEMO 5: Full Integration Example")
    print("="*60)
    
    engine = IntelligentResponseEngine()
    
    # Simulate user commands
    user_inputs = [
        "Hey Vox, what time is it?",
        "open notepad",
        "search for weather forecast",
        "close it",  # Should understand 'it' refers to notepad
        "play",  # Ambiguous
        "mmmbll",  # Unclear
    ]
    
    print("\n  Simulated voice session:")
    
    for text in user_inputs:
        # Simulate parsing (in real code, use parse_command_nlp)
        parsed = _simulate_parse(text)
        result = engine.process_command(text, parsed)
        
        print(f"\n  👤 User: \"{text}\"")
        
        if result.get('needs_disambiguation'):
            print(f"  🤖 VoxMind: \"{result['disambiguation_message']}\"")
            if result.get('disambiguation_options'):
                for i, opt in enumerate(result['disambiguation_options'][:3]):
                    print(f"       {i+1}. {opt['description']}")
        else:
            print(f"  🤖 VoxMind: \"{result['response']}\"")
        
        if result.get('context_used'):
            print(f"      [Used context from previous turn]")


def _simulate_parse(text: str) -> dict:
    """Simulate parsing for demo (replace with real parser in production)."""
    text_lower = text.lower()
    
    # Remove wake words
    for wake in ['hey vox', 'vox', 'computer']:
        if text_lower.startswith(wake):
            text_lower = text_lower[len(wake):].strip(', ')
    
    if 'time' in text_lower:
        return {'type': 'time', 'confidence': 0.95}
    if 'open' in text_lower:
        app = text_lower.split('open')[-1].strip()
        return {'type': 'app_control', 'app': app, 'action': 'open', 'confidence': 0.9}
    if 'close' in text_lower:
        return {'type': 'app_control', 'action': 'close', 'confidence': 0.85}
    if 'search' in text_lower:
        query = text_lower.split('search for')[-1].strip() if 'search for' in text_lower else ''
        return {'type': 'search', 'query': query, 'confidence': 0.9}
    if text_lower == 'play':
        return {'type': 'play_music', 'confidence': 0.35, 
                'alternatives': [('search', 0.30), ('app_control', 0.25)]}
    
    return {'type': 'unknown', 'confidence': 0.1}


def main():
    """Run all demos."""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║      VoxMind Intelligent Response System Demo                ║")
    print("║      Making voice responses better than Gemini               ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    
    demo_disambiguation()
    demo_response_variation()
    demo_context_memory()
    demo_streaming()
    demo_full_integration()
    
    print("\n" + "="*60)
    print("KEY TAKEAWAYS: What makes ChatGPT voice better?")
    print("="*60)
    print("""
    1. DISAMBIGUATION: When unsure, ask "Did you mean...?" with options
       - Shows confidence in understanding
       - Gives user control without frustration
    
    2. RESPONSE VARIATION: Never say the exact same thing twice
       - Multiple templates per intent
       - Feels more natural and human-like
    
    3. CONTEXT MEMORY: Understand follow-up questions
       - "Open Chrome" then "close it" → closes Chrome
       - Pronoun resolution (it, that, this)
    
    4. STREAMING: Start responding before fully ready
       - Word-by-word output feels faster
       - User doesn't wait for full processing
    
    5. GRACEFUL DEGRADATION: Handle unclear audio well
       - Polite clarification requests
       - Don't just say "I don't understand"
    """)


if __name__ == "__main__":
    main()
