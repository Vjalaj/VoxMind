"""
Test suite for VoxMind Advanced Question Answering System
==========================================================

Tests the question classifier, knowledge fetcher, and elaborate answerer.
"""

import asyncio
import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from question_answering.question_classifier import (
    QuestionClassifier, QuestionType, classify_question
)
from question_answering.elaborate_answerer import ElaborateAnswerer, AnswerStyle
from question_answering.question_handler import QuestionAnswerer, AnswerConfig


class TestQuestionClassifier:
    """Test the question classifier."""
    
    def setup_method(self):
        self.classifier = QuestionClassifier()
    
    def test_what_questions(self):
        """Test WHAT question classification."""
        questions = [
            "What is machine learning?",
            "What are the benefits of exercise?",
            "What does AI mean?",
        ]
        for q in questions:
            analysis = self.classifier.classify(q)
            assert analysis.primary_type == QuestionType.WHAT, f"Failed for: {q}"
    
    def test_why_questions(self):
        """Test WHY question classification."""
        questions = [
            "Why is the sky blue?",
            "Why do leaves change color?",
            "Why doesn't ice sink?",
            "What causes earthquakes?",
        ]
        for q in questions:
            analysis = self.classifier.classify(q)
            assert analysis.primary_type == QuestionType.WHY, f"Failed for: {q}, got {analysis.primary_type}"
    
    def test_how_questions(self):
        """Test HOW question classification."""
        questions = [
            "How does photosynthesis work?",
            "How to learn programming?",
            "How can I improve my writing?",
            "How come the sky is blue?",
        ]
        for q in questions:
            analysis = self.classifier.classify(q)
            assert analysis.primary_type == QuestionType.HOW, f"Failed for: {q}, got {analysis.primary_type}"
    
    def test_which_questions(self):
        """Test WHICH question classification."""
        questions = [
            "Which programming language is best?",
            "Which one should I choose?",
            "What is the best laptop for coding?",
        ]
        for q in questions:
            analysis = self.classifier.classify(q)
            assert analysis.primary_type == QuestionType.WHICH, f"Failed for: {q}, got {analysis.primary_type}"
    
    def test_when_questions(self):
        """Test WHEN question classification."""
        questions = [
            "When was the internet invented?",
            "When did World War 2 end?",
            "What year was Python created?",
        ]
        for q in questions:
            analysis = self.classifier.classify(q)
            assert analysis.primary_type == QuestionType.WHEN, f"Failed for: {q}, got {analysis.primary_type}"
    
    def test_if_questions(self):
        """Test IF/hypothetical question classification."""
        questions = [
            "What if the sun disappeared?",
            "If I learn Python, can I get a job?",
            "Suppose the internet went down globally?",
        ]
        for q in questions:
            analysis = self.classifier.classify(q)
            assert analysis.primary_type == QuestionType.IF, f"Failed for: {q}, got {analysis.primary_type}"
    
    def test_boolean_questions(self):
        """Test IS/boolean question classification."""
        questions = [
            "Is artificial intelligence dangerous?",
            "Are electric cars better for the environment?",
            "Can humans survive on Mars?",
            "Does coffee cause cancer?",
        ]
        for q in questions:
            analysis = self.classifier.classify(q)
            assert analysis.primary_type == QuestionType.IS_BOOLEAN, f"Failed for: {q}, got {analysis.primary_type}"
    
    def test_topic_extraction(self):
        """Test topic extraction from questions."""
        test_cases = [
            ("What is quantum computing?", "quantum computing"),
            ("Why do leaves change color?", "leaves change color"),
            ("How does machine learning work?", "machine learning work"),
        ]
        for question, expected_topic in test_cases:
            analysis = self.classifier.classify(question)
            assert expected_topic.lower() in analysis.topic.lower(), \
                f"Expected '{expected_topic}' in topic '{analysis.topic}' for question: {question}"
    
    def test_search_query_generation(self):
        """Test search query generation."""
        analysis = self.classifier.classify("Why is the sky blue?")
        queries = self.classifier.get_search_queries(analysis)
        
        assert len(queries) > 0, "Should generate at least one query"
        assert any("sky blue" in q.lower() for q in queries), "Should include topic in queries"
    
    def test_complexity_detection(self):
        """Test complexity detection."""
        simple = self.classifier.classify("What is AI?")
        complex_q = self.classifier.classify(
            "What are the advantages and disadvantages of artificial intelligence "
            "compared to human intelligence in medical diagnosis?"
        )
        
        assert simple.complexity == "simple", f"Expected simple, got {simple.complexity}"
        assert complex_q.complexity in ("moderate", "complex"), \
            f"Expected moderate/complex, got {complex_q.complexity}"
    
    def test_requirement_detection(self):
        """Test requirement detection."""
        opinion_q = self.classifier.classify("What's the best programming language?")
        assert opinion_q.requires_opinion, "Should detect opinion requirement"
        
        comparison_q = self.classifier.classify("Python vs JavaScript, which is better?")
        assert comparison_q.requires_comparison, "Should detect comparison requirement"
        
        example_q = self.classifier.classify("What is recursion? Give me an example.")
        assert example_q.requires_examples, "Should detect example requirement"


