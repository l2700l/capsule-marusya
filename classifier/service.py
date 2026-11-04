from classifier.rules import classify_rule
from classifier.semantic import SemanticClassifier


class ClassifierService:
    def __init__(self, registry):
        self.registry = registry
        self.semantic = SemanticClassifier(registry)
    def classify_semantic(self, text: str):
      return self.semantic.classify(text)
    def classify(self, text: str) -> dict:
        text = text.strip()

        if not text:
            return {
                "skill": "unknown",
                "score": 0.0,
                "method": "none",
                "alternatives": [],
            }

        rule_result = classify_rule(text, self.registry)

        if rule_result:
            return {
                "skill": rule_result,
                "score": 1.0,
                "method": "rules",
                "alternatives": [],
            }

        result = self.semantic.classify(text)

        result["method"] = "semantic"

        return result