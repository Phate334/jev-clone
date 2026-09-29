"""重試設定與退避處理。"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Any

from .errors import (TypeSafeError, TypeSafeAPIError, TypeSafeAPIConnectionError,
                     TypeSafeAPITimeoutError, _retry_after)


@dataclass(frozen=True)
class RetryPolicy:
    """SDK-shaped controls. Local default: no automatic network retries."""

    max_retries: int = 0
    backoff_initial: float = 0.5
    backoff_max: float = 8.0
    backoff_jitter: float = 0.25
    http_statuses: set[int] = field(default_factory=lambda: {429, 500, 502, 503, 504})
    respect_retry_after: bool = True
    api_connection_error: bool = True
    api_timeout_error: bool = True
    exceptions: tuple[type[Exception], ...] = ()
    predicate: Any = None
    timeout: float | None = None

    def __post_init__(self):
        if isinstance(self.max_retries, bool) or not isinstance(self.max_retries, int) or self.max_retries < 0:
            raise TypeSafeError("max_retries must be a nonnegative integer")
        for name in ("backoff_initial", "backoff_max", "backoff_jitter"):
            value = getattr(self, name)
            if not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
                raise TypeSafeError(f"{name} must be finite and nonnegative")
        if self.backoff_jitter > 1:
            raise TypeSafeError("backoff_jitter must be <= 1")
        if self.timeout is not None and (not math.isfinite(self.timeout) or self.timeout <= 0):
            raise TypeSafeError("Retry timeout must be positive or None")

    def accepts(self, exc):
        if isinstance(exc, TypeSafeAPITimeoutError):
            builtin = self.api_timeout_error
        elif isinstance(exc, TypeSafeAPIConnectionError):
            builtin = self.api_connection_error
        elif isinstance(exc, TypeSafeAPIError):
            builtin = exc.status in self.http_statuses
        else:
            builtin = False
        return builtin or isinstance(exc, tuple(self.exceptions)) or bool(self.predicate and self.predicate(exc))


def _retry_call(operation, policy):
    start = time.monotonic()
    for attempt in range(policy.max_retries + 1):
        try:
            return operation()
        except Exception as exc:
            if attempt == policy.max_retries or not policy.accepts(exc):
                raise
            delay = min(policy.backoff_max, policy.backoff_initial * (2 ** attempt))
            delay *= 1 - random.random() * policy.backoff_jitter
            if policy.respect_retry_after and isinstance(exc, TypeSafeAPIError):
                server_delay = _retry_after(exc.headers)
                if server_delay is not None:
                    delay = max(delay, server_delay)
            if policy.timeout is not None and time.monotonic() - start + delay >= policy.timeout:
                raise
            time.sleep(delay)
