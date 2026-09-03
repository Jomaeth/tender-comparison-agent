---
name: tender-comparison-agent
description: >
  Compare several supplier tenders / quotations for the same job and produce a
  like-for-like comparison table plus a short recommendation draft. Use this
  skill whenever the user asks to compare bids, quotations, tenders or 報價
  ("compare these three quotes", "邊份標書最抵", "幫我比較供應商報價",
  "which tender should we pick"). It extracts prices, terms, exclusions and
  hidden conditions from each PDF, normalises them to one comparison basis,
  and flags risk clauses. The skill drafts; a named human decides and signs.
---

# Tender Comparison Agent 標書比較代理

## Intent 意圖

Do the half-day of reading a QS or purchasing manager would otherwise do by
hand: read every tender in a folder — **including the small print** — pull
out price, programme, payment, warranty, validity and every exclusion, then
put all bidders on the same comparison basis so the cheapest headline price
can be tested. 讀晒 folder 入面每份標書（包括附註細字）→ 抽出價錢、工期、付款、
保修、有效期、所有不包括項目 → 砌返同一比較基準 → 出比較表同建議初稿 →
**停在人手決定關卡**。

The plain-language SOP is `workflows/tender_comparison.md`.

## Principles 原則（不可妥協）

1. **AI drafts → Human checks → Human signs.** The comparison and the
   recommendation are DRAFTS. Which tender wins is a commercial decision made
   by a named person. AI 起草，人決定，人簽名。
2. **Every number is traced.** Quote the tender and the item / note number for
   every figure. If a figure is an estimate, say so in the same sentence.
   所有數字要引返出處；估算要標明係估算。
3. **Never guess a price.** Exclusions are filled back using the benchmark
   table in `config/scope_benchmarks.json`, and the source of each benchmark
   is stated. Do not invent market rates. 唔可以作價。
4. **Read-only inputs.** Do not modify anything under `demo-data/` or
   `tools/`. Write only under `outputs/`.
5. **Surface the small print.** A hidden escalation clause or a 30% deposit
   is worth more to the reader than a pretty table. 附註細字係重點。

## Deterministic tools 確定性工具（動詞 → 工具）

| # | Verb | Tool (`tools/`) | What it does |
|---|------|------------------|--------------|
| 1 | EXTRACT | `extract_tenders.py` | Read every PDF in a folder → structured JSON (company, total, line items, terms, notes) |
| 2 | COMPARE | `compare_tenders.py` | JSON + benchmark config → like-for-like table, risk flags (Markdown) |

Both tools resolve paths relative to the repo root and work from any working
directory. They never call a model and never touch the network.

## Standard run 標準執行（demo path）

Input: the PDFs in `demo-data/tenders/` (three fictional fit-out tenders for
the same office project, ref TQ-2026-018).

1. `python tools/extract_tenders.py --input demo-data/tenders --out outputs/tenders_extracted.json`
2. `python tools/compare_tenders.py --extracted outputs/tenders_extracted.json --config config/scope_benchmarks.json --out outputs/tender_comparison.md`
3. Read `outputs/tender_comparison.md`. Then write
   `outputs/tender_recommendation.md` — **no more than 150 words** — covering:
   which tender offers the best value on a like-for-like basis, which carries
   the most risk and why (cite tender + note number), and the two or three
   points to clarify with bidders before any decision.
4. Stop. Report back: tools run, headline vs like-for-like totals for each
   bidder, the risk flags found, and the paths of the two output files.
   Do not recommend a winner as a decision — recommend what to clarify.

## Review gate 批核關卡

- Gate type: **Human-IN（事前批核）** — the recommendation goes to the person
  who will sign the award. They confirm the benchmark assumptions, may
  request clarification from bidders, and decide. Nothing is sent to any
  bidder by this skill.
- Criteria: Source（每個數字可追溯）· Accuracy（補回項目與原標書一致）·
  Risk（加價條款、訂金、保修、有效期已列出）· Accountability（決定人簽名）。

## Outputs 輸出

`outputs/tenders_extracted.json` · `outputs/tender_comparison.md` ·
`outputs/tender_recommendation.md` — all marked DRAFT until a human signs.

## Adapting to your own tenders 用喺你自己嘅標書

Put your PDFs in a folder, update `config/scope_benchmarks.json` with the
scope items that matter for your job and a benchmark price for each (usually
the most complete bid), then run the same three steps. The keyword lists are
what the comparison tool uses to decide whether a bid covers a scope item —
edit them to match your trade's wording.
