import asyncio
import logging
import random
from typing import Any, Callable, Coroutine

logger = logging.getLogger("ekip.llm.retry")


def is_retryable_status_code(code: int) -> bool:
    """Classify HTTP status codes as transient (retryable) vs permanent (non-retryable)."""
    # 429 = Rate Limit, 500+ = Provider server error / Gateway timeout
    return code == 429 or code >= 500


def calculate_backoff_delay(attempt: int, base_delay: float = 0.5, max_delay: float = 8.0) -> float:
    """
    Computes exponential backoff with full jitter to avoid retry storms.
    delay = min(max_delay, base_delay * (2 ^ attempt)) + uniform_jitter
    """
    exp_delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
    jitter = random.uniform(0.0, 0.5)
    return exp_delay + jitter


async def execute_with_retry(
    operation: Callable[[], Coroutine[Any, Any, Any]],
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 8.0,
) -> Any:
    """
    Executes an async LLM provider operation with bounded retries and jitter.
    Fails fast on non-retryable 4xx client errors.
    """
    last_exception: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return await operation()
        except Exception as e:
            last_exception = e
            status_code = getattr(e, "status_code", None)

            # Do NOT retry non-transient client errors (e.g. 400 Bad Request, 401 Unauthorized)
            if status_code is not None and not is_retryable_status_code(status_code):
                logger.warning(f"Non-retryable client error {status_code}: {e}. Aborting retries.")
                raise e

            if attempt == max_attempts:
                logger.error(f"Exhausted all {max_attempts} retry attempts. Last error: {e}")
                break

            delay = calculate_backoff_delay(attempt, base_delay, max_delay)
            logger.warning(
                f"Transient error on attempt {attempt}/{max_attempts}: {e}. Retrying in {delay:.2f}s..."
            )
            await asyncio.sleep(delay)

    assert last_exception is not None
    raise last_exception
