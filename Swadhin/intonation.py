"""
VoxMind Intonation Module
==========================
Makes voice output smooth, lucid, and natural with human-like intonation.

This module provides:
1. Prosody Control - Pitch contours, stress patterns, rhythm
2. Sentence Analysis - Detects questions, exclamations, lists, emphasis
3. Emotional Intonation - Happy, sad, concerned, excited tones
4. Natural Pauses - Breathing points, clause boundaries
5. SSML Generation - For advanced TTS engines

Inspired by:
- Human speech patterns and linguistics
- Google Cloud TTS prosody controls
- Amazon Polly's speech marks
- Microsoft Azure Neural TTS

Author: Swadhin
"""

import re
import math
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# === Enums and Data Classes ===

class SentenceType(Enum):
    """Types of sentences for intonation patterns"""
    STATEMENT = "statement"          # Falling intonation at end
    QUESTION_YES_NO = "question_yn"  # Rising intonation at end
    QUESTION_WH = "question_wh"      # Rise-fall pattern
    EXCLAMATION = "exclamation"      # Higher pitch, emphatic
    COMMAND = "command"              # Firm, level intonation
    LIST = "list"                    # Rising for items, falling for last
    CONTINUATION = "continuation"    # Slight rise (more to come)


class EmotionalTone(Enum):
    """Emotional tones for voice modulation"""
    NEUTRAL = "neutral"
    FRIENDLY = "friendly"
    PROFESSIONAL = "professional"
    EXCITED = "excited"
    CONCERNED = "concerned"
    APOLOGETIC = "apologetic"
    ENCOURAGING = "encouraging"
    CALM = "calm"
    URGENT = "urgent"


class EmphasisLevel(Enum):
    """Levels of word emphasis"""
    NONE = "none"
    MODERATE = "moderate"
    STRONG = "strong"
    REDUCED = "reduced"


@dataclass
class ProsodySettings:
    """Prosody control settings"""
    rate: float = 1.0           # 0.5 to 2.0 (1.0 = normal)
    pitch: float = 0.0          # -10 to +10 semitones
    pitch_range: float = 1.0    # 0.5 to 2.0 (affects expressiveness)
    volume: float = 0.0         # -6 to +6 dB
    contour: str = ""           # Pitch contour pattern
    

@dataclass
class WordAnnotation:
    """Annotation for individual words"""
    word: str
    emphasis: EmphasisLevel = EmphasisLevel.NONE
    pitch_offset: float = 0.0       # Semitones
    rate_modifier: float = 1.0
    pause_before_ms: int = 0
    pause_after_ms: int = 0
    is_new_info: bool = False       # New/important information
    is_contrast: bool = False       # Contrasting word


@dataclass
class SentenceAnnotation:
    """Annotation for a complete sentence"""
    text: str
    sentence_type: SentenceType = SentenceType.STATEMENT
    emotional_tone: EmotionalTone = EmotionalTone.NEUTRAL
    words: List[WordAnnotation] = field(default_factory=list)
    final_pitch_change: float = 0.0     # How much pitch changes at end
    overall_rate: float = 1.0
    overall_pitch: float = 0.0


@dataclass
class IntonationResult:
    """Result of intonation analysis"""
    original_text: str
    annotated_sentences: List[SentenceAnnotation]
    ssml: str = ""                      # SSML representation
    prosody_markers: List[Dict] = field(default_factory=list)
    estimated_duration_ms: int = 0


# === Linguistic Patterns ===

# Question words (WH-words)
WH_WORDS = {
    'what', 'where', 'when', 'why', 'who', 'whom', 'whose',
    'which', 'how', 'how much', 'how many', 'how long', 'how often'
}

# Emphasis trigger words
EMPHASIS_TRIGGERS = {
    'very', 'really', 'extremely', 'absolutely', 'definitely',
    'never', 'always', 'must', 'important', 'critical', 'essential',
    'amazing', 'incredible', 'fantastic', 'terrible', 'awful'
}

# Contrast words
CONTRAST_WORDS = {
    'but', 'however', 'although', 'though', 'yet', 'still',
    'instead', 'rather', 'otherwise', 'nevertheless', 'nonetheless',
    'on the other hand', 'in contrast', 'conversely'
}

