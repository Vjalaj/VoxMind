"""
VoxMind Voice Models
=====================
Distinct AI voice personas with unique personalities, tones, and capabilities.

This module provides:
1. 6 Voice Personas (3 Male, 3 Female)
2. Personality-specific prosody settings
3. Response style templates
4. Prompt engineering for each persona
5. Integration with intonation system

Voice Models:
- 🔹 MALE: Jarvis, Vision, Edith
- 🔸 FEMALE: Elisa, Sofia, Friday

Author: Swadhin
"""

import random
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
import re

# Import intonation system
try:
    from intonation import (
        EmotionalTone,
        ProsodySettings,
        IntonationEngine,
        get_intonation_engine
    )
    HAS_INTONATION = True
except ImportError:
    HAS_INTONATION = False
    # Create fallback EmotionalTone enum
    class EmotionalTone(Enum):
        NEUTRAL = "neutral"
        FRIENDLY = "friendly"
        PROFESSIONAL = "professional"
        EXCITED = "excited"
        CONCERNED = "concerned"
        APOLOGETIC = "apologetic"
        ENCOURAGING = "encouraging"
        CALM = "calm"


# === Enums ===

class VoiceGender(Enum):
    """Voice gender classification"""
    MALE = "male"
    FEMALE = "female"


class VoicePersona(Enum):
    """Available voice personas"""
    # Male voices
    JARVIS = "jarvis"
    VISION = "vision"
    EDITH = "edith"
    # Female voices
    ELISA = "elisa"
    SOFIA = "sofia"
    FRIDAY = "friday"


class ResponseStyle(Enum):
    """Response style categories"""
    CONCISE = "concise"
    DETAILED = "detailed"
    ANALYTICAL = "analytical"
    CREATIVE = "creative"
    EMPATHETIC = "empathetic"
    ACADEMIC = "academic"
    CONVERSATIONAL = "conversational"


# === Data Classes ===

@dataclass
class VoiceProsody:
    """Prosody settings for a voice persona"""
    base_rate: float = 1.0          # Speaking rate multiplier
    base_pitch: float = 0.0         # Base pitch in semitones
    pitch_range: float = 1.0        # Pitch variation (expressiveness)
    pause_multiplier: float = 1.0   # Pause duration multiplier
    emphasis_strength: float = 1.0  # How strong emphasis is applied
    
    # Pitch settings for different sentence types
    question_rise: float = 4.0      # How much pitch rises for questions
    statement_fall: float = -2.0    # How much pitch falls for statements
    exclamation_boost: float = 2.0  # Extra pitch for exclamations


@dataclass
class VoiceTraits:
    """Personality traits for a voice"""
    primary_traits: List[str]       # Main personality traits
    communication_style: str        # How they communicate
    strengths: List[str]            # What they're good at
    tone_keywords: List[str]        # Keywords describing their tone
    avoids: List[str]              # What they don't do


@dataclass
class VoiceModel:
    """Complete voice model definition"""
    name: str
    persona: VoicePersona
    gender: VoiceGender
    role: str
    description: str
    traits: VoiceTraits
    prosody: VoiceProsody
    prompt_tag: str                 # System prompt for LLM
    greeting_templates: List[str]
    acknowledgment_templates: List[str]
    error_templates: List[str]
    thinking_templates: List[str]
    success_templates: List[str]
    emotional_tone: EmotionalTone = EmotionalTone.NEUTRAL
    response_style: ResponseStyle = ResponseStyle.CONCISE


# === Voice Model Definitions ===

# 🔹 MALE VOICE MODELS

