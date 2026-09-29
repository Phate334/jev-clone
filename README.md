# jev

`jev` 是 Python 套件，讓應用程式將情境與判定標準交給語言模型，取得結構化的分類、評分或是非判斷。例如：根據服務故障描述，判斷負責團隊、影響程度與是否需要通知值班工程師。

- **Choice**：從候選選項中選擇答案，並回傳各選項機率。
- **Score**：依有序等級計算期望分數。
- **Noul**：回傳肯定答案的機率。

本專案是獨立的 Jev SDK 相容實作，透過 OpenAI 相容 API 自動辨識 llama.cpp 或 vLLM，再使用後端原生介面讀取候選答案的 logprobs。推論由另外啟動的模型服務執行；套件本身不提供模型或 HTTP 服務。機率與信心值不代表已校正的答對率。

## 建立環境

安裝 [uv](https://docs.astral.sh/uv/getting-started/installation/)，在專案根目錄執行：

```bash
uv sync --locked
```

uv 依 `.python-version` 與 `uv.lock` 建立 Python 環境。第一次使用建議依[部署文件](docs/deployment.md) 的 llama.cpp 流程，在主機下載約 6.72 GB 的 Gemma 4 12B Q4 權重，再啟動官方 Docker GPU 容器。此流程已在 RTX 3060 12 GB 完成短輸入範例驗證；vLLM 是替代方案，不必同時部署。

確認部署文件的 `/health` 回傳 `ok` 後，在執行 Python 的終端設定：

```bash
export JEV_BASE_URL=http://127.0.0.1:8080/v1
export JEV_MODEL=local-judge
export JEV_BACKEND=llamacpp
# vLLM：JEV_BACKEND=vllm，JEV_BASE_URL=http://127.0.0.1:8000/v1
```

若後端需要驗證，另設 `JEV_API_KEY`。換一個終端時需重新設定環境變數。Python 在主機執行，不是在模型容器內執行；以下命令均以專案根目錄為工作目錄。

模型名稱使用服務提供的 ID 或別名，套件不限制權重來源。`JEV_BACKEND` 可設為 `llamacpp`、`vllm` 或 `auto`（預設）；明確指定後端時不會查詢 `/v1/models`，適合模型資訊不完整的 proxy。proxy 仍需支援[後端原生 API](docs/python-api.md#自動辨識)。

## 使用方式

執行[最小範例](examples/quickstart.py)，取得是否需要通知值班工程師的肯定答案機率：

```bash
uv run python examples/quickstart.py
```

完成最小呼叫後，接著執行 [JSON 範例](examples/README.md)，一次體驗 Choice、Score 與 Noul，並對照實測結果說明。

## 深入閱讀

- [Python 介面](docs/python-api.md)：問題型別、同步／非同步呼叫與設定。
- [後端原理](docs/backends.md)：候選機率的計算方式、引擎差異與限制。
- [概念文章](blog.md)：專案的決策機率背景。
- [文件索引](docs/README.md)：完整文件導覽。

另附 [Gemma 4 歷史評測](docs/evaluation.md) 與原始結果，供研究參考。這批數據來自另一個評測 runner，不是本套件的後端驗證或效能保證。
