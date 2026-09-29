# 文件索引

初次使用請從根目錄 [README](../README.md) 開始；決策機率的概念說明見 [blog.md](../blog.md)。

| 文件 | 內容 |
| --- | --- |
| [環境部署](deployment.md) | 主機下載 Q4 權重、官方 Docker GPU 部署、就緒檢查與實測範圍 |
| [使用範例](../examples/README.md) | JSON 輸入、SDK 呼叫、實測結果解讀與常見問題 |
| [Python 介面](python-api.md) | 同步／非同步用法、設定、SDK 相容範圍、自動辨識 |
| [後端原理](backends.md) | 候選 logprobs、機率計算、兩種引擎差異與問題排除 |
| [Gemma 4 評測](evaluation.md) | 既有準確率、效能數據、資料來源與重現限制 |
| [評測案例](evaluation-cases.md) | 跨模型錯誤、高信心錯誤與題目摘錄 |
| [歷史評測設定](evaluation-setup.md) | 模型與推論參數、設定差異及重跑所缺的條件 |

原始評測 JSON／JSONL 保留於 [gemma4-results](gemma4-results/)。
