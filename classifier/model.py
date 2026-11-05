import os
from sentence_transformers import SentenceTransformer


class ModelProvider:

    def __init__(self):
        self.model = None

    def load(self):
        if self.model is None:
            model_name = os.getenv(
                "CLASSIFIER_MODEL",
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            )
            self.model = SentenceTransformer(model_name)

        return self.model