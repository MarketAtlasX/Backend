from typing import List

import numpy as np

from ..pipeline_adapter import run_embedding_pipeline


class BGEMModel:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._dim = 384
        self._model = None
        self._load_attempted = False

    def _load(self):
        if self._load_attempted:
            return
        self._load_attempted = True
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name, device="cpu")
        except Exception:
            self._model = None

    def encode(self, texts: List[str]) -> List[List[float]]:
        self._load()
        if self._model is not None:
            embeddings = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
            return embeddings.tolist()
        try:
            import asyncio
            result = asyncio.run(run_embedding_pipeline(texts))
            embeddings = result.get("embeddings", [])
            if embeddings:
                return embeddings
        except Exception:
            pass
        return [np.random.randn(self._dim).tolist() for _ in texts]

    def encode_query(self, text: str) -> List[float]:
        return self.encode([text])[0]

    @property
    def dimension(self) -> int:
        return self._dim


embedding_model = BGEMModel()
