from app.core.config import settings
from app.llm import ChatMessage, LLMClient, LLMRequest, get_llm_client
from app.rag.query_transform.base import QueryTransformationResult


class HyDETransformer:
    """
    Hypothetical Document Embeddings (HyDE) Transformer.
    Generates a speculative document passage answering the user's question.
    The embedding of this hypothetical passage lives in document-vector space,
    significantly improving Dense ANN cosine similarity with actual matching chunks.
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or get_llm_client()

    async def transform(self, query: str) -> QueryTransformationResult:
        messages = [
            ChatMessage(
                role="system",
                content=(
                    "You are an enterprise knowledge base assistant. Given a user question, write a brief, "
                    "realistic hypothetical document excerpt (2-3 sentences) that directly answers the question "
                    "from an official enterprise policy or technical specification. "
                    "Do NOT include introductory conversational filler, disclaimers, or metadata."
                ),
            ),
            ChatMessage(role="user", content=f"Question: {query.strip()}"),
        ]

        req = LLMRequest(
            messages=messages,
            model=settings.LLM_MODEL,
            temperature=0.2,
            max_tokens=200,
        )

        result = await self.llm_client.generate(req)
        hypothetical_doc = result.content.strip()

        return QueryTransformationResult(
            original_query=query,
            transformed_query=hypothetical_doc,
            expanded_queries=[query],
            strategy_used="hyde",
            hypothetical_document=hypothetical_doc,
        )