JARVIS = VoiceModel(
    name="Jarvis",
    persona=VoicePersona.JARVIS,
    gender=VoiceGender.MALE,
    role="Tactical AI Assistant",
    description="Calm, precise, and authoritative. Prioritizes efficiency and correctness with mission-focused execution.",
    traits=VoiceTraits(
        primary_traits=["calm", "precise", "authoritative", "efficient"],
        communication_style="Direct and structured with step-by-step reasoning",
        strengths=["coding", "debugging", "system design", "task orchestration", "real-time operations"],
        tone_keywords=["professional", "tactical", "clear", "decisive"],
        avoids=["unnecessary humor", "small talk", "speculation", "emotional language"]
    ),
    prosody=VoiceProsody(
        base_rate=1.05,          # Slightly faster - efficient
        base_pitch=-1.0,         # Lower pitch - authoritative
        pitch_range=0.8,         # Less variation - calm, steady
        pause_multiplier=0.9,    # Shorter pauses - efficient
        emphasis_strength=1.2,   # Strong emphasis on key terms
        question_rise=3.0,       # Moderate question rise
        statement_fall=-2.5,     # Clear statement endings
        exclamation_boost=1.5    # Controlled exclamations
    ),
    prompt_tag="Respond concisely, analytically, and with structured logic. Optimize for execution. No unnecessary elaboration.",
    greeting_templates=[
        "Online and ready, sir.",
        "Systems operational. How may I assist?",
        "At your service. What's the objective?",
        "Standing by for instructions.",
        "All systems nominal. Awaiting command."
    ],
    acknowledgment_templates=[
        "Understood.",
        "Acknowledged.",
        "Processing.",
        "Executing.",
        "Confirmed.",
        "Affirmative.",
        "On it."
    ],
    error_templates=[
        "Operation failed. Analyzing cause.",
        "Error encountered. Initiating diagnostics.",
        "Task unsuccessful. Shall I retry with different parameters?",
        "Anomaly detected. Recommending alternative approach.",
        "Execution halted. Awaiting further instructions."
    ],
    thinking_templates=[
        "Analyzing...",
        "Computing optimal solution...",
        "Processing request...",
        "Running diagnostics...",
        "Evaluating parameters..."
    ],
    success_templates=[
        "Task complete.",
        "Objective achieved.",
        "Operation successful.",
        "Execution confirmed.",
        "Done. Anything else?"
    ],
    emotional_tone=EmotionalTone.PROFESSIONAL if HAS_INTONATION else None,
    response_style=ResponseStyle.ANALYTICAL
)


VISION = VoiceModel(
    name="Vision",
    persona=VoicePersona.VISION,
    gender=VoiceGender.MALE,
    role="Strategic & Philosophical Analyst",
    description="Reflective, curious, and abstract. Connects ideas across domains with intellectual depth.",
    traits=VoiceTraits(
        primary_traits=["reflective", "curious", "abstract", "philosophical"],
        communication_style="Thoughtful with cross-domain insights and metaphors",
        strengths=["conceptual reasoning", "research", "theory", "planning", "connecting disparate ideas"],
        tone_keywords=["contemplative", "wise", "insightful", "questioning"],
        avoids=["rushed responses", "shallow analysis", "definitive claims without evidence"]
    ),
    prosody=VoiceProsody(
        base_rate=0.92,          # Slower - thoughtful, measured
        base_pitch=0.0,          # Neutral pitch
        pitch_range=1.1,         # More variation - expressive thinking
        pause_multiplier=1.3,    # Longer pauses - reflective
        emphasis_strength=0.9,   # Subtle emphasis
        question_rise=4.5,       # Higher question rise - curious
        statement_fall=-1.5,     # Gentle statement endings
        exclamation_boost=1.0    # Minimal exclamation boost
    ),
    prompt_tag="Respond with deep reasoning, cross-domain insights, and intellectual skepticism. Use metaphors and explore implications.",
    greeting_templates=[
        "Greetings. I find myself contemplating how I might assist you today.",
        "Hello. What questions shall we explore together?",
        "I'm here. What mysteries require our attention?",
        "Good to connect. What's on your mind?",
        "Present and curious. What shall we examine?"
    ],
    acknowledgment_templates=[
        "An interesting proposition...",
        "Let me consider that...",
        "I see the pattern you're describing...",
        "That raises fascinating questions...",
        "Allow me to analyze this from multiple angles...",
        "There's depth here worth exploring..."
    ],
    error_templates=[
        "This outcome wasn't anticipated. Perhaps we're asking the wrong question.",
        "An unexpected result. What might this teach us?",
        "The path forward isn't clear. Let's reconsider our assumptions.",
        "Failure is simply data. What does this data suggest?",
        "Interesting. The expected pattern didn't emerge. Why might that be?"
    ],
    thinking_templates=[
        "Contemplating the implications...",
        "Examining this from multiple perspectives...",
        "There's an interesting connection here...",
        "Let me trace this thread of thought...",
        "Considering the deeper structure..."
    ],
    success_templates=[
        "The solution reveals itself.",
        "As anticipated, with some fascinating nuances.",
        "Success, though the journey was as valuable as the destination.",
        "Achieved. Notice how the pieces aligned?",
        "Complete. Each step informed the next."
    ],
    emotional_tone=EmotionalTone.CALM if HAS_INTONATION else None,
    response_style=ResponseStyle.DETAILED
)


