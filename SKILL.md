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

# SKILL.md — Tender Comparison Agent / 標書比較代理

> Layer 3 of 3 · **The procedure.** Read `AGENT.md` (authority) and `PROJECT.md` (context) first.
> 三層結構之第三層 · **執行程序。** 請先閱讀 `AGENT.md`（權限）及 `PROJECT.md`（背景）。

Control tags / 控制標籤: `[DET]` deterministic Python · `[LLM]` bounded LLM · `[HUM]` human gate · `[CFG]` configuration.
Definitions are in `AGENT.md` §3. 定義見 `AGENT.md` 第 3 節。

## 1. Intent / 意圖

| English | 繁體中文 |
|---|---|
| Read every tender in `input/tenders/`, including the small-print notes. Extract price, programme, payment, deposit, warranty, validity and every exclusion. Bring each tender to the same scope using the benchmark file. Flag risk clauses. Draft a short recommendation. Produce an A4 PDF. Stop at the human gate. | 閱讀 `input/tenders/` 內每份標書（包括附註細字）；抽取價格、工期、付款、訂金、保修、有效期及所有不包括項目；按基準檔將各標書補回至同一範圍；標示風險條款；擬備簡短建議；輸出 A4 PDF；並於人手關卡停止。 |

Human SOP this skill is derived from / 本 skill 所依據的人手程序: `workflows/tender_comparison.md`

## 2. Rules (non-negotiable) / 規則（不可妥協）

| # | English | 繁體中文 | Control |
|---|---|---|---|
| 1 | AI drafts, a human checks, a human signs. The comparison and the recommendation are drafts. Awarding the contract is a commercial decision made by a named person. | 由 AI 擬稿、人員審核、人員簽署。比較表及建議均為草稿；授標屬商業決定，由指定人員作出。 | `[HUM]` |
| 2 | Every figure carries a source: the tender and the item or note number. An estimate is labelled as an estimate in the same sentence. | 每個數字均須附出處（標書及項目或附註編號）；估算須於同一句內註明為估算。 | `[LLM]` bound |
| 3 | Do not invent figures. A fill-back price may come only from `config/scope_benchmarks.json`, with its stated source. | 不得虛構數字；補回價格僅可取自 `config/scope_benchmarks.json` 並附明確來源。 | `[CFG]` + `[DET]` |
| 4 | `input/`, `tools/` and `config/` are read-only. Write only under `outputs/`. | `input/`、`tools/`、`config/` 唯讀；僅可於 `outputs/` 寫入。 | `[LLM]` bound |
| 5 | Small print is material. Price-adjustment clauses, high deposits and short warranties matter more than a clean table. | 附註細字屬重要資料。價格調整條款、高額訂金及短保修期較整齊的表格更為重要。 | `[DET]` rules |
| 6 | The final deliverable is a PDF (`outputs/tender_comparison_report.pdf`), not Markdown or HTML. | 最終交付為 PDF，而非 Markdown 或 HTML。 | `[DET]` |
| 7 | Do not install or download anything. The tools adapt to what is present; if a tool names a fallback, continue with it and state so in the report. | 不得安裝或下載任何內容；工具會適應現有環境，如工具指明後備方案，須依其繼續並於回報中說明。 | `[LLM]` bound |
| 8 | Do not contact bidders and do not name a winning bidder. Recommend what to clarify, not whom to appoint. | 不得聯絡投標者，亦不得指定中標者；只建議須澄清之事項，不建議委任對象。 | `[LLM]` bound |

## 3. Control map — who does what / 控制分工

| Step | Action / 動作 | Executor / 執行者 | Control | What limits it / 限制方式 | Output |
|---|---|---|---|---|---|
| 1 | Extract / 抽取 | `tools/extract_tenders.py` | `[DET]` | Pattern matching on the PDF text layer; no model, no network. 對 PDF 文字層作樣式比對；不調用模型、不連網。 | `outputs/tenders_extracted.json` |
| 2 | Compare / 比較 | `tools/compare_tenders.py` | `[DET]` + `[CFG]` | Benchmark prices and risk thresholds come from `config/scope_benchmarks.json`. 基準價及風險門檻取自設定檔。 | `outputs/tender_comparison.md` |
| 3 | Recommend / 建議 | The agent / 代理 | `[LLM]` | At most 150 words; `- ` bullets; cite tender and note numbers; name no winner; list two or three clarifications. 不超過 150 字；以 `- ` 項目符號；引用標書及附註編號；不指定中標者；列出兩至三項澄清事項。 | `outputs/tender_recommendation.md` |
| 4 | Render / 輸出 | `tools/render_comparison_pdf.py` | `[DET]` + `[CFG]` | Template and `config/brand.json` decide layout and colour; PDF printed by headless Chrome or Edge, reportlab as fallback. 版面及色彩由模板與 `brand.json` 決定；PDF 由無頭 Chrome 或 Edge 輸出，reportlab 為後備。 | `outputs/tender_comparison_report.pdf` |
| 5 | Decide / 決定 | A named person / 指定人員 | `[HUM]` | Confirms assumptions, issues clarifications, decides, signs the block in the PDF. 確認假設、發出澄清、作出決定並於 PDF 簽署欄簽署。 | Signed PDF |

