---
name: tender-comparison-agent
description: >
  Compare supplier tenders / quotations for the same job and produce a
  like-for-like comparison table plus a short recommendation draft. Use when
  asked to compare bids, quotations, tenders or 報價 ("compare these quotes",
  "邊份標書最抵", "幫我比較供應商報價", "which tender should we pick"). Extracts
  price, terms, exclusions and conditions from each PDF, puts every bidder on
  one comparison basis, flags risk clauses. Drafts only — a named person decides.
---

# Tender Comparison Agent 標書比較代理

## Intent 意圖

讀 `input/tenders/` 入面每份標書 —— **包括附註細字** —— 抽出價錢、工期、付款、保修、
有效期、所有不包括項目；用 `config/scope_benchmarks.json` 將每份標書補回到同一比較
基準；標出風險條款；寫一段建議初稿。然後**停在人手決定關卡**。

SOP（人做法）：`workflows/tender_comparison.md`

## Rules 規則（不可妥協）

1. **AI 起草 → 人檢查 → 人簽名。** 比較表同建議都係 DRAFT。邊份中標係商業決定，由具名嘅人做。
2. **每個數字要有出處。** 引返標書同項目 / 附註號碼。估算要喺同一句講明係估算。
3. **唔可以作價。** 補回項目只可以用 `config/scope_benchmarks.json` 列明來源嘅基準價。
4. **`input/` 同 `tools/` 只讀。** 只寫入 `outputs/`。
5. **附註細字係重點。** 加價條款、高訂金、短保修比一張靚表更重要。

## Tools 確定性工具

| # | Verb | Tool | Input → Output |
|---|------|------|----------------|
| 1 | EXTRACT | `tools/extract_tenders.py` | `input/tenders/*.pdf` → `outputs/tenders_extracted.json` |
| 2 | COMPARE | `tools/compare_tenders.py` | JSON + `config/scope_benchmarks.json` → `outputs/tender_comparison.md` |

兩個 tool 都係純 regex / 算術：唔會 call model、唔上網。由 repo 任何位置行都得。

## Run 執行

1. `python tools/extract_tenders.py --input input/tenders --out outputs/tenders_extracted.json`
2. `python tools/compare_tenders.py --extracted outputs/tenders_extracted.json --config config/scope_benchmarks.json --out outputs/tender_comparison.md`
3. 讀 `outputs/tender_comparison.md`，寫 `outputs/tender_recommendation.md`（**150 字以內**）：
   同一基準下邊份性價比最高、邊份風險最大同點解（引標書 + 附註號碼）、決定前要向投標者澄清嘅兩三點。
4. 停。回報：行咗邊啲 tool、每份標書表面總價 vs 可比較總成本、風險標記、兩個 output 路徑。
   唔好推薦「中標者」—— 推薦「要澄清乜」。

## Gate 關卡

- **Human-IN（事前批核）**：建議交俾簽中標決定嗰個人。佢確認基準假設、有需要向投標者澄清（人發，唔係 agent 發）、然後決定。本 skill 唔會聯絡任何投標者。
- Criteria：Source（每個數字可追溯）· Accuracy（補回項目與原標書一致）· Risk（加價、訂金、保修、有效期已列）· Accountability（決定人簽名）。

## Outputs

`outputs/tenders_extracted.json` · `outputs/tender_comparison.md` · `outputs/tender_recommendation.md` — 全部 DRAFT 直至有人簽名。

## Configuration

`config/scope_benchmarks.json`：呢單嘢必須包嘅範圍項目（keyword + 基準價 + 基準來源）、不包括項目嘅關鍵字、風險規則（訂金上限、保修下限、有效期下限、加價 / 暫定數 / 有條件工期關鍵字）。換工程類型就改呢個檔，唔使改 code。
