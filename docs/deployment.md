# 以官方 Docker 映像啟動 Gemma 4 12B

[文件索引](README.md)

以下以 Linux、NVIDIA GPU 為例，需先安裝 Docker、curl、NVIDIA 驅動程式與 [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)。Python 用戶端由 uv 管理，推論引擎在容器內執行。先確認 `docker version` 可連到 daemon，`nvidia-smi` 可列出 GPU；權限不足時請先完成 Docker 安裝設定。

## llama.cpp：下載模型

使用[官方映像](https://github.com/ggml-org/llama.cpp/blob/master/docs/docker.md)與 [Gemma 4 12B QAT GGUF](https://huggingface.co/unsloth/gemma-4-12B-it-qat-GGUF) 的 UD-Q4_K_XL 權重。權重為 6,716,356,800 bytes（約 6.26 GiB）；另需 Docker 映像與執行空間，建議至少 20 GB 可用磁碟，這不是 GPU 記憶體需求。

在主機下載至專案外的快取目錄，避免將模型加入版本控制。以下固定模型 revision；下載中斷時可重跑 curl 命令續傳：

```bash
mkdir -p "$HOME/.cache/jev/models"
curl --fail --location --retry 3 --continue-at - \
  --output "$HOME/.cache/jev/models/gemma-4-12B-it-qat-UD-Q4_K_XL.gguf.part" \
  'https://huggingface.co/unsloth/gemma-4-12B-it-qat-GGUF/resolve/980b060c40a8539ac159e0501a3e0f66a6365af3/gemma-4-12B-it-qat-UD-Q4_K_XL.gguf?download=true'
```

下載成功後，核對 SHA-256 並改為正式檔名：

```bash
printf '%s  %s\n' \
  '90fd44e29e0d7cffeb0fd00dc73cfdab9ed0b0e95306ecf7821ea634c940c370' \
  "$HOME/.cache/jev/models/gemma-4-12B-it-qat-UD-Q4_K_XL.gguf.part" \
  | sha256sum --check && \
mv "$HOME/.cache/jev/models/gemma-4-12B-it-qat-UD-Q4_K_XL.gguf.part" \
  "$HOME/.cache/jev/models/gemma-4-12B-it-qat-UD-Q4_K_XL.gguf"
```

已有完整且通過核對的檔案時，跳過下載步驟。

## llama.cpp：啟動與確認就緒

以下固定官方 CUDA 映像 digest（build 11223，commit `4da633776`），唯讀掛載模型目錄：

```bash
docker run -d --rm --name jev-llamacpp --gpus all \
  -p 127.0.0.1:8080:8080 \
  -v "$HOME/.cache/jev/models:/models:ro" \
  ghcr.io/ggml-org/llama.cpp@sha256:5d0812fe45cb5dcb4ac5c588148a601aca63b6b224601f8d1f6f01fdfb07a111 \
  -m /models/gemma-4-12B-it-qat-UD-Q4_K_XL.gguf \
  --alias local-judge --host 0.0.0.0 --port 8080 \
  --jinja --ctx-size 16384 --parallel 4 --n-gpu-layers 99 \
  --reasoning off
```

`-d` 讓容器在背景執行，回傳容器 ID 不代表模型已載入。第一次啟動會先下載 Docker 映像。查看載入進度：

```bash
docker logs -f jev-llamacpp
```

看到服務開始監聽後，以 Ctrl+C 離開日誌畫面；這不會停止背景容器。確認模型就緒：

```bash
curl --fail --show-error http://127.0.0.1:8080/health
curl --fail --show-error http://127.0.0.1:8080/v1/models
```

第一個請求應回傳 `{"status":"ok"}`，第二個應列出 `local-judge`。載入期間可能回傳 HTTP 503；請先檢查日誌，不要直接執行 SDK。就緒後可跳至[使用範例](../examples/README.md)，不需要再啟動 vLLM。

## vLLM（尚未完成實機驗證）

此範例使用會變動的 `latest` 映像與未固定 revision 的模型，目前無法保證不同時間執行會取得相同版本。若要重複實驗，需先驗證並固定映像 digest 與模型 revision。vLLM 可替代 llama.cpp，兩者擇一啟動即可；BF16 權重需要更多 GPU 記憶體。使用[官方映像](https://docs.vllm.ai/en/latest/deployment/docker/)與 [Google Gemma 4 12B IT](https://huggingface.co/google/gemma-4-12B-it)：

```bash
docker run -d --rm --name jev-vllm --gpus all --ipc=host \
  -p 127.0.0.1:8000:8000 \
  -v jev-hf-cache:/root/.cache/huggingface \
  -e HF_TOKEN \
  vllm/vllm-openai:latest \
  --model google/gemma-4-12B-it --served-model-name local-judge \
  --host 0.0.0.0 --port 8000 --dtype bfloat16 --max-model-len 4096 \
  --logprobs-mode raw_logprobs --generation-config vllm \
  --chat-template-kwargs '{"enable_thinking":false}'
```

若模型下載需要驗證，執行上方命令前先在主機設定 `HF_TOKEN`。首次啟動會下載權重，可用 `docker logs -f jev-vllm` 查看進度；載入完成後以[健康檢查](https://docs.vllm.ai/en/latest/api/vllm/entrypoints/serve/instrumentator/health/)與模型清單確認服務：

```bash
curl --fail --show-error http://127.0.0.1:8000/health
curl --fail --show-error http://127.0.0.1:8000/v1/models
```

確認健康檢查成功、模型清單列出 `local-judge`，再執行 `export OPENAI_BASE_URL=http://127.0.0.1:8000/v1`，依[使用範例](../examples/README.md)呼叫 SDK。vLLM 的 BF16 範例與 llama.cpp 的 Q4 量化範例使用不同權重格式與精度；GPU 記憶體需求、版本固定方式與容器操作見[下節](#硬體版本與容器管理)。

## 硬體、版本與容器管理

vLLM 的 [Gemma 4 部署指南](https://github.com/vllm-project/recipes/blob/main/Google/Gemma4.md)將 12B BF16 的 NVIDIA GPU 需求列為單張 40 GB 以上。實際用量仍取決於輸入長度、同時處理的請求數與引擎版本。llama.cpp 範例使用 Q4 權重，另需預留 KV cache 與運算所需記憶體，不能直接套用 BF16 的估算。兩個容器建議擇一執行，避免同時占用 GPU 記憶體。

llama.cpp 以 `-m` 載入本機 GGUF，不載入多模態投影模型，因本專案只評分文字。若要改用 CPU，將 CUDA 映像替換為 `ghcr.io/ggml-org/llama.cpp:server`、移除 `--gpus all`，並將 `--n-gpu-layers 99` 改成 `--n-gpu-layers 0`；CPU 方案需另行驗證版本與效能。vLLM 範例則維持 NVIDIA GPU 環境。

llama.cpp 權重保留於主機的 `~/.cache/jev/models`，vLLM 權重保留於 Docker 儲存卷 `jev-hf-cache`；移除容器不會刪除它們。容器內服務監聽 `0.0.0.0`，主機則透過 `127.0.0.1:8080` 或 `127.0.0.1:8000` 連線。不要直接將未設驗證的服務開放到外部網路。

重複執行時，請保留相同的模型 revision、映像 digest、啟動參數與硬體設定，並在專案根目錄以 `uv sync --locked` 安裝 Python 相依套件。

```bash
# 查看啟動紀錄；依使用的後端擇一執行。
docker logs -f jev-llamacpp
docker logs -f jev-vllm

# 結束目前使用的後端；--rm 會在停止後移除容器。
docker stop jev-llamacpp
docker stop jev-vllm
```

## 實測範圍與問題排除

2026-09-28 在 RTX 3060 12 GB、主機約 16 GiB RAM、Docker Engine 29.1.3 上，以本頁固定版本完成 llama.cpp GPU 載入與[JSON 範例](../examples/README.md) 呼叫。`--ctx-size 16384 --parallel 4` 在此版本配置為每 slot 4096 tokens；這是單一短輸入的功能驗證，不代表所有長度或並行負載都能在 12 GB GPU 上執行。

| 狀況 | 處理方式 |
| --- | --- |
| 容器內下載很慢，或 `-hf` 啟動未進入載入階段 | 改用本頁主機下載與 `-m` 掛載流程 |
| 健康檢查連線失敗或 HTTP 503 | 用 `docker ps -a` 與 `docker logs jev-llamacpp` 區分容器退出、下載與模型載入狀態 |
| 容器名稱或 8080 port 已被占用 | 先確認既有服務用途，不要直接刪除；改用其他容器名稱或主機 port，並同步調整用戶端網址 |
| CUDA 記憶體不足 | 關閉其他 GPU 工作，或減少 context、slots／GPU layers 後重新驗證；部分 CPU 執行會變慢 |
| `enable_thinking` 棄用警告 | 此版本的啟動參數使用 `--reasoning off`；SDK 的 template 設定仍已通過本次範例 |

歷史評測使用不同的模型與執行流程，重跑條件見[評測報告](evaluation.md#重現範圍)。
