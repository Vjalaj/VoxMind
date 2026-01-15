class ContextManager:
    def __init__(self):
        self.data = {}

    def get(self, user_id, key, default=None):
        return self.data.get(user_id, {}).get(key, default)

    def set(self, user_id, key, value):
        self.data.setdefault(user_id, {})[key] = value

    def reset(self, user_id):
        self.data[user_id] = {}
