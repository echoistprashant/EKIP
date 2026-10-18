from app.rag.query_transform.base import QueryTransformationResult


class MockQueryTransformer:
    """Deterministic Mock Query Transformer for zero-latency offline testing."""

    def __init__(self, strategy: str = "expansion") -> None:
        self.strategy = strategy

    async def transform(self, query: str) -> QueryTransformationResult:
        clean_query = query.strip()

        if self.strategy == "hyde":
            hypo = f"Hypothetical enterprise documentation detailing procedures and protocols for {clean_query}."
            return QueryTransformationResult(
                original_query=clean_query,
                transformed_query=hypo,
                expanded_queries=[clean_query],
                strategy_used="hyde",
                hypothetical_document=hypo,
            )

        if self.strategy == "expansion":
            expanded = [
                clean_query,
                f"{clean_query} standard operating procedure",
                f"{clean_query} architecture guidelines",
            ]
            return QueryTransformationResult(
                original_query=clean_query,
                transformed_query=clean_query,
                expanded_queries=expanded,
                strategy_used="expansion",
            )

        if self.strategy == "rewrite":
            rewritten = f"Enterprise policy and technical specifications regarding {clean_query}"
            return QueryTransformationResult(
                original_query=clean_query,
                transformed_query=rewritten,
                expanded_queries=[rewritten],
                strategy_used="rewrite",
            )

        return QueryTransformationResult(
            original_query=clean_query,
            transformed_query=clean_query,
            expanded_queries=[clean_query],
            strategy_used="none",
        )
