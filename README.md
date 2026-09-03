# tender-comparison-agent

Agent skill：將同一項工程嘅多份標書（PDF）砌返同一比較基準，標出風險條款，出一份 **OpenDeedigital 風格嘅 A4 PDF 比較報告**（連建議初稿同審批簽名欄）。AI 起草，人決定。

## Structure

```
tender-comparison-agent/
├── SKILL.md                        [md]      agent 指令：Intent · Rules · Tools · Run · Gate · Style
├── AGENTS.md                       [md]      Codex / agent 入口 → 指向 SKILL.md
├── workflows/
│   └── tender_comparison.md        [md]      人做法 SOP —— skill 跟呢份寫
├── tools/                          [python]  3 個 deterministic tool
│   ├── extract_tenders.py                    1 EXTRACT
│   ├── compare_tenders.py                    2 COMPARE
│   └── render_comparison_pdf.py              3 RENDER → PDF
├── config/
│   ├── scope_benchmarks.json       [config]  範圍項目 · 基準價 · 風險規則
│   └── brand.json                  [config]  OpenDeedigital 品牌色 · 字體 · logo
├── brand_assets/ODD Logo.png       [asset]
├── input/tenders/                  [input]   標書 PDF —— 唔會 commit
└── outputs/                        [output]  tool 同 agent 寫入嘅位置；最終係 .pdf
```

## 邊啲係 .md，邊啲係 python

| 類型 | 檔案 | 邊個寫 | 作用 |
|---|---|---|---|
| `.md` | `SKILL.md` | 識睇標書嘅人 | 話俾 agent 聽：目標、規則、幾時用邊個 tool、幾時停、交付格式 |
| `.md` | `workflows/tender_comparison.md` | 同上 | 人手做法逐步寫低（SOP）；SKILL.md 係佢嘅 agent 版 |
| `.py` | `tools/*.py` | 開發者 | 確定性運算同模板：同一輸入永遠同一輸出，冇 model、冇上網 |
| `.json` | `config/*.json` | 識睇標書嘅人 / 品牌負責人 | 業務參數同品牌：改呢度，唔使改 code |

## Deterministic tools — 3 個

| # | Tool | 讀 | 寫 | 做乜 |
|---|---|---|---|---|
| 1 | `extract_tenders.py` | `input/tenders/*.pdf` | `outputs/tenders_extracted.json` | 每份 PDF 抽：公司、總價、分項、工期、訂金、付款、保修、有效期、附註 |
| 2 | `compare_tenders.py` | JSON + `scope_benchmarks.json` | `outputs/tender_comparison.md` | 補回不包括項目（列明來源嘅基準價）→ 可比較總成本；風險標記；待澄清清單 |
| 3 | `render_comparison_pdf.py` | JSON + 建議 md + `brand.json` + logo | `outputs/tender_comparison_report.html` → **`.pdf`** | OpenDeedigital 風格 A4 報告：品牌色帶、比較表、每份標書卡、建議、審批簽名欄 |

## Output 點樣產生

```
input/tenders/*.pdf
   │  1 extract_tenders.py                                  (python · 確定性)
   ▼
outputs/tenders_extracted.json
   │  2 compare_tenders.py + scope_benchmarks.json          (python · 確定性)
   ▼
outputs/tender_comparison.md          ← 比較表、補回明細、風險條款
   │  agent 讀表，跟 SKILL.md 第 3 步                        (model · 起草)
   ▼
outputs/tender_recommendation.md      ← ≤150 字建議初稿
   │  3 render_comparison_pdf.py + brand.json + logo        (python · 模板 → headless Chrome 印 PDF)
   ▼
outputs/tender_comparison_report.pdf  ← 最終交付（A4 · OpenDeedigital 風格 · DRAFT · 簽名欄）
   │
   ▼
人：確認基準 · 向投標者澄清 · 決定 · 簽名                     (gate)
```

數字全部由 python 計；model 只讀表同寫建議，每個數字要引返出處；版面由模板同品牌 config 決定，唔係 model 決定。

## Run

```bash
pip install -r requirements.txt          # pymupdf；PDF 需要本機有 Chrome 或 Edge
# 放標書 PDF 入 input/tenders/
python tools/extract_tenders.py
python tools/compare_tenders.py
# （agent 寫 outputs/tender_recommendation.md）
python tools/render_comparison_pdf.py
```

用 agent（Codex / Claude Code）開呢個 folder，佢會讀 `AGENTS.md → SKILL.md`，然後：

```
跟住 SKILL.md 做：比較 input/tenders 入面嘅標書，出 PDF 比較報告。
```

## Input data

`input/` 唔會 commit —— 標書係項目文件。示範用嘅三份 dummy 標書另外提供（zip），放入 `input/tenders/` 即可。

## Requirements

Python 3.10+ · PyMuPDF · 本機 Chrome / Edge（印 PDF；冇嘅話會留低 HTML）。冇 API key、冇網絡需求。
