"""Embedding helper shared by the app and the experiment scripts."""
import os
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = os.getenv("EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")


@lru_cache(maxsize=1)
def model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def embed(texts: list[str]) -> np.ndarray:
    # normalize_embeddings=True -> dot product == cosine similarity
    return model().encode(texts, normalize_embeddings=True, convert_to_numpy=True)


def cos(a: str, b: str) -> float:
    va, vb = embed([a, b])
    return float(va @ vb)
