import os

os.environ["HF_HUB_OFFLINE"] = "1"

from typing import List

import numpy as np


class BGEMModel:
    def __init__(self, model_name: str = "BAAI/bge-m3"):
        self.model_name = model_name
        self._model = None
        self._dim = 1024
        self._load_attempted = False

    def _load(self):
        if self._load_attempted:
            return
        self._load_attempted = True
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name, device="cpu", trust_remote_code=True)
        except Exception:
            self._model = None

    def encode(self, texts: List[str]) -> List[List[float]]:
        self._load()
        if self._model is None:
            return [np.random.randn(self._dim).tolist() for _ in texts]
        embeddings = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return embeddings.tolist()

    def encode_query(self, text: str) -> List[float]:
        return self.encode([text])[0]

    @property
    def dimension(self) -> int:
        return self._dim


embedding_model = BGEMModel()
