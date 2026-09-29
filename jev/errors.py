"""公開例外型別與 HTTP 錯誤分類。"""

from __future__ import annotations

import time
from email.utils import parsedate_to_datetime


class TypeSafeError(Exception):
    """Base error for this independently implemented client."""


class JevError(TypeSafeError):
    """Invalid input, incomplete scoring, or backend failure."""

class TypeSafeAPIError(TypeSafeError):
    def __init__(self, status, body=None, headers=None, endpoint=None):
        self.status, self.body = status, body
        self.headers = {str(k).lower(): v for k, v in (headers or {}).items()}
        self.endpoint = endpoint
        super().__init__(f"Backend HTTP {status} at {endpoint}: {body}")

    @property
    def request_id(self):
        return self.headers.get("x-typesafe-request-id")


class TypeSafeBadRequestError(TypeSafeAPIError):
    pass


class TypeSafeAuthenticationError(TypeSafeAPIError):
    pass


class TypeSafePermissionDeniedError(TypeSafeAPIError):
    pass


class TypeSafeNotFoundError(TypeSafeAPIError):
    pass


class TypeSafeUnprocessableEntityError(TypeSafeAPIError):
    pass


class TypeSafeInternalServerError(TypeSafeAPIError):
    pass


def _retry_after(headers):
    headers = {str(k).lower(): v for k, v in headers.items()}
    try:
        if "retry-after-ms" in headers:
            return max(0.0, float(headers["retry-after-ms"]) / 1000)
        value = headers.get("retry-after")
        if value is None:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            return max(0.0, parsedate_to_datetime(value).timestamp() - time.time())
    except (TypeError, ValueError, OverflowError):
        return None


class TypeSafeRateLimitError(TypeSafeAPIError):
    @property
    def retry_after_ms(self):
        delay = _retry_after(self.headers)
        return None if delay is None else delay * 1000


def _http_error_class(status):
    return {400: TypeSafeBadRequestError, 401: TypeSafeAuthenticationError,
            403: TypeSafePermissionDeniedError, 404: TypeSafeNotFoundError,
            422: TypeSafeUnprocessableEntityError, 429: TypeSafeRateLimitError}.get(
                status, TypeSafeInternalServerError if status >= 500 else TypeSafeAPIError)


class TypeSafeAPIConnectionError(TypeSafeError, ConnectionError):
    pass


class TypeSafeAPITimeoutError(TypeSafeAPIConnectionError, TimeoutError):
    def __init__(self, message, *, timeout=None):
        self.timeout = timeout
        super().__init__(message)


class TypeSafeAPIResponseValidationError(TypeSafeAPIError):
    def __init__(self, status=200, body=None, headers=None, field_path=None, endpoint=None):
        self.field_path = field_path
        super().__init__(status, body, headers, endpoint)
