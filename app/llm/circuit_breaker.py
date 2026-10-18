import time
from enum import Enum


class CircuitState(str, Enum):
    CLOSED = "closed"        # Healthy, traffic flows normally
    OPEN = "open"            # Failing, requests blocked immediately (fail-fast)
    HALF_OPEN = "half_open"  # Testing recovery with a single probe request


class CircuitBreakerOpenException(Exception):
    """Raised when an operation is attempted on an open circuit."""
    pass


class CircuitBreaker:
    """
    Protects downstream LLM providers during outages.
    Trips to OPEN after `failure_threshold` consecutive failures.
    Transitions to HALF_OPEN after `recovery_timeout` seconds to probe health.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.last_failure_time: float = 0.0

    def is_available(self) -> bool:
        """Check if circuit allows calls or has entered half-open probe state."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            elapsed = time.monotonic() - self.last_failure_time
            if elapsed >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                return True
            return False

        # If HALF_OPEN, allows probe request
        return True

    def record_success(self) -> None:
        """Reset failure counts on successful response."""
        self.consecutive_failures = 0
        self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Increment failure count and trip circuit if threshold reached."""
        self.consecutive_failures += 1
        self.last_failure_time = time.monotonic()

        if self.state == CircuitState.HALF_OPEN or self.consecutive_failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
