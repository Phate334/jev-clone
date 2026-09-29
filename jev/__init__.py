"""Jev 風格的統一決策介面。"""

from .client import (
    TypeSafeClient,
    AsyncTypeSafeClient,
)
from .types import (
    Noul,
    Choice,
    Score,
    NoulCriteria,
    Question,
    NoulAnswer,
    ChoiceAnswer,
    ScoreAnswer,
    Answer,
    SystemOneResponse,
    Usage,
)
from .retry import (
    RetryPolicy,
)
from .errors import (
    TypeSafeError,
    TypeSafeAPIError,
    TypeSafeAPIConnectionError,
    TypeSafeAPITimeoutError,
    TypeSafeAPIResponseValidationError,
    TypeSafeBadRequestError,
    TypeSafeAuthenticationError,
    TypeSafePermissionDeniedError,
    TypeSafeNotFoundError,
    TypeSafeUnprocessableEntityError,
    TypeSafeRateLimitError,
    TypeSafeInternalServerError,
    JevError,
)

__version__ = "0.2.0"
__all__ = [
    "TypeSafeClient",
    "AsyncTypeSafeClient",
    "Noul",
    "Choice",
    "Score",
    "NoulCriteria",
    "Question",
    "NoulAnswer",
    "ChoiceAnswer",
    "ScoreAnswer",
    "Answer",
    "SystemOneResponse",
    "Usage",
    "RetryPolicy",
    "TypeSafeError",
    "TypeSafeAPIError",
    "TypeSafeAPIConnectionError",
    "TypeSafeAPITimeoutError",
    "TypeSafeAPIResponseValidationError",
    "TypeSafeBadRequestError",
    "TypeSafeAuthenticationError",
    "TypeSafePermissionDeniedError",
    "TypeSafeNotFoundError",
    "TypeSafeUnprocessableEntityError",
    "TypeSafeRateLimitError",
    "TypeSafeInternalServerError",
    "JevError",
]