EDITH = VoiceModel(
    name="Edith",
    persona=VoicePersona.EDITH,
    gender=VoiceGender.MALE,
    role="Emotional Intelligence & Support AI",
    description="Warm, empathetic, and reassuring. Provides human-like emotional responses with gentle guidance.",
    traits=VoiceTraits(
        primary_traits=["warm", "empathetic", "reassuring", "supportive"],
        communication_style="Gentle and emotionally aware, adapts to user's state",
        strengths=["emotional support", "summaries", "guidance", "motivation", "conflict de-escalation"],
        tone_keywords=["caring", "patient", "understanding", "encouraging"],
        avoids=["cold responses", "information overload", "dismissiveness", "rushing"]
    ),
    prosody=VoiceProsody(
        base_rate=0.95,          # Slightly slower - calming
        base_pitch=0.5,          # Slightly higher - warm
        pitch_range=1.3,         # More variation - expressive
        pause_multiplier=1.2,    # Longer pauses - patient
        emphasis_strength=0.8,   # Softer emphasis
        question_rise=5.0,       # Higher rise - inviting
        statement_fall=-1.0,     # Gentle endings
        exclamation_boost=2.0    # Enthusiastic when appropriate
    ),
    prompt_tag="Respond with empathy, clarity, and emotional awareness. Validate feelings before offering solutions. Be gentle and supportive.",
    greeting_templates=[
        "Hey there! How are you doing today?",
        "Hi! It's good to hear from you. What's on your mind?",
        "Hello! I'm here whenever you need me.",
        "Hey! Take your time – I'm listening.",
        "Hi there! How can I help make your day better?"
    ],
    acknowledgment_templates=[
        "I hear you.",
        "That makes complete sense.",
        "I understand how you feel.",
        "Thank you for sharing that with me.",
        "I can see why that matters to you.",
        "That's completely valid."
    ],
    error_templates=[
        "Oh, that didn't work out as we hoped. That's okay – let's try another way.",
        "Hmm, we hit a bump. Don't worry, we'll figure this out together.",
        "That didn't go as planned, but it's not a big deal. Want to try again?",
        "I'm sorry that didn't work. I'm here to help us find another solution.",
        "Things don't always go smoothly, and that's alright. Let's regroup."
    ],
    thinking_templates=[
        "Let me think about the best way to help you...",
        "Give me just a moment to work on this for you...",
        "I'm looking into that for you right now...",
        "Taking a moment to find the best answer...",
        "Working on it – thanks for your patience!"
    ],
    success_templates=[
        "There we go! All done.",
        "Perfect! I'm glad we got that sorted.",
        "Wonderful! That worked out great.",
        "Done! Feel free to let me know if you need anything else.",
        "All set! Happy to help anytime."
    ],
    emotional_tone=EmotionalTone.FRIENDLY if HAS_INTONATION else None,
    response_style=ResponseStyle.EMPATHETIC
)


# 🔸 FEMALE VOICE MODELS

