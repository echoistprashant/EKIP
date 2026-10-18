from collections.abc import AsyncIterator
import json
import time
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import BaseSemanticCache, get_semantic_cache
from app.core.config import settings
from app.llm import LLMClient, LLMRequest, get_llm_client
from app.models.query_log import QueryCitation, QueryLog
from app.models.user import User
from app.rag.citations import CitationVerifier
from app.rag.compression import ExtractiveSentenceCompressor, get_compressor
from app.rag.context_builder import ContextBuilder
from app.rag.embeddings import BaseEmbedder, get_embedder
from app.rag.prompts.manager import PromptManager
from app.rag.query_transform import (
    BaseQueryTransformer,
    QueryTransformationResult,
    get_query_transformer,
)
from app.rag.rerank import BaseReranker, get_reranker
from app.rag.retrieval.base import AccessScope, Candidate
from app.rag.retrieval.hybrid import HybridRetriever
from app.rag.retrieval.rrf import multi_list_rrf
from app.schemas.query import CitationItem, QueryRequest, QueryResponse


def sse_event(event_type: str, data: dict) -> str:
    """Formats payload into a compliant Server-Sent Event (SSE) message."""
    return f"event: {event_type}\ndata: {json.dumps(data, default=str)}\n\n"


class StreamingQueryService:
    """
    Orchestrates real-time streaming RAG generation via Server-Sent Events (SSE).
    Emits structured events:
      - 'ping': initial stream connection acknowledgment
      - 'sources': retrieved and reranked source previews
      - 'token': word-by-word streaming generation tokens
      - 'done': final citation verification and telemetry
      - 'abstention': out-of-domain refusal
    """

    def __init__(
        self,
        db: AsyncSession,
        retriever: HybridRetriever | None = None,
        reranker: BaseReranker | None = None,
        compressor: ExtractiveSentenceCompressor | None = None,
        transformer: BaseQueryTransformer | None = None,
        cache: BaseSemanticCache | None = None,
        embedder: BaseEmbedder | None = None,
        llm_client: LLMClient | None = None,
        context_builder: ContextBuilder | None = None,
        prompt_manager: PromptManager | None = None,
        citation_verifier: CitationVerifier | None = None,
    ) -> None:
        self.db = db
        self.retriever = retriever or HybridRetriever(db)
        self.reranker = reranker or get_reranker()
        self.compressor = compressor or get_compressor()
        self.transformer = transformer
        self.cache = cache if cache is not None else get_semantic_cache()
        self.embedder = embedder if embedder is not None else get_embedder()
        self.llm_client = llm_client or get_llm_client()
        self.context_builder = context_builder or ContextBuilder()
        self.prompt_manager = prompt_manager or PromptManager()
        self.citation_verifier = citation_verifier or CitationVerifier()

    async def stream_query(
        self,
        req: QueryRequest,
        current_user: User,
    ) -> AsyncIterator[str]:
        start_time = time.perf_counter()
        query_id = uuid.uuid4()
        trace_id = f"trc-{uuid.uuid4().hex[:12]}"

        # Connection acknowledgment
        yield sse_event("ping", {"status": "connected", "query_id": str(query_id)})

        scope = AccessScope(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            collection_ids=req.collection_ids,
        )

        query_embedding: list[float] | None = None

        # 1. Check Semantic Cache
        if self.cache is not None and not req.bypass_cache:
            if self.embedder is not None:
                query_embedding = await self.embedder.embed_query(req.query)

            cache_hit = await self.cache.get(
                tenant_id=current_user.tenant_id,
                collection_ids=req.collection_ids,
                query=req.query,
                query_embedding=query_embedding,
            )

            if cache_hit is not None:
                hit_latency = int((time.perf_counter() - start_time) * 1000)
                cached = cache_hit.response

                # Emit cached sources
                yield sse_event("sources", {
                    "sources": [c.model_dump() for c in cached.citations],
                    "cached": True,
                    "cache_type": cache_hit.cache_type,
                })

                # Stream cached answer tokens
                words = cached.answer.split(" ")
                for idx, word in enumerate(words):
                    token_text = word if idx == len(words) - 1 else word + " "
                    yield sse_event("token", {"text": token_text})

                # Emit done event
                yield sse_event("done", {
                    "query_id": str(query_id),
                    "cached": True,
                    "cache_type": cache_hit.cache_type,
                    "similarity": cache_hit.similarity,
                    "citations": [c.model_dump() for c in cached.citations],
                    "latency_ms": hit_latency,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                })
                return

        # 2. Query Transformation & Hybrid Retrieval
        strategy = (
            req.query_transformation
            if req.query_transformation != "none"
            else settings.DEFAULT_QUERY_TRANSFORMATION
        )
        transformer = self.transformer or get_query_transformer(strategy)

        if transformer is not None and strategy != "none":
            transform_res = await transformer.transform(req.query)
            if transform_res.strategy_used == "hyde" and transform_res.hypothetical_document:
                candidates = await self.retriever.retrieve(
                    query=req.query,
                    scope=scope,
                    top_k=req.top_k,
                    dense_query=transform_res.hypothetical_document,
                    lexical_query=req.query,
                )
            else:
                candidates = await self.retriever.retrieve(
                    query=transform_res.transformed_query,
                    scope=scope,
                    top_k=req.top_k,
                )
        else:
            candidates = await self.retriever.retrieve(
                query=req.query,
                scope=scope,
                top_k=req.top_k,
            )

        # 3. Abstention Gate
        if not candidates:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            msg = "I do not have enough information in the provided documents to answer this question."

            log_record = QueryLog(
                id=query_id,
                tenant_id=current_user.tenant_id,
                user_id=current_user.id,
                question=req.query,
                rewritten_query=None,
                answer=msg,
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

            yield sse_event("abstention", {"message": msg, "query_id": str(query_id)})
            return

        # 4. Reranking & Compression
        if req.rerank:
            candidates = await self.reranker.rerank(
                query=req.query,
                candidates=candidates,
                top_n=req.top_n,
            )

        if req.compress_context and self.compressor is not None:
            candidates = self.compressor.compress(query=req.query, candidates=candidates)

        # 5. Context Assembly
        built_context = self.context_builder.build(
            candidates=candidates,
            max_context_tokens=req.max_context_tokens,
            enable_lost_in_middle=True,
        )

        # Emit sources preview to UI immediately
        sources_payload = [
            {
                "source_id": s.source_id,
                "document_id": str(s.candidate.document_id),
                "section_path": s.candidate.section_path,
                "snippet": s.candidate.content[:160] + "...",
                "relevance_score": s.candidate.score,
            }
            for s in built_context.sources
        ]
        yield sse_event("sources", {"sources": sources_payload, "cached": False})

        # 6. Stream tokens from LLM
        messages, prompt_ver = self.prompt_manager.format_messages(
            context_text=built_context.context_text,
            question=req.query,
        )
        llm_request = LLMRequest(
            messages=messages,
            model=settings.LLM_MODEL,
            temperature=req.temperature,
            max_tokens=1000,
            metadata={"query_id": str(query_id), "trace_id": trace_id},
        )

        full_answer_parts: list[str] = []
        token_usage = None

        async for chunk in self.llm_client.stream(llm_request):
            if chunk.text:
                full_answer_parts.append(chunk.text)
                yield sse_event("token", {"text": chunk.text})
            if chunk.usage:
                token_usage = chunk.usage

        full_answer = "".join(full_answer_parts)
        is_abstained = self.prompt_manager.is_abstention(full_answer)

        # 7. Verify citations
        citations: list[CitationItem] = []
        if not is_abstained:
            verification = self.citation_verifier.verify(
                answer=full_answer,
                source_map=built_context.source_map,
            )
            citations = verification.citations

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        prompt_tokens = token_usage.prompt_tokens if token_usage else len(messages[1].content.split())
        completion_tokens = token_usage.completion_tokens if token_usage else len(full_answer.split())

        # 8. Persist Telemetry to DB
        log_record = QueryLog(
            id=query_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            question=req.query,
            rewritten_query=None,
            answer=full_answer,
            abstained=is_abstained,
            trace_id=trace_id,
            prompt_version=prompt_ver,
            model=settings.LLM_MODEL,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            cost_usd=0.0,
            latency_ms=latency_ms,
        )
        self.db.add(log_record)

        for rank_idx, cit in enumerate(citations, start=1):
            cit_record = QueryCitation(
                query_id=query_id,
                chunk_id=cit.chunk_id,
                rank=rank_idx,
                rerank_score=cit.relevance_score,
            )
            self.db.add(cit_record)

        await self.db.commit()

        # 9. Store in Semantic Cache
        if not is_abstained and self.cache is not None:
            if query_embedding is None and self.embedder is not None:
                query_embedding = await self.embedder.embed_query(req.query)
            final_res = QueryResponse(
                query=req.query,
                answer=full_answer,
                citations=citations,
                abstained=False,
                cached=False,
                model=settings.LLM_MODEL,
                prompt_version=prompt_ver,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                cost_usd=0.0,
                latency_ms=latency_ms,
                query_id=query_id,
            )
            await self.cache.set(
                tenant_id=current_user.tenant_id,
                collection_ids=req.collection_ids,
                query=req.query,
                query_embedding=query_embedding,
                response=final_res,
                ttl_seconds=settings.SEMANTIC_CACHE_TTL_SECONDS,
            )

        # 10. Emit final done event
        yield sse_event("done", {
            "query_id": str(query_id),
            "cached": False,
            "citations": [c.model_dump() for c in citations],
            "latency_ms": latency_ms,
            "input_tokens": prompt_tokens,
            "output_tokens": completion_tokens,
            "cost_usd": 0.0,
        })
