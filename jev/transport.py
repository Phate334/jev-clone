"""HTTP 連線、驗證資訊、逾時與請求數限制。"""

from __future__ import annotations

import json
import math
import socket
import threading
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from .errors import (JevError, TypeSafeAPIResponseValidationError,
                     TypeSafeAPITimeoutError, TypeSafeAPIConnectionError, _http_error_class)
from .scoring import _json


class _BaseClient:
    def __init__(self, base_url=None, *, api_key=None,
                 concurrency=4, timeout=120.0, calibration_temperature=1.0,
                 chat_template_kwargs=None, headers=None):
        """Configure the inference server, separately from the Jev JSON request.

        calibration_temperature affects candidate normalization, not sampling.
        At most concurrency HTTP requests are in flight for this client.
        """
        self.base_url = (base_url or self.default_url).rstrip("/")
        parsed = urlsplit(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.query or parsed.fragment:
            raise JevError("OPENAI_BASE_URL 必須是有效的 HTTP(S) 網址，不能包含查詢參數或片段")
        if self.base_url.endswith("/v1"):
            self.base_url = self.base_url[:-3]
        if isinstance(concurrency, bool) or not isinstance(concurrency, int) or concurrency < 1:
            raise JevError("concurrency must be a positive integer")
        if not math.isfinite(timeout) or timeout <= 0:
            raise JevError("timeout must be positive and finite")
        if not math.isfinite(calibration_temperature) or calibration_temperature <= 0:
            raise JevError("calibration_temperature must be positive and finite")
        self.api_key = api_key
        self.headers = dict(headers or {})
        self.concurrency = concurrency
        self.timeout = timeout
        self.temperature = calibration_temperature
        self.template_kwargs = ({"enable_thinking": False} if chat_template_kwargs is None
                                else dict(chat_template_kwargs))
        self._limit = threading.BoundedSemaphore(concurrency)
        self._detected = {}
        self._detection_lock = threading.Lock()

    def _post(self, path, body):
        return self._request("POST", path, body)

    def _request(self, method, path, body=None):
        headers = {key: value for key, value in self.headers.items()
                   if key.lower() not in {"authorization", "content-type", "accept"}}
        headers.update({"Content-Type": "application/json", "Accept": "application/json"})
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        request = urllib.request.Request(self.base_url + path, data=None if body is None else _json(body).encode(),
                                         headers=headers, method=method)
        with self._limit:
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    try:
                        data = json.load(response)
                    except ValueError as exc:
                        raise TypeSafeAPIResponseValidationError(200, None, {}, "body", path) from exc
            except urllib.error.HTTPError as exc:
                detail = exc.read(4096).decode("utf-8", errors="replace")
                try:
                    detail = json.loads(detail)
                except ValueError:
                    pass
                cls = _http_error_class(exc.code)
                raise cls(exc.code, detail, dict(exc.headers), path) from exc
            except (TimeoutError, socket.timeout) as exc:
                raise TypeSafeAPITimeoutError(str(exc), timeout=self.timeout) from exc
            except (urllib.error.URLError, OSError) as exc:
                if isinstance(getattr(exc, "reason", None), (TimeoutError, socket.timeout)):
                    raise TypeSafeAPITimeoutError(str(exc), timeout=self.timeout) from exc
                raise TypeSafeAPIConnectionError(f"Backend request failed at {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise JevError(f"Expected a JSON object from {path}")
        return data