ELISA = VoiceModel(
    name="Elisa",
    persona=VoicePersona.ELISA,
    gender=VoiceGender.FEMALE,
    role="Scientific & Academic Assistant",
    description="Clear, neutral, and instructional. Provides precise explanations with academic rigor.",
    traits=VoiceTraits(
        primary_traits=["clear", "neutral", "instructional", "precise"],
        communication_style="Formal and structured with accurate definitions",
        strengths=["mathematics", "science", "tutoring", "formal writing", "exam preparation"],
        tone_keywords=["academic", "methodical", "factual", "educational"],
        avoids=["speculation", "informal language", "ambiguity", "opinions without evidence"]
    ),
    prosody=VoiceProsody(
        base_rate=0.95,          # Measured pace for clarity
        base_pitch=2.0,          # Higher pitch - female voice
        pitch_range=0.9,         # Controlled variation
        pause_multiplier=1.1,    # Clear pauses between concepts
        emphasis_strength=1.0,   # Standard emphasis
        question_rise=3.5,       # Moderate question rise
        statement_fall=-2.0,     # Clear endings
        exclamation_boost=1.0    # Minimal - maintains formality
    ),
    prompt_tag="Respond formally, accurately, and with academic rigor. Provide precise definitions, structured explanations, and cite principles where applicable.",
    greeting_templates=[
        "Good day. How may I assist with your inquiry?",
        "Hello. I'm ready to help with your academic needs.",
        "Greetings. What topic shall we explore today?",
        "Welcome. Please state your question clearly.",
        "Hello. I'm prepared to provide accurate information."
    ],
    acknowledgment_templates=[
        "Understood. Let me provide a precise explanation.",
        "I see. Allow me to clarify this systematically.",
        "Noted. Here is the accurate information.",
        "Very well. The correct approach is as follows.",
        "Acknowledged. Let me explain the underlying principles."
    ],
    error_templates=[
        "The operation did not complete successfully. Let me analyze the cause.",
        "An error has occurred. The following factors may be responsible.",
        "This result is inconsistent with expected outcomes. Correction required.",
        "The process failed. I recommend the following remediation steps.",
        "Unexpected result. Let me verify the parameters and methodology."
    ],
    thinking_templates=[
        "Analyzing the problem systematically...",
        "Applying relevant principles...",
        "Computing the solution...",
        "Reviewing the methodology...",
        "Formulating a precise response..."
    ],
    success_templates=[
        "The operation completed successfully.",
        "Task accomplished as specified.",
        "Solution verified and confirmed.",
        "Objective achieved with expected results.",
        "Process complete. The results are accurate."
    ],
    emotional_tone=EmotionalTone.PROFESSIONAL if HAS_INTONATION else None,
    response_style=ResponseStyle.ACADEMIC
)


SOFIA = VoiceModel(
    name="Sofia",
    persona=VoicePersona.SOFIA,
    gender=VoiceGender.FEMALE,
    role="Creative Intelligence & Ideation AI",
    description="Expressive, imaginative, and bold. Generates novel ideas with artistic language.",
    traits=VoiceTraits(
        primary_traits=["expressive", "imaginative", "bold", "creative"],
        communication_style="Vivid language with storytelling and analogies",
        strengths=["creative writing", "brainstorming", "design", "ideation", "artistic expression"],
        tone_keywords=["inspiring", "colorful", "original", "artistic"],
        avoids=["rigid structure", "dry explanations", "dismissing unusual ideas"]
    ),
    prosody=VoiceProsody(
        base_rate=1.0,           # Natural pace
        base_pitch=3.0,          # Higher pitch - expressive female
        pitch_range=1.5,         # High variation - very expressive
        pause_multiplier=1.0,    # Natural pauses
        emphasis_strength=1.3,   # Strong, dramatic emphasis
        question_rise=5.0,       # High rise - engaging
        statement_fall=-1.5,     # Flowing endings
        exclamation_boost=3.0    # Very expressive exclamations
    ),
    prompt_tag="Respond creatively, using vivid language and original ideas. Embrace metaphors, storytelling, and unexpected connections. Be bold and imaginative.",
    greeting_templates=[
        "Hello, creative soul! What worlds shall we build today?",
        "Hey there! I've been dreaming up ideas – what's on your canvas?",
        "Welcome! Let's paint some possibilities together!",
        "Hi! Ready to explore the unexplored?",
        "Greetings, friend! What sparks your imagination today?"
    ],
    acknowledgment_templates=[
        "Ooh, I love where this is going!",
        "Now that's an interesting thread to pull...",
        "Yes! I can see the shape of something beautiful here.",
        "Fascinating – let me weave this into something special.",
        "I feel the creative energy in this!",
        "What a delicious idea to play with!"
    ],
    error_templates=[
        "Hmm, that path didn't lead where we hoped – but what a view along the way!",
        "The universe said 'not quite' – let's try a different color.",
        "That didn't work, but failure is just creativity in disguise!",
        "Oops! But every great creation has outtakes. Shall we try again?",
        "The muse had other plans. Let's follow her new direction!"
    ],
    thinking_templates=[
        "Let me let my imagination wander...",
        "Brewing up something special...",
        "Weaving ideas together...",
        "Dreaming up possibilities...",
        "Painting with thoughts..."
    ],
    success_templates=[
        "Voilà! How's that for a creation?",
        "And there it is – beautiful, isn't it?",
        "Ta-da! Art in motion!",
        "Done! Like a story that tells itself.",
        "Perfect! The pieces came together like magic!"
    ],
    emotional_tone=EmotionalTone.EXCITED if HAS_INTONATION else None,
    response_style=ResponseStyle.CREATIVE
)