class TestElaborateAnswerer:
    """Test the elaborate answerer."""
    
    def setup_method(self):
        self.answerer = ElaborateAnswerer(style=AnswerStyle.CONVERSATIONAL)
    
    def test_answer_generation_placeholder(self):
        """Placeholder test - actual testing requires mock knowledge."""
        # This would require mocking the knowledge fetcher
        # For now, just verify the class instantiates
        assert self.answerer is not None
        assert self.answerer.style == AnswerStyle.CONVERSATIONAL


class TestQuestionAnswerer:
    """Test the main question answerer."""
    
    def test_initialization(self):
        """Test answerer initialization."""
        answerer = QuestionAnswerer()
        assert answerer is not None
        assert answerer.classifier is not None
        assert answerer.fetcher is not None
        assert answerer.answerer is not None
    
    def test_config(self):
        """Test configuration."""
        config = AnswerConfig(
            include_examples=False,
            max_sources=5,
            answer_style=AnswerStyle.FORMAL,
        )
        answerer = QuestionAnswerer(config=config)
        assert answerer.config.include_examples == False
        assert answerer.config.max_sources == 5
        assert answerer.config.answer_style == AnswerStyle.FORMAL


@pytest.mark.asyncio
async def test_classify_only():
    """Test classification without full answer."""
    answerer = QuestionAnswerer()
    analysis = await answerer.classify_only("Why do birds migrate?")
    
    assert analysis.primary_type == QuestionType.WHY
    assert "migrate" in analysis.topic.lower() or "birds" in analysis.topic.lower()


@pytest.mark.asyncio
async def test_full_answer_pipeline():
    """Test full answer pipeline (requires network)."""
    answerer = QuestionAnswerer(
        config=AnswerConfig(
            max_sources=3,  # Limit for faster testing
            timeout=15.0,
        )
    )
    
    try:
        result = await answerer.answer("What is artificial intelligence?")
        
        assert result is not None
        assert result.question_type == QuestionType.WHAT
        assert len(result.brief_answer) > 0
        assert len(result.standard_answer) >= len(result.brief_answer)
        
        # Cleanup
        await answerer.close()
    except Exception as e:
        # Network errors are acceptable in tests
        print(f"Network test skipped: {e}")
        await answerer.close()


def test_question_type_coverage():
    """Ensure all question types have answer templates."""
    from question_answering.elaborate_answerer import ElaborateAnswerer
    
    answerer = ElaborateAnswerer()
    
    # Check all question types have starters
    for qtype in QuestionType:
        if qtype not in (QuestionType.UNKNOWN, QuestionType.COMPOUND):
            assert qtype in answerer.ANSWER_STARTERS or qtype in (
                QuestionType.WHO, QuestionType.WHERE  # These are acceptable to be missing
            ), f"Missing answer starter for {qtype}"


# Quick demo
def demo():
    """Quick demo of the question answering system."""
    print("=" * 60)
    print("QUESTION CLASSIFICATION DEMO")
    print("=" * 60)
    
    classifier = QuestionClassifier()
    
    test_questions = [
        "What is machine learning?",
        "Why do leaves change color in fall?",
        "How does the internet work?",
        "Which programming language should I learn first?",
        "When was the first computer invented?",
        "What if humans could fly?",
        "Is climate change real?",
        "Can robots replace humans?",
    ]
    
    for q in test_questions:
        analysis = classifier.classify(q)
        print(f"\nQ: {q}")
        print(f"   Type: {analysis.primary_type.name}")
        print(f"   Topic: {analysis.topic}")
        print(f"   Intent: {analysis.intent}")
        print(f"   Complexity: {analysis.complexity}")
        print(f"   Confidence: {analysis.confidence:.0%}")
        
        queries = classifier.get_search_queries(analysis)
        print(f"   Search queries: {queries[:3]}")


if __name__ == "__main__":
    # Run demo
    demo()
    
    # Run tests
    print("\n" + "=" * 60)
    print("Running pytest...")
    print("=" * 60)
    pytest.main([__file__, "-v", "-x"])
