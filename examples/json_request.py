import json
from pathlib import Path

from jev import TypeSafeClient


with Path(__file__).with_name("request.json").open(encoding="utf-8") as source:
    request = json.load(source)

with TypeSafeClient() as client:
    result = client.system_one(**request)
    print(result.model_dump_json(indent=2))
