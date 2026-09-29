"""同步與非同步的 Jev SDK 相容介面。"""

from __future__ import annotations

import asyncio
import math
import os
from collections.abc import Mapping
from copy import copy
from pydantic import BaseModel, ValidationError

from .backends import _Backend
from .errors import TypeSafeError, TypeSafeAPIResponseValidationError
from .retry import RetryPolicy, _retry_call
from .scoring import _json
from .types import _Question, SystemOneResponse


class TypeSafeClient:
    """Jev SDK 相容介面，以 model 指定後端提供的模型。"""

    default_url = _Backend.default_url

    def __init__(self, api_key=None, *, model=None, retry=None, timeout=None,
                 headers=None, transport=None, http_client=None, openai_base_url=None, base_url=None,
                 concurrency=4, calibration_temperature=1.0,
                 chat_template_kwargs=None):
        if transport is not None and http_client is not None:
            raise ValueError("transport and http_client are mutually exclusive")
        if transport is not None or http_client is not None:
            raise NotImplementedError("Custom httpx2 clients/transports are not supported by this local adapter")
        self.model = model or os.environ.get("TYPESAFE_DEFAULT_MODEL", "").strip() or "local-judge"
        self.retry = retry if retry is not None else RetryPolicy()
        if not isinstance(self.retry, RetryPolicy):
            raise TypeSafeError("retry must be a RetryPolicy from this module")
        if timeout is not None and (isinstance(timeout, bool) or not isinstance(timeout, (int, float))):
            raise TypeSafeError("This adapter accepts timeout as seconds, not httpx2.Timeout")
        if openai_base_url is not None and base_url is not None:
            raise TypeSafeError("openai_base_url 與相容參數 base_url 請擇一設定")
        endpoint = openai_base_url if openai_base_url is not None else base_url
        if endpoint is None:
            endpoint = os.environ.get("OPENAI_BASE_URL", "").strip() or self.default_url
        self.openai_base_url = endpoint
        self._backend = _Backend(base_url=endpoint,
                            api_key=api_key if api_key is not None else os.environ.get("OPENAI_API_KEY"),
                            concurrency=concurrency, timeout=120.0 if timeout is None else timeout,
                            calibration_temperature=calibration_temperature,
                            chat_template_kwargs=chat_template_kwargs,
                            headers=dict(headers or {}))
        self._closed = False

    def __enter__(self):
        if self._closed:
            raise TypeSafeError("Client is closed")
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        self._closed = True

    def _run(self, request, *, retry=None, timeout=None, extra_headers=None):
        if self._closed:
            raise TypeSafeError("Client is closed")
        policy = self.retry if retry is None else retry
        if not isinstance(policy, RetryPolicy):
            raise TypeSafeError("retry must be a RetryPolicy from this module")
        backend = copy(self._backend) if timeout is not None or extra_headers else self._backend
        if timeout is not None:
            if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
                raise TypeSafeError("timeout must be a number of seconds")
            if not math.isfinite(timeout) or timeout <= 0:
                raise TypeSafeError("timeout 必須是大於零的有限數值")
            backend.timeout = timeout
        if extra_headers:
            backend.headers = {**self._backend.headers, **extra_headers}
        return _retry_call(lambda: backend.evaluate_json(request), policy)

    def system_one(self, state, questions, *, model=None, retry=None, timeout=None,
                   extra_headers=None, extra_body=None, response_model=None):
        """Official-style signature; accepts question models or dictionaries."""
        if not isinstance(questions, Mapping) or not questions:
            raise TypeSafeError("questions must be a nonempty mapping")
        serialized = {}
        for name, question in questions.items():
            serialized[name] = (question.model_dump(mode="json", exclude_none=True)
                                if isinstance(question, _Question) else question)
        request = {"model": self.model if model is None else model,
                   "state": state, "questions": serialized}
        if extra_body is not None:
            request.update(extra_body)
        result = self._run(request, retry=retry, timeout=timeout, extra_headers=extra_headers)
        target = response_model or SystemOneResponse
        if not isinstance(target, type) or not issubclass(target, BaseModel):
            raise TypeSafeError("response_model must be a Pydantic BaseModel subclass")
        try:
            return target.model_validate_json(_json(result))
        except ValidationError as exc:
            path = ".".join(map(str, exc.errors()[0]["loc"]))
            raise TypeSafeAPIResponseValidationError(200, result, {}, path, "system_one") from exc


class AsyncTypeSafeClient(TypeSafeClient):
    """Same interface with async methods, running bounded HTTP work in threads."""

    async def __aenter__(self):
        return super().__enter__()

    async def __aexit__(self, *exc):
        await self.aclose()

    async def aclose(self):
        super().close()

    async def system_one(self, state, questions, *, model=None, retry=None, timeout=None,
                         extra_headers=None, extra_body=None, response_model=None):
        return await asyncio.to_thread(super().system_one, state, questions, model=model,
                                       retry=retry, timeout=timeout, extra_headers=extra_headers,
                                       extra_body=extra_body, response_model=response_model)
