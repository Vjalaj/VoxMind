"""
Question Handler for VoxMind
=============================
Main entry point for the advanced question answering system.

Orchestrates:
1. Question classification
2. Knowledge fetching
3. Elaborate answer generation

Usage:
    from Swadhin.question_answering import answer_question, QuestionAnswerer
    
    # Simple async interface
    result = await answer_question("Why is the sky blue?")
    print(result.detailed_answer)
    
    # Full control
    answerer = QuestionAnswerer()
    result = await answerer.answer("How does machine learning work?")
    
    # Access different answer formats
    print(result.brief_answer)      # Quick answer
    print(result.standard_answer)   # Moderate detail
    print(result.detailed_answer)   # Full elaboration
    print(result.speech_optimized)  # For TTS
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from .question_classifier import QuestionClassifier, QuestionAnalysis, QuestionType
from .knowledge_fetcher import KnowledgeFetcher, AggregatedKnowledge, fetch_knowledge
from .elaborate_answerer import ElaborateAnswerer, AnswerResult, AnswerStyle

logger = logging.getLogger(__name__)


@dataclass
class AnswerConfig:
    """Configuration for answer generation."""
    include_examples: bool = True
    include_perspectives: bool = True
    include_discussions: bool = True
    include_academic: bool = False
    max_sources: int = 10
    max_answer_length: int = 2000
    answer_style: AnswerStyle = AnswerStyle.CONVERSATIONAL
    timeout: float = 30.0  # seconds


class QuestionAnswerer:
    """
    Main class for answering questions elaborately.
    
    Supports all question types:
    - WHAT: Definitions, explanations
    - WHY: Reasons, causes, motivations  
    - WHICH: Choices, comparisons
    - WHEN: Time, dates, timing
    - HOW: Methods, processes, instructions
    - IF: Conditionals, hypotheticals
    - IS IT/THERE: Boolean, existence verification
    """
    
    def __init__(self, config: Optional[AnswerConfig] = None):
        """Initialize with optional configuration."""
        self.config = config or AnswerConfig()
        self.classifier = QuestionClassifier()
        self.fetcher = KnowledgeFetcher()
        self.answerer = ElaborateAnswerer(style=self.config.answer_style)
        
        # Statistics
        self._questions_answered = 0
        self._total_time = 0.0
    
    async def answer(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None,
        override_config: Optional[AnswerConfig] = None,
    ) -> AnswerResult:
        """
        Answer a question elaborately.
        
        Args:
            question: The question to answer
            context: Optional context (previous conversation, user preferences)
            override_config: Optional config override for this question
            
        Returns:
            AnswerResult with multiple answer formats
        """
        start_time = time.time()
        config = override_config or self.config
        
        try:
            # Step 1: Classify the question
            logger.info(f"Classifying question: {question[:50]}...")
            analysis = self.classifier.classify(question)
            logger.info(f"Question type: {analysis.primary_type.name}, Topic: {analysis.topic}")
            
            # Step 2: Generate search queries
            queries = self.classifier.get_search_queries(analysis)
            logger.info(f"Generated {len(queries)} search queries")
            
            # Step 3: Fetch comprehensive knowledge
            logger.info("Fetching knowledge from multiple sources...")
            knowledge = await asyncio.wait_for(
                self.fetcher.fetch_comprehensive(
                    queries=queries,
                    question_type=analysis.primary_type.name.lower(),
                    max_sources=config.max_sources,
                    include_discussions=config.include_discussions,
                    include_academic=config.include_academic,
                ),
                timeout=config.timeout
            )
            logger.info(f"Fetched {knowledge.total_sources} sources, {knowledge.total_words} words")
            
            # Step 4: Generate elaborate answer
            logger.info("Generating elaborate answer...")
            result = self.answerer.generate_answer(
                analysis=analysis,
                knowledge=knowledge,
                include_examples=config.include_examples,
                include_perspectives=config.include_perspectives,
                max_length=config.max_answer_length,
            )
            
            # Update stats
            elapsed = time.time() - start_time
            self._questions_answered += 1
            self._total_time += elapsed
            logger.info(f"Answer generated in {elapsed:.2f}s")
            
            return result
            
        except asyncio.TimeoutError:
            logger.warning(f"Question answering timed out after {config.timeout}s")
            return self._create_timeout_result(question)
        
        except Exception as e:
            logger.error(f"Error answering question: {e}")
            return self._create_error_result(question, str(e))
    
    def answer_sync(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AnswerResult:
        """
        Synchronous wrapper for answer().
        
        For use in non-async contexts.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create new loop for nested call
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run,
                        self.answer(question, context)
                    )
                    return future.result(timeout=self.config.timeout + 5)
            else:
                return loop.run_until_complete(self.answer(question, context))
        except Exception as e:
            return self._create_error_result(question, str(e))
    
    async def classify_only(self, question: str) -> QuestionAnalysis:
        """Just classify a question without answering."""
        return self.classifier.classify(question)
    
    async def get_quick_answer(self, question: str) -> str:
        """Get a quick brief answer."""
        result = await self.answer(question)
        return result.brief_answer
    
    async def get_detailed_answer(self, question: str) -> str:
        """Get a detailed elaborate answer."""
        result = await self.answer(question)
        return result.detailed_answer
    
    async def get_speech_answer(self, question: str) -> str:
        """Get an answer optimized for text-to-speech."""
        result = await self.answer(question)
        return result.speech_optimized
    
    def _create_timeout_result(self, question: str) -> AnswerResult:
        """Create a result for timeout."""
        msg = "I'm sorry, it took too long to gather information. Could you try rephrasing your question?"
        return AnswerResult(
            question=question,
            question_type=QuestionType.UNKNOWN,
            brief_answer=msg,
            standard_answer=msg,
            detailed_answer=msg,
            main_points=[],
            examples=[],
            perspectives=[],
            reasoning=[],
            steps=[],
            comparisons=[],
            timeline=[],
            confidence=0.0,
            sources_used=0,
            answer_style=self.config.answer_style,
            follow_up_questions=[],
            speech_optimized=msg,
        )
    
    def _create_error_result(self, question: str, error: str) -> AnswerResult:
        """Create a result for errors."""
        msg = f"I encountered an issue while researching your question. {error}"
        return AnswerResult(
            question=question,
            question_type=QuestionType.UNKNOWN,
            brief_answer=msg,
            standard_answer=msg,
            detailed_answer=msg,
            main_points=[],
            examples=[],
            perspectives=[],
            reasoning=[],
            steps=[],
            comparisons=[],
            timeline=[],
            confidence=0.0,
            sources_used=0,
            answer_style=self.config.answer_style,
            follow_up_questions=[],
            speech_optimized=msg,
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get answering statistics."""
        avg_time = self._total_time / max(self._questions_answered, 1)
        return {
            'questions_answered': self._questions_answered,
            'total_time': self._total_time,
            'average_time': avg_time,
        }
    
    async def close(self):
        """Close resources."""
        await self.fetcher.close()


# Global instance
_answerer: Optional[QuestionAnswerer] = None


def get_answerer() -> QuestionAnswerer:
    """Get the global question answerer instance."""
    global _answerer
    if _answerer is None:
        _answerer = QuestionAnswerer()
    return _answerer


async def answer_question(
    question: str,
    detailed: bool = False,
    for_speech: bool = False,
) -> AnswerResult:
    """
    Main entry point for answering questions.
    
    Args:
        question: The question to answer
        detailed: If True, prioritizes detailed answer
        for_speech: If True, optimizes for TTS
        
    Returns:
        AnswerResult with all answer formats
        
    Usage:
        result = await answer_question("Why do birds migrate?")
        print(result.detailed_answer)
        
        # For voice assistants
        result = await answer_question("How do computers work?", for_speech=True)
        print(result.speech_optimized)
    """
    answerer = get_answerer()
    return await answerer.answer(question)


async def quick_answer(question: str) -> str:
    """Get a quick 1-2 sentence answer."""
    answerer = get_answerer()
    return await answerer.get_quick_answer(question)


async def discuss_topic(question: str) -> str:
    """Get a discussive, elaborate answer."""
    answerer = get_answerer()
    return await answerer.get_detailed_answer(question)


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demo the question answering system."""
    print("=" * 70)
    print("VOXMIND ADVANCED QUESTION ANSWERING SYSTEM")
    print("=" * 70)
    
    # Test questions of different types
    test_questions = [
        # WHAT questions
        "What is quantum computing?",
        
        # WHY questions  
        "Why do leaves change color in fall?",
        
        # HOW questions
        "How does machine learning work?",
        
        # WHICH questions
        "Which programming language should I learn first?",
        
        # WHEN questions
        "When was the internet invented?",
        
        # IF questions
        "What would happen if bees went extinct?",
        
        # IS/Boolean questions
        "Is artificial intelligence dangerous?",
    ]
    
    answerer = QuestionAnswerer()
    
    for question in test_questions:
        print(f"\n{'='*70}")
        print(f"QUESTION: {question}")
        print("-" * 70)
        
        result = await answerer.answer(question)
        
        print(f"Type: {result.question_type.name}")
        print(f"Sources: {result.sources_used}")
        print(f"Confidence: {result.confidence:.0%}")
        
        print(f"\n📝 BRIEF ANSWER:")
        print(result.brief_answer)
        
        print(f"\n📚 STANDARD ANSWER:")
        print(result.standard_answer)
        
        if result.main_points:
            print(f"\n🎯 KEY POINTS:")
            for point in result.main_points[:3]:
                print(f"  • {point[:100]}...")
        
        if result.follow_up_questions:
            print(f"\n💭 FOLLOW-UP QUESTIONS:")
            for q in result.follow_up_questions:
                print(f"  • {q}")
        
        print()
    
    # Cleanup
    await answerer.close()
    
    print("=" * 70)
    print("Demo complete!")


if __name__ == "__main__":
    asyncio.run(demo())
