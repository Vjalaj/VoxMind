import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

class ResponseGenerationBridge:
    """Lightweight bridge so the Response Generation team can consume parser context."""

    def __init__(self):
        self.log_path = Path(__file__).with_name("response_generation.log")
        self.log_path.touch(exist_ok=True)

    def notify(self, parsed_result: Dict[str, Any], context: Dict[str, Any]) -> None:
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "intent": parsed_result.get("type"),
            "confidence": parsed_result.get("confidence"),
            "source": parsed_result.get("source"),
            "entities": {k: v for k, v in parsed_result.items() if k not in {"type", "confidence", "source"}},
            "context": context
        }
        try:
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload) + "\n")
            logger.info("Response generation team notified")
        except Exception as exc:
            logger.warning(f"Response generation logging failed: {exc}")
