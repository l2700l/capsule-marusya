import numpy as np


class SemanticMatcher:

    def __init__(
        self,
        model,
        intents: dict[str, list[str]],
        threshold: float = 0.55,
        margin: float = 0.05,
    ):
        self.model = model
        self.threshold = threshold
        self.margin = margin

        self.embeddings = {}

        for intent, examples in intents.items():
            if not examples:
                continue

            self.embeddings[intent] = model.encode(
                examples,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )

    def classify(self, text: str) -> dict:
        query = self.model.encode(
            [text],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )[0]

        scores = {
            intent: float(np.max(np.dot(vectors, query)))
            for intent, vectors in self.embeddings.items()
        }

        ranked = sorted(
            scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        if not ranked:
            return {
                "intent": "unknown",
                "score": 0.0,
                "margin": 0.0,
                "alternatives": [],
            }

        best_intent, best_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0
        margin = best_score - second_score

        if best_score < self.threshold or margin < self.margin:
            best_intent = "unknown"

        return {
            "intent": best_intent,
            "score": round(best_score, 4),
            "margin": round(margin, 4),
            "alternatives": [
                {"intent": intent, "score": round(score, 4)}
                for intent, score in ranked[:3]
            ],
        }