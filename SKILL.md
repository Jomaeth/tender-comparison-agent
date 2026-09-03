---
name: tender-comparison-agent
description: >
  Compare supplier tenders / quotations for the same job and deliver a
  like-for-like comparison report as an OpenDeedigital-styled PDF, with a
  short recommendation draft. Use when asked to compare bids, quotations,
  tenders or 報價 ("compare these quotes", "邊份標書最抵", "幫我比較供應商報價",
  "which tender should we pick"). Extracts price, terms, exclusions and
  conditions from each PDF, puts every bidder on one comparison basis, flags
  risk clauses. Drafts only — a named person decides.
---

# Tender Comparison Agent 標書比較代理

## Intent 意圖

讀 `input/tenders/` 入面每份標書 —— **包括附註細字** —— 抽出價錢、工期、付款、保修、
有效期、所有不包括項目；用 `config/scope_benchmarks.json` 將每份標書補回到同一比較
基準；標出風險條款；寫一段建議初稿；出一份 **OpenDeedigital 風格嘅 A4 PDF 報告**。
然後**停在人手決定關卡**。

SOP（人做法）：`workflows/tender_comparison.md`

## Rules 規則（不可妥協）

1. **AI 起草 → 人檢查 → 人簽名。** 比較表同建議都係 DRAFT。邊份中標係商業決定，由具名嘅人做。
2. **每個數字要有出處。** 引返標書同項目 / 附註號碼。估算要喺同一句講明係估算。
3. **唔可以作價。** 補回項目只可以用 `config/scope_benchmarks.json` 列明來源嘅基準價。
4. **`input/` 同 `tools/` 只讀。** 只寫入 `outputs/`。
5. **附註細字係重點。** 加價條款、高訂金、短保修比一張靚表更重要。
6. **最終交付係 PDF。** 唔係 markdown、唔係 HTML —— 決定人拎住嘅係 `outputs/tender_comparison_report.pdf`。

## Tools 確定性工具

| # | Verb | Tool | Input → Output |
|---|------|------|----------------|
| 1 | EXTRACT | `tools/extract_tenders.py` | `input/tenders/*.pdf` → `outputs/tenders_extracted.json` |
| 2 | COMPARE | `tools/compare_tenders.py` | JSON + `config/scope_benchmarks.json` → `outputs/tender_comparison.md` |
| 3 | RENDER | `tools/render_comparison_pdf.py` | JSON + 建議 md + `config/brand.json` → `outputs/tender_comparison_report.html` → **`.pdf`** |

三個 tool 都係純 regex / 算術 / 模板：唔會 call model、唔上網（PDF 由本機 headless Chrome / Edge 印出）。由 repo 任何位置行都得。

## Run 執行

1. `python tools/extract_tenders.py --input input/tenders --out outputs/tenders_extracted.json`
2. `python tools/compare_tenders.py --extracted outputs/tenders_extracted.json --config config/scope_benchmarks.json --out outputs/tender_comparison.md`
3. 讀 `outputs/tender_comparison.md`，寫 `outputs/tender_recommendation.md`（**150 字以內**，用 `- ` bullet）：
   同一基準下邊份性價比最高、邊份風險最大同點解（引標書 + 附註號碼）、決定前要向投標者澄清嘅兩三點。
4. `python tools/render_comparison_pdf.py --extracted outputs/tenders_extracted.json --recommendation outputs/tender_recommendation.md --out-pdf outputs/tender_comparison_report.pdf`
   — 出 OpenDeedigital 風格 A4 PDF：比較表、每份標書補回明細與風險、你嘅建議、審批簽名欄。
5. 停。回報：行咗邊啲 tool、每份標書表面總價 vs 可比較總成本、風險標記、**PDF 路徑**。
   唔好推薦「中標者」—— 推薦「要澄清乜」。

## Gate 關卡

- **Human-IN（事前批核）**：PDF 交俾簽中標決定嗰個人。佢確認基準假設、有需要向投標者澄清（人發，唔係 agent 發）、然後決定並喺 PDF 簽名欄簽署。本 skill 唔會聯絡任何投標者。
- Criteria：Source（每個數字可追溯）· Accuracy（補回項目與原標書一致）· Risk（加價、訂金、保修、有效期已列）· Accountability（決定人簽名）。

## Style 風格

OpenDeedigital 品牌：`config/brand.json`（主色 #F36B15 橙、副色 #9B0A68 紫紅、深色 #231F20、淺底 #FFF7F0；狀態色 GO / CONTROL / STOP）+ `brand_assets/ODD Logo.png`。
報告 = 品牌色帶 + logo → DRAFT 標記 → 比較表 → 每份標書卡 → 建議 → 審批簽名欄 → footer「AI drafts · Human checks · Human signs」。

## Outputs

`outputs/tenders_extracted.json` · `outputs/tender_comparison.md` · `outputs/tender_recommendation.md` ·
`outputs/tender_comparison_report.html` · **`outputs/tender_comparison_report.pdf`（最終交付）** — 全部 DRAFT 直至有人簽名。

## Configuration

- `config/scope_benchmarks.json`：必須包嘅範圍項目（keyword + 基準價 + 來源）、不包括關鍵字、風險規則。換工程類型改呢個檔。
- `config/brand.json`：品牌色、字體、logo 路徑、footer。換公司改呢個檔。
