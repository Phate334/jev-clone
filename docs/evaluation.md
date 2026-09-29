# Gemma 4 評測報告

[文件索引](README.md)

本文件依 [gemma4-results/](gemma4-results/) 的摘要與逐題紀錄整理，未重新執行模型推論。

## 資料與方法

| 項目 | 紀錄 |
| --- | --- |
| 模型 | Gemma 4 E2B／E4B／12B IT QAT，UD-Q4_K_XL GGUF；原摘要標示來自 Unsloth |
| 推論 | llama-server b11153、CPU-only（`-ngl 0`） |
| 讀值 | `/v1/chat/completions`、GBNF 單字母限制、logprobs |
| 輸出 | Jev System One 形狀的 request／answers；未提供 `/v1/systemone` 服務 |
| JevBench | 公開 easy 48、original 72、hard 111，共 231 題 |
| TMMLU+ | `ikala/tmmluplus` v1.1、test，23 科共 7,862 題 |

這批結果來自另一個評測 runner，不應視為本專案 `jev` 兩種後端流程的實測。沒有 vLLM 結果，也沒有 Jev 原模型的對照組。

JevBench 題型計分以 summary 的 `scoring_rule` 為準：Choice 取最大機率選項；Noul 以 0.5 區分 yes／no；Score 將期望等級四捨五入後比對答案，另記錄等級 argmax 正確率。三個模型的 Score 兩種計分在本批資料中得到相同正確題數，但規則本身不同。TMMLU+ 則比較最大字母機率與 gold。

## 準確率

| 模型 | JevBench 正確／總數 | Overall | easy | original | hard | TMMLU+ 正確／總數 | Overall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| E2B | 154/231 | 66.7% | 100.0% | 77.8% | 45.0% | 2738/7862 | 34.8% |
| E4B | 179/231 | 77.5% | 100.0% | 97.2% | 55.0% | 3808/7862 | 48.4% |
| 12B | 199/231 | 86.1% | 100.0% | 97.2% | 73.0% | 4488/7862 | 57.1% |

| 模型 | JevBench Noul（74） | Choice（139） | Score（18） | TMMLU STEM（1549） | 專業（4920） | 台灣／正體中文（1393） |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| E2B | 67.6% | 66.2% | 66.7% | 34.0% | 33.4% | 40.8% |
| E4B | 78.4% | 77.0% | 77.8% | 48.2% | 47.3% | 52.5% |
| 12B | 87.8% | 86.3% | 77.8% | 54.2% | 57.4% | 59.3% |

六組評測皆完成全部題目，沒有請求失敗。

E2B 到 12B，JevBench 整體上升約 19.5 個百分點、hard 上升約 27.9 個百分點；TMMLU+ 子集上升約 22.3 個百分點。easy 已達天花板，hard 較能區分這三個模型。此觀察限於本次模型、量化與題集，不能推廣為所有任務的規模定律。

## 信心與錯誤

12B 的 TMMLU+ 紀錄中，confidence ≥ 0.85 卻答錯的有 764 題。此 confidence 對應 `1 - H(p)/log(K)` 的分布集中度，不能稱為最大選項機率或校正後答對率。

原摘要的信心分組顯示正確率隨區間提高，但單調不等於已校正。詳細分組、跨模型錯誤交集與摘錄見[案例分析](evaluation-cases.md)，結構化來源見 [case_analysis.json](gemma4-results/case_analysis.json)。

## 效能紀錄與設定差異

| 模型 | JevBench 平均延遲 | 該次執行耗時 | TMMLU+ 平均延遲 | 該次執行耗時 |
| --- | ---: | ---: | ---: | ---: |
| E2B | 5821 ms | 674 s | 1193 ms | 4690 s |
| E4B | 11044 ms | 1287 s | 4590 ms | 8906 s |
| 12B | 26453 ms | 3084 s | 5668 ms | 22284 s |

`runtime_sec_this_run` 只計該輪 runner 的實際經過時間；E4B 的原總覽註記曾 resume，不能把該欄一律視為完整重跑時間。並行時延遲總和也不等於實際經過時間。

