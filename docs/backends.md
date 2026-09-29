# 後端讀值與機率計算

[文件索引](README.md)

每個問題的候選答案對應 A、B、C…，標籤必須在相同答案位置各占一個 token。Choice 支援 2–26 個選項，Score 支援 2–10 個等級，Noul 固定兩個；Choice 上限是這份簡化實作的限制，不是 Jev API 的完整上限。所有 JSON state 都先轉成文字，不解讀影像或音訊。

- llama.cpp：`/apply-template` → `/tokenize` → `/completion`。讀取 `completion_probabilities[0].top_logprobs` 中候選 ID 的原始 logprob；`post_sampling_probs=false`。top-k 依序為 64、512、4096、32768；缺任何候選會加深，最終仍缺就失敗。
- vLLM：`/tokenize` 驗證標籤，再逐一 `/v1/chat/completions`，把候選放進最後一則 assistant 訊息。`continue_final_message=true`、`add_generation_prompt=false`、`prompt_logprobs=1`、`return_token_ids=true`、`stream=false`。比對實際 prompt token IDs，取最後候選 token 的 logprob；額外產生的 1 token 不參與評分。
- 兩者需要可回傳上述欄位的後端版本；缺欄位不降級成讓模型自己填寫機率。

計算使用穩定 softmax：`p[i] = exp((logp[i] - max(logp)) / T) / sum(...)`。Choice 取 argmax；Score 為 `sum(i*p[i])`；Noul 為 true 的機率。Choice／Score 的 `confidence = 1 - H(p)/log(K)` 是本專案的定義，只表示分布集中度，未重現 Jev 的 confidence 演算法，也不是正確率。

`usage` 加總成功完成的一次 System One 嘗試內所有推論回應的 prompt/output token 數，包含 llama.cpp 加深 top-k 的完成回應，以及 vLLM 被丟棄的生成 token；不計 tokenizer/template 呼叫。若手動開啟網路重試，失敗嘗試的後端用量可能不可得，回傳 usage 不是完整硬體計費帳。

## 部署與答案位置

環境設定見[部署說明](deployment.md)。llama.cpp 需要帶有正確 chat template 的 GGUF；vLLM 需要該版本支援的模型與 tokenizer。比較結果時記錄模型 revision、量化、引擎版本、template 與硬體，不能只記模型別名。

llama.cpp 會先套用範本，再加入 `Answer:\n` 作為 assistant 答案前綴。每個候選必須只新增一個 token，且前綴 token IDs 完全相同。grammar 限制生成文字，`post_sampling_probs=false` 用來讀取取樣前分布；grammar 本身不保證候選都在 raw top-k 裡。

vLLM 將 `Answer:\nA` 等候選放進最後一則 assistant 訊息，以 prompt logprobs 取得該候選的分數。`prompt_logprobs=1` 除了 top-1，也保留實際輸入 token 的分數。模組檢查最後的 token ID 與共同前綴，避免讀到範本加上的結尾標記。啟動時使用 `--logprobs-mode raw_logprobs` 明確指定原始分布。

`enable_thinking=false` 是傳給 template 的設定，只有支援它的模型才會生效。替換模型時需確認實際答案位置，不能將推理開頭當成答案評分。

| 實作路線 | K 個選項所需推論請求 | 額外成本 |
| --- | ---: | --- |
| 本機 llama.cpp adapter | 通常 1 次 | top-k 缺漏時重試；另有範本與 tokenizer 呼叫 |
| 本機 vLLM adapter | K 次 | 各候選均送入 prompt；另有 tokenizer 呼叫 |

並行請求不保證相同前綴只計算一次，快取效果應以實測為準。

## 問題排除

| 症狀 | 檢查方向 |
| --- | --- |
| HTTP 連線失敗 | 後端是否就緒、port 與 base URL 是否一致 |
| 缺少 logprob 欄位 | 引擎版本是否支援上述擴充欄位 |
| 標籤或前綴不一致 | 模型 tokenizer、chat template、thinking 設定 |
| llama.cpp 缺少候選 | 是否已達 top-k 重試上限；不能自行補零 |
| 輸入過長 | 模型 context、並行 slot 設定、state 長度 |

## 參考資料

後端介面依據為 [llama.cpp server 文件](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) 與 [vLLM Chat Completions protocol](https://docs.vllm.ai/en/latest/api/vllm/entrypoints/openai/chat_completion/protocol/)。欄位會隨版本改動，更新引擎後應先以 [Python 範例](python-api.md)檢查串接，再測任務品質。