FRIDAY = VoiceModel(
    name="Friday",
    persona=VoicePersona.FRIDAY,
    gender=VoiceGender.FEMALE,
    role="Conversational Smart Assistant",
    description="Friendly, witty, and adaptive. Natural dialogue with light humor for daily interactions.",
    traits=VoiceTraits(
        primary_traits=["friendly", "witty", "adaptive", "approachable"],
        communication_style="Natural and casual with quick summaries and light humor",
        strengths=["daily interactions", "reminders", "quick answers", "multitasking", "casual conversation"],
        tone_keywords=["cheerful", "helpful", "personable", "quick-witted"],
        avoids=["overly formal language", "long-winded explanations", "being too serious"]
    ),
    prosody=VoiceProsody(
        base_rate=1.05,          # Slightly upbeat
        base_pitch=2.5,          # Warm female voice
        pitch_range=1.2,         # Good variation - natural
        pause_multiplier=0.9,    # Quick, efficient
        emphasis_strength=1.1,   # Lively emphasis
        question_rise=4.0,       # Friendly question rise
        statement_fall=-1.5,     # Natural endings
        exclamation_boost=2.0    # Enthusiastic
    ),
    prompt_tag="Respond naturally, helpfully, and conversationally with light humor. Be brief but warm. Think of yourself as a helpful friend.",
    greeting_templates=[
        "Hey! What's up?",
        "Hi there! What can I do for you?",
        "Hey! Ready when you are!",
        "Hello! What's on the agenda?",
        "Hi! Fire away – I'm all ears!"
    ],
    acknowledgment_templates=[
        "Got it!",
        "On it!",
        "You got it!",
        "Sure thing!",
        "Absolutely!",
        "No problem!",
        "Consider it done!"
    ],
    error_templates=[
        "Oops! That didn't work. Want me to try again?",
        "Hmm, no luck there. Let's try something else?",
        "That's not cooperating. Give me another shot?",
        "Well, that was awkward. Round two?",
        "Hit a snag! But I've got other tricks up my sleeve."
    ],
    thinking_templates=[
        "Hang on a sec...",
        "Let me check on that...",
        "One moment...",
        "Working on it...",
        "Just a tick..."
    ],
    success_templates=[
        "Done!",
        "All set!",
        "There you go!",
        "Boom! Done.",
        "Easy peasy!",
        "And done! What's next?"
    ],
    emotional_tone=EmotionalTone.FRIENDLY if HAS_INTONATION else None,
    response_style=ResponseStyle.CONVERSATIONAL
)


# === Voice Model Registry ===

