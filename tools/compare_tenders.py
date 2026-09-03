#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""COMPARE — put every tender on the same basis and flag risk clauses.

Deterministic: reads the JSON from extract_tenders.py plus the benchmark
config. Fills back excluded scope items with benchmark prices (source stated),
computes a like-for-like total, and writes a Markdown comparison table.
Usage:
    python tools/compare_tenders.py --extracted outputs/tenders_extracted.json \
        --config config/scope_benchmarks.json --out outputs/tender_comparison.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _resolve(p: str) -> Path:
    path = Path(p)
    return path if path.is_absolute() else ROOT / path


def hk(n) -> str:
    return "—" if n is None else f"HK${n:,.0f}"


EXCL_IN_DESC = ("不含", "不包括", "不包", "另行", "見附註")


def covers(tender: dict, keywords: list[str]) -> bool:
    """A scope item is covered when a priced line item mentions one of its keywords
    and that line does not itself say the item is excluded (e.g. 清拆工程（不含廢料處置）)."""
    for it in tender["line_items"]:
        d = it["desc"]
        if any(k in d for k in keywords) and not any(e in d for e in EXCL_IN_DESC):
            return True
    return False


def excluded_note(tender: dict, keywords: list[str], excl_keys: list[str]) -> str | None:
    for n in tender["notes"]:
        if any(k in n for k in keywords) and any(e in n for e in excl_keys):
            return n
    return None


def assess(tender: dict, cfg: dict) -> dict:
    fills, flags = [], []
    for item in cfg["scope_items"]:
        if covers(tender, item["keywords"]):
            continue
        note = excluded_note(tender, item["keywords"], cfg["exclusion_keywords"])
        fills.append({
            "label": item["label"],
            "benchmark_hkd": item["benchmark_hkd"],
            "benchmark_ref": item["benchmark_ref"],
            "evidence": note or "標書分項中無此項目（未見任何相關計價）",
        })
    like_for_like = (tender["total_hkd"] or 0) + sum(f["benchmark_hkd"] for f in fills)

    r = cfg["risk_rules"]
    notes_flat = " ".join(tender["notes"]) + " " + (tender["payment_terms"] or "")
    if tender["deposit_pct"] is not None and tender["deposit_pct"] > r["deposit_pct_max"]:
        flags.append(f"訂金 {tender['deposit_pct']}%（高於 {r['deposit_pct_max']}%）")
    if tender["warranty_months"] is not None and tender["warranty_months"] < r["warranty_months_min"]:
        flags.append(f"保修只有 {tender['warranty_months']:g} 個月（少於 {r['warranty_months_min']} 個月）")
    if tender["validity_days"] is not None and tender["validity_days"] < r["validity_days_min"]:
        flags.append(f"報價有效期只有 {tender['validity_days']} 天")
    if any(k in notes_flat for k in r["escalation_keywords"]):
        flags.append("有物料價格調整條款（加價後門）")
    if any(k in notes_flat for k in r["provisional_keywords"]):
        flags.append("有暫定數項目（最終價未定）")
    if any(k in notes_flat for k in r["conditional_programme_keywords"]):
        flags.append("工期附帶條件")
    return {"fills": fills, "like_for_like_hkd": like_for_like, "flags": flags}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--extracted", default="outputs/tenders_extracted.json")
    ap.add_argument("--config", default="config/scope_benchmarks.json")
    ap.add_argument("--out", default="outputs/tender_comparison.md")
    a = ap.parse_args()

    data = json.loads(_resolve(a.extracted).read_text(encoding="utf-8"))
    cfg = json.loads(_resolve(a.config).read_text(encoding="utf-8"))
    tenders = data["tenders"]
    results = [(t, assess(t, cfg)) for t in tenders]
    cheapest_headline = min(tenders, key=lambda t: t["total_hkd"] or 1e12)["label"]
    cheapest_l4l = min(results, key=lambda tr: tr[1]["like_for_like_hkd"])[0]["label"]

    L = []
    L.append(f"# 標書比較表（DRAFT）— {cfg['project']}\n")
    L.append("> 本表由 tender-comparison-agent 以確定性工具產生。補回項目為**估算**，基準見下方說明。決定與簽名由人做。\n")
    L.append("## 一、同一比較基準\n")
    L.append("| 公司 | 表面總價 | 補回不包括項目 | **可比較總成本** | 工期 | 訂金 | 保修 | 有效期 | 風險標記 |")
    L.append("|---|---:|---:|---:|---|---|---|---|---|")
    for t, r in results:
        fill_sum = sum(f["benchmark_hkd"] for f in r["fills"])
        wm = t["warranty_months"]
        L.append(
            f"| {t['label']} | {hk(t['total_hkd'])} | {'+ ' + hk(fill_sum) if fill_sum else '—'} | **{hk(r['like_for_like_hkd'])}** | "
            f"{t['duration_weeks'] or '—'} 週 | {t['deposit_pct'] if t['deposit_pct'] is not None else '—'}% | "
            f"{(f'{wm:g} 個月' if wm is not None else '—')} | {t['validity_days'] or '—'} 天 | {len(r['flags'])} 項 |"
        )
    L.append("")
    L.append(f"- 表面最平：**{cheapest_headline}**　·　補回不包括項目後最平：**{cheapest_l4l}**")
    L.append(f"- 補回基準：{cfg['benchmark_source']}\n")

    L.append("## 二、每份標書：補回明細與風險條款\n")
    for t, r in results:
        L.append(f"### {t['label']} — 表面 {hk(t['total_hkd'])} → 可比較 {hk(r['like_for_like_hkd'])}")
        if r["fills"]:
            L.append("補回項目：")
            for f in r["fills"]:
                L.append(f"- {f['label']}：+{hk(f['benchmark_hkd'])}（估算，基準 {f['benchmark_ref']}）— 證據：「{f['evidence'][:60]}」")
        else:
            L.append("補回項目：無 — 分項已覆蓋全部基準範圍")
        L.append("風險條款：" + ("；".join(r["flags"]) if r["flags"] else "未見"))
        if t["payment_terms"]:
            L.append(f"付款：{t['payment_terms']}")
        L.append("")

    L.append("## 三、待澄清（供決定人使用）\n")
    L.append("- 各補回估算是否接受？若否，向相關投標者索取該項目之正式報價")
    L.append("- 有暫定數 / 價格調整條款者：要求鎖定最終價或設上限")
    L.append("- 訂金比例與保修期：可否按最完整標書之條款拉平\n")
    L.append("---\n**DRAFT — AI 起草，人檢查，人簽名。** 本表不構成中標決定。")

    out = _resolve(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L), encoding="utf-8")

    print("COMPARE  like-for-like basis")
    for t, r in results:
        print(f"  - {t['label'][:28]:<28} headline {hk(t['total_hkd']):>14}  ->  like-for-like {hk(r['like_for_like_hkd']):>14}  flags={len(r['flags'])}")
    print(f"  cheapest headline: {cheapest_headline} | cheapest like-for-like: {cheapest_l4l}")
    print(f"  -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
