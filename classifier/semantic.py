import os

import numpy as np
from sentence_transformers import SentenceTransformer


class SemanticClassifier:

    def __init__(self, registry):
        model_name = os.getenv(
            "CLASSIFIER_MODEL",
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        )

        examples = registry.get_examples()

        self.model = SentenceTransformer(model_name)

        self.threshold = float(
            os.getenv("CLASSIFIER_THRESHOLD", "0.55")
        )

        self.margin = float(
            os.getenv("CLASSIFIER_MARGIN", "0.05")
        )

        self.skills = {}
        self.embeddings = {}

        for skill, phrases in examples.items():
            if not phrases:
                continue

            vectors = self.model.encode(
                phrases,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )

            self.skills[skill] = phrases
            self.embeddings[skill] = vectors

    def classify(self, text: str) -> dict:
        query = self.model.encode(
            [text],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )[0]

        scores = {}

        for skill, vectors in self.embeddings.items():
            similarities = np.dot(vectors, query)
            scores[skill] = float(np.max(similarities))

        ranked = sorted(
            scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        if not ranked:
            return {
                "skill": "unknown",
                "score": 0.0,
                "alternatives": [],
            }

        best_skill, best_score = ranked[0]

        second_score = (
            ranked[1][1] if len(ranked) > 1 else 0.0
        )

        alternatives = [
            {
                "skill": skill,
                "score": round(score, 4),
            }
            for skill, score in ranked[:3]
        ]

        if best_score < self.threshold:
            best_skill = "unknown"

        elif best_score - second_score < self.margin:
            best_skill = "unknown"

        return {
            "skill": best_skill,
            "score": round(best_score, 4),
            "margin": round(best_score - second_score, 4),
            "alternatives": alternatives,
        }