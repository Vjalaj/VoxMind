"""
Elaborate Answerer for VoxMind
===============================
Generates elaborate, discussive answers based on question type.

Key features:
- Question-type specific answer structures
- Discussive and intuitive responses
- Multiple perspectives when relevant
- Examples and analogies
- Proper reasoning chains for "why" questions
- Step-by-step for "how" questions
- Comparative analysis for "which" questions
"""

import re
import random
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from .question_classifier import QuestionType, QuestionAnalysis
from .knowledge_fetcher import AggregatedKnowledge, FetchedContent

logger = logging.getLogger(__name__)


class AnswerStyle(Enum):
    """Answer delivery styles."""
    FORMAL = "formal"
    CONVERSATIONAL = "conversational"
    EDUCATIONAL = "educational"
    ANALYTICAL = "analytical"


@dataclass
class AnswerResult:
    """Result of answering a question."""
    question: str
    question_type: QuestionType
    
    # Different answer formats
    brief_answer: str           # 1-2 sentences
    standard_answer: str        # 3-5 sentences
    detailed_answer: str        # Full elaborate answer
    
    # Answer components
    main_points: List[str]      # Key points extracted
    examples: List[str]         # Examples if applicable
    perspectives: List[Dict[str, str]]  # Different viewpoints
    reasoning: List[str]        # Reasoning chain (for why questions)
    steps: List[str]            # Steps (for how questions)
    comparisons: List[Dict[str, Any]]  # Comparisons (for which questions)
    timeline: List[Dict[str, str]]  # Timeline (for when questions)
    
    # Metadata
    confidence: float
    sources_used: int
    answer_style: AnswerStyle
    follow_up_questions: List[str]
    
    # For speech output
    speech_optimized: str       # Optimized for TTS


