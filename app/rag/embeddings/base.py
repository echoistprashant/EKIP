from typing import Protocol


class BaseEmbedder(Protocol):
    """
    Protocol for vector embedding models.
    Provides uniform interface for local ONNX models (FastEmbed),
    cloud APIs (Cohere/OpenAI), and test fakes.
    """

    model_name: str
    dimension: int

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a batch of document chunk texts.
        Returns a list of float vectors, each of length `self.dimension`.
        """
        ...

    async def embed_query(self, text: str) -> list[float]:
        """
        Embed a single search query text.
        Applies query prefix if required by the model.
        Returns a float vector of length `self.dimension`.
        """
        ...
