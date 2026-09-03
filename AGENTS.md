# AGENTS.md — Tender Comparison Agent

You are working inside a teaching repo that implements one agentic workflow: several supplier tenders (PDF) → like-for-like comparison → recommendation draft.

**Read `SKILL.md` first and follow it.** It defines the intent, the non-negotiable principles, the tool order, and where you must stop.

Quick rules (full list in `SKILL.md`):

1. AI drafts → human checks → human signs. The comparison and recommendation are DRAFTS; the award decision is a person's.
2. Trace every number to a tender and item / note number. Say "估算" wherever a figure is a benchmark fill-back.
3. Never invent a market price. Use `config/scope_benchmarks.json` and state its source.
4. `demo-data/` and `tools/` are read-only. Write only under `outputs/`.
5. Use the tools for extraction and comparison. Your own job is reading the output and writing the ≤150-word recommendation.

Standard demo run:

```
python tools/extract_tenders.py --input demo-data/tenders --out outputs/tenders_extracted.json
python tools/compare_tenders.py --extracted outputs/tenders_extracted.json --config config/scope_benchmarks.json --out outputs/tender_comparison.md
```

Then write `outputs/tender_recommendation.md` and report: tools run, headline vs like-for-like totals per bidder, risk flags, output paths. Stop.

Language: reply in the language the user writes in (廣東話 / 繁體中文 / English).
