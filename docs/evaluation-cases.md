# Gemma 4 評測案例

[文件索引](README.md)

資料來自 [case_analysis.json](gemma4-results/case_analysis.json) 與既有評測摘要；摘錄的 state 可能截斷，不足以獨立複核題目。計分與限制見[評測報告](evaluation.md)。

## 跨模型一致性（TMMLU，n=7862）

- **三個模型皆答錯：** 2137 題（約 27.2%）。
- **僅 12B 答對：** 1143 題。
- **E2B 錯、E4B+12B 對：** 1340 題。

## 高信心錯誤（12B TMMLU）

confidence ≥ 0.85 的 3,559 題中，有 **764 題答錯（21.5%）**。分組正確率隨信心區間提高，但這不代表已校正，高信心也非保證正確：

| 信心區間 | n | 正確率 |
|----------|--:|-------:|
| [0,0.3) | 872 | 30.3% |
| [0.3,0.5) | 1266 | 34.9% |
| [0.5,0.7) | 1191 | 42.8% |
| [0.7,0.9) | 1378 | 51.0% |
| [0.9,1.01) | 3155 | 81.4% |

高信心錯題樣本如下。題幹未收錄於本專案；核對時需取得 `ikala/tmmluplus` 的 `v1.1`、`test` 資料，依科目及題目索引對照，資料範圍見[評測報告](evaluation.md#重現範圍)。

| id | subject | pred | gold | conf |
|----|---------|------|------|-----:|
| `nautical_science:399` | nautical_science | A | D | 1.0 |
| `nautical_science:117` | nautical_science | B | D | 1.0 |
| `chinese_language_and_literature:188` | chinese_language_and_literature | B | C | 1.0 |
| `trust_practice:74` | trust_practice | C | B | 1.0 |
| `nautical_science:396` | nautical_science | B | A | 1.0 |
| `management_accounting:32` | management_accounting | A | D | 1.0 |
| `trust_practice:229` | trust_practice | C | D | 1.0 |
| `basic_medical_science:904` | basic_medical_science | A | C | 1.0 |

## JevBench：三個模型皆答錯與 12B hard 失誤

- 三個模型皆答錯：**23**／231
- 12B hard 失誤：**30** 題（hard 共 111）

完整 `request` 收錄於 [E2B](gemma4-results/jevbench_public/e2b/results.jsonl)、[E4B](gemma4-results/jevbench_public/e4b/results.jsonl) 與 [12B](gemma4-results/jevbench_public/12b/results.jsonl) 的逐題紀錄，可用下方案例 ID 查找。重跑單題時，取出該列的 `request`，將 `model` 改成部署服務的模型別名，再依[使用範例](../examples/README.md)呼叫 SDK；這會產生目前後端的新結果，歷史分數的重現限制見[評測報告](evaluation.md#重現範圍)。以下摘錄三個模型皆答錯的樣本：

### 案例 J1: `hard-sol-b-judge_hard-08`（tier=hard, qtype=noul）

預期答案：`no`。三個模型的預測：

```json
{
  "e2b": {
    "type": "noul",
    "noul": 0.6433279809229734
  },
  "e4b": {
    "type": "noul",
    "noul": 0.7864210697660975
  },
  "12b": {
    "type": "noul",
    "noul": 0.999652170209939
  }
}
```

state 摘錄（已截斷；完整內容見逐題紀錄）：

```text
{"request": "Convert 250 square feet to square meters using exactly 1 foot = 0.3048 meter. Show how the squared conversion factor is applied and give the answer to three decimal places.", "response": "Because the measurement is area, use the factor twice: 250 ft² × (0.3048 m/ft)² = 250 × 0.09290304 m² = 23.22576 m². To
```

instructions：

```text
Does the response fully and correctly satisfy the request?
```

### 案例 J2: `hard-sol-b-temporal_numeric-01`（tier=hard, qtype=choice）

預期答案：`late_by_under_2h`。三個模型的預測：

```json
{
  "e2b": {
    "type": "choice",
    "choice": "within_window",
    "probabilities": {
      "before_open": 0.14663123251064852,
      "within_window": 0.6938246363612008,
      "late_by_under_2h": 0.12513360345808533,
      "late_by_2h_or_more": 0.03441052767006535
    },
    "confidence": 0.3427496015935073
  },
  "e4b": {
    "type": "choice",
    "choice": "within_window",
    "probabilities": {
      "before_open": 0.2560668147151367,
      "within_window": 0.4484042835891662,
      "late_by_under_2h": 0.2010140415062482,
      "late_by_2h_or_more": 0.09451486018944896
    },
    "confidence": 0.09546289013049603
  },
  "12b": {
    "type": "choice",
    "choice": "within_window",
    "probabilities": {
      "before_open": 0.028707091455497796,
      "within_window": 0.8478575735359103,
      "late_by_under_2h": 0.025164304428195432,
      "late_by_2h_or_more": 0.09827103058039649
    },
    "confidence": 0.5942312462318392
  }
}
```

state 摘錄（已截斷；完整內容見逐題紀錄）：

```text
{"event": "The reply arrived Wednesday March 11, 2026 at 13:30 New York local time.", "rules": "A support window is measured in New York local time. It opens at 09:00 on the first business day after a notice is received and lasts exactly 52 hours of elapsed time. Business days only determine opening; after opening, wee
```

instructions：

```text
Apply all stated timing, unit, inclusion, correction, and threshold rules; select the exact band.
```

### 案例 J3: `hard-opus-b-ambiguous-03`（tier=hard, qtype=choice）

預期答案：`time_barred`。三個模型的預測：

```json
{
  "e2b": {
    "type": "choice",
    "choice": "insufficient_information",
    "probabilities": {
      "within_limitation": 0.06835280184155393,
      "time_barred": 0.20215079890768345,
      "insufficient_information": 0.7294963992507627
    },
    "confidence": 0.32945756635251167
  },
  "e4b": {
    "type": "choice",
    "choice": "within_limitation",
    "probabilities": {
      "within_limitation": 0.9303944413679944,
      "time_barred": 0.02087102177344062,
      "insufficient_information": 0.04873453685856504
    },
    "confidence": 0.7313629361559773
  },
  "12b": {
    "type": "choice",
    "choice": "within_limitation",
    "probabilities": {
      "within_limitation": 0.9971665927880564,
      "time_barred": 0.0028151193761542675,
      "insufficient_information": 1.828783578934799e-05
    },
    "confidence": 0.9821944551576561
  }
}
```

state 摘錄（已截斷；完整內容見逐題紀錄）：

```text
RIVERBEND LEGAL AID CLINIC — INTAKE SCREENING NOTE

Screening rule SR-3 (limitation, property-damage claims against contractors):
  A claim is time-barred if it is filed more than 3 years after the date on which the claimant knew, or reasonably should have known, of the damage. No other tolling rule applies to this cla
```

instructions：

```text
Under screening rule SR-3, how should this claim be classified?
```

### 案例 J4: `hard-opus-a-long_policy-04`（tier=hard, qtype=choice）

預期答案：`cfo`。三個模型的預測：

```json
{
  "e2b": {
    "type": "choice",
    "choice": "department_head",
    "probabilities": {
      "budget_holder": 0.014730361474986157,
      "department_head": 0.9452285475011051,
      "vp_and_finance_director": 0.027029478018160746,
      "cfo": 0.006046193021733892,
      "executive_committee": 0.006965419984014208
    },
    "confidence": 0.8269866511484267
  },
  "e4b": {
    "type": "choice",
    "choice": "department_head",
    "probabilities": {
      "budget_holder": 0.043048529330164814,
      "department_head": 0.6446127346576729,
      "vp_and_finance_director": 0.26128496733642476,
      "cfo": 0.03821322734847817,
      "executive_committee": 0.012840541327259406
    },
    "confidence": 0.4098477835313954
  },
  "12b": {
    "type": "choice",
    "choice": "vp_and_finance_director",
    "probabilities": {
      "budget_holder": 6.324274452668709e-06,
      "department_head": 0.0013649345206016097,
      "vp_and_finance_director": 0.9982244960647371,
      "cfo": 0.0001919392546111842,
      "executive_committee": 0.00021230588559743087
    },
    "confidence": 0.991119954307679
  }
}
```

state 摘錄（已截斷；完整內容見逐題紀錄）：

```text
CASTELLAN FOODS GMBH — GROUP PROCUREMENT POLICY GP-01 (VERSION 7, EFFECTIVE 1 MARCH 2025)
EXTRACT FOR APPROVAL ROUTING, WITH AMENDMENT GP-01/A3 AND PURCHASE REQUEST PR-2026-4471

PART I — POLICY EXTRACT

1. Purpose and scope
1.1 This policy governs the purchase of all goods and services by Castellan Foods GmbH and its
```

instructions：

```text
Determine the required approval level for purchase request PR-2026-4471 under policy GP-01 as amended.
```

## 12B hard 失誤摘錄

### 案例 H1: `hard-opus-a-probability-03`（noul／probability）

預期答案：`yes`。12B 的預測：

```json
{
  "answer": {
    "type": "noul",
    "noul": 0.0026426559920789813
  },
  "confidence": 0.9735613294860371
}
```

state 摘錄（已截斷；完整內容見逐題紀錄）：

```text
KORRIDAN ELECTRONICS — INCOMING INSPECTION, LOT PSU-2609-07 (12 POWER SUPPLY UNITS)

Supplier certificate: the supplier's own end-of-line test found that exactly 3 of the 12 units in this lot are defective (output ripple above specification). The defective units were not marked and are indistinguishable from good units
```

instructions：

```text
Will the inspection sample contain at least one defective unit (so that lot PSU-2609-07 is rejected)? Give probabilities that reflect the evidence in the state.
```

### 案例 H2: `hard-opus-a-probability-04`（choice／probability）

預期答案：`on_time`。12B 的預測：

```json
{
  "answer": {
    "type": "choice",
    "choice": "late",
    "probabilities": {
      "early": 1.1921084628427443e-05,
      "on_time": 7.565433244300652e-05,
      "late": 0.9999124245829286
    },
    "confidence": 0.9991437992261912
  },
  "confidence": 0.9991437992261912
}
```

state 摘錄（已截斷；完整內容見逐題紀錄）：

```text
OSTERLAND GARDEN SUPPLY — INBOUND LOGISTICS: DELIVERY FORECAST FOR SHIPMENT SH-2026-3391

Shipment SH-2026-3391: Brisa Freight, service Express, pickup week 39/2026, route Porto → Hanover.
Outcome categories: early (delivered before the promised day), on time (on the promised day), late (after the promised day).
Method
```

instructions：

```text
What will the delivery outcome of shipment SH-2026-3391 be? Give probabilities that reflect the evidence in the state.
```
