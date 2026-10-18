import asyncio
import time
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import BaseSemanticCache, get_semantic_cache
from app.core.config import settings
from app.evaluation import RAGTriadEvaluator, get_evaluator
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


class QueryService:
    """
    Orchestrates end-to-end Grounded RAG Generation:
    1. Two-Tier Semantic Cache (L1 Exact Hash + L2 Vector Cosine Similarity)
    2. Query Transformation (HyDE / Multi-Query Expansion / Rewriting)
    3. Multi-list or Hybrid Retrieval (Dense HNSW + Lexical GIN with RRF)
    4. Out-of-domain / zero candidate abstention gate
    5. Stage 2: Deep Cross-Encoder Reranking (top_k -> top_n)
    6. Context Compression: Extractive sentence window trimming
    7. Token-budgeted, Lost-in-the-Middle XML context assembly
    8. Resilient LLM generation with versioned grounded prompts
    9. Sentence-level citation extraction and grounding verification
    10. RAG Triad Evaluation & Hallucination Guardrails
    11. Audit and telemetry persistence (query_logs + query_citations)
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
        evaluator: RAGTriadEvaluator | None = None,
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
        self.evaluator = evaluator or get_evaluator()
        self.llm_client = llm_client or get_llm_client()
        self.context_builder = context_builder or ContextBuilder()
        self.prompt_manager = prompt_manager or PromptManager()
        self.citation_verifier = citation_verifier or CitationVerifier()

    async def _execute_retrieval_with_transformation(
        self,
        req: QueryRequest,
        scope: AccessScope,
    ) -> tuple[list[Candidate], QueryTransformationResult]:
        strategy = (
            req.query_transformation
            if req.query_transformation != "none"
            else settings.DEFAULT_QUERY_TRANSFORMATION
        )

        transformer = self.transformer or get_query_transformer(strategy)
        if transformer is None or strategy == "none":
            candidates = await self.retriever.retrieve(
                query=req.query,
                scope=scope,
                top_k=req.top_k,
            )
            return candidates, QueryTransformationResult(
                original_query=req.query,
                transformed_query=req.query,
                expanded_queries=[req.query],
                strategy_used="none",
            )

        # Run query transformation
        transform_result = await transformer.transform(req.query)

        if transform_result.strategy_used == "hyde" and transform_result.hypothetical_document:
            # HyDE: use hypothetical doc for Dense vector search, original query for Lexical FTS
            candidates = await self.retriever.retrieve(
                query=req.query,
                scope=scope,
                top_k=req.top_k,
                dense_query=transform_result.hypothetical_document,
                lexical_query=req.query,
            )
        elif transform_result.strategy_used == "expansion" and len(transform_result.expanded_queries) > 1:
            # Multi-Query Expansion: retrieve for all variations concurrently, fuse via Multi-List RRF
            tasks = [
                self.retriever.retrieve(
                    query=q,
                    scope=scope,
                    top_k=req.top_k,
                )
                for q in transform_result.expanded_queries
            ]
            cand_lists = await asyncio.gather(*tasks)
            candidates = multi_list_rrf(cand_lists, k=60)[: req.top_k]
        elif transform_result.strategy_used == "rewrite":
            # Rewritten Query: execute retrieval with rewritten query
            candidates = await self.retriever.retrieve(
                query=transform_result.transformed_query,
                scope=scope,
                top_k=req.top_k,
            )
        else:
            candidates = await self.retriever.retrieve(
                query=req.query,
                scope=scope,
                top_k=req.top_k,
            )

        return candidates, transform_result

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

        query_embedding: list[float] | None = None

        # 2. Check Semantic Cache (L1 Exact Hash or L2 Cosine Vector Similarity)
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
                cached_res = QueryResponse(
                    query=req.query,
                    rewritten_query=cache_hit.response.rewritten_query,
                    query_transformation_strategy=cache_hit.response.query_transformation_strategy,
                    answer=cache_hit.response.answer,
                    citations=cache_hit.response.citations,
                    abstained=cache_hit.response.abstained,
                    cached=True,
                    cache_type=cache_hit.cache_type,
                    cache_similarity=cache_hit.similarity,
                    matched_query=cache_hit.matched_query,
                    model=cache_hit.response.model,
                    prompt_version=cache_hit.response.prompt_version,
                    input_tokens=0,
                    output_tokens=0,
                    cost_usd=0.0,
                    latency_ms=hit_latency,
                    groundedness_score=cache_hit.response.groundedness_score,
                    hallucination_warning=cache_hit.response.hallucination_warning,
                    query_id=query_id,
                )

                # Persist cache-hit telemetry log to query_logs
                log_record = QueryLog(
                    id=query_id,
                    tenant_id=current_user.tenant_id,
                    user_id=current_user.id,
                    question=req.query,
                    rewritten_query=cached_res.rewritten_query,
                    answer=cached_res.answer,
                    abstained=cached_res.abstained,
                    trace_id=trace_id,
                    prompt_version=cached_res.prompt_version,
                    model=f"{cached_res.model}-cache",
                    input_tokens=0,
                    output_tokens=0,
                    cost_usd=0.0,
                    latency_ms=hit_latency,
                    groundedness_score=cached_res.groundedness_score,
                    context_relevance_score=1.0,
                    answer_relevance_score=1.0,
                    hallucination_flag=cached_res.hallucination_warning,
                )
                self.db.add(log_record)
                await self.db.commit()

                return cached_res

        # 3. Stage 1: Query Transformation & Hybrid Candidate Retrieval
        candidates, transform_res = await self._execute_retrieval_with_transformation(
            req=req,
            scope=scope,
        )

        effective_rewritten = (
            transform_res.transformed_query if transform_res.strategy_used != "none" else None
        )

        # 4. Abstention Gate: Zero candidates found
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
                rewritten_query=effective_rewritten,
                answer=abstention_answer,
                abstained=True,
                trace_id=trace_id,
                prompt_version=self.prompt_manager.default_version,
                model="abstention-gate",
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
                latency_ms=latency_ms,
                groundedness_score=1.0,
                context_relevance_score=0.0,
                answer_relevance_score=1.0,
                hallucination_flag=False,
            )
            self.db.add(log_record)
            await self.db.commit()

            return QueryResponse(
                query=req.query,
                rewritten_query=effective_rewritten,
                query_transformation_strategy=transform_res.strategy_used,
                answer=abstention_answer,
                citations=[],
                abstained=True,
                cached=False,
                model="abstention-gate",
                prompt_version=self.prompt_manager.default_version,
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
                latency_ms=latency_ms,
                groundedness_score=1.0,
                hallucination_warning=False,
                query_id=query_id,
            )

        # 5. Stage 2: Cross-Encoder Reranking
        if req.rerank:
            candidates = await self.reranker.rerank(
                query=req.query,
                candidates=candidates,
                top_n=req.top_n,
            )

        # 6. Context Compression (Extractive sentence window)
        if req.compress_context and self.compressor is not None:
            candidates = self.compressor.compress(
                query=req.query,
                candidates=candidates,
            )

        # 7. Context Assembly (Token budget + Lost-in-the-Middle permutation)
        built_context = self.context_builder.build(
            candidates=candidates,
            max_context_tokens=req.max_context_tokens,
            enable_lost_in_middle=True,
        )

        # 8. Format grounded prompts
        messages, prompt_ver = self.prompt_manager.format_messages(
            context_text=built_context.context_text,
            question=req.query,
        )

        # 9. Execute LLM generation
        llm_request = LLMRequest(
            messages=messages,
            model=settings.LLM_MODEL,
            temperature=req.temperature,
            max_tokens=1000,
            metadata={"query_id": str(query_id), "trace_id": trace_id},
        )
        llm_result = await self.llm_client.generate(llm_request)

        # 10. Check if LLM output indicates abstention
        is_abstained = self.prompt_manager.is_abstention(llm_result.content)

        # 11. Extract and verify citations
        citations: list[CitationItem] = []
        if not is_abstained:
            verification = self.citation_verifier.verify(
                answer=llm_result.content,
                source_map=built_context.source_map,
            )
            citations = verification.citations

        # 12. Run RAG Triad Evaluation & Hallucination Guardrails
        eval_result = await self.evaluator.evaluate(
            query=req.query,
            context=built_context.context_text,
            answer=llm_result.content,
        )

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # 13. Persist telemetry to query_logs and query_citations
        log_record = QueryLog(
            id=query_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            question=req.query,
            rewritten_query=effective_rewritten,
            answer=llm_result.content,
            abstained=is_abstained,
            trace_id=trace_id,
            prompt_version=prompt_ver,
            model=llm_result.model,
            input_tokens=llm_result.usage.prompt_tokens,
            output_tokens=llm_result.usage.completion_tokens,
            cost_usd=llm_result.cost_usd,
            latency_ms=latency_ms,
            groundedness_score=eval_result.groundedness,
            context_relevance_score=eval_result.context_relevance,
            answer_relevance_score=eval_result.answer_relevance,
            hallucination_flag=eval_result.hallucination_warning,
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

        final_response = QueryResponse(
            query=req.query,
            rewritten_query=effective_rewritten,
            query_transformation_strategy=transform_res.strategy_used,
            answer=llm_result.content,
            citations=citations,
            abstained=is_abstained,
            cached=False,
            model=llm_result.model,
            prompt_version=prompt_ver,
            input_tokens=llm_result.usage.prompt_tokens,
            output_tokens=llm_result.usage.completion_tokens,
            cost_usd=round(float(llm_result.cost_usd), 6),
            latency_ms=latency_ms,
            groundedness_score=eval_result.groundedness,
            hallucination_warning=eval_result.hallucination_warning,
            query_id=query_id,
        )

        # 14. Populate Semantic Cache if not abstained and passed guardrails
        if not is_abstained and not eval_result.hallucination_warning and self.cache is not None:
            if query_embedding is None and self.embedder is not None:
                query_embedding = await self.embedder.embed_query(req.query)
            await self.cache.set(
                tenant_id=current_user.tenant_id,
                collection_ids=req.collection_ids,
                query=req.query,
                query_embedding=query_embedding,
                response=final_response,
                ttl_seconds=settings.SEMANTIC_CACHE_TTL_SECONDS,
            )

        return final_response
