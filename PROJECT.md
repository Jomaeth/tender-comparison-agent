# PROJECT.md — Tender Comparison Agent / 標書比較代理

> Layer 1 of 3 · **The work context: what is being done, with what, by whom.**
> 三層結構之第一層 · **工作背景：處理何事、使用何物、由誰負責。**
> Layer 2 `AGENT.md` = role and authority · Layer 3 `SKILL.md` = procedure.

## 1. Purpose / 目的

| English | 繁體中文 |
|---|---|
| Compare two or more supplier tenders for the same job on one like-for-like basis, flag risk clauses, and deliver a branded A4 PDF report with a short recommendation draft and an approval block. | 就同一工程的多份供應商標書建立同一比較基準、標示風險條款，並交付附簡短建議初稿及審批簽署欄的品牌化 A4 PDF 報告。 |
| Decision owner: a named person (for example the commercial manager or quantity surveyor). The agent prepares; the person decides. | 決策人：指定人員（例如商務經理或工料測量師）。代理負責準備，由該人員決定。 |

## 2. The three-layer model / 三層模型

```
PROJECT.md   what is the work, which data, which standards        → written by the practitioner
AGENT.md     who the agent is, what it may and must never do       → written by the practitioner
SKILL.md     the ordered procedure; each step tagged DET/LLM/HUM   → written by the practitioner
   │
   ├── tools/      [DET]  Python: extraction, comparison, rendering
   ├── config/     [CFG]  JSON: benchmark prices, risk thresholds, brand
   └── workflows/  [HUM]  the human SOP the skill was derived from
```

## 3. Files and who owns them / 檔案及負責人

| Path / 路徑 | Type | Control | Owner | English | 繁體中文 |
|---|---|---|---|---|---|
| `PROJECT.md` `AGENT.md` `SKILL.md` | `.md` | `[LLM]` bound / `[HUM]` | Practitioner | Instructions the model follows. | 模型須遵循的指令。 |
| `workflows/tender_comparison.md` | `.md` | `[HUM]` | Practitioner | The human SOP in plain language. | 以平白文字撰寫的人手標準作業程序。 |
| `tools/extract_tenders.py` | `.py` | `[DET]` | Developer | Reads each tender PDF and extracts price, items, terms, exclusions and notes by pattern matching. | 以樣式比對方式讀取每份標書 PDF，抽取價格、分項、條款、不包括項目及附註。 |
| `tools/compare_tenders.py` | `.py` | `[DET]` | Developer | Fills excluded scope back at benchmark prices and applies risk rules. | 以基準價補回不包括的範圍，並套用風險規則。 |
| `tools/render_comparison_pdf.py` | `.py` | `[DET]` | Developer | Builds the branded HTML and prints it to PDF. | 生成品牌化 HTML 並輸出為 PDF。 |
| `config/scope_benchmarks.json` | `.json` | `[CFG]` | Practitioner | Required scope items, benchmark prices with sources, risk thresholds. | 必需範圍項目、附來源的基準價及風險門檻。 |
| `config/brand.json` | `.json` | `[CFG]` | Brand owner | Colours, fonts, logo path, footer. | 色彩、字體、標誌路徑及頁腳。 |
| `input/tenders/` | PDFs | — | Project team | Tender documents. **Local only. Never committed.** | 標書文件。**僅限本機，不得提交至 Git。** |
| `outputs/` | generated | — | Agent / tools | Extracted data, comparison table, recommendation, final PDF. **Local only. Never committed.** | 抽取資料、比較表、建議及最終 PDF。**僅限本機，不得提交至 Git。** |

## 4. Data handling / 資料處理

| English | 繁體中文 |
|---|---|
| This repository contains **instructions, tools and configuration only**. Demonstration tender documents and the generated reports are kept on the presenter's machine and are excluded by `.gitignore`. | 本 repo 僅包含**指令、工具及設定**。示範標書及所生成的報告只存放於講者本機，並已由 `.gitignore` 排除。 |
| Real tender documents are confidential. Do not place them in a public tool or a public repository. | 真實標書屬機密文件，不得放入公開工具或公開 repo。 |
| The agent never contacts bidders. Clarification requests, if any, are sent by a person. | 代理不會聯絡投標者；如需澄清，由人員發出。 |

## 5. Environment / 環境

| English | 繁體中文 |
|---|---|
| Python 3.10 or later. One PDF text reader is sufficient; the tool uses whichever is already installed (PyMuPDF, pypdf, pdfminer.six or poppler). | Python 3.10 或以上。只需一個 PDF 文字讀取套件；工具會使用已安裝者（PyMuPDF、pypdf、pdfminer.six 或 poppler）。 |
| PDF output uses headless Chrome or Edge if present, otherwise reportlab. Nothing needs to be downloaded during a run. | PDF 輸出優先使用本機 Chrome 或 Edge，否則使用 reportlab；執行期間無須下載任何內容。 |

## 6. Run / 執行

```bash
python tools/extract_tenders.py    --input input/tenders --out outputs/tenders_extracted.json      # [DET]
python tools/compare_tenders.py    --extracted outputs/tenders_extracted.json \
                                   --config config/scope_benchmarks.json --out outputs/tender_comparison.md   # [DET]
# The agent now writes outputs/tender_recommendation.md (<= 150 words)                            # [LLM]
python tools/render_comparison_pdf.py --extracted outputs/tenders_extracted.json \
       --recommendation outputs/tender_recommendation.md --out-pdf outputs/tender_comparison_report.pdf  # [DET]
```

## 7. Opening this project in Codex / 於 Codex 開啟本專案

1. Open Codex and choose **Open folder / 開啟資料夾**; select the folder that contains this file.
   開啟 Codex，選擇「開啟資料夾」，選取包含本檔案的資料夾。
2. Confirm that `input/tenders/` contains the tender PDFs (local copies).
   確認 `input/tenders/` 內已有標書 PDF（本機副本）。
3. Codex reads `AGENTS.md`, which points to `AGENT.md`, `PROJECT.md` and `SKILL.md`.
   Codex 會讀取 `AGENTS.md`，並由其指向 `AGENT.md`、`PROJECT.md` 及 `SKILL.md`。
4. Enter the instruction / 輸入指令:

```
Follow SKILL.md. Compare the tenders in input/tenders and produce the PDF comparison report.
Do not name a winner. Stop at the human gate.
```

## 8. Glossary / 詞彙

| Term | English | 繁體中文 |
|---|---|---|
| Like-for-like | All bidders priced on the same scope. | 所有投標者按相同範圍計價。 |
| Fill-back | Adding the benchmark price of an excluded item to a bidder's total. | 將不包括項目的基準價加入投標者總價。 |
| Provisional sum | A placeholder amount that may change. | 可能變動的暫定金額。 |
| Human gate | A point where the process stops for a named person. | 流程須停止以待指定人員處理的關卡。 |
