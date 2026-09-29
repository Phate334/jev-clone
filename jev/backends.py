"""後端辨識、問題並行處理與兩種引擎的 logprob 讀值。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from .errors import JevError
from .scoring import _json, _items, _prepare, _probabilities, _answer, _count, _tokens
from .transport import _BaseClient


class _Backend(_BaseClient):
    default_url = "http://127.0.0.1:8000/v1"

    def evaluate_json(self, request):
        """Accept a Jev-shaped dict and return model/answers/usage as a dict.

        This is a Python client, not a /v1/systemone HTTP server. Question IDs
        are preserved in the output and are not included in the model prompt.
        """
        if not isinstance(request, dict):
            raise JevError("The request must be a JSON object")
        try:
            _json(request)
        except (TypeError, ValueError) as exc:
            raise JevError("Request must contain only valid JSON values") from exc
        if not isinstance(request.get("model"), str) or not request["model"]:
            raise JevError("model is required and must be a nonempty string")
        if not isinstance(request.get("state"), (str, dict, list)):
            raise JevError("state must be a string, object, or array")
        questions = request.get("questions")
        if not isinstance(questions, dict) or not questions:
            raise JevError("questions must be a nonempty object")
        if not all(isinstance(key, str) for key in questions):
            raise JevError("Question IDs must be strings")
        # Validate the whole request before sending any inference request.
        prepared = [(key, question, _items(question)) for key, question in questions.items()]
        model = request["model"]

        def evaluate(entry):
            key, question, items = entry
            messages, labels = _prepare(request["state"], question, items)
            try:
                logps, usage, actual_model = self._score(model, messages, labels)
                p = _probabilities(logps, self.temperature)
                return key, _answer(question, items, p), usage, actual_model
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                raise JevError(f"Invalid backend response for question {key!r}: {exc}") from exc

        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            rows = list(pool.map(evaluate, prepared))
        models = {row[3] for row in rows}
        if len(models) != 1:
            raise JevError("Backend returned inconsistent model identities")
        return {
            "model": rows[0][3],
            "answers": {row[0]: row[1] for row in rows},
            "usage": {name: sum(row[2][name] for row in rows)
                      for name in ("input_tokens", "output_tokens")},
        }


    def _detect(self, model):
        with self._detection_lock:
            if model in self._detected:
                return self._detected[model]
            data = self._request("GET", "/v1/models").get("data")
            if not isinstance(data, list) or not all(isinstance(row, dict) for row in data):
                raise JevError("/v1/models 未回傳有效的模型清單")
            matches = [row for row in data if row.get("id") == model]
            if not matches:
                raise JevError(f"後端未提供模型 {model!r}，請確認 model")
            owners = {str(row.get("owned_by", "")).lower() for row in matches}
            if owners == {"vllm"}:
                kind = "vllm"
            elif owners == {"llamacpp"}:
                kind = "llama"
            else:
                raise JevError("無法從 /v1/models 的 owned_by 辨識 vLLM 或 llama.cpp；請確認代理保留原始模型資訊")
            self._detected[model] = kind
            return kind

    def _score(self, model, messages, labels):
        kind = self._detect(model)
        if kind == "llama":
            return self._score_llama(model, messages, labels)
        return self._score_vllm(model, messages, labels)

    readout_depths = (64, 512, 4096, 32768)

    def _tokenize(self, text):
        response = self._post("/tokenize", {
            "content": text, "add_special": False, "parse_special": True,
        })
        return _tokens(response.get("tokens"))

    def _score_llama(self, model, messages, labels):
        rendered = self._post("/apply-template", {
            "messages": messages, "chat_template_kwargs": self.template_kwargs,
        })
        if not isinstance(rendered.get("prompt"), str) or not rendered["prompt"]:
            raise JevError("/apply-template did not return a prompt")
        prompt = rendered["prompt"] + "Answer:\n"
        prefix = self._tokenize(prompt)
        token_ids = []
        for label in labels:
            ids = self._tokenize(prompt + label)
            if len(ids) != len(prefix) + 1 or ids[:-1] != prefix:
                raise JevError("Labels must each append one token to the identical answer prefix")
            token_ids.append(ids[-1])
        if len(set(token_ids)) != len(labels):
            raise JevError("Labels must map to distinct tokens")
        usage = {"input_tokens": 0, "output_tokens": 0}
        for depth in self.readout_depths:
            response = self._post("/completion", {
                "model": model,
                "prompt": prompt, "n_predict": 1, "temperature": 0,
                "n_probs": depth, "post_sampling_probs": False,
                "grammar": "root ::= " + " | ".join(_json(x) for x in labels),
                "cache_prompt": True, "stream": False,
            })
            if response.get("truncated"):
                raise JevError("Context was truncated; cannot score the original state")
            usage["input_tokens"] += _count(response["tokens_evaluated"])
            usage["output_tokens"] += _count(response["tokens_predicted"])
            positions = response.get("completion_probabilities")
            if not isinstance(positions, list) or len(positions) != 1:
                raise JevError("Expected raw logprobs at exactly one output position")
            entries = positions[0].get("top_logprobs")
            if not isinstance(entries, list):
                raise JevError("Expected top_logprobs; post-sampling probabilities are not accepted")
            by_id = {entry["id"]: entry["logprob"] for entry in entries}
            if all(token_id in by_id for token_id in token_ids):
                actual_model = response.get("model") or model
                if not isinstance(actual_model, str):
                    raise JevError("Invalid backend model name")
                return [by_id[token_id] for token_id in token_ids], usage, actual_model
        raise JevError("Raw top-k omitted a candidate even after retries; no probabilities returned")


    def _score_vllm(self, model, messages, labels):
        def evaluate(label):
            tokenized = self._post("/tokenize", {
                "model": model, "prompt": label, "add_special_tokens": False,
            })
            ids = _tokens(tokenized.get("tokens"))
            if len(ids) != 1:
                raise JevError(f"Label {label!r} must be exactly one token")
            response = self._post("/v1/chat/completions", {
                "model": model,
                "messages": messages + [{"role": "assistant", "content": "Answer:\n" + label}],
                "continue_final_message": True, "add_generation_prompt": False,
                "chat_template_kwargs": self.template_kwargs,
                "prompt_logprobs": 1, "return_token_ids": True,
                "max_tokens": 1, "temperature": 0, "stream": False,
            })
            prompt_ids = _tokens(response.get("prompt_token_ids"))
            rows = response.get("prompt_logprobs")
            if not isinstance(rows, list) or len(rows) != len(prompt_ids):
                raise JevError("prompt_logprobs must align with prompt_token_ids")
            if prompt_ids[-1] != ids[0]:
                raise JevError("Candidate is not the final token; check the template and answer boundary")
            last = rows[-1]
            entry = last.get(str(ids[0])) if isinstance(last, dict) else None
            if not isinstance(entry, dict) or "logprob" not in entry:
                raise JevError("Backend omitted the actual candidate token logprob")
            usage = {
                "input_tokens": _count(response["usage"]["prompt_tokens"]),
                "output_tokens": _count(response["usage"]["completion_tokens"]),
            }
            actual_model = response.get("model") or model
            if not isinstance(actual_model, str):
                raise JevError("Invalid backend model name")
            return entry["logprob"], prompt_ids[:-1], usage, actual_model, ids[0]

        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            rows = list(pool.map(evaluate, labels))
        if any(row[1] != rows[0][1] for row in rows):
            raise JevError("Candidates have different token prefixes; their scores are not comparable")
        if len({row[4] for row in rows}) != len(labels):
            raise JevError("Labels must map to distinct tokens")
        if len({row[3] for row in rows}) != 1:
            raise JevError("Backend returned inconsistent model identities")
        return [row[0] for row in rows], {
            name: sum(row[2][name] for row in rows)
            for name in ("input_tokens", "output_tokens")
        }, rows[0][3]
