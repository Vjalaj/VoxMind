"""Command router for backend execution."""

from typing import Any, Callable, Dict, List, Optional
from .request_context import RequestContext


class CommandRouter:
    def __init__(self):
        self._handlers: Dict[str, Callable[[Dict[str, Any]], str]] = {}
        self._fallback: Optional[Callable[[Dict[str, Any]], str]] = None
        self._middleware: List[Any] = []

    def register(self, command: str, handler: Callable[[Dict[str, Any]], str]) -> None:
        self._handlers[command] = handler

    def set_fallback(self, handler: Callable[[Dict[str, Any]], str]) -> None:
        self._fallback = handler

    def use(self, middleware) -> None:
        self._middleware.append(middleware)

    def dispatch(self, raw_text: str, parsed: Dict[str, Any]) -> RequestContext:
        ctx = RequestContext(raw_text=raw_text, parsed=parsed)

        for mw in self._middleware:
            try:
                mw.before(ctx)
            except Exception:
                pass

        handler = self._handlers.get(parsed.get("command")) or self._fallback

        try:
            if handler is None:
                raise ValueError("No handler registered")
            ctx.response = handler(parsed)
        except Exception as exc:
            ctx.error = exc
            ctx.response = None

        for mw in self._middleware:
            try:
                mw.after(ctx)
            except Exception:
                pass

        return ctx