JevBench 各模型原部署紀錄均為 `-np 2 -c 16384`、concurrency 2，另載入 mmproj；原總覽卻列出不同的 context、E4B 並行設定及 E2B 無 mmproj。設定差異見[歷史評測設定](evaluation-setup.md)。在缺少逐次啟動紀錄時，不將這些數字解讀為嚴格控制變因的效能比較。

## 原始資料索引

| 模型 | JevBench summary | 逐題紀錄 | TMMLU+ summary | 逐題紀錄 |
| --- | --- | --- | --- | --- |
| E2B | [summary](gemma4-results/jevbench_public/e2b/summary.json) | [JSONL](gemma4-results/jevbench_public/e2b/results.jsonl) | [summary](gemma4-results/tmmluplus_hard/e2b/summary.json) | [JSONL](gemma4-results/tmmluplus_hard/e2b/results.jsonl) |
| E4B | [summary](gemma4-results/jevbench_public/e4b/summary.json) | [JSONL](gemma4-results/jevbench_public/e4b/results.jsonl) | [summary](gemma4-results/tmmluplus_hard/e4b/summary.json) | [JSONL](gemma4-results/tmmluplus_hard/e4b/results.jsonl) |
| 12B | [summary](gemma4-results/jevbench_public/12b/summary.json) | [JSONL](gemma4-results/jevbench_public/12b/results.jsonl) | [summary](gemma4-results/tmmluplus_hard/12b/summary.json) | [JSONL](gemma4-results/tmmluplus_hard/12b/results.jsonl) |

題數明細見 [JevBench inventory](gemma4-results/jevbench_public/inventory.json)、[TMMLU+ inventory](gemma4-results/tmmluplus_hard/inventory.json)；原始規模分析仍保留為 [SCALE_ANALYSIS.json](gemma4-results/jevbench_public/SCALE_ANALYSIS.json)。

## 重現範圍

目前可核對既有結果，也可部署套件重新評分單題，但無法完整重跑表中的歷史分數：

| 目標 | 現有資料與操作方式 | 尚缺的條件 |
| --- | --- | --- |
| 核對準確率 | 逐題 JSONL 的 `correct`、`ok` 與各模型 `summary.json` 可相互比對 | 不需執行模型；只能核對紀錄中的計分結果 |
| 重新評分 JevBench 單題 | 依[部署說明](deployment.md)啟動模型，取出 JSONL 的 `request`、更新模型別名，再依[使用範例](../examples/README.md)呼叫 | 使用目前套件的新流程，結果不保證與歷史紀錄相同 |
| 重跑完整準確率 | 已有題數、計分規則、模型檔名與部分參數 | 缺少原評測程式、固定權重版本，以及下述題集與 prompt 設定 |
| 重跑效能比較 | 已有延遲與耗時摘要 | 缺少一致的逐次啟動設定、完整硬體環境與接續執行紀錄 |

本目錄及附帶結果壓縮檔均未提供原評測程式 `scripts/run_jevbench_public.py`。模型權重也未附上；原檔名未附固定 revision 或校驗值，無法確認重新下載的權重與歷史評測一致。已知引擎版本及參數見[歷史評測設定](evaluation-setup.md)。

JevBench 原紀錄的來源標示為 Benchmark Heaven／JevBench 公開集，未提供可鎖定的來源 revision。JSONL 含 request 可供閱讀，嚴格重現仍需確認原題集版本與 runner。此結果不含 sealed 題，不能與包含其他評分軸的 Official Score 直接比較。

TMMLU+ 原紀錄指定資料集 `ikala/tmmluplus`、revision `v1.1`、split `test`；本機 JSONL 只有 `subject:id`、預測、答案與機率等資訊，沒有題幹。重現需依該版本與 inventory 的 23 科取得原題，還原 prompt 與評測設定。所選科目不代表完整 TMMLU+。

既有 runner 未附，無法僅從正規化後分布確認每次原始 logprobs 是否包含全部候選，以及如何處理缺漏；若需驗證校正或跨引擎等價性，應保留完整請求設定與原始讀值另行評測。
