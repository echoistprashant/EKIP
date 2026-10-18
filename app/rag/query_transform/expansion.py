import re
from app.core.config import settings
from app.llm import ChatMessage, LLMClient, LLMRequest, get_llm_client
from app.rag.query_transform.base import QueryTransformationResult


class MultiQueryExpander:
    """
    Expands a single user question into multiple diverse search queries
    capturing synonyms, technical keywords, and alternate phrasings.
    Retrieval is executed across all queries and fused via Multi-List RRF.
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or get_llm_client()

    async def transform(self, query: str) -> QueryTransformationResult:
        clean_query = query.strip()
        messages = [
            ChatMessage(
                role="system",
                content=(
                    "You are an AI search query optimization engine. Given a user search question, "
                    "generate exactly 3 diverse alternative search queries that capture different "
                    "perspectives, technical terminology, synonyms, or acronyms for retrieving documentation.\n"
                    "Rules:\n"
                    "1. Provide exactly 3 queries, one per line.\n"
                    "2. Do NOT number them, use bullets, or provide explanations."
                ),
            ),
            ChatMessage(role="user", content=f"User Query: {clean_query}"),
        ]

        req = LLMRequest(
            messages=messages,
            model=settings.LLM_MODEL,
            temperature=0.3,
            max_tokens=150,
        )

        result = await self.llm_client.generate(req)

        # Parse generated queries line by line
        parsed_queries: list[str] = [clean_query]
        seen_lower: set[str] = {clean_query.lower()}

        for line in result.content.strip().splitlines():
            cleaned_line = re.sub(r"^\s*(?:\d+[\.\)]|-|\*)\s*", "", line).strip()
            if cleaned_line and cleaned_line.lower() not in seen_lower:
                seen_lower.add(cleaned_line.lower())
                parsed_queries.append(cleaned_line)

        return QueryTransformationResult(
            original_query=clean_query,
            transformed_query=" | ".join(parsed_queries),
            expanded_queries=parsed_queries,
            strategy_used="expansion",
        )
