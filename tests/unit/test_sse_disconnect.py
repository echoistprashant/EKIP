import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.user import User
from app.rag.retrieval.base import Candidate
from app.schemas.query import QueryRequest
from app.services.streaming_service import StreamingQueryService


@pytest.mark.asyncio
async def test_sse_stops_generation_and_db_write_on_client_disconnect():
    """
    Test that when client disconnects during SSE streaming:
    1. stream_query checks request.is_disconnected().
    2. Generation immediately halts.
    3. No QueryLog or QueryCitation records are committed to the DB.
    """
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    service = StreamingQueryService(mock_db)

    # Bypass token budget in unit test
    with patch("app.services.streaming_service.check_token_budget") as mock_budget:
        mock_budget.return_value = None

        cand = Candidate(
            chunk_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            collection_id=uuid.uuid4(),
            content="mock ground truth content",
            section_path="Section 1",
            page_start=1,
            page_end=1,
            score=0.9,
            retrieval_method="dense",
        )
        mock_retriever = AsyncMock()
        mock_retriever.retrieve.return_value = [cand]
        service.retriever = mock_retriever

        mock_reranker = AsyncMock()
        mock_reranker.rerank.return_value = [cand]
        service.reranker = mock_reranker

        user = User(id=uuid.uuid4(), tenant_id=uuid.uuid4(), email="u@test.com", role="admin")
        req = QueryRequest(query="test query")

        mock_request = AsyncMock()
        mock_llm = MagicMock()

        async def fake_stream(_):
            yield MagicMock(text="chunk1 ", usage=None)
            # Client disconnects during stream
            mock_request.is_disconnected.return_value = True
            yield MagicMock(text="chunk2 ", usage=None)

        mock_llm.stream = fake_stream
        service.llm_client = mock_llm

        # Initially connected, then disconnected
        mock_request.is_disconnected.side_effect = [False, True]

        events = []
        async for event in service.stream_query(req=req, current_user=user, request=mock_request):
            events.append(event)

        # Crucial assertions:
        # 1. We did not yield all chunks or the final "done" event because client disconnected
        assert not any("done" in e for e in events)
        # 2. Database commit was NOT called because DB writes were aborted!
        assert not mock_db.commit.called
