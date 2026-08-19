import re
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class QueryIntentType(str, Enum):
    ENTITY_LOOKUP = "ENTITY_LOOKUP"
    COMMUNICATION_QUERY = "COMMUNICATION_QUERY"
    TIMELINE_QUERY = "TIMELINE_QUERY"
    RELATIONSHIP_QUERY = "RELATIONSHIP_QUERY"
    FINDING_QUERY = "FINDING_QUERY"
    UNKNOWN = "UNKNOWN"


class QueryIntent(BaseModel):
    """
    Structured Query Intent model derived from deterministic pattern rules.
    """
    intent_type: QueryIntentType = Field(..., description="Categorized query intent")
    confidence: float = Field(..., description="Pattern matching confidence score")
    matched_pattern: Optional[str] = Field(None, description="Matched pattern rule regex")


# Deterministic pattern rules
PATTERNS = [
    (
        QueryIntentType.COMMUNICATION_QUERY,
        0.95,
        r"(who did .* (talk to|call|message|contact|email|speak to)|communications? involving|call logs? for|contacted|calls|messages)",
    ),
    (
        QueryIntentType.RELATIONSHIP_QUERY,
        0.95,
        r"(how are .* connected|relationship between|connected to|associated with|link between|connection between|how is .* related)",
    ),
    (
        QueryIntentType.TIMELINE_QUERY,
        0.90,
        r"(timeline|what happened on|events on|events between|chronology|when did|what occurred)",
    ),
    (
        QueryIntentType.FINDING_QUERY,
        0.90,
        r"(what was flagged|suspicious|anomal\w+|why was .* flagged|rule findings?|alerts?)",
    ),
    (
        QueryIntentType.ENTITY_LOOKUP,
        0.85,
        r"(who is|what do we know about|tell me about|details (on|for)|information (about|on)|find .*|overview of)",
    ),
]


def classify_intent(question: str) -> QueryIntent:
    """
    Classifies investigator question intent using deterministic keyword/pattern rules.
    100% rule-based and explainable — no ML model or LLM inference.
    """
    if not question or not question.strip():
        return QueryIntent(intent_type=QueryIntentType.UNKNOWN, confidence=0.0, matched_pattern=None)

    text = question.strip().lower()

    for intent_type, conf, pattern in PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return QueryIntent(
                intent_type=intent_type,
                confidence=conf,
                matched_pattern=pattern,
            )

    return QueryIntent(
        intent_type=QueryIntentType.UNKNOWN,
        confidence=0.30,
        matched_pattern="default_fallback",
    )