# Continuation words (more to follow)
CONTINUATION_WORDS = {
    'and', 'also', 'moreover', 'furthermore', 'additionally',
    'first', 'second', 'third', 'finally', 'lastly',
    'for example', 'for instance', 'such as'
}

# Words that often receive reduced emphasis
FUNCTION_WORDS = {
    'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been',
    'to', 'of', 'in', 'on', 'at', 'by', 'for', 'with', 'from',
    'it', 'its', 'this', 'that', 'these', 'those',
    'and', 'or', 'but', 'if', 'as'
}

# Emotional keywords for tone detection
EMOTIONAL_KEYWORDS = {
    EmotionalTone.EXCITED: ['wow', 'amazing', 'awesome', 'fantastic', 'great', 'excellent', 'wonderful', 'incredible', '!'],
    EmotionalTone.CONCERNED: ['sorry', 'unfortunately', 'problem', 'issue', 'error', 'failed', 'wrong', 'trouble'],
    EmotionalTone.APOLOGETIC: ['sorry', 'apologize', 'apologies', 'regret', 'my bad', 'mistake'],
    EmotionalTone.ENCOURAGING: ['you can', 'try', 'let\'s', 'together', 'great job', 'well done', 'keep going'],
    EmotionalTone.URGENT: ['immediately', 'urgent', 'now', 'quickly', 'hurry', 'asap', 'important'],
    EmotionalTone.CALM: ['relax', 'easy', 'slowly', 'no rush', 'take your time', 'don\'t worry'],
}


# === Intonation Patterns ===

# Pitch contours for different sentence types (percentage through sentence -> pitch offset in semitones)
PITCH_CONTOURS = {
    SentenceType.STATEMENT: [
        (0.0, 0), (0.2, 1), (0.5, 0.5), (0.8, 0), (1.0, -2)  # Falling at end
    ],
    SentenceType.QUESTION_YES_NO: [
        (0.0, 0), (0.3, 0), (0.6, 0), (0.8, 1), (1.0, 4)  # Rising at end
    ],
    SentenceType.QUESTION_WH: [
        (0.0, 2), (0.2, 1), (0.5, 0), (0.8, 0), (1.0, -1)  # High start, slight fall
    ],
    SentenceType.EXCLAMATION: [
        (0.0, 2), (0.2, 3), (0.4, 2), (0.7, 1), (1.0, -1)  # Higher overall, emphatic
    ],
    SentenceType.COMMAND: [
        (0.0, 1), (0.3, 0.5), (0.6, 0), (0.8, 0), (1.0, -1)  # Firm, level
    ],
    SentenceType.LIST: [
        (0.0, 0), (0.5, 1), (1.0, 0)  # Each item rises, reset
    ],
    SentenceType.CONTINUATION: [
        (0.0, 0), (0.5, 0), (0.8, 0.5), (1.0, 1)  # Slight rise at end
    ]
}

# Emotional prosody modifiers
EMOTIONAL_PROSODY = {
    EmotionalTone.NEUTRAL: ProsodySettings(rate=1.0, pitch=0, pitch_range=1.0),
    EmotionalTone.FRIENDLY: ProsodySettings(rate=1.05, pitch=1, pitch_range=1.2),
    EmotionalTone.PROFESSIONAL: ProsodySettings(rate=0.95, pitch=-0.5, pitch_range=0.9),
    EmotionalTone.EXCITED: ProsodySettings(rate=1.15, pitch=2, pitch_range=1.5),
    EmotionalTone.CONCERNED: ProsodySettings(rate=0.9, pitch=-1, pitch_range=0.8),
    EmotionalTone.APOLOGETIC: ProsodySettings(rate=0.9, pitch=-1.5, pitch_range=0.7),
    EmotionalTone.ENCOURAGING: ProsodySettings(rate=1.05, pitch=1.5, pitch_range=1.3),
    EmotionalTone.CALM: ProsodySettings(rate=0.85, pitch=-0.5, pitch_range=0.8),
    EmotionalTone.URGENT: ProsodySettings(rate=1.2, pitch=1, pitch_range=1.1),
}

