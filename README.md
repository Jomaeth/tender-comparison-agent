# Tender Comparison Agent 標書比較代理

> **AI drafts · Human checks · Human signs**
> 三份標書，老闆一眼睇「最平就係最好」？Agent 讀晒附註細字，砌返同一比較基準，答案往往唔同

This repo is a self-contained teaching demo. Clone it, open the folder in **Codex** (or Claude Code / any agent that reads `SKILL.md`), and give it the prompt below. The skill, two deterministic Python tools, and three fictional tenders are inside.

呢個 repo 係一個自足嘅教學示範。Clone 落嚟，用 **Codex** 開呢個 folder，貼下面個 prompt 就得。

---

## 30-second demo 三十秒示範

```bash
git clone --depth 1 https://github.com/Jomaeth/tender-comparison-agent.git
cd tender-comparison-agent
pip install -r requirements.txt
```

Open the folder in Codex and paste:

```
跟住 SKILL.md 做：比較 demo-data/tenders 入面三份標書，出比較表同一段建議。
最後話我知：每間公司嘅表面總價 vs 可比較總成本、搵到咩風險條款、同兩個 output 檔案嘅路徑。
```

The agent extracts every tender (including the small print), fills back excluded scope items with stated benchmarks, flags risk clauses, writes a ≤150-word recommendation — and **stops**. It never picks the winner; a named person does.

---

## The scenario 情境

Your company is fitting out a new office (ref TQ-2026-018). Three contractors have quoted:

| | Headline price | Programme |
|---|---:|---|
| A · 宏基裝飾工程 | HK$2,618,000 | 12 weeks |
| B · 快達裝修 | **HK$2,180,000 — cheapest** | 10 weeks |
| C · 精藝室內工程 | HK$2,952,000 | 13 weeks |

Tender B is the cheapest on the cover page. Run the agent and see what its eight notes on the back page do to that number.

**All three tenders are fictional**, written for teaching. Company names, addresses and prices are invented.

---

## What is inside 入面有咩

```
tender-comparison-agent/
├── SKILL.md                    ← the agent reads this first (Intent · Principles · Tools · Gate)
├── AGENTS.md                   ← Codex entry point → points to SKILL.md
├── workflows/
│   └── tender_comparison.md    ← plain-language SOP: how a QS compares bids by hand
├── tools/
│   ├── extract_tenders.py      EXTRACT  every PDF → structured JSON (price, items, terms, notes)
│   └── compare_tenders.py      COMPARE  JSON + benchmarks → like-for-like table + risk flags
├── config/
│   └── scope_benchmarks.json   ← scope items that must be covered + benchmark price + source
├── demo-data/tenders/          ← three fictional tender PDFs
└── outputs/                    ← generated here (gitignored)
```

---

## Why this shape 點解咁設計

| Layer | What | Why it matters |
|---|---|---|
| **Workflow** (`workflows/*.md`) | The SOP a QS / purchasing manager follows | The practitioner writes this — not a programmer |
| **Agent** (Codex / Claude / Gemini) | Reads the SOP, runs the tools, writes the recommendation | Handles reading and judgement; cites every number |
| **Tools** (`tools/*.py`) | Deterministic extraction and arithmetic | Prices are parsed and summed, never hallucinated |
| **Config** (`config/*.json`) | Benchmarks with stated sources | "Estimate" is always labelled and traceable |
| **Gate** | Hard stop before any decision | The award is signed by a person |

To use it on your own tenders: drop your PDFs in a folder, edit `config/scope_benchmarks.json` for the scope items that matter in your trade, run the same steps. See the sister repo [monthly-report-agent](https://github.com/Jomaeth/monthly-report-agent) for the same pattern on a monthly report.

---

## Requirements

Python 3.10+ · `pip install -r requirements.txt` (PyMuPDF only). No API keys, no network.

---

Built by [OpenDeedigital](https://opendeedigital.io) · Johnny K.C. Ma · [johnnyma.ai](https://johnnyma.ai)
Teaching reference for CEF AI courses and the HKIC AI2C course. Code: MIT. SOP text: CC BY 4.0.
