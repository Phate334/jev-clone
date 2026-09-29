# Python 介面與相容範圍

[文件索引](README.md)

先完成[快速入門](../README.md#建立環境) 的環境與連線設定。以下範例使用部署文件中的模型別名 `local-judge`，在主機存成 Python 檔案後以 `uv run 檔名.py` 執行。

```python
from jev import TypeSafeClient, Choice, Score, Noul, NoulCriteria
# 連線位置由 JEV_BASE_URL 設定，兩個後端使用相同介面。

with TypeSafeClient(model="local-judge") as client:
    result = client.system_one(
        state={"message": "所有使用者都無法登入", "retry": "failed"},
        questions={
            "team": Choice(criteria={"identity": "身分驗證", "billing": "帳務"}),
            "severity": Score(criteria=["功能正常", "部分中斷", "全部中斷"]),
            "escalate": Noul(instructions="是否立即通知值班工程師？",
                             criteria=NoulCriteria(true="核心功能中斷")),
        },
    )
    print(result.choices["team"].choice)
    print(result.scores["severity"].probabilities[2])
    print(result.nouls["escalate"].noul)
    print(result.usage.input_tokens)
    print(result.model_dump_json(indent=2))
```

`instructions` 可省略；Noul 若完全沒有問題或判定描述，會拒絕推論。`questions` 也可直接傳入 Jev 格式的字典。Python 的 Score `legend`、`probabilities` 使用整數鍵；`model_dump(mode="json")` 或 `model_dump_json()` 會轉回 JSON 字串鍵。

非同步呼叫使用相同參數：

```python
import asyncio
from jev import AsyncTypeSafeClient, Noul

async def main():
    async with AsyncTypeSafeClient() as client:
        result = await client.system_one("登入失敗", {"q": Noul(instructions="服務是否異常？")})
        print(result.nouls["q"].noul)

asyncio.run(main())
```

取消非同步呼叫不會立即中斷已送出的 HTTP 請求，仍由 `timeout` 控制。同步用 `close()`，非同步用 `await aclose()`，或使用對應 context manager。

可指定自己的 Pydantic 回應型別；繼承 `SystemOneResponse` 時，具名欄位會從同名答案填入：

```python
from jev import TypeSafeClient, SystemOneResponse, NoulAnswer, Noul

class Decision(SystemOneResponse):
    escalate: NoulAnswer

with TypeSafeClient() as client:
    result = client.system_one("登入失敗", {"escalate": Noul(instructions="要升級處理嗎？")},
                               response_model=Decision)
    print(result.escalate.noul)
```

任意 `BaseModel` 子類別也可作為 `response_model`，其欄位對應完整的 `model/answers/usage` JSON。

## 設定與相容範圍

| 設定 | 行為 |
| --- | --- |
| `openai_base_url` | 優先於 `JEV_BASE_URL`，再使用 `OPENAI_BASE_URL`；預設 `http://127.0.0.1:8000/v1`，接受有或沒有尾端 `/v1` 的網址 |
| `backend` | 優先於 `JEV_BACKEND`；接受 `auto`（預設）、`llamacpp`、`vllm`。明確指定時跳過模型清單查詢 |
| `base_url` | Jev SDK 相容別名，不能與 `openai_base_url` 同時設定 |
| `api_key` | 優先於 `JEV_API_KEY`，再使用 `OPENAI_API_KEY`；本機服務可省略 |
| `model` | 依序使用明確參數、`JEV_MODEL`、`TYPESAFE_DEFAULT_MODEL`、`local-judge`；每次呼叫可覆寫 |
| `timeout` | 每個 HTTP 請求的逾時秒數，預設 120；每次呼叫可覆寫 |
| `concurrency` | 同一 client 的 HTTP 並行上限，預設 4 |
| `calibration_temperature` | 候選分布的正規化溫度，預設 1.0；校正效果需另行驗證 |
| `chat_template_kwargs` | 預設 `{"enable_thinking": false}`，供 Gemma 4 12B 停用推理文字 |
| `headers`／`extra_headers` | client 設定與單次呼叫設定；後者優先，驗證標頭由 `api_key` 控制 |
| `retry` | `RetryPolicy`，預設不重試；支援 client 與單次呼叫設定 |
| `extra_body` | 淺層合併至請求，可覆寫 state、model、questions；不作為引擎取樣參數 |

這是獨立的 Jev SDK 相容實作，匯入來源為 `jev`。保留同步／非同步 `system_one`、問題與回應型別、自訂 `response_model`、重試及例外型別。模型限制與分數定義見[後端原理](backends.md)。

不支援官方的模型目錄 `models.list()`、自訂 `http_client`／`transport`、`httpx2.Timeout` 或彙總後的 `raw_http_response`；`request_id` 為 None。不讀取 `TYPESAFE_API_KEY`／`TYPESAFE_BASE_URL`，也未提供 `/v1/systemone` HTTP 服務。

JSON 讀取後的字典可直接傳入 `client.system_one(**request)`；完整輸入、示意回應與執行步驟見[使用範例](../examples/README.md)。

`JEV_*` 是本套件專用設定；未設定時仍接受上述舊環境變數。明確傳入的參數優先，包含 JSON 請求中的 `model`，不會被 `JEV_MODEL` 覆寫。套件不下載模型，也不限制模型來源。

## 自動辨識

只有 `backend="auto"` 時才查詢模型清單。首次對模型推論時，以相同的驗證資訊查詢 `GET /v1/models`，依相符模型的 `owned_by` 判斷 `vllm` 或 `llamacpp`。結果在同一 client 內依模型快取；服務變更後請建立新的 client。未知後端、模型不存在或查詢失敗均回報錯誤。

若 proxy 未提供引擎資訊，設定 `JEV_BACKEND=llamacpp` 或 `JEV_BACKEND=vllm`，即可略過 `/v1/models`，直接使用指定模型。此設定套用於同一 client 的所有模型；不同引擎請使用不同 client。

反向代理仍需轉送後端原生 API：llama.cpp 需要 `/tokenize`、`/apply-template`、`/completion`，vLLM 需要 `/tokenize`、`/v1/chat/completions` 及 prompt logprobs 等擴充欄位。僅提供標準 Chat Completions 的 proxy 不足以執行本套件。llama.cpp 的範本與 tokenizer 請求不帶模型名稱，proxy 必須將這些路徑與推論請求送到同一模型，必要時使用模型專屬網址。若網址為 `/proxy/v1`，原生 API 會送至 `/proxy/tokenize` 等路徑。

辨識依據見 [llama.cpp 文件](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md#get-v1models-openai-compatible-model-info-api)與 [vLLM 原始碼](https://github.com/vllm-project/vllm/blob/main/vllm/entrypoints/serve/engine/protocol.py)。後端版本與驗證範圍見[部署文件](deployment.md)。`owned_by` 並非標準化的引擎識別欄位，代理改寫或版本變動可能使辨識失敗。