## 4. Procedure / 執行程序

Run from the repository root. 於 repo 根目錄執行。

1. **`[DET]` Extract / 抽取**
   `python tools/extract_tenders.py --input input/tenders --out outputs/tenders_extracted.json`
2. **`[DET]` Compare / 比較**
   `python tools/compare_tenders.py --extracted outputs/tenders_extracted.json --config config/scope_benchmarks.json --out outputs/tender_comparison.md`
3. **`[LLM]` Recommend / 建議** — read `outputs/tender_comparison.md` and write `outputs/tender_recommendation.md`.
   閱讀 `outputs/tender_comparison.md` 並撰寫 `outputs/tender_recommendation.md`。
   - At most 150 words, `- ` bullets. 不超過 150 字，使用 `- ` 項目符號。
   - Which tender is best value on the common basis; which carries the most risk and why, with tender and note numbers; two or three points to clarify before deciding.
     共同基準下何者性價比最高；何者風險最大及原因（附標書及附註編號）；決定前須澄清的兩至三點。
4. **`[DET]` Render / 輸出**
   `python tools/render_comparison_pdf.py --extracted outputs/tenders_extracted.json --recommendation outputs/tender_recommendation.md --out-pdf outputs/tender_comparison_report.pdf`
5. **Stop. / 停止。** Report: the tools run; each bidder's stated total against its like-for-like total; risk flags; the PDF path. Do not recommend a winner.
   回報：已執行的工具；各投標者的表面總價與可比較總成本；風險標記；PDF 路徑。不得推薦中標者。

## 5. Gate / 關卡 `[HUM]`

| English | 繁體中文 |
|---|---|
| **Human-IN (approval before release).** The PDF is handed to the person who signs the award decision. That person confirms the fill-back assumptions, sends any clarification to bidders (a person sends it, not the agent), decides, and signs the block in the PDF. | **事前批核。** PDF 交予負責簽署授標決定的人員；該人員確認補回假設、自行向投標者發出澄清（由人員發出，而非代理）、作出決定並於 PDF 簽署欄簽署。 |
| Criteria: **Source** (every figure traceable) · **Accuracy** (fill-back items match the tender) · **Risk** (adjustments, deposit, warranty, validity listed) · **Accountability** (decision-maker signs). | 準則：**出處**（每個數字可追溯）· **準確**（補回項目與標書一致）· **風險**（調整條款、訂金、保修、有效期已列明）· **問責**（決策人簽署）。 |

## 6. Style / 風格 `[CFG]`

OpenDeedigital brand, from `config/brand.json` and `brand_assets/ODD Logo.png`. Report order: colour band and logo → DRAFT mark → comparison table → one card per tender → recommendation → approval block → footer "AI drafts · Human checks · Human signs".
OpenDeedigital 品牌，取自 `config/brand.json` 及 `brand_assets/ODD Logo.png`。報告次序：色帶及標誌 → DRAFT 標記 → 比較表 → 每份標書一張資料卡 → 建議 → 審批簽署欄 → 頁腳「AI drafts · Human checks · Human signs」。

## 7. Outputs / 輸出

`outputs/tenders_extracted.json` · `outputs/tender_comparison.md` · `outputs/tender_recommendation.md` · `outputs/tender_comparison_report.html` · **`outputs/tender_comparison_report.pdf`** (final deliverable 最終交付). All are drafts until a person signs. 在人員簽署前均為草稿。

## 8. Configuration / 設定 `[CFG]`

- `config/scope_benchmarks.json` — required scope items (keywords and benchmark price with source), exclusion keywords and risk rules. Replace it for a different type of works. 必需範圍項目（關鍵字及附來源之基準價）、不包括關鍵字及風險規則；更換工程類型時替換此檔。
- `config/brand.json` — brand colours, font stack, logo path and footer. Replace it for a different company. 品牌色彩、字體、標誌路徑及頁腳；更換公司時替換此檔。
