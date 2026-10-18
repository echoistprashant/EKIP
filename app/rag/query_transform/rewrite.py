from app.core.config import settings
from app.llm import ChatMessage, LLMClient, LLMRequest, get_llm_client
from app.rag.query_transform.base import QueryTransformationResult


class QueryRewriter:
    """
    Rewrites ambiguous, colloquial, or fragmented user queries into a single
    precise, terminology-rich search query for optimal search recall.
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or get_llm_client()

    async def transform(self, query: str) -> QueryTransformationResult:
        clean_query = query.strip()
        messages = [
            ChatMessage(
                role="system",
                content=(
                    "You are an enterprise search query rewriter. Given a user query, "
                    "rewrite it into a single clear, concise, keyword-rich declarative search query. "
                    "Do NOT include conversational filler, quotes, or explanations. "
                    "Output only the rewritten query."
                ),
            ),
            ChatMessage(role="user", content=f"User Query: {clean_query}"),
        ]

        req = LLMRequest(
            messages=messages,
            model=settings.LLM_MODEL,
            temperature=0.0,
            max_tokens=100,
        )

        result = await self.llm_client.generate(req)
        rewritten = result.content.strip().strip('"').strip("'")

        return QueryTransformationResult(
            original_query=clean_query,
            transformed_query=rewritten,
            expanded_queries=[rewritten],
            strategy_used="rewrite",
        )
