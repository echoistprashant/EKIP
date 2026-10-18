import time
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.llm import LLMClient, LLMRequest, get_llm_client
from app.models.query_log import QueryCitation, QueryLog
from app.models.user import User
from app.rag.citations import CitationVerifier
from app.rag.context_builder import ContextBuilder
from app.rag.prompts.manager import PromptManager
from app.rag.retrieval.base import AccessScope, Candidate
from app.rag.retrieval.hybrid import HybridRetriever
from app.schemas.query import CitationItem, QueryRequest, QueryResponse


class QueryService:
    """
    Orchestrates end-to-end Grounded RAG Generation:
    1. Hybrid Candidate Retrieval (Dense + Lexical RRF)
    2. Out-of-domain / zero candidate abstention gate
    3. Token-budgeted, Lost-in-the-Middle context assembly
    4. Resilient LLM generation with versioned grounded prompts
    5. Sentence-level citation extraction and grounding verification
    6. Audit and telemetry persistence (query_logs + query_citations)
    """

    def __init__(
        self,
        db: AsyncSession,
        retriever: HybridRetriever | None = None,
        llm_client: LLMClient | None = None,
        context_builder: ContextBuilder | None = None,
        prompt_manager: PromptManager | None = None,
        citation_verifier: CitationVerifier | None = None,
    ) -> None:
        self.db = db
        self.retriever = retriever or HybridRetriever(db)
        self.llm_client = llm_client or get_llm_client()
        self.context_builder = context_builder or ContextBuilder()
        self.prompt_manager = prompt_manager or PromptManager()
        self.citation_verifier = citation_verifier or CitationVerifier()

    async def execute_query(
        self,
        req: QueryRequest,
        current_user: User,
    ) -> QueryResponse:
        start_time = time.perf_counter()
        query_id = uuid.uuid4()
        trace_id = f"trc-{uuid.uuid4().hex[:12]}"

        # 1. Establish tenant-scoped access perimeter
        scope = AccessScope(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            collection_ids=req.collection_ids,
        )

        # 2. Retrieve candidates via Hybrid Search (Dense + Lexical + RRF)
        candidates = await self.retriever.retrieve(
            query=req.query,
            scope=scope,
            top_k=req.top_k,
        )

        # 3. Abstention Gate: Zero candidates found
        if not candidates:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            abstention_answer = (
                "I do not have enough information in the provided documents to answer this question."
            )

            # Persist zero-cost abstention log
            log_record = QueryLog(
                id=query_id,
                tenant_id=current_user.tenant_id,
                user_id=current_user.id,
                question=req.query,
                rewritten_query=None,
                answer=abstention_answer,
                abstained=True,
                trace_id=trace_id,
                prompt_version=self.prompt_manager.default_version,
                model="abstention-gate",
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
                latency_ms=latency_ms,
            )
            self.db.add(log_record)
            await self.db.commit()

            return QueryResponse(
                query=req.query,
                answer=abstention_answer,
                citations=[],
                abstained=True,
                model="abstention-gate",
                prompt_version=self.prompt_manager.default_version,
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
                latency_ms=latency_ms,
                query_id=query_id,
            )

        # 4. Context Assembly (Token budget + Lost-in-the-Middle permutation)
        built_context = self.context_builder.build(
            candidates=candidates,
            max_context_tokens=req.max_context_tokens,
            enable_lost_in_middle=True,
        )

        # 5. Format grounded prompts
        messages, prompt_ver = self.prompt_manager.format_messages(
            context_text=built_context.context_text,
            question=req.query,
        )

        # 6. Execute LLM generation
        llm_request = LLMRequest(
            messages=messages,
            model=settings.LLM_MODEL,
            temperature=req.temperature,
            max_tokens=1000,
            metadata={"query_id": str(query_id), "trace_id": trace_id},
        )
        llm_result = await self.llm_client.generate(llm_request)

        # 7. Check if LLM output indicates abstention
        is_abstained = self.prompt_manager.is_abstention(llm_result.content)

        # 8. Extract and verify citations
        citations: list[CitationItem] = []
        if not is_abstained:
            verification = self.citation_verifier.verify(
                answer=llm_result.content,
                source_map=built_context.source_map,
            )
            citations = verification.citations

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # 9. Persist telemetry to query_logs and query_citations
        log_record = QueryLog(
            id=query_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            question=req.query,
            rewritten_query=None,
            answer=llm_result.content,
            abstained=is_abstained,
            trace_id=trace_id,
            prompt_version=prompt_ver,
            model=llm_result.model,
            input_tokens=llm_result.usage.prompt_tokens,
            output_tokens=llm_result.usage.completion_tokens,
            cost_usd=llm_result.cost_usd,
            latency_ms=latency_ms,
        )
        self.db.add(log_record)

        # Persist citations if any
        for rank_idx, cit in enumerate(citations, start=1):
            cit_record = QueryCitation(
                query_id=query_id,
                chunk_id=cit.chunk_id,
                rank=rank_idx,
                rerank_score=cit.relevance_score,
            )
            self.db.add(cit_record)

        await self.db.commit()

        return QueryResponse(
            query=req.query,
            answer=llm_result.content,
            citations=citations,
            abstained=is_abstained,
            model=llm_result.model,
            prompt_version=prompt_ver,
            input_tokens=llm_result.usage.prompt_tokens,
            output_tokens=llm_result.usage.completion_tokens,
            cost_usd=round(float(llm_result.cost_usd), 6),
            latency_ms=latency_ms,
            query_id=query_id,
        )