# Pause durations (milliseconds)
PAUSE_DURATIONS = {
    'comma': 150,
    'semicolon': 250,
    'colon': 200,
    'period': 400,
    'question': 400,
    'exclamation': 350,
    'ellipsis': 500,
    'dash': 200,
    'paragraph': 600,
    'breath': 100,      # Natural breathing pause
    'emphasis': 50,     # Short pause before emphasized word
}


# === Main Intonation Engine ===

class IntonationEngine:
    """
    Engine for adding human-like intonation to speech.
    
    Usage:
        engine = IntonationEngine()
        
        # Analyze text and get intonation data
        result = engine.analyze("Hello! How are you today?")
        
        # Get SSML for TTS engines
        ssml = result.ssml
        
        # Get prosody markers for custom TTS
        markers = result.prosody_markers
        
        # Apply to pyttsx3
        engine.apply_to_pyttsx3(tts_engine, result)
    """
    
    def __init__(self, default_tone: EmotionalTone = EmotionalTone.FRIENDLY):
        """
        Initialize the intonation engine.
        
        Args:
            default_tone: Default emotional tone for speech
        """
        self.default_tone = default_tone
        self.words_per_minute = 150  # Average speaking rate
    
    def analyze(self, text: str, emotional_tone: Optional[EmotionalTone] = None) -> IntonationResult:
        """
        Analyze text and generate intonation data.
        
        Args:
            text: The text to analyze
            emotional_tone: Override emotional tone (auto-detected if None)
            
        Returns:
            IntonationResult with annotations and SSML
        """
        # Split into sentences
        sentences = self._split_sentences(text)
        
        # Detect or use provided emotional tone
        if emotional_tone is None:
            emotional_tone = self._detect_emotion(text)
        
        # Analyze each sentence
        annotated_sentences = []
        for sentence in sentences:
            annotation = self._analyze_sentence(sentence, emotional_tone)
            annotated_sentences.append(annotation)
        
        # Generate SSML
        ssml = self._generate_ssml(annotated_sentences, emotional_tone)
        
        # Generate prosody markers
        markers = self._generate_prosody_markers(annotated_sentences)
        
        # Estimate duration
        word_count = len(text.split())
        estimated_duration = int((word_count / self.words_per_minute) * 60 * 1000)
        
        return IntonationResult(
            original_text=text,
            annotated_sentences=annotated_sentences,
            ssml=ssml,
            prosody_markers=markers,
            estimated_duration_ms=estimated_duration
        )
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Split on sentence-ending punctuation
        pattern = r'(?<=[.!?])\s+'
        sentences = re.split(pattern, text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _detect_emotion(self, text: str) -> EmotionalTone:
        """Detect emotional tone from text content"""
        text_lower = text.lower()
        
        # Score each emotion
        scores = {}
        for tone, keywords in EMOTIONAL_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            scores[tone] = score
        
        # Return highest scoring emotion (or default)
        if scores:
            best_tone = max(scores, key=scores.get)
            if scores[best_tone] > 0:
                return best_tone
        
        return self.default_tone
    
    def _detect_sentence_type(self, sentence: str) -> SentenceType:
        """Detect the type of sentence for intonation pattern"""
        sentence = sentence.strip()
        
        # Check punctuation
        if sentence.endswith('?'):
            # Determine if WH-question or yes/no question
            first_word = sentence.split()[0].lower() if sentence.split() else ""
            if first_word in WH_WORDS or any(sentence.lower().startswith(wh) for wh in WH_WORDS):
                return SentenceType.QUESTION_WH
            return SentenceType.QUESTION_YES_NO
        
        if sentence.endswith('!'):
            return SentenceType.EXCLAMATION
        
        # Check for commands (imperative)
        first_word = sentence.split()[0].lower() if sentence.split() else ""
        command_verbs = {'click', 'open', 'close', 'go', 'find', 'show', 'tell', 'let', 'please', 'try'}
        if first_word in command_verbs:
            return SentenceType.COMMAND
        
        # Check for lists (contains commas separating items)
        if sentence.count(',') >= 2 and ' and ' in sentence.lower():
            return SentenceType.LIST
        
        # Check for continuation
        if any(sentence.lower().startswith(cw) for cw in ['also', 'and', 'additionally', 'moreover']):
            return SentenceType.CONTINUATION
        
        # Check if ends with comma or colon (incomplete)
        if sentence.endswith(',') or sentence.endswith(':'):
            return SentenceType.CONTINUATION
        
        return SentenceType.STATEMENT
    
    def _analyze_sentence(self, sentence: str, emotional_tone: EmotionalTone) -> SentenceAnnotation:
        """Analyze a single sentence"""
        sentence_type = self._detect_sentence_type(sentence)
        
        # Analyze words
        words = self._tokenize(sentence)
        word_annotations = []
        
        for i, word in enumerate(words):
            annotation = self._analyze_word(word, i, len(words), sentence_type)
            word_annotations.append(annotation)
        
        # Calculate final pitch change based on sentence type
        contour = PITCH_CONTOURS.get(sentence_type, PITCH_CONTOURS[SentenceType.STATEMENT])
        final_pitch = contour[-1][1] if contour else 0
        
        # Apply emotional prosody modifiers
        prosody = EMOTIONAL_PROSODY.get(emotional_tone, EMOTIONAL_PROSODY[EmotionalTone.NEUTRAL])
        
        return SentenceAnnotation(
            text=sentence,
            sentence_type=sentence_type,
            emotional_tone=emotional_tone,
            words=word_annotations,
            final_pitch_change=final_pitch + prosody.pitch,
            overall_rate=prosody.rate,
            overall_pitch=prosody.pitch
        )
    
    def _tokenize(self, sentence: str) -> List[str]:
        """Tokenize sentence into words, preserving punctuation"""
        # Split on whitespace, keep punctuation attached
        return sentence.split()
    
    def _analyze_word(self, word: str, position: int, total_words: int, 
                      sentence_type: SentenceType) -> WordAnnotation:
        """Analyze a single word for prosody"""
        word_lower = word.lower().strip('.,!?;:')
        
        # Determine emphasis level
        emphasis = EmphasisLevel.NONE
        pitch_offset = 0.0
        rate_mod = 1.0
        pause_before = 0
        pause_after = 0
        is_new_info = False
        is_contrast = False
        
        # Check for emphasis triggers
        if word_lower in EMPHASIS_TRIGGERS:
            emphasis = EmphasisLevel.STRONG
            pitch_offset = 1.5
            pause_before = PAUSE_DURATIONS['emphasis']
        
        # Check for contrast words
        if word_lower in CONTRAST_WORDS:
            is_contrast = True
            emphasis = EmphasisLevel.MODERATE
            pitch_offset = 1.0
            pause_before = PAUSE_DURATIONS['comma']
        
        # Reduce emphasis on function words
        if word_lower in FUNCTION_WORDS and emphasis == EmphasisLevel.NONE:
            emphasis = EmphasisLevel.REDUCED
            pitch_offset = -0.5
            rate_mod = 1.1  # Slightly faster
        
        # All-caps words get emphasis
        if word.isupper() and len(word) > 1:
            emphasis = EmphasisLevel.STRONG
            pitch_offset = 2.0
            rate_mod = 0.9  # Slightly slower
        
        # First content word often carries sentence stress
        if position == 0 and word_lower not in FUNCTION_WORDS:
            pitch_offset += 0.5
        
        # Calculate pitch based on position in sentence (sentence melody)
        contour = PITCH_CONTOURS.get(sentence_type, PITCH_CONTOURS[SentenceType.STATEMENT])
        position_pct = position / max(total_words - 1, 1)
        contour_pitch = self._interpolate_contour(contour, position_pct)
        pitch_offset += contour_pitch
        
        # Add pause after punctuation
        if word.endswith(','):
            pause_after = PAUSE_DURATIONS['comma']
        elif word.endswith(';'):
            pause_after = PAUSE_DURATIONS['semicolon']
        elif word.endswith(':'):
            pause_after = PAUSE_DURATIONS['colon']
        elif word.endswith('.'):
            pause_after = PAUSE_DURATIONS['period']
        elif word.endswith('?'):
            pause_after = PAUSE_DURATIONS['question']
        elif word.endswith('!'):
            pause_after = PAUSE_DURATIONS['exclamation']
        elif word.endswith('...'):
            pause_after = PAUSE_DURATIONS['ellipsis']
        elif word.endswith('—') or word.endswith('-'):
            pause_after = PAUSE_DURATIONS['dash']
        
        return WordAnnotation(
            word=word,
            emphasis=emphasis,
            pitch_offset=pitch_offset,
            rate_modifier=rate_mod,
            pause_before_ms=pause_before,
            pause_after_ms=pause_after,
            is_new_info=is_new_info,
            is_contrast=is_contrast
        )
    
    def _interpolate_contour(self, contour: List[Tuple[float, float]], position: float) -> float:
        """Interpolate pitch value from contour at given position (0-1)"""
        if not contour:
            return 0.0
        
        # Find surrounding points
        for i in range(len(contour) - 1):
            if contour[i][0] <= position <= contour[i+1][0]:
                # Linear interpolation
                t = (position - contour[i][0]) / (contour[i+1][0] - contour[i][0])
                return contour[i][1] + t * (contour[i+1][1] - contour[i][1])
        
        # Return last value if beyond range
        return contour[-1][1]
    
    def _generate_ssml(self, sentences: List[SentenceAnnotation], 
                       emotional_tone: EmotionalTone) -> str:
        """Generate SSML markup for TTS engines"""
        prosody = EMOTIONAL_PROSODY.get(emotional_tone, EMOTIONAL_PROSODY[EmotionalTone.NEUTRAL])
        
        # Start SSML document
        ssml_parts = ['<speak>']
        
        # Add overall prosody wrapper
        rate_pct = int(prosody.rate * 100)
        pitch_st = f"{prosody.pitch:+.1f}st" if prosody.pitch != 0 else "0st"
        ssml_parts.append(f'<prosody rate="{rate_pct}%" pitch="{pitch_st}">')
        
        for sent in sentences:
            # Add sentence-level prosody
            sent_rate = int(sent.overall_rate * 100)
            ssml_parts.append(f'<prosody rate="{sent_rate}%">')
            
            for word_ann in sent.words:
                # Add pause before if needed
                if word_ann.pause_before_ms > 0:
                    ssml_parts.append(f'<break time="{word_ann.pause_before_ms}ms"/>')
                
                # Add word with prosody
                if word_ann.emphasis == EmphasisLevel.STRONG:
                    ssml_parts.append(f'<emphasis level="strong">{word_ann.word}</emphasis>')
                elif word_ann.emphasis == EmphasisLevel.MODERATE:
                    ssml_parts.append(f'<emphasis level="moderate">{word_ann.word}</emphasis>')
                elif word_ann.emphasis == EmphasisLevel.REDUCED:
                    ssml_parts.append(f'<emphasis level="reduced">{word_ann.word}</emphasis>')
                else:
                    # Apply pitch offset if significant
                    if abs(word_ann.pitch_offset) > 0.5:
                        pitch = f"{word_ann.pitch_offset:+.1f}st"
                        ssml_parts.append(f'<prosody pitch="{pitch}">{word_ann.word}</prosody>')
                    else:
                        ssml_parts.append(word_ann.word)
                
                ssml_parts.append(' ')
                
                # Add pause after if needed
                if word_ann.pause_after_ms > 0:
                    ssml_parts.append(f'<break time="{word_ann.pause_after_ms}ms"/>')
            
            ssml_parts.append('</prosody>')
        
        ssml_parts.append('</prosody>')
        ssml_parts.append('</speak>')
        
        return ''.join(ssml_parts)
    
    def _generate_prosody_markers(self, sentences: List[SentenceAnnotation]) -> List[Dict]:
        """Generate prosody markers for custom TTS implementations"""
        markers = []
        word_index = 0
        
        for sent in sentences:
            # Sentence start marker
            markers.append({
                'type': 'sentence_start',
                'sentence_type': sent.sentence_type.value,
                'emotional_tone': sent.emotional_tone.value,
                'overall_rate': sent.overall_rate,
                'overall_pitch': sent.overall_pitch,
                'word_index': word_index
            })
            
            for word_ann in sent.words:
                markers.append({
                    'type': 'word',
                    'word': word_ann.word,
                    'word_index': word_index,
                    'emphasis': word_ann.emphasis.value,
                    'pitch_offset': word_ann.pitch_offset,
                    'rate_modifier': word_ann.rate_modifier,
                    'pause_before_ms': word_ann.pause_before_ms,
                    'pause_after_ms': word_ann.pause_after_ms,
                    'is_contrast': word_ann.is_contrast
                })
                word_index += 1
            
            # Sentence end marker
            markers.append({
                'type': 'sentence_end',
                'final_pitch_change': sent.final_pitch_change,
                'word_index': word_index
            })
        
        return markers
    
    def apply_to_pyttsx3(self, engine, result: IntonationResult, 
                         base_rate: int = 150, base_volume: float = 0.9) -> None:
        """
        Apply intonation to a pyttsx3 engine.
        
        Note: pyttsx3 has limited prosody control. This applies what's possible:
        - Rate adjustments (via speaking segments at different rates)
        - Volume adjustments
        - Pauses (via time.sleep between segments)
        
        Args:
            engine: pyttsx3 engine instance
            result: IntonationResult from analyze()
            base_rate: Base speaking rate (words per minute)
            base_volume: Base volume (0.0 to 1.0)
        """
        import time
        
        for sent in result.annotated_sentences:
            # Apply overall sentence prosody
            prosody = EMOTIONAL_PROSODY.get(sent.emotional_tone, EMOTIONAL_PROSODY[EmotionalTone.NEUTRAL])
            
            adjusted_rate = int(base_rate * sent.overall_rate * prosody.rate)
            adjusted_volume = min(1.0, base_volume + (prosody.volume / 10))
            
            engine.setProperty('rate', adjusted_rate)
            engine.setProperty('volume', adjusted_volume)
            
            # Process words with pauses
            current_phrase = []
            
            for word_ann in sent.words:
                # Handle pause before
                if word_ann.pause_before_ms > 0 and current_phrase:
                    # Speak accumulated phrase
                    engine.say(' '.join(current_phrase))
                    engine.runAndWait()
                    time.sleep(word_ann.pause_before_ms / 1000.0)
                    current_phrase = []
                
                current_phrase.append(word_ann.word)
                
                # Handle pause after
                if word_ann.pause_after_ms > 0:
                    engine.say(' '.join(current_phrase))
                    engine.runAndWait()
                    time.sleep(word_ann.pause_after_ms / 1000.0)
                    current_phrase = []
            
            # Speak remaining phrase
            if current_phrase:
                engine.say(' '.join(current_phrase))
                engine.runAndWait()
    
    def get_natural_text(self, result: IntonationResult) -> str:
        """
        Get text with natural pause markers for simple TTS.
        Uses commas and periods to hint at pauses.
        
        Args:
            result: IntonationResult from analyze()
            
        Returns:
            Text with added pause markers
        """
        parts = []
        
        for sent in result.annotated_sentences:
            words = []
            for word_ann in sent.words:
                if word_ann.pause_before_ms >= PAUSE_DURATIONS['comma'] and words:
                    # Add a comma to indicate pause
                    if not words[-1].endswith(','):
                        words[-1] = words[-1] + ','
                
                words.append(word_ann.word)
            
            parts.append(' '.join(words))
        
        return ' '.join(parts)


# === Convenience Functions ===

_engine: Optional[IntonationEngine] = None

def get_intonation_engine(tone: EmotionalTone = EmotionalTone.FRIENDLY) -> IntonationEngine:
    """Get or create the default intonation engine"""
    global _engine
    if _engine is None:
        _engine = IntonationEngine(default_tone=tone)
    return _engine


def add_intonation(text: str, tone: str = "friendly") -> IntonationResult:
    """
    Add human-like intonation to text.
    
    Args:
        text: The text to process
        tone: Emotional tone (friendly, professional, excited, etc.)
        
    Returns:
        IntonationResult with SSML and prosody markers
    """
    try:
        emotional_tone = EmotionalTone(tone.lower())
    except ValueError:
        emotional_tone = EmotionalTone.FRIENDLY
    
    engine = get_intonation_engine()
    return engine.analyze(text, emotional_tone)


def get_ssml(text: str, tone: str = "friendly") -> str:
    """
    Get SSML-formatted text with intonation.
    
    Args:
        text: The text to process
        tone: Emotional tone
        
    Returns:
        SSML string for TTS engines
    """
    result = add_intonation(text, tone)
    return result.ssml


def speak_with_intonation(text: str, tone: str = "friendly", 
                          rate: int = 150, volume: float = 0.9) -> None:
    """
    Speak text with human-like intonation using pyttsx3.
    
    Args:
        text: The text to speak
        tone: Emotional tone
        rate: Base speaking rate
        volume: Base volume
    """
    try:
        import pyttsx3
        
        engine_instance = pyttsx3.init()
        intonation = get_intonation_engine()
        result = intonation.analyze(text, EmotionalTone(tone.lower()))
        
        intonation.apply_to_pyttsx3(engine_instance, result, rate, volume)
        
        engine_instance.stop()
    except ImportError:
        logger.error("pyttsx3 not installed. Run: pip install pyttsx3")
    except Exception as e:
        logger.error(f"Error speaking text: {e}")


def analyze_prosody(text: str) -> Dict[str, Any]:
    """
    Analyze text and return prosody information.
    
    Args:
        text: The text to analyze
        
    Returns:
        Dictionary with prosody analysis
    """
    engine = get_intonation_engine()
    result = engine.analyze(text)
    
    return {
        'text': result.original_text,
        'estimated_duration_ms': result.estimated_duration_ms,
        'sentences': [
            {
                'text': s.text,
                'type': s.sentence_type.value,
                'tone': s.emotional_tone.value,
                'final_pitch_change': s.final_pitch_change,
                'word_count': len(s.words),
                'emphasis_words': [w.word for w in s.words if w.emphasis != EmphasisLevel.NONE]
            }
            for s in result.annotated_sentences
        ]
    }


# === CLI Testing ===

if __name__ == "__main__":
    print("VoxMind Intonation Module - Testing")
    print("=" * 60)
    
    # Test sentences
    test_texts = [
        "Hello! How are you today?",
        "Found Google Chrome for you!",
        "I'm sorry, but I couldn't find that application.",
        "Please click the settings button to continue.",
        "You have three new messages, two emails, and one notification.",
        "That's absolutely amazing! Great job!",
        "WARNING: This action cannot be undone.",
    ]
    
    engine = IntonationEngine()
    
    for text in test_texts:
        print(f"\n📝 Input: {text}")
        result = engine.analyze(text)
        
        for sent in result.annotated_sentences:
            print(f"   Type: {sent.sentence_type.value}")
            print(f"   Tone: {sent.emotional_tone.value}")
            print(f"   Final pitch: {sent.final_pitch_change:+.1f} semitones")
            
            # Show emphasized words
            emphasis_words = [w.word for w in sent.words 
                           if w.emphasis in (EmphasisLevel.STRONG, EmphasisLevel.MODERATE)]
            if emphasis_words:
                print(f"   Emphasis: {', '.join(emphasis_words)}")
        
        print(f"   Duration: ~{result.estimated_duration_ms}ms")
    
    # Show SSML example
    print("\n" + "=" * 60)
    print("📄 SSML Example:")
    print("-" * 60)
    result = engine.analyze("Hello! How are you today?", EmotionalTone.FRIENDLY)
    print(result.ssml)
    
    # Test speaking (if pyttsx3 available)
    print("\n" + "=" * 60)
    try:
        import pyttsx3
        print("🔊 Speaking test phrase...")
        speak_with_intonation("Hello! Welcome to VoxMind. How can I help you today?", "friendly")
        print("✅ Speech complete!")
    except ImportError:
        print("⚠️ pyttsx3 not installed. Skipping speech test.")
