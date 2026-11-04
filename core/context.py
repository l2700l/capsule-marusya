class ContextManager:

    def __init__(self):
        self.contexts = {}

    def get(self, context_id):
        if context_id not in self.contexts:
            self.contexts[context_id] = {
                "active_skill": None,
                "dialog_state": {},
            }

        return self.contexts[context_id]

    def set_active_skill(self, context_id, skill_name):
        context = self.get(context_id)
        context["active_skill"] = skill_name

    def clear_active_skill(self, context_id):
        context = self.get(context_id)
        context["active_skill"] = None
        context["dialog_state"].clear()

    def remove(self, context_id):
        self.contexts.pop(context_id, None)