# Gemma 4 歷史評測設定

[文件索引](README.md)

本頁列出歷史評測的模型與參數，供核對結果。若要部署目前的套件，請依[部署說明](deployment.md)操作。

## 能否重跑歷史評測？

目前缺少原評測程式及部分版本與執行設定，無法完整重跑歷史評測。下列參數供核對使用；可重做的項目與缺少的條件見[評測報告的重現範圍](evaluation.md#重現範圍)。

## JevBench 公開集的執行參數

- **推論引擎**：llama-server b11153。
- **啟動參數**：`-np 2 -c 16384 -ngl 0 --jinja --reasoning-budget 0`；每個 slot 為 8192 tokens，使用 CPU 推論。
- **用戶端並行數**：2。
- **推論介面**：Chat Completions，搭配 GBNF 單字母限制與 logprobs；結果整理為 Jev 風格的 `request`／`answers.decision`。
- **題集**：easy 48 題、original 72 題、hard 111 題，共 231 題。

## 模型權重

原紀錄使用以下 GGUF，並列有各模型對應的 `mmproj-F16.gguf`。檔名未包含下載來源的固定 revision 或檔案校驗值，不能僅靠同名檔案確認權重完全相同。

| 模型 | 權重檔名 |
| --- | --- |
| E2B | `gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf` |
| E4B | `gemma-4-E4B-it-qat-UD-Q4_K_XL.gguf` |
| 12B | `gemma-4-12B-it-qat-UD-Q4_K_XL.gguf` |

## 執行設定的差異

原總覽將 E2B 記為 `-np 2 -c 8192`、E4B 為 `-np 4 -c 16384 -b 4096 -ub 1024`、12B 為 `-np 2 -c 8192`，並註記 E2B 無 mmproj、E4B 曾接續執行（前約 139 題使用舊參數）。這與上列 JevBench 專屬紀錄不同。重跑前需要確認各次執行的實際參數與接續範圍；目前的效能數字不適合作為固定相同條件下的比較。