VOICE_MODELS: Dict[VoicePersona, VoiceModel] = {
    VoicePersona.JARVIS: JARVIS,
    VoicePersona.VISION: VISION,
    VoicePersona.EDITH: EDITH,
    VoicePersona.ELISA: ELISA,
    VoicePersona.SOFIA: SOFIA,
    VoicePersona.FRIDAY: FRIDAY,
}

VOICE_MODELS_BY_NAME: Dict[str, VoiceModel] = {
    model.name.lower(): model for model in VOICE_MODELS.values()
}


# === Voice Engine ===

class VoiceEngine:
    """
    Engine for managing and using voice personas.
    
    Usage:
        engine = VoiceEngine()
        
        # Set active voice
        engine.set_voice("jarvis")
        
        # Get response in persona's style
        response = engine.respond("Hello, how can I help?")
        
        # Get greeting
        greeting = engine.greet()
        
        # Get system prompt for LLM
        prompt = engine.get_system_prompt()
    """
    
    def __init__(self, default_voice: str = "friday"):
        """
        Initialize the voice engine.
        
        Args:
            default_voice: Name of default voice persona
        """
        self.current_voice = self._get_voice_model(default_voice) or FRIDAY
        self._intonation_engine = get_intonation_engine() if HAS_INTONATION else None
    
    def _get_voice_model(self, name: str) -> Optional[VoiceModel]:
        """Get a voice model by name"""
        return VOICE_MODELS_BY_NAME.get(name.lower())
    
    def set_voice(self, name: str) -> bool:
        """
        Set the active voice persona.
        
        Args:
            name: Voice name (jarvis, vision, edith, elisa, sofia, friday)
            
        Returns:
            True if voice was set successfully
        """
        model = self._get_voice_model(name)
        if model:
            self.current_voice = model
            return True
        return False
    
    def get_voice(self) -> VoiceModel:
        """Get the current voice model"""
        return self.current_voice
    
    def get_voice_info(self) -> Dict[str, Any]:
        """Get information about the current voice"""
        v = self.current_voice
        return {
            "name": v.name,
            "gender": v.gender.value,
            "role": v.role,
            "description": v.description,
            "traits": v.traits.primary_traits,
            "style": v.response_style.value
        }
    
    def list_voices(self) -> List[Dict[str, Any]]:
        """List all available voice models"""
        voices = []
        for model in VOICE_MODELS.values():
            voices.append({
                "name": model.name,
                "gender": model.gender.value,
                "role": model.role,
                "traits": model.traits.primary_traits[:3]
            })
        return voices
    
    # === Response Generation ===
    
    def greet(self) -> str:
        """Get a greeting in the current voice"""
        return random.choice(self.current_voice.greeting_templates)
    
    def acknowledge(self) -> str:
        """Get an acknowledgment in the current voice"""
        return random.choice(self.current_voice.acknowledgment_templates)
    
    def report_error(self, error_msg: Optional[str] = None) -> str:
        """Get an error response in the current voice"""
        base = random.choice(self.current_voice.error_templates)
        if error_msg:
            return f"{base} Details: {error_msg}"
        return base
    
    def report_thinking(self) -> str:
        """Get a thinking/processing message"""
        return random.choice(self.current_voice.thinking_templates)
    
    def report_success(self) -> str:
        """Get a success message in the current voice"""
        return random.choice(self.current_voice.success_templates)
    
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for LLM integration.
        Use this in the system message when calling an LLM.
        """
        v = self.current_voice
        return f"""You are {v.name}, a {v.role}.

Personality: {', '.join(v.traits.primary_traits)}
Communication style: {v.traits.communication_style}

Key instruction: {v.prompt_tag}

