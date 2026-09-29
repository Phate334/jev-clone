# jev 使用範例

本範例以服務登入故障為情境，示範透過 `jev` 判斷負責團隊、影響程度與是否需要立即升級處理。

## 範例資料

- [request.json](request.json)：SDK 呼叫的輸入，包含 `model`、`state` 與 `questions`，示範 Choice、Score、Noul 三種問題。
- [example_response.json](example_response.json)：回應格式示意，包含答案、機率、信心與 token 用量。數值不是實測結果，不應作為測試的預期答案。

## 執行前提

依照[專案 README](../README.md#建立環境) 執行 `uv sync --locked`，並依[部署文件](../docs/deployment.md) 啟動 llama.cpp，確認 `/health` 回傳 `ok`、`/v1/models` 列出 `local-judge` 後再繼續。已有相容 vLLM 服務也可使用相同 SDK，但本頁實測結果來自 llama.cpp。

在專案根目錄設定連線位置：

```bash
export JEV_BASE_URL=http://127.0.0.1:8080/v1
```

vLLM 的部署範例使用 `http://127.0.0.1:8000/v1`。若服務需要驗證，另設 `JEV_API_KEY`。

輸入指定的模型為 `local-judge`，必須與後端提供的模型名稱或別名一致；若不同，請修改輸入的 `model`。此明確設定優先於 `JEV_MODEL`；最小範例 `quickstart.py` 則直接使用環境變數的模型設定。

## 呼叫 SDK

在專案根目錄執行 [json_request.py](json_request.py)。腳本會讀取同目錄的 `request.json`，程式在主機執行，不需進入 Docker 容器：

```bash
uv run python examples/json_request.py
```

此命令會實際呼叫模型並將回應印到終端機，不會讀取或覆寫示意回應檔。實際答案與 token 用量取決於模型及後端。

## 結果解讀

2026-09-28 依[部署文件](../docs/deployment.md) 的固定映像與模型版本，在 RTX 3060 12 GB 執行上述命令，得到以下結果（數值已四捨五入）：

| 欄位 | 實測值 | 意義 |
| --- | --- | --- |
| `answers.team.choice` | `identity` | 模型選擇登入與身分驗證團隊 |
| `answers.severity.score` | 1.999976 | 三個等級以 0、1、2 編號；期望分數接近最高影響等級，不是百分比 |
| `answers.escalate.noul` | 0.999977 | 對「需要立即升級處理」的肯定答案機率 |
| `usage.input_tokens` | 368 | SDK 彙總三個問題的推論輸入用量 |
| `usage.output_tokens` | 3 | 本次三個問題的推論輸出用量 |

`confidence` 表示候選分布集中度，不是經校正的答對率；不要把接近 1 的數值視為保證。示意回應檔刻意保留不同機率以展示格式，實際輸出不必與它逐字相同。這次成功只驗證此輸入與 llama.cpp GPU 流程，不代表整個評測題集或 vLLM 都已驗證。

## 常見問題

| 狀況 | 檢查方式 |
| --- | --- |
| 找不到 `request.json` | 確認 `request.json` 與 `json_request.py` 位於同一個目錄 |
| 無法連線、HTTP 503 | 先完成模型載入；確認目前終端的 `JEV_BASE_URL` 為 `http://127.0.0.1:8080/v1` |
| 找不到模型或無法辨識後端 | 檢查 `/v1/models` 是否包含 `local-judge`，且 `owned_by` 為 `llamacpp` 或 `vllm` |

JSON 是 `system_one()` 的參數資料，不是直接傳給後端 Chat Completions API 的請求格式。完整介面說明見 [Python API 文件](../docs/python-api.md)。
