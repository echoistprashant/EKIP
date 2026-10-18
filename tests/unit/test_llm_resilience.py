import pytest
from fastapi import HTTPException

from app.llm.circuit_breaker import CircuitBreaker, CircuitState
from app.llm.client import ChatMessage, LLMRequest
from app.llm.cost import calculate_cost_usd
from app.llm.providers.mock_llm import MockLLMClient
from app.llm.retry import execute_with_retry
from app.llm.router import ResilientLLMRouter


def test_cost_calculation():
    # 1000 input tokens + 500 output tokens for gemini-1.5-flash
    # input: 1000 * 0.075 / 1M = 0.000075
    # output: 500 * 0.30 / 1M = 0.000150
    # total = 0.000225 USD
    cost = calculate_cost_usd("gemini-1.5-flash", 1000, 500)
    assert cost == 0.000225

    # Mock model is 0.0
    mock_cost = calculate_cost_usd("mock-model", 1000, 500)
    assert mock_cost == 0.0


@pytest.mark.asyncio
async def test_retry_on_transient_error():
    attempts = 0

    async def flaky_call():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            err = HTTPException(status_code=429, detail="Rate limit exceeded")
            err.status_code = 429
            raise err
        return "SUCCESS"

    result = await execute_with_retry(
        flaky_call,
        max_attempts=3,
        base_delay=0.01,
        max_delay=0.1,
    )
    assert result == "SUCCESS"
    assert attempts == 3


@pytest.mark.asyncio
async def test_do_not_retry_non_transient_400():
    attempts = 0

    async def bad_request_call():
        nonlocal attempts
        attempts += 1
        err = HTTPException(status_code=400, detail="Invalid prompt structure")
        err.status_code = 400
        raise err

    with pytest.raises(HTTPException) as exc_info:
        await execute_with_retry(
            bad_request_call,
            max_attempts=3,
            base_delay=0.01,
        )

    # Must abort immediately on 400 without burning retry budget
    assert exc_info.value.status_code == 400
    assert attempts == 1


def test_circuit_breaker_transitions():
    cb = CircuitBreaker(name="test-cb", failure_threshold=2, recovery_timeout=0.1)
    assert cb.state == CircuitState.CLOSED
    assert cb.is_available() is True

    # 1 failure
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED

    # 2nd failure -> Trips circuit
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.is_available() is False

    # Success resets
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.is_available() is True


@pytest.mark.asyncio
async def test_router_automatic_fallback():
    primary_mock = MockLLMClient()
    fallback_mock = MockLLMClient(default_response="Response from Fallback Provider [1]")

    # Inject failure into primary
    err = HTTPException(status_code=503, detail="Primary provider service unavailable")
    err.status_code = 503
    primary_mock.simulate_failure(err)

    router = ResilientLLMRouter(
        primary_client=primary_mock,
        primary_model="gemini-1.5-flash",
        fallback_client=fallback_mock,
        fallback_model="mock-model",
        failure_threshold=1,
    )

    req = LLMRequest(
        messages=[ChatMessage(role="user", content="How to setup replication?")],
        model="gemini-1.5-flash",
    )

    # Primary will fail -> Router gracefully executes fallback!
    res = await router.generate(req)

    assert "Response from Fallback Provider" in res.content
    assert router.primary_breaker.state == CircuitState.OPEN
