#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""EXTRACT — read every tender PDF in a folder and write structured JSON.

Deterministic: regex over the PDF text layer. No model, no network.
Usage:
    python tools/extract_tenders.py --input demo-data/tenders --out outputs/tenders_extracted.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    sys.exit("PyMuPDF is required: pip install pymupdf")

ROOT = Path(__file__).resolve().parents[1]

AMOUNT = re.compile(r"^\d{1,3}(?:,\d{3})+$")
ITEM_NO = re.compile(r"^(?:\d{1,2}|P\d)$")
NOTE_LINE = re.compile(r"^\d{1,2}[.、]\s*")
NOTE_KEYS = ("不包括", "不含", "另行", "實報實銷", "暫定數", "前提", "波動", "自行委聘", "恕不負責")


def _resolve(p: str) -> Path:
    path = Path(p)
    return path if path.is_absolute() else ROOT / path


def _num(s: str | None) -> int | None:
    return int(s.replace(",", "")) if s else None


def _first(pattern: str, text: str, flags=0, group=1):
    m = re.search(pattern, text, flags)
    return m.group(group) if m else None


def parse_tender(pdf: Path) -> dict:
    doc = fitz.open(pdf)
    text = "\n".join(page.get_text() for page in doc)
    lines = [l.strip() for l in text.splitlines()]
    lines = [l for l in lines if l]
    flat = " ".join(lines)

    # --- line items: "<no>" / "<desc>" [/ "<desc cont.>"] / "<amount>" ---
    items = []
    i = 0
    while i < len(lines) - 2:
        if ITEM_NO.match(lines[i]):
            if AMOUNT.match(lines[i + 2]):
                items.append({"no": lines[i], "desc": lines[i + 1], "amount_hkd": _num(lines[i + 2])})
                i += 3
                continue
            if i + 3 < len(lines) and AMOUNT.match(lines[i + 3]):
                items.append({"no": lines[i], "desc": lines[i + 1] + lines[i + 2], "amount_hkd": _num(lines[i + 3])})
                i += 4
                continue
        i += 1

    # --- headline total ---
    total = _num(_first(r"(?:投標總價|總價)[^\d]{0,40}?(\d{1,3}(?:,\d{3})+)", flat))

    # --- terms ---
    weeks = _first(r"(\d+)\s*個?星期", flat)
    deposit = _first(r"(\d+)\s*%\s*訂金", flat)
    if deposit is None and re.search(r"毋須訂\s*金|無須訂\s*金|不需訂\s*金", flat):
        deposit = "0"
    warranty_n, warranty_u = None, None
    m = re.search(r"保修[^\d]{0,30}?(\d+)\s*(個月|天|日)", flat)
    if m:
        warranty_n, warranty_u = int(m.group(1)), m.group(2)
    warranty_months = None
    if warranty_n is not None:
        warranty_months = warranty_n if warranty_u == "個月" else round(warranty_n / 30, 1)
    validity = _num_plain(_first(r"有效期[^\d]{0,20}?(\d+)\s*天", flat))

    payment = None
    labels = {"保固金", "保修", "保修期", "保修承諾", "保險", "標書有效期", "報價有效期", "施工期", "有效期"}
    for key in ("付款條款", "付款辦法"):
        if key in lines:
            k = lines.index(key)
            parts = [lines[k + 1]]
            if k + 2 < len(lines) and lines[k + 2] not in labels and len(lines[k + 2]) <= 12:
                parts.append(lines[k + 2])  # wrapped continuation of the same cell
            payment = "".join(parts)
            break

    # short label from the file name: "Tender_B_快達裝修.pdf" -> "B · 快達裝修"
    m_lab = re.match(r"Tender_([A-Za-z0-9]+)_(.+)$", pdf.stem)
    label = f"{m_lab.group(1)} · {m_lab.group(2)}" if m_lab else pdf.stem

    notes = [l for l in lines if NOTE_LINE.match(l) or any(k in l for k in NOTE_KEYS)]
    # keep notes that carry content; de-duplicate while preserving order
    seen, clean_notes = set(), []
    for n in notes:
        if len(n) > 6 and n not in seen:
            seen.add(n); clean_notes.append(n)

    return {
        "file": pdf.name,
        "label": label,
        "company": lines[0] if lines else pdf.stem,
        "date": _first(r"日期[：:]\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{4}|[0-9]{4} 年 [0-9]{1,2} 月 [0-9]{1,2} 日)", flat),
        "total_hkd": total,
        "line_items": items,
        "line_items_sum_hkd": sum(it["amount_hkd"] or 0 for it in items),
        "duration_weeks": int(weeks) if weeks else None,
        "deposit_pct": int(deposit) if deposit is not None else None,
        "payment_terms": payment,
        "warranty_months": warranty_months,
        "validity_days": validity,
        "notes": clean_notes,
        "text_chars": len(text),
    }


def _num_plain(s: str | None) -> int | None:
    return int(s) if s else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", default="demo-data/tenders", help="folder containing tender PDFs")
    ap.add_argument("--out", default="outputs/tenders_extracted.json")
    a = ap.parse_args()

    folder = _resolve(a.input)
    pdfs = sorted(folder.glob("*.pdf"))
    if not pdfs:
        sys.exit(f"no PDF found in {folder}")
    tenders = [parse_tender(p) for p in pdfs]

    out = _resolve(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"source_folder": str(folder), "tenders": tenders}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"EXTRACT  {len(tenders)} tender(s) from {folder}")
    for t in tenders:
        chk = "OK" if t["total_hkd"] == t["line_items_sum_hkd"] else "CHECK"
        print(f"  - {t['label']:<18} total HK${t['total_hkd']:,}  items={len(t['line_items'])} sum={t['line_items_sum_hkd']:,} [{chk}]  notes={len(t['notes'])}")
    print(f"  -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
