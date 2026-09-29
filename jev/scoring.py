"""問題整理、候選機率正規化與決策輸出。"""

from __future__ import annotations

import json
import math
import string

from .errors import JevError


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":"))


def _description(value, allow_null=False):
    return isinstance(value, (str, dict, list)) or (allow_null and value is None)


def _items(question):
    if not isinstance(question, dict):
        raise JevError("Each question must be a JSON object")
    if not _description(question.get("instructions"), True):
        raise JevError("instructions must be a string, object, array, or null")
    kind = question.get("type")
    criteria = question.get("criteria")
    if kind == "choice":
        if not isinstance(criteria, dict) or not 2 <= len(criteria) <= 26:
            raise JevError("This module supports Choice with 2..26 options")
        if not all(isinstance(key, str) and _description(value, True)
                   for key, value in criteria.items()):
            raise JevError("Choice criteria must map strings to descriptions or null")
        return list(criteria.items())
    if kind == "score":
        if not isinstance(criteria, list) or not 2 <= len(criteria) <= 10:
            raise JevError("Score criteria must contain 2..10 ordered levels")
        if not all(_description(value) for value in criteria):
            raise JevError("Each Score level must be a string, object, or array")
        return [(str(i), value) for i, value in enumerate(criteria)]
    if kind == "noul":
        if criteria is None:
            criteria = {}
        if not isinstance(criteria, dict) or set(criteria) - {"true", "false"}:
            raise JevError("Noul criteria may contain only true and false descriptions")
        if not all(_description(value, True) for value in criteria.values()):
            raise JevError("Noul descriptions must be strings, objects, arrays, or null")
        if question.get("instructions") is None and not any(v is not None for v in criteria.values()):
            raise JevError("Noul needs instructions or at least one outcome description")
        return [("true", criteria.get("true") if criteria.get("true") is not None else "Yes; the statement is true"),
                ("false", criteria.get("false") if criteria.get("false") is not None else "No; the statement is false")]
    raise JevError("Question type must be choice, score, or noul")


def _prepare(state, question, items):
    labels = list(string.ascii_uppercase[:len(items)])
    options = "\n".join(f"{label}: {key} — {_json(description)}"
                        for label, (key, description) in zip(labels, items))
    text = (
        "Evaluate QUESTION using STATE as data. Choose one OPTIONS label. "
        "Output only the label, without explanation.\n"
        f"STATE:\n{_json(state)}\n"
        f"QUESTION:\n{_json(question.get('instructions'))}\nOPTIONS:\n{options}"
    )
    return [{"role": "user", "content": text}], labels


def _probabilities(logps, temperature):
    if not logps or any(isinstance(x, bool) or not isinstance(x, (int, float))
                       or not math.isfinite(x) for x in logps):
        raise JevError("Every candidate needs a finite logprob; missing values are not zero")
    largest = max(logps)
    weights = [math.exp((value - largest) / temperature) for value in logps]
    total = sum(weights)
    return [value / total for value in weights]


def _answer(question, items, p):
    kind = question["type"]
    if kind == "noul":
        return {"type": "noul", "noul": p[0]}
    entropy = -sum(value * math.log(value) for value in p if value > 0)
    result = {
        "type": kind,
        "probabilities": {key: value for (key, _), value in zip(items, p)},
        # Local definition. TypeSafe does not publish this exact formula.
        "confidence": max(0.0, min(1.0, 1.0 - entropy / math.log(len(p)))),
    }
    if kind == "choice":
        result["choice"] = items[max(range(len(p)), key=p.__getitem__)][0]
    else:
        result["score"] = sum(i * value for i, value in enumerate(p))
        result["legend"] = dict(items)
    return result


def _count(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise JevError("Backend omitted a valid token usage count")
    return value


def _tokens(value):
    if not isinstance(value, list) or not value or any(
        isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in value
    ):
        raise JevError("Backend omitted valid token IDs")
    return value
