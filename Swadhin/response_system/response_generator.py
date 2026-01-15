from response_templates import render
from context import ContextManager
from cache import ResponseCache

class ResponseGenerator:
    def __init__(self):
        self.context = ContextManager()
        self.cache = ResponseCache()

    def generate(self, user_id, command, tone="friendly", **kwargs):
        cache_key = f"{user_id}:{command}:{tone}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        # Onboarding
        if not self.context.get(user_id, "onboarded"):
            self.context.set(user_id, "onboarded", True)
            response = render("onboarding", tone, name=kwargs.get("name", "User"))
            self.cache.set(cache_key, response)
            return response

        # Confirmation dialog
        if command == "delete":
            return render("confirm", "neutral", action="delete this item")

        # Error fallback
        if command not in ["greet"]:
            return render("error", "neutral")

        response = render(command, tone, **kwargs)
        self.cache.set(cache_key, response)
        return response