class ElaborateAnswerer:
    """
    Generates elaborate, discussive answers based on question analysis.
    """
    
    # Answer templates by question type
    ANSWER_STARTERS = {
        QuestionType.WHAT: [
            "{topic} is {definition}",
            "In essence, {topic} refers to {definition}",
            "To put it simply, {topic} means {definition}",
            "{topic} can be understood as {definition}",
            "Let me explain {topic}: {definition}",
        ],
        QuestionType.WHY: [
            "The reason {topic} is {reason}",
            "{topic} because {reason}",
            "This happens because {reason}",
            "There are several reasons for this: {reason}",
            "The explanation lies in {reason}",
            "To understand why, consider that {reason}",
        ],
        QuestionType.HOW: [
            "Here's how {topic} works: {process}",
            "The process involves {process}",
            "To {topic}, you would {process}",
            "This works by {process}",
            "The mechanism behind this is {process}",
            "Let me walk you through how this works: {process}",
        ],
        QuestionType.WHEN: [
            "{topic} occurred in {time}",
            "This happened {time}",
            "The timing was {time}",
            "Historically, {time}",
            "{time} marks when {topic}",
        ],
        QuestionType.WHICH: [
            "When comparing options, {comparison}",
            "The best choice depends on {comparison}",
            "Let's look at the alternatives: {comparison}",
            "Each option has its merits: {comparison}",
            "To help you decide: {comparison}",
        ],
        QuestionType.IF: [
            "If that were the case, {consequence}",
            "In that scenario, {consequence}",
            "The likely outcome would be {consequence}",
            "Hypothetically speaking, {consequence}",
            "Should that happen, {consequence}",
        ],
        QuestionType.IS_BOOLEAN: [
            "Yes, {confirmation}",
            "No, {denial}",
            "It depends: {nuance}",
            "Generally speaking, {answer}",
            "The answer is {answer}, because {reason}",
        ],
        QuestionType.WHO: [
            "{person} is {description}",
            "{person} was {description}",
            "This refers to {person}, who {description}",
        ],
        QuestionType.WHERE: [
            "{topic} is located in {location}",
            "You can find this in {location}",
            "The location is {location}",
        ],
    }
    
    # Transition phrases for elaboration
    ELABORATION_TRANSITIONS = [
        "To elaborate further,",
        "Building on this,",
        "Additionally,",
        "It's worth noting that",
        "Furthermore,",
        "What's particularly interesting is",
        "This connects to",
        "In other words,",
        "Put another way,",
        "To give you more context,",
    ]
    
    # Discussion phrases
    DISCUSSION_PHRASES = [
        "There are different perspectives on this.",
        "Some argue that",
        "On the other hand,",
        "However, it's important to consider",
        "This is a nuanced topic because",
        "Experts have varying opinions:",
        "The debate centers around",
        "While some believe",
        "Others contend that",
        "Looking at this from another angle,",
    ]
    
    # Example introducers
    EXAMPLE_PHRASES = [
        "For example,",
        "Consider this example:",
        "To illustrate,",
        "Here's a concrete case:",
        "Take, for instance,",
        "A good example of this is",
        "You can see this in action when",
    ]
    
    def __init__(self, style: AnswerStyle = AnswerStyle.CONVERSATIONAL):
        """Initialize with preferred answer style."""
        self.style = style
    
    def generate_answer(
        self,
        analysis: QuestionAnalysis,
        knowledge: AggregatedKnowledge,
        include_examples: bool = True,
        include_perspectives: bool = True,
        max_length: int = 2000,
    ) -> AnswerResult:
        """
        Generate an elaborate answer based on question analysis and knowledge.
        
        Args:
            analysis: Question analysis from classifier
            knowledge: Aggregated knowledge from fetcher
            include_examples: Whether to include examples
            include_perspectives: Whether to include different viewpoints
            max_length: Maximum answer length in characters
            
        Returns:
            AnswerResult with multiple answer formats
        """
        question_type = analysis.primary_type
        
        # Extract relevant information
        main_points = self._extract_main_points(knowledge, analysis)
        examples = self._extract_examples(knowledge) if include_examples else []
        perspectives = self._extract_perspectives(knowledge) if include_perspectives else []
        
        # Generate type-specific content
        reasoning = self._generate_reasoning(analysis, knowledge) if question_type == QuestionType.WHY else []
        steps = self._generate_steps(analysis, knowledge) if question_type == QuestionType.HOW else []
        comparisons = self._generate_comparisons(analysis, knowledge) if question_type == QuestionType.WHICH else []
        timeline = knowledge.timeline if question_type == QuestionType.WHEN else []
        
        # Generate different answer lengths
        brief = self._generate_brief_answer(analysis, main_points)
        standard = self._generate_standard_answer(analysis, main_points, examples)
        detailed = self._generate_detailed_answer(
            analysis, knowledge, main_points, examples, perspectives,
            reasoning, steps, comparisons, timeline, max_length
        )
        
        # Generate follow-up questions
        follow_ups = self._generate_follow_up_questions(analysis, knowledge)
        
        # Optimize for speech
        speech_optimized = self._optimize_for_speech(standard)
        
        return AnswerResult(
            question=analysis.original_question,
            question_type=question_type,
            brief_answer=brief,
            standard_answer=standard,
            detailed_answer=detailed,
            main_points=main_points,
            examples=examples,
            perspectives=perspectives,
            reasoning=reasoning,
            steps=steps,
            comparisons=comparisons,
            timeline=timeline,
            confidence=knowledge.total_sources / 10,  # Normalize
            sources_used=knowledge.total_sources,
            answer_style=self.style,
            follow_up_questions=follow_ups,
            speech_optimized=speech_optimized,
        )
    
    def _extract_main_points(
        self,
        knowledge: AggregatedKnowledge,
        analysis: QuestionAnalysis
    ) -> List[str]:
        """Extract main points relevant to the question."""
        points = []
        
        # Start with main facts
        points.extend(knowledge.main_facts[:5])
        
        # Add consensus points
        for cp in knowledge.consensus_points[:3]:
            if cp not in points:
                points.append(cp)
        
        # Extract from high-reliability content
        for content in knowledge.contents:
            if content.reliability_score >= 0.8:
                for kp in content.key_points[:2]:
                    if kp not in points and len(kp) > 30:
                        points.append(kp)
        
        return points[:8]  # Limit to 8 points
    
    def _extract_examples(self, knowledge: AggregatedKnowledge) -> List[str]:
        """Extract examples from content."""
        examples = []
        
        # Look for example patterns in content
        example_patterns = [
            r'[Ff]or example[,:]?\s+([^.]+\.)',
            r'[Ss]uch as\s+([^.]+\.)',
            r'[Ll]ike\s+([^.]+\.)',
            r'[Ff]or instance[,:]?\s+([^.]+\.)',
            r'[Cc]onsider\s+([^.]+\.)',
        ]
        
        for content in knowledge.contents[:5]:
            for pattern in example_patterns:
                matches = re.findall(pattern, content.content)
                for match in matches[:2]:
                    if len(match) > 20 and match not in examples:
                        examples.append(match.strip())
        
        return examples[:5]
    
    def _extract_perspectives(
        self,
        knowledge: AggregatedKnowledge
    ) -> List[Dict[str, str]]:
        """Extract different perspectives."""
        perspectives = knowledge.different_perspectives.copy()
        
        # Look for contrasting views in content
        contrast_patterns = [
            r'[Ss]ome (?:argue|believe|think) that ([^.]+)',
            r'[Oo]thers (?:argue|believe|contend) that ([^.]+)',
            r'[Hh]owever[,]?\s+([^.]+)',
            r'[Oo]n the other hand[,]?\s+([^.]+)',
        ]
        
        for content in knowledge.contents:
            if content.content_type == 'discussion':
                for pattern in contrast_patterns:
                    matches = re.findall(pattern, content.content)
                    for match in matches[:1]:
                        perspectives.append({
                            'source': content.source,
                            'viewpoint': match.strip(),
                        })
        
        return perspectives[:4]
    
    def _generate_reasoning(
        self,
        analysis: QuestionAnalysis,
        knowledge: AggregatedKnowledge
    ) -> List[str]:
        """Generate reasoning chain for WHY questions."""
        reasons = []
        
        # Look for causal language
        causal_patterns = [
            r'because\s+([^.]+)',
            r'due to\s+([^.]+)',
            r'as a result of\s+([^.]+)',
            r'caused by\s+([^.]+)',
            r'the reason (?:is|being)\s+([^.]+)',
            r'this (?:is|was) because\s+([^.]+)',
            r'(?:leads?|led) to\s+([^.]+)',
        ]
        
        for content in knowledge.contents[:5]:
            for pattern in causal_patterns:
                matches = re.findall(pattern, content.content, re.I)
                for match in matches[:2]:
                    reason = match.strip()
                    if len(reason) > 20 and reason not in reasons:
                        reasons.append(reason)
        
        return reasons[:5]
    
    def _generate_steps(
        self,
        analysis: QuestionAnalysis,
        knowledge: AggregatedKnowledge
    ) -> List[str]:
        """Generate step-by-step guide for HOW questions."""
        steps = []
        
        # Look for step indicators
        step_patterns = [
            r'(?:first|1\.?|step\s*1)[,:]?\s+([^.]+)',
            r'(?:second|2\.?|step\s*2)[,:]?\s+([^.]+)',
            r'(?:third|3\.?|step\s*3)[,:]?\s+([^.]+)',
            r'(?:then|next|after that)[,:]?\s+([^.]+)',
            r'(?:finally|lastly)[,:]?\s+([^.]+)',
        ]
        
        for content in knowledge.contents[:5]:
            # Look for numbered lists
            numbered = re.findall(r'(\d+)[\.\)]\s+([^.]+\.)', content.content)
            for num, step in numbered[:5]:
                if step.strip() not in steps:
                    steps.append(step.strip())
            
            # Look for procedural language
            for pattern in step_patterns:
                matches = re.findall(pattern, content.content, re.I)
                for match in matches[:1]:
                    if match.strip() not in steps:
                        steps.append(match.strip())
        
        return steps[:7]  # Limit to 7 steps
    
    def _generate_comparisons(
        self,
        analysis: QuestionAnalysis,
        knowledge: AggregatedKnowledge
    ) -> List[Dict[str, Any]]:
        """Generate comparison data for WHICH questions."""
        comparisons = []
        
        # Look for comparative language
        compare_patterns = [
            r'(\w+)\s+is\s+(?:better|worse|faster|slower|more|less)\s+than\s+(\w+)',
            r'compared to\s+(\w+)[,]?\s+(\w+)',
            r'(\w+)\s+(?:versus|vs\.?)\s+(\w+)',
        ]
        
        for content in knowledge.contents[:5]:
            for pattern in compare_patterns:
                matches = re.findall(pattern, content.content, re.I)
                for match in matches[:2]:
                    if len(match) >= 2:
                        comparisons.append({
                            'option_a': match[0],
                            'option_b': match[1] if len(match) > 1 else '',
                            'context': content.content[:200],
                        })
        
        return comparisons[:4]
    
    def _generate_brief_answer(
        self,
        analysis: QuestionAnalysis,
        main_points: List[str]
    ) -> str:
        """Generate a 1-2 sentence brief answer."""
        if not main_points:
            return f"I couldn't find specific information about {analysis.topic}."
        
        # Use first main point
        first_point = main_points[0]
        
        # Clean and format
        if len(first_point) > 200:
            # Find sentence boundary
            sentences = first_point.split('. ')
            first_point = sentences[0] + '.'
        
        return first_point
    
    def _generate_standard_answer(
        self,
        analysis: QuestionAnalysis,
        main_points: List[str],
        examples: List[str]
    ) -> str:
        """Generate a 3-5 sentence standard answer."""
        # Handle empty knowledge
        if not main_points and not examples:
            return f"I couldn't find detailed information about {analysis.topic}. Could you try rephrasing your question or asking about a more specific aspect?"
        
        parts = []
        
        # Opening based on question type
        starters = self.ANSWER_STARTERS.get(analysis.primary_type, [])
        if starters and main_points:
            starter = random.choice(starters)
            # Fill in template
            first_point = main_points[0] if main_points else "this topic"
            parts.append(first_point)
        elif main_points:
            parts.append(main_points[0])
        
        # Add 1-2 more points
        for point in main_points[1:3]:
            transition = random.choice(self.ELABORATION_TRANSITIONS)
            parts.append(f"{transition} {point}")
        
        # Add example if available
        if examples:
            example_intro = random.choice(self.EXAMPLE_PHRASES)
            parts.append(f"{example_intro} {examples[0]}")
        
        result = ' '.join(parts)
        return result if result.strip() else f"I found limited information about {analysis.topic}."
    
    def _generate_detailed_answer(
        self,
        analysis: QuestionAnalysis,
        knowledge: AggregatedKnowledge,
        main_points: List[str],
        examples: List[str],
        perspectives: List[Dict[str, str]],
        reasoning: List[str],
        steps: List[str],
        comparisons: List[Dict[str, Any]],
        timeline: List[Dict[str, str]],
        max_length: int
    ) -> str:
        """Generate a full elaborate answer."""
        sections = []
        
        # Introduction
        intro = self._write_introduction(analysis, main_points)
        sections.append(intro)
        
        # Main explanation
        explanation = self._write_main_explanation(analysis, main_points, knowledge)
        sections.append(explanation)
        
        # Type-specific sections
        if analysis.primary_type == QuestionType.WHY and reasoning:
            sections.append(self._write_reasoning_section(reasoning))
        
        if analysis.primary_type == QuestionType.HOW and steps:
            sections.append(self._write_steps_section(steps))
        
        if analysis.primary_type == QuestionType.WHICH and comparisons:
            sections.append(self._write_comparison_section(comparisons))
        
        if analysis.primary_type == QuestionType.WHEN and timeline:
            sections.append(self._write_timeline_section(timeline))
        
        # Examples section
        if examples and analysis.requires_examples:
            sections.append(self._write_examples_section(examples))
        
        # Different perspectives (for discussive answers)
        if perspectives and (analysis.requires_discussion or analysis.requires_opinion):
            sections.append(self._write_perspectives_section(perspectives))
        
        # Conclusion
        conclusion = self._write_conclusion(analysis)
        sections.append(conclusion)
        
        # Join and trim if needed
        full_answer = '\n\n'.join(sections)
        
        if len(full_answer) > max_length:
            # Trim to max length at sentence boundary
            full_answer = full_answer[:max_length]
            last_period = full_answer.rfind('.')
            if last_period > max_length * 0.7:
                full_answer = full_answer[:last_period + 1]
        
        return full_answer
    
    def _write_introduction(
        self,
        analysis: QuestionAnalysis,
        main_points: List[str]
    ) -> str:
        """Write an engaging introduction."""
        # If no main points, return a fallback
        if not main_points:
            return f"I searched for information about {analysis.topic}, but couldn't find comprehensive details. Let me share what I could gather."
        
        intros = {
            QuestionType.WHAT: f"Let me explain {analysis.topic} in detail.",
            QuestionType.WHY: f"This is a great question. Let me walk you through the reasons.",
            QuestionType.HOW: f"I'll explain the process step by step.",
            QuestionType.WHEN: f"Let me give you the timeline and context.",
            QuestionType.WHICH: f"This depends on several factors. Let me help you compare.",
            QuestionType.IF: f"This is an interesting hypothetical. Here's what we can consider.",
            QuestionType.IS_BOOLEAN: f"Let me give you a nuanced answer to this.",
            QuestionType.WHO: f"Here's what we know about this.",
            QuestionType.WHERE: f"Let me provide the location and context.",
        }
        
        intro = intros.get(analysis.primary_type, "Here's what I found:")
        
        if main_points:
            intro += f" {main_points[0]}"
        
        return intro
    
    def _write_main_explanation(
        self,
        analysis: QuestionAnalysis,
        main_points: List[str],
        knowledge: AggregatedKnowledge
    ) -> str:
        """Write the main explanation section."""
        if not main_points or len(main_points) <= 1:
            # Try to extract something from knowledge contents directly
            if knowledge.contents:
                content = knowledge.contents[0].content[:500]
                return content
            return ""
        
        parts = []
        
        for i, point in enumerate(main_points[1:5]):
            if i > 0:
                transition = random.choice(self.ELABORATION_TRANSITIONS)
                parts.append(f"{transition} {point}")
            else:
                parts.append(point)
        
        return ' '.join(parts)
    
    def _write_reasoning_section(self, reasoning: List[str]) -> str:
        """Write reasoning section for WHY questions."""
        if not reasoning:
            return ""
        
        parts = ["**Understanding the Reasons:**"]
        for i, reason in enumerate(reasoning, 1):
            parts.append(f"{i}. {reason}")
        
        return '\n'.join(parts)
    
    def _write_steps_section(self, steps: List[str]) -> str:
        """Write step-by-step section for HOW questions."""
        if not steps:
            return ""
        
        parts = ["**Step-by-Step Process:**"]
        for i, step in enumerate(steps, 1):
            parts.append(f"{i}. {step}")
        
        return '\n'.join(parts)
    
    def _write_comparison_section(
        self,
        comparisons: List[Dict[str, Any]]
    ) -> str:
        """Write comparison section for WHICH questions."""
        if not comparisons:
            return ""
        
        parts = ["**Comparing the Options:**"]
        for comp in comparisons:
            parts.append(f"• {comp.get('option_a', '')} vs {comp.get('option_b', '')}")
        
        return '\n'.join(parts)
    
    def _write_timeline_section(
        self,
        timeline: List[Dict[str, str]]
    ) -> str:
        """Write timeline section for WHEN questions."""
        if not timeline:
            return ""
        
        parts = ["**Timeline:**"]
        for event in timeline:
            parts.append(f"• {event.get('date', '')}: {event.get('event', '')}")
        
        return '\n'.join(parts)
    
    def _write_examples_section(self, examples: List[str]) -> str:
        """Write examples section."""
        if not examples:
            return ""
        
        parts = ["**Examples:**"]
        for example in examples:
            parts.append(f"• {example}")
        
        return '\n'.join(parts)
    
    def _write_perspectives_section(
        self,
        perspectives: List[Dict[str, str]]
    ) -> str:
        """Write different perspectives section."""
        if not perspectives:
            return ""
        
        parts = ["**Different Perspectives:**"]
        parts.append(random.choice(self.DISCUSSION_PHRASES))
        
        for perspective in perspectives:
            source = perspective.get('source', 'Some')
            viewpoint = perspective.get('viewpoint', '')
            parts.append(f"• From {source}: {viewpoint}")
        
        return '\n'.join(parts)
    
    def _write_conclusion(self, analysis: QuestionAnalysis) -> str:
        """Write a concluding remark."""
        conclusions = {
            QuestionType.WHAT: "I hope this clarifies what you wanted to know!",
            QuestionType.WHY: "These are the key reasons behind this. Does this help explain it?",
            QuestionType.HOW: "Following these steps should help you accomplish this.",
            QuestionType.WHEN: "This should give you the temporal context you need.",
            QuestionType.WHICH: "The best choice really depends on your specific needs and priorities.",
            QuestionType.IF: "Of course, actual outcomes could vary based on many factors.",
            QuestionType.IS_BOOLEAN: "I hope this addresses your question thoroughly.",
        }
        
        return conclusions.get(analysis.primary_type, "Let me know if you'd like more details!")
    
    def _generate_follow_up_questions(
        self,
        analysis: QuestionAnalysis,
        knowledge: AggregatedKnowledge
    ) -> List[str]:
        """Generate suggested follow-up questions."""
        follow_ups = []
        topic = analysis.topic
        
        # Type-specific follow-ups
        type_follow_ups = {
            QuestionType.WHAT: [
                f"How does {topic} work in practice?",
                f"What are the benefits of {topic}?",
                f"Can you give more examples of {topic}?",
            ],
            QuestionType.WHY: [
                f"What are the implications of this?",
                f"How can we address this?",
                f"Are there exceptions to this?",
            ],
            QuestionType.HOW: [
                f"What tools do I need for this?",
                f"What are common mistakes to avoid?",
                f"How long does this typically take?",
            ],
            QuestionType.WHICH: [
                f"What are the costs involved?",
                f"What do experts recommend?",
                f"What factors should I prioritize?",
            ],
        }
        
        follow_ups = type_follow_ups.get(analysis.primary_type, [])[:3]
        
        return follow_ups
    
    def _optimize_for_speech(self, text: str) -> str:
        """Optimize answer for text-to-speech."""
        # Remove markdown
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        text = re.sub(r'^\s*[\*\-]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
        
        # Simplify punctuation
        text = re.sub(r'\s+', ' ', text)
        
        # Limit length for speech
        if len(text) > 400:
            sentences = text.split('. ')
            text = '. '.join(sentences[:4])
            if not text.endswith('.'):
                text += '.'
        
        return text.strip()
