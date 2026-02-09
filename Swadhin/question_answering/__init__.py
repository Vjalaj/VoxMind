"""
VoxMind Advanced Question Answering System
===========================================
Handles multiple question types with elaborate, discussive responses.

Supported question types:
- WHAT: Definitions, explanations
- WHY: Reasons, causes, motivations
- WHICH: Choices, comparisons, selections
- WHEN: Time, dates, temporal information
- HOW: Processes, methods, instructions
- IF: Conditionals, hypotheticals, possibilities
- IS IT/THERE: Boolean questions, existence verification

Usage:
    from Swadhin.question_answering import QuestionAnswerer, answer_question
    
    # Simple interface
    result = await answer_question("Why do leaves change color in fall?")
    print(result.answer)
    
    # Full control
    answerer = QuestionAnswerer()
    result = await answerer.answer("How does machine learning work?")
    print(result.detailed_answer)
"""

from .question_classifier import QuestionClassifier, QuestionType
from .elaborate_answerer import ElaborateAnswerer, AnswerResult
from .knowledge_fetcher import KnowledgeFetcher
from .question_handler import QuestionAnswerer, answer_question

__all__ = [
    'QuestionClassifier',
    'QuestionType',
    'ElaborateAnswerer',
    'AnswerResult',
    'KnowledgeFetcher',
    'QuestionAnswerer',
    'answer_question',
]
