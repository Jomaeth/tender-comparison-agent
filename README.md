# tender-comparison-agent

Agent skill：將同一項工程嘅多份標書（PDF）砌返同一比較基準，標出風險條款，出建議初稿。AI 起草，人決定。

## Structure

```
tender-comparison-agent/
├── SKILL.md                        [md]      agent 指令：Intent · Rules · Tools · Run · Gate
├── AGENTS.md                       [md]      Codex / agent 入口 → 指向 SKILL.md
├── workflows/
│   └── tender_comparison.md        [md]      人做法 SOP —— skill 跟呢份寫
├── tools/                          [python]  2 個 deterministic tool
│   ├── extract_tenders.py                    EXTRACT
│   └── compare_tenders.py                    COMPARE
├── config/
│   └── scope_benchmarks.json       [config]  範圍項目 · 基準價 · 風險規則
├── input/tenders/                  [input]   標書 PDF —— 唔會 commit
└── outputs/                        [output]  tool 同 agent 寫入嘅位置
```

## 邊啲係 .md，邊啲係 python

| 類型 | 檔案 | 邊個寫 | 作用 |
|---|---|---|---|
| `.md` | `SKILL.md` | 識睇標書嘅人 | 話俾 agent 聽：目標、規則、幾時用邊個 tool、幾時停 |
| `.md` | `workflows/tender_comparison.md` | 同上 | 人手做法逐步寫低（SOP）；SKILL.md 係佢嘅 agent 版 |
| `.py` | `tools/*.py` | 開發者 | 確定性運算：同一輸入永遠同一輸出，冇 model、冇上網 |
| `.json` | `config/scope_benchmarks.json` | 識睇標書嘅人 | 業務參數：改呢度，唔使改 code |

## Deterministic tools — 2 個

| # | Tool | 讀 | 寫 | 做乜 |
|---|---|---|---|---|
| 1 | `extract_tenders.py` | `input/tenders/*.pdf` | `outputs/tenders_extracted.json` | 每份 PDF 抽：公司、總價、分項、工期、訂金、付款、保修、有效期、附註 |
| 2 | `compare_tenders.py` | 上面個 JSON + `config/scope_benchmarks.json` | `outputs/tender_comparison.md` | 補回不包括項目（用列明來源嘅基準價）→ 可比較總成本；風險標記；待澄清清單 |

## Output 點樣產生

```
input/tenders/*.pdf
   │  extract_tenders.py                        (python · 確定性)
   ▼
outputs/tenders_extracted.json
   │  compare_tenders.py + config              (python · 確定性)
   ▼
outputs/tender_comparison.md      ← 比較表、補回明細、風險條款
   │  agent 讀表，跟 SKILL.md 第 3 步          (model · 起草)
   ▼
outputs/tender_recommendation.md  ← ≤150 字建議初稿
   │
   ▼
人：確認基準 · 向投標者澄清 · 決定 · 簽名      (gate)
```

數字全部由 python 計；model 只負責讀表同寫建議，而且每個數字要引返出處。

## Run

```bash
pip install -r requirements.txt          # pymupdf
# 放標書 PDF 入 input/tenders/
python tools/extract_tenders.py
python tools/compare_tenders.py
```

用 agent（Codex / Claude Code）開呢個 folder，佢會讀 `AGENTS.md → SKILL.md`，然後：

```
跟住 SKILL.md 做：比較 input/tenders 入面嘅標書，出比較表同一段建議。
```

## Input data

`input/` 唔會 commit —— 標書係項目文件。示範用嘅三份 dummy 標書另外提供（zip），放入 `input/tenders/` 即可。

## Requirements

Python 3.10+ · PyMuPDF。冇 API key、冇網絡需求。
