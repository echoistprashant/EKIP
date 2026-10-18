import asyncio
from typing import Any
from fastembed import TextEmbedding


class FastEmbedEmbedder:
    """
    Local in-process ONNX-based embedding model.
    100% free, runs on CPU without GPU, zero API keys required.
    """

    def __init__(self, model_name: str = "BAAI/bge-large-en-v1.5", batch_size: int = 32):
        self.model_name = model_name
        self.dimension = 1024
        self.batch_size = batch_size
        self._model: TextEmbedding | None = None

    def _get_model(self) -> TextEmbedding:
        if self._model is None:
            # Lazy initialize model so startup is fast
            self._model = TextEmbedding(model_name=self.model_name)
        return self._model

    def _embed_documents_sync(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        embeddings_generator = model.embed(texts, batch_size=self.batch_size)
        return [vec.tolist() for vec in embeddings_generator]

    def _embed_query_sync(self, text: str) -> list[float]:
        model = self._get_model()
        # query_embed applies specific query prefix optimizations (e.g. for BGE)
        embeddings_generator = model.query_embed([text])
        return list(embeddings_generator)[0].tolist()

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Run CPU-bound embedding computation in separate thread to prevent event loop blocking."""
        if not texts:
            return []
        return await asyncio.to_thread(self._embed_documents_sync, texts)

    async def embed_query(self, text: str) -> list[float]:
        """Embed search query with prefix optimization in worker thread."""
        return await asyncio.to_thread(self._embed_query_sync, text)
