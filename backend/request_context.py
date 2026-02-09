"""Request context for backend command processing."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class RequestContext:
    raw_text: str
    parsed: Dict[str, Any]
    response: Optional[str] = None
    error: Optional[Exception] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
