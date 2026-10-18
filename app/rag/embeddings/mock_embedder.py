import hashlib
import math
import random


class MockEmbedder:
    """
    Deterministic 1024-dimension mock embedder for lightning-fast testing and CI.
    Generates repeatable, unit-normalized vectors without downloading weights.
    """

    def __init__(self, dimension: int = 1024):
        self.model_name = "mock-embedder-1024"
        self.dimension = dimension

    def _generate_vector(self, text: str) -> list[float]:
        # Seed pseudo-random generator with SHA-256 of text for deterministic output
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16)
        rng = random.Random(seed)

        raw_vec = [rng.gauss(0.0, 1.0) for _ in range(self.dimension)]

        # L2 Normalization: divide each element by Euclidean norm
        norm = math.sqrt(sum(x * x for x in raw_vec))
        if norm == 0:
            return [0.0] * self.dimension
        return [x / norm for x in raw_vec]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._generate_vector(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._generate_vector(text)