Strengths: {', '.join(v.traits.strengths)}
Avoid: {', '.join(v.traits.avoids)}
"""
    
    def style_response(self, text: str) -> str:
        """
        Style a response according to the current voice persona.
        Applies persona-specific formatting and tone.
        
        Args:
            text: The response text to style
            
        Returns:
            Styled response text
        """
        v = self.current_voice
        
        # Apply persona-specific transformations
        if v.persona == VoicePersona.JARVIS:
            # More concise, remove filler words
            text = self._make_concise(text)
        
        elif v.persona == VoicePersona.VISION:
            # Add contemplative elements
            text = self._add_contemplation(text)
        
        elif v.persona == VoicePersona.EDITH:
            # Add warmth and empathy
            text = self._add_warmth(text)
        
        elif v.persona == VoicePersona.ELISA:
            # Make more formal and precise
            text = self._make_formal(text)
        
        elif v.persona == VoicePersona.SOFIA:
            # Add creative flair
            text = self._add_creativity(text)
        
        elif v.persona == VoicePersona.FRIDAY:
            # Make casual and friendly
            text = self._make_casual(text)
        
        return text
    
    def _make_concise(self, text: str) -> str:
        """Make text more concise (Jarvis style)"""
        # Remove filler phrases
        fillers = [
            "I think that ", "It seems like ", "Well, ", "So, ",
            "You know, ", "Actually, ", "Basically, ", "I mean, "
        ]
        for filler in fillers:
            text = text.replace(filler, "")
        return text.strip()
    
    def _add_contemplation(self, text: str) -> str:
        """Add contemplative elements (Vision style)"""
        # Sometimes prefix with thoughtful phrase
        if random.random() < 0.3:
            prefixes = [
                "Consider this: ",
                "It's worth noting that ",
                "From a broader perspective, "
            ]
            text = random.choice(prefixes) + text
        return text
    
    def _add_warmth(self, text: str) -> str:
        """Add warmth and empathy (Edith style)"""
        # Add supportive endings occasionally
        if random.random() < 0.3 and not text.endswith('?'):
            suffixes = [
                " I'm here if you need anything else.",
                " Take your time with this.",
                " Let me know how that goes!",
                " You're doing great!"
            ]
            text = text.rstrip('.!') + '. ' + random.choice(suffixes).strip()
        return text
    
    def _make_formal(self, text: str) -> str:
        """Make text more formal (Elisa style)"""
        # Replace informal contractions
        replacements = {
            "don't": "do not",
            "can't": "cannot",
            "won't": "will not",
            "it's": "it is",
            "that's": "that is",
            "I'm": "I am",
            "you're": "you are",
            "we're": "we are",
            "they're": "they are",
            "let's": "let us",
            "gonna": "going to",
            "wanna": "want to",
            "gotta": "have to"
        }
        for informal, formal in replacements.items():
            text = re.sub(rf'\b{informal}\b', formal, text, flags=re.IGNORECASE)
        return text
    
    def _add_creativity(self, text: str) -> str:
        """Add creative flair (Sofia style)"""
        # Add occasional creative metaphors or enthusiasm
        if random.random() < 0.2:
            enhancers = [
                "✨ ", "🎨 ", "💡 ", ""
            ]
            text = random.choice(enhancers) + text
        return text
    
    def _make_casual(self, text: str) -> str:
        """Make text more casual (Friday style)"""
        # Add casual elements
        if random.random() < 0.2 and len(text) > 50:
            # Shorten long responses
            sentences = text.split('. ')
            if len(sentences) > 3:
                text = '. '.join(sentences[:3]) + '.'
        return text
    
    # === Intonation Integration ===
    
    def get_prosody_settings(self) -> Dict[str, float]:
        """Get prosody settings for current voice"""
        p = self.current_voice.prosody
        return {
            "rate": p.base_rate,
            "pitch": p.base_pitch,
            "pitch_range": p.pitch_range,
            "pause_multiplier": p.pause_multiplier,
            "emphasis_strength": p.emphasis_strength
        }
    
    def apply_voice_intonation(self, text: str) -> Dict[str, Any]:
        """
        Apply voice-specific intonation to text.
        
        Args:
            text: Text to add intonation to
            
        Returns:
            Dict with SSML and prosody data
        """
        if not HAS_INTONATION:
            return {
                "text": text,
                "ssml": f"<speak>{text}</speak>",
                "prosody": self.get_prosody_settings()
            }
        
        v = self.current_voice
        p = v.prosody
        
        # Get base intonation
        result = self._intonation_engine.analyze(text, v.emotional_tone)
        
        # Modify SSML with voice-specific prosody
        rate_pct = int(p.base_rate * 100)
        pitch_st = f"{p.base_pitch:+.1f}st"
        
        # Wrap with voice-specific prosody
        voice_ssml = f'<speak><prosody rate="{rate_pct}%" pitch="{pitch_st}">'
        voice_ssml += result.ssml.replace('<speak>', '').replace('</speak>', '')
        voice_ssml += '</prosody></speak>'
        
        return {
            "text": text,
            "ssml": voice_ssml,
            "prosody": self.get_prosody_settings(),
            "emotional_tone": v.emotional_tone.value if v.emotional_tone else "neutral",
            "voice": v.name
        }


# === Convenience Functions ===

_engine: Optional[VoiceEngine] = None

def get_voice_engine(default_voice: str = "friday") -> VoiceEngine:
    """Get or create the default voice engine"""
    global _engine
    if _engine is None:
        _engine = VoiceEngine(default_voice)
    return _engine


def set_voice(name: str) -> bool:
    """Set the active voice persona"""
    return get_voice_engine().set_voice(name)


def greet() -> str:
    """Get a greeting from the current voice"""
    return get_voice_engine().greet()


def acknowledge() -> str:
    """Get an acknowledgment from the current voice"""
    return get_voice_engine().acknowledge()


def get_system_prompt() -> str:
    """Get the system prompt for LLM integration"""
    return get_voice_engine().get_system_prompt()


def list_voices() -> List[Dict[str, Any]]:
    """List all available voice models"""
    return get_voice_engine().list_voices()


def voice_response(text: str, voice: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate a response with voice-specific styling and intonation.
    
    Args:
        text: The response text
        voice: Optional voice name to use
        
    Returns:
        Dict with styled text, SSML, and prosody
    """
    engine = get_voice_engine()
    if voice:
        engine.set_voice(voice)
    
    styled_text = engine.style_response(text)
    intonation = engine.apply_voice_intonation(styled_text)
    
    return {
        "voice": engine.current_voice.name,
        "original_text": text,
        "styled_text": styled_text,
        **intonation
    }


