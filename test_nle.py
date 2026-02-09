"""Test the VoxMind Natural Language Engine capabilities."""
from core.natural_language_engine import NaturalLanguageEngine

engine = NaturalLanguageEngine()
engine.set_user_name('Tony')

print('='*60)
print('VOXMIND NATURAL LANGUAGE ENGINE - INTELLIGENT ASSISTANT CAPABILITIES')
print('='*60)

# Test 1: Fuzzy correction of speech errors
print('\n[1] SPEECH ERROR CORRECTION (Fuzzy Matching):')
tests = [
    'serch for python tutorials',
    'opn crome browser',
    'wat time is it',
    'increase volumne',
    'open notpad',
    'um can you like search google for weather'
]
for t in tests:
    corrected = engine.preprocess(t)
    print(f'  "{t}"')
    print(f'  -> "{corrected}"')
    print()

# Test 2: Word prediction
print('[2] WORD PREDICTION (Anticipating User Input):')
contexts = ['open', 'search for', 'what is the', 'set brightness', 'play']
for ctx in contexts:
    preds = engine.predict_completion(ctx)[:3]
    print(f'  "{ctx}" -> {preds}')

# Test 3: Contextual conversation
print('\n[3] CONVERSATIONAL MEMORY (Context Tracking):')
engine.record_exchange('search for python', 'Searching for python...', 'search', {'query': 'python'})
print('  User: "search for python"')
print('  Bot: "Searching for python..."')
print('  User: "tell me more about it"')
resolved = engine.preprocess('tell me more about it')
print(f'  -> Resolved: "{resolved}" (it -> python)')

# Test 4: Natural responses
print('\n[4] NATURAL RESPONSE GENERATION:')
responses = [
    engine.generate_response('search', {'query': 'weather forecast'}),
    engine.generate_response('app_control', {'app_name': 'Spotify'}),
    engine.generate_response('greeting', {}),
]
for r in responses:
    print(f'  -> {r}')

print('\n' + '='*60)
print('Ready for life-like VoxMind interaction!')
print('='*60)
