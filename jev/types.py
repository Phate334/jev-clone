"""問題、答案與回應的共用資料型別。"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union
from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator
from typing_extensions import TypedDict


JSONContent = Union[str, dict[str, JsonValue], list[JsonValue]]


class NoulCriteria(TypedDict, total=False):
    true: JSONContent | None
    false: JSONContent | None
    __pydantic_config__ = ConfigDict(extra="forbid")


class _Question(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    instructions: JSONContent | None = None


class Noul(_Question):
    type: Literal["noul"] = "noul"
    criteria: NoulCriteria | None = None


class Choice(_Question):
    type: Literal["choice"] = "choice"
    criteria: dict[str, JSONContent | None]


class Score(_Question):
    type: Literal["score"] = "score"
    criteria: list[JSONContent]


Question = Union[Noul, Choice, Score, dict[str, Any]]


class _Response(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True, strict=True)


class Usage(_Response):
    input_tokens: int | None = None
    output_tokens: int | None = None


class NoulAnswer(_Response):
    type: Literal["noul"] = "noul"
    noul: float


class ChoiceAnswer(_Response):
    type: Literal["choice"] = "choice"
    choice: str
    confidence: float
    probabilities: dict[str, float]


class ScoreAnswer(_Response):
    type: Literal["score"] = "score"
    score: float
    confidence: float
    legend: dict[int, JSONContent]
    probabilities: dict[int, float]

    @field_validator("legend", "probabilities", mode="before")
    @classmethod
    def _integer_keys(cls, value):
        if not isinstance(value, dict):
            return value
        output = {}
        for key, entry in value.items():
            if isinstance(key, str) and key.isascii() and key.isdigit():
                key = int(key)
            if isinstance(key, bool) or not isinstance(key, int) or key < 0 or key in output:
                raise ValueError("Score keys must be unique nonnegative integer indices")
            output[key] = entry
        return output


Answer = Annotated[Union[NoulAnswer, ChoiceAnswer, ScoreAnswer], Field(discriminator="type")]


class SystemOneResponse(_Response):
    model: str
    usage: Usage
    answers: dict[str, Answer] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _lift_named_answers(cls, value):
        # Subclass fields can directly name answers, as in the public SDK API.
        if isinstance(value, dict) and isinstance(value.get("answers"), dict):
            value = dict(value)
            for name in cls.model_fields.keys() - {"model", "usage", "answers"}:
                if name not in value and name in value["answers"]:
                    value[name] = value["answers"][name]
        return value

    @property
    def nouls(self) -> dict[str, NoulAnswer]:
        return {key: value for key, value in self.answers.items() if isinstance(value, NoulAnswer)}

    @property
    def choices(self) -> dict[str, ChoiceAnswer]:
        return {key: value for key, value in self.answers.items() if isinstance(value, ChoiceAnswer)}

    @property
    def scores(self) -> dict[str, ScoreAnswer]:
        return {key: value for key, value in self.answers.items() if isinstance(value, ScoreAnswer)}

    @property
    def request_id(self):
        return None  # No TypeSafe service request was made.

    @property
    def raw_http_response(self):
        raise NotImplementedError("A local result aggregates several HTTP calls; use model_dump_json()")
