from typing import Literal

from app.core.config import settings
from app.rag.query_transform.base import BaseQueryTransformer, QueryTransformationResult
from app.rag.query_transform.expansion import MultiQueryExpander
from app.rag.query_transform.hyde import HyDETransformer
from app.rag.query_transform.mock_transformer import MockQueryTransformer
from app.rag.query_transform.rewrite import QueryRewriter


def get_query_transformer(
    strategy: Literal["none", "hyde", "expansion", "rewrite", "mock"] = "none",
) -> BaseQueryTransformer | None:
    """
    Factory function returning the appropriate Query Transformer based on strategy.
    """
    if strategy == "mock":
        return MockQueryTransformer()
    if strategy == "hyde":
        return HyDETransformer()
    if strategy == "expansion":
        return MultiQueryExpander()
    if strategy == "rewrite":
        return QueryRewriter()
    return None


__all__ = [
    "BaseQueryTransformer",
    "QueryTransformationResult",
    "HyDETransformer",
    "MultiQueryExpander",
    "QueryRewriter",
    "MockQueryTransformer",
    "get_query_transformer",
]
