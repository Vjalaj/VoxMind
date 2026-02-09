"""
Question Classifier for VoxMind
================================
Classifies questions by type to determine appropriate answering strategy.

Question Types:
- WHAT: Seeks definitions, explanations, descriptions
- WHY: Seeks reasons, causes, motivations, purposes
- WHICH: Seeks choices, comparisons, best options
- WHEN: Seeks temporal information, dates, timing
- HOW: Seeks methods, processes, instructions
- IF: Seeks conditionals, hypotheticals, possibilities
- IS_BOOLEAN: Seeks yes/no confirmation (is it, is there, can, does, etc.)
- COMPOUND: Multiple question types combined
"""

import re
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class QuestionType(Enum):
    """Types of questions VoxMind can answer."""
    WHAT = auto()       # Definitions, explanations
    WHY = auto()        # Reasons, causes
    WHICH = auto()      # Comparisons, choices
    WHEN = auto()       # Temporal, timing
    HOW = auto()        # Methods, processes
    IF = auto()         # Conditionals, hypotheticals
    IS_BOOLEAN = auto() # Yes/no, existence
    WHO = auto()        # People, entities
    WHERE = auto()      # Location, place
    COMPOUND = auto()   # Multiple types
    UNKNOWN = auto()    # Cannot classify


@dataclass
class QuestionAnalysis:
    """Analysis result for a question."""
    original_question: str
    normalized_question: str
    primary_type: QuestionType
    secondary_types: List[QuestionType] = field(default_factory=list)
    topic: str = ""
    subtopics: List[str] = field(default_factory=list)
    intent: str = ""  # e.g., "learn", "compare", "verify", "understand"
    complexity: str = "simple"  # simple, moderate, complex
    requires_opinion: bool = False
    requires_comparison: bool = False
    requires_temporal: bool = False
    requires_examples: bool = False
    requires_discussion: bool = False
    confidence: float = 0.0
    keywords: List[str] = field(default_factory=list)
    context_hints: Dict[str, Any] = field(default_factory=dict)