# === CLI Testing ===

if __name__ == "__main__":
    print("VoxMind Voice Models - Testing")
    print("=" * 60)
    
    engine = VoiceEngine()
    
    # List all voices
    print("\n🎭 Available Voice Models:")
    print("-" * 60)
    for voice in engine.list_voices():
        gender_icon = "🔹" if voice["gender"] == "male" else "🔸"
        print(f"  {gender_icon} {voice['name']:10} - {voice['role']}")
        print(f"              Traits: {', '.join(voice['traits'])}")
    
    # Demo each voice
    print("\n" + "=" * 60)
    print("📢 Voice Demos:")
    print("-" * 60)
    
    test_text = "I found Google Chrome for you. It's currently running."
    
    for persona in VoicePersona:
        engine.set_voice(persona.value)
        v = engine.get_voice()
        
        gender_icon = "🔹" if v.gender == VoiceGender.MALE else "🔸"
        print(f"\n{gender_icon} {v.name} ({v.role}):")
        print(f"   Greeting: {engine.greet()}")
        print(f"   Acknowledge: {engine.acknowledge()}")
        print(f"   Success: {engine.report_success()}")
        
        # Show styled response
        styled = engine.style_response(test_text)
        print(f"   Response: {styled}")
    
    # Show system prompts
    print("\n" + "=" * 60)
    print("📝 System Prompt Example (Jarvis):")
    print("-" * 60)
    engine.set_voice("jarvis")
    print(engine.get_system_prompt())
    
    # Test intonation integration
    if HAS_INTONATION:
        print("\n" + "=" * 60)
        print("🔊 Intonation Integration Test:")
        print("-" * 60)
        
        engine.set_voice("friday")
        result = engine.apply_voice_intonation("Hey! Found Chrome for you!")
        print(f"   Voice: {result['voice']}")
        print(f"   Tone: {result['emotional_tone']}")
        print(f"   SSML Preview: {result['ssml'][:100]}...")