class QuestionClassifier:
    """
    Classifies questions and extracts topic/intent for better answering.
    """
    
    # Question word patterns with their types and intents
    QUESTION_PATTERNS = {
        QuestionType.WHAT: {
            'patterns': [
                r'^what\s+(?:is|are|was|were)\s+',
                r'^what\s+(?:does|do|did)\s+',
                r'^what\s+(?:can|could|would|should|will)\s+',
                r'^what\s+about\s+',
                r'^what\s+happens?\s+',
                r'^what\'?s\s+',
                # Elaborate topic triggers - treat as WHAT (explanation/description)
                # BUT NOT when followed by "how" (that's a HOW question)
                r'^describe\s+(?!how\s)',
                r'^discuss\s+(?!how\s)',
                r'^explain\s+(?!(?:me\s+)?how\s)',  # "explain X" but not "explain how X"
                r'^elaborate\s+(?:on\s+)?(?!how\s)',
                r'^(?:talk|speak)\s+(?:to\s+me\s+)?about\s+(?!how\s)',
                r'^tell\s+me\s+(?:more\s+)?about\s+(?!how\s)',
                r'^teach\s+me\s+(?!how\s)(?:about\s+)?',
                r'^analyze\s+',
                r'^analyse\s+',
                r'^explore\s+(?!how\s)',
                r'^research\s+',
                r'^walk\s+(?:me\s+)?through\s+',
                r'^break\s+(?:it\s+)?down[:]?\s*',
            ],
            'intent': 'explain',
            'extract_topic': lambda m, q: re.sub(
                r'^(?:what\s+(?:is|are|was|were|does|do|did|can|could|would|should|will|about|happens?|\'?s)|'
                r'describe|discuss|explain|elaborate\s+(?:on)?|'
                r'(?:talk|speak)\s+(?:to\s+me\s+)?about|tell\s+me\s+(?:more\s+)?about|'
                r'teach\s+me\s+(?:about)?|analyze|analyse|explore|research|'
                r'walk\s+(?:me\s+)?through|break\s+(?:it\s+)?down[:]?)\s*', 
                '', q, flags=re.I
            ).strip().rstrip('?'),
        },
        QuestionType.WHY: {
            'patterns': [
                r'^why\s+(?:is|are|was|were)\s+',
                r'^why\s+(?:does|do|did)\s+',
                r'^why\s+(?:can|could|would|should|will)\s+',
                r'^why\s+(?:don\'?t|doesn\'?t|didn\'?t)\s+',
                r'^why\s+',
                r'(?:what|for what)\s+reason',
                r'what\s+causes?\s+',
                r'what\s+(?:is|are)\s+the\s+(?:reason|cause)',
            ],
            'intent': 'reason',
            'extract_topic': lambda m, q: re.sub(r'^why\s+(?:is|are|was|were|does|do|did|can|could|would|should|will|don\'?t|doesn\'?t|didn\'?t)?\s*', '', q, flags=re.I).rstrip('?'),
        },
        QuestionType.WHICH: {
            'patterns': [
                r'^which\s+(?:is|are|was|were)\s+',
                r'^which\s+(?:one|ones)\s+',
                r'^which\s+(?:should|would|could)\s+',
                r'^which\s+',
                r'(?:what|which)\s+(?:is|are)\s+(?:the\s+)?(?:best|better|worst|worse)',
                r'(?:should\s+i|would\s+you)\s+(?:choose|pick|select|use)',
                r'(?:compare|comparison|versus|vs\.?|or)\s+',
            ],
            'intent': 'compare',
            'extract_topic': lambda m, q: re.sub(r'^which\s+(?:is|are|was|were|one|ones|should|would|could)?\s*', '', q, flags=re.I).rstrip('?'),
        },
        QuestionType.WHEN: {
            'patterns': [
                r'^when\s+(?:is|are|was|were)\s+',
                r'^when\s+(?:does|do|did)\s+',
                r'^when\s+(?:can|could|would|should|will)\s+',
                r'^when\s+',
                r'(?:what|at what)\s+time\s+',
                r'what\s+(?:year|date|day|month|period)\s+',
                r'(?:how\s+long)\s+(?:ago|until|before|after)\s+',
            ],
            'intent': 'temporal',
            'extract_topic': lambda m, q: re.sub(r'^when\s+(?:is|are|was|were|does|do|did|can|could|would|should|will)?\s*', '', q, flags=re.I).rstrip('?'),
        },
        QuestionType.HOW: {
            'patterns': [
                r'^how\s+(?:do|does|did)\s+',
                r'^how\s+(?:can|could|would|should|will)\s+',
                r'^how\s+(?:is|are|was|were)\s+',
                r'^how\s+to\s+',
                r'^how\s+(?:much|many|long|far|often|old)\s+',
                r'^how\s+come\s+',
                r'^in\s+what\s+(?:way|manner|method)\s+',
                r'(?:what|which)\s+(?:is|are)\s+the\s+(?:process|method|way|step)',
                r'(?:tell|show|teach|explain)\s+(?:me\s+)?how\s+',
            ],
            'intent': 'method',
            'extract_topic': lambda m, q: re.sub(
                r'^(?:(?:tell|show|teach|explain)\s+(?:me\s+)?)?how\s+(?:does|do|did|can|could|would|should|will|is|are|was|were|to|much|many|long|far|often|old|come)?\s*',
                '', q, flags=re.I
            ).strip().rstrip('?'),
        },
        QuestionType.IF: {
            'patterns': [
                r'^(?:what\s+)?if\s+',
                r'^(?:what\s+)?(?:would|could|might)\s+happen\s+if\s+',
                r'^suppose\s+',
                r'^assuming\s+',
                r'^in\s+(?:the\s+)?case\s+(?:that|of)\s+',
                r'^hypothetically\s+',
                r'^(?:is|are|would)\s+it\s+possible\s+',
            ],
            'intent': 'hypothetical',
            'extract_topic': lambda m, q: re.sub(r'^(?:what\s+)?if\s+', '', q, flags=re.I).rstrip('?'),
        },
        QuestionType.IS_BOOLEAN: {
            'patterns': [
                r'^(?:is|are|was|were)\s+(?:it|there|this|that|these|those)\s+',
                r'^(?:is|are|was|were)\s+\w+\s+',
                r'^(?:can|could|will|would|should|do|does|did|has|have|had)\s+',
                r'^(?:isn\'?t|aren\'?t|wasn\'?t|weren\'?t)\s+',
                r'^(?:can\'?t|couldn\'?t|won\'?t|wouldn\'?t|shouldn\'?t|don\'?t|doesn\'?t|didn\'?t|hasn\'?t|haven\'?t|hadn\'?t)\s+',
                r'^(?:am\s+i|are\s+you|is\s+he|is\s+she|is\s+it)\s+',
            ],
            'intent': 'verify',
            'extract_topic': lambda m, q: re.sub(r'^(?:is|are|was|were|can|could|will|would|should|do|does|did|has|have|had|isn\'?t|aren\'?t|wasn\'?t|weren\'?t|can\'?t|couldn\'?t|won\'?t|wouldn\'?t|shouldn\'?t|don\'?t|doesn\'?t|didn\'?t|hasn\'?t|haven\'?t|hadn\'?t|am\s+i|are\s+you|is\s+he|is\s+she|is\s+it)\s+', '', q, flags=re.I).rstrip('?'),
        },
        QuestionType.WHO: {
            'patterns': [
                r'^who\s+(?:is|are|was|were)\s+',
                r'^who\s+(?:does|do|did)\s+',
                r'^who\s+(?:can|could|would|should|will)\s+',
                r'^who\s+',
                r'^whom\s+',
            ],
            'intent': 'identify',
            'extract_topic': lambda m, q: re.sub(r'^who(?:m)?\s+(?:is|are|was|were|does|do|did|can|could|would|should|will)?\s*', '', q, flags=re.I).rstrip('?'),
        },
        QuestionType.WHERE: {
            'patterns': [
                r'^where\s+(?:is|are|was|were)\s+',
                r'^where\s+(?:does|do|did)\s+',
                r'^where\s+(?:can|could|would|should|will)\s+',
                r'^where\s+',
                r'(?:what|which)\s+(?:place|location|country|city)\s+',
            ],
            'intent': 'locate',
            'extract_topic': lambda m, q: re.sub(r'^where\s+(?:is|are|was|were|does|do|did|can|could|would|should|will)?\s*', '', q, flags=re.I).rstrip('?'),
        },
    }
    
    # Complexity indicators
    COMPLEXITY_INDICATORS = {
        'complex': [
            r'\band\b.*\band\b',  # Multiple conjunctions
            r'\bor\b.*\bor\b',
            r'relationship|correlation|causation|implication',
            r'compare|contrast|differentiate|distinguish',
            r'pros?\s+and\s+cons?|advantages?\s+and\s+disadvantages?',
            r'how\s+does\s+.+\s+affect|impact|influence',
        ],
        'moderate': [
            r'\band\b|\bor\b',
            r'explain|describe|elaborate',
            r'difference|similar|like',
            r'between\s+.+\s+and',
        ],
    }
    
    # Requirement indicators
    REQUIREMENT_PATTERNS = {
        'requires_opinion': [
            r'\bbest\b|\bworst\b|\bbetter\b|\bworse\b',
            r'\bshould\b|\brecommend\b|\badvise\b',
            r'\bthink\b|\bopinion\b|\bbelieve\b',
            r'\bpros?\b|\bcons?\b|\badvantage\b|\bdisadvantage\b',
        ],
        'requires_comparison': [
            r'\bversus\b|\bvs\.?\b|\bcompare\b|\bcontrast\b',
            r'\bdifference\b|\bsimilar\b',
            r'\bor\b.*\bor\b|\bor\b.*\?',
            r'which\s+(?:is|are)\s+(?:better|best|worse|worst)',
        ],
        'requires_temporal': [
            r'\bwhen\b|\btime\b|\bdate\b|\byear\b',
            r'\bbefore\b|\bafter\b|\bduring\b',
            r'\bhistory\b|\bfuture\b|\bpast\b',
            r'\bhow\s+long\b|\bhow\s+old\b',
        ],
        'requires_examples': [
            r'\bexample\b|\binstance\b|\bsuch\s+as\b',
            r'\blike\s+what\b|\bfor\s+instance\b',
            r'\bdemonstrate\b|\billustrate\b',
        ],
        'requires_discussion': [
            r'\bdiscuss\b|\belaborate\b|\bexplain\s+in\s+detail\b',
            r'\bwhy\s+or\s+why\s+not\b|\bpros?\s+and\s+cons?\b',
            r'\barguments?\s+for\s+and\s+against\b',
            r'\bcontrovers\w+\b|\bdebate\b',
        ],
    }

    def __init__(self):
        """Initialize the classifier."""
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for efficiency."""
        self._compiled_patterns: Dict[QuestionType, List[re.Pattern]] = {}
        for qtype, config in self.QUESTION_PATTERNS.items():
            self._compiled_patterns[qtype] = [
                re.compile(p, re.IGNORECASE) for p in config['patterns']
            ]
        
        self._compiled_complexity = {
            level: [re.compile(p, re.I) for p in patterns]
            for level, patterns in self.COMPLEXITY_INDICATORS.items()
        }
        
        self._compiled_requirements = {
            req: [re.compile(p, re.I) for p in patterns]
            for req, patterns in self.REQUIREMENT_PATTERNS.items()
        }
    
    def classify(self, question: str) -> QuestionAnalysis:
        """
        Classify a question and extract analysis.
        
        Args:
            question: The question to analyze
            
        Returns:
            QuestionAnalysis with type, topic, intent, and requirements
        """
        # Normalize
        normalized = question.strip()
        if not normalized.endswith('?'):
            normalized += '?'
        
        # Find primary question type
        primary_type = QuestionType.UNKNOWN
        secondary_types = []
        best_confidence = 0.0
        matched_config = None
        
        for qtype, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                match = pattern.search(normalized)
                if match:
                    # Score based on match position and length
                    position_score = 1.0 - (match.start() / len(normalized))
                    length_score = len(match.group()) / len(normalized)
                    confidence = (position_score * 0.6 + length_score * 0.4)
                    
                    if confidence > best_confidence:
                        if primary_type != QuestionType.UNKNOWN:
                            secondary_types.append(primary_type)
                        primary_type = qtype
                        best_confidence = confidence
                        matched_config = self.QUESTION_PATTERNS[qtype]
                    elif confidence > 0.3:
                        if qtype not in secondary_types:
                            secondary_types.append(qtype)
        
        # Extract topic
        topic = ""
        if matched_config and 'extract_topic' in matched_config:
            topic = matched_config['extract_topic'](None, normalized)
        
        # Clean up topic
        topic = self._clean_topic(topic)
        
        # Determine intent
        intent = matched_config['intent'] if matched_config else 'unknown'
        
        # Analyze complexity
        complexity = self._analyze_complexity(normalized)
        
        # Check requirements
        requires_opinion = self._check_requirement(normalized, 'requires_opinion')
        requires_comparison = self._check_requirement(normalized, 'requires_comparison')
        requires_temporal = self._check_requirement(normalized, 'requires_temporal')
        requires_examples = self._check_requirement(normalized, 'requires_examples')
        requires_discussion = self._check_requirement(normalized, 'requires_discussion')
        
        # Extract keywords
        keywords = self._extract_keywords(normalized)
        
        # Subtopics for compound questions
        subtopics = self._extract_subtopics(normalized, topic)
        
        return QuestionAnalysis(
            original_question=question,
            normalized_question=normalized,
            primary_type=primary_type,
            secondary_types=secondary_types[:3],  # Limit to 3
            topic=topic,
            subtopics=subtopics,
            intent=intent,
            complexity=complexity,
            requires_opinion=requires_opinion,
            requires_comparison=requires_comparison,
            requires_temporal=requires_temporal,
            requires_examples=requires_examples,
            requires_discussion=requires_discussion or len(secondary_types) > 0,
            confidence=best_confidence,
            keywords=keywords,
        )
    
    def _clean_topic(self, topic: str) -> str:
        """Clean extracted topic."""
        # Remove common filler words at start/end
        fillers = ['the', 'a', 'an', 'some', 'any', 'about', 'regarding', 'concerning']
        words = topic.split()
        
        # Remove leading fillers
        while words and words[0].lower() in fillers:
            words.pop(0)
        
        # Remove trailing punctuation
        if words:
            words[-1] = words[-1].rstrip('?.,!')
        
        return ' '.join(words)
    
    def _analyze_complexity(self, question: str) -> str:
        """Determine question complexity."""
        for level in ['complex', 'moderate']:
            patterns = self._compiled_complexity.get(level, [])
            for pattern in patterns:
                if pattern.search(question):
                    return level
        return 'simple'
    
    def _check_requirement(self, question: str, requirement: str) -> bool:
        """Check if question has a specific requirement."""
        patterns = self._compiled_requirements.get(requirement, [])
        return any(p.search(question) for p in patterns)
    
    def _extract_keywords(self, question: str) -> List[str]:
        """Extract important keywords from question."""
        # Remove question words and common words
        stopwords = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'to', 'of', 'in', 'for',
            'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'under', 'again',
            'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why',
            'how', 'what', 'which', 'who', 'whom', 'this', 'that', 'these',
            'those', 'am', 'it', 'its', 'i', 'me', 'my', 'myself', 'we', 'our',
            'ours', 'ourselves', 'you', 'your', 'yours', 'yourself', 'he', 'him',
            'his', 'himself', 'she', 'her', 'hers', 'herself', 'they', 'them',
            'their', 'theirs', 'themselves', 'or', 'and', 'but', 'if', 'about',
        }
        
        # Extract words
        words = re.findall(r'\b[a-zA-Z]+\b', question.lower())
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        
        # Deduplicate while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
        
        return unique_keywords[:10]  # Limit to 10 keywords
    
    def _extract_subtopics(self, question: str, main_topic: str) -> List[str]:
        """Extract subtopics for compound questions."""
        subtopics = []
        
        # Look for "and" conjunctions
        and_parts = re.split(r'\s+and\s+', question, flags=re.I)
        if len(and_parts) > 1:
            for part in and_parts[1:]:
                # Extract noun phrases
                cleaned = self._clean_topic(part)
                if cleaned and cleaned != main_topic:
                    subtopics.append(cleaned[:50])  # Limit length
        
        # Look for comma-separated items
        comma_parts = re.split(r',\s*', main_topic)
        if len(comma_parts) > 1:
            subtopics.extend([p.strip() for p in comma_parts[1:] if p.strip()])
        
        return subtopics[:5]  # Limit to 5 subtopics
    
    def get_search_queries(self, analysis: QuestionAnalysis) -> List[str]:
        """
        Generate search queries based on question analysis.
        
        Returns multiple queries optimized for different search strategies.
        """
        queries = []
        topic = analysis.topic
        
        # Clean up topic - remove articles and improve specificity
        clean_topic = re.sub(r'^(?:an?|the)\s+', '', topic, flags=re.I).strip()
        
        # For HOW questions about processes/mechanisms, rephrase for better search
        if analysis.primary_type == QuestionType.HOW:
            # Check for "[subject] [verb]" patterns like "airplane fly/flies", "car work/works"
            subject_verb_match = re.match(
                r'^(\w+(?:\s+\w+)?)\s+(fly|flies|work|works|move|moves|run|runs|operate|operates|function|functions)$', 
                clean_topic, re.I
            )
            if subject_verb_match:
                subject = subject_verb_match.group(1)
                verb = subject_verb_match.group(2).lower()
                
                # Generate physics/mechanism queries
                if verb in ('fly', 'flies'):
                    queries.append(f"{subject} flight physics")
                    queries.append(f"how does {subject} fly")
                    queries.append(f"{subject} aerodynamics lift")
                    queries.append(f"principles of {subject} flight")
                elif verb in ('work', 'works'):
                    queries.append(f"how {subject} works")
                    queries.append(f"{subject} working principle")
                    queries.append(f"{subject} mechanism")
                elif verb in ('move', 'moves', 'run', 'runs'):
                    queries.append(f"how {subject} works")
                    queries.append(f"{subject} motion physics")
                else:
                    queries.append(f"how {subject} {verb}")
                    queries.append(f"{subject} mechanism")
            else:
                # Standard HOW queries
                queries.append(f"how to {clean_topic}")
                queries.append(f"{clean_topic} process steps")
                queries.append(f"{clean_topic} guide tutorial")
        
        # Primary topic query (with cleaned version)
        elif topic:
            queries.append(clean_topic)
            if clean_topic != topic:
                queries.append(topic)
        
        # Question-type specific queries
        if analysis.primary_type == QuestionType.WHY:
            queries.append(f"reasons {clean_topic}")
            queries.append(f"causes of {clean_topic}")
            queries.append(f"{clean_topic} explanation why")
        
        elif analysis.primary_type == QuestionType.WHAT:
            # For WHAT/describe/explain, use the topic directly
            queries.append(clean_topic)
            queries.append(f"{clean_topic} definition")
            queries.append(f"{clean_topic} explained")
        
        elif analysis.primary_type == QuestionType.WHEN:
            queries.append(f"{clean_topic} date time history")
            queries.append(f"when did {clean_topic}")
        
        elif analysis.primary_type == QuestionType.WHICH:
            queries.append(f"best {clean_topic}")
            queries.append(f"{clean_topic} comparison")
            queries.append(f"{clean_topic} vs alternatives")
        
        elif analysis.primary_type == QuestionType.IF:
            queries.append(f"what happens if {clean_topic}")
            queries.append(f"{clean_topic} consequences effects")
        
        elif analysis.primary_type == QuestionType.IS_BOOLEAN:
            queries.append(f"{clean_topic} true false")
            queries.append(f"is {clean_topic}")
        
        # Add keyword-based queries
        if len(analysis.keywords) >= 2:
            queries.append(' '.join(analysis.keywords[:5]))
        
        # Subtopic queries
        for subtopic in analysis.subtopics[:2]:
            queries.append(subtopic)
        
        # Deduplicate
        seen = set()
        unique_queries = []
        for q in queries:
            q_lower = q.lower().strip()
            if q_lower and q_lower not in seen:
                seen.add(q_lower)
                unique_queries.append(q)
        
        return unique_queries[:6]  # Limit to 6 queries


# Convenience function
def classify_question(question: str) -> QuestionAnalysis:
    """Classify a question and return analysis."""
    classifier = QuestionClassifier()
    return classifier.classify(question)
