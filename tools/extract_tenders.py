#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""EXTRACT — read every tender PDF in a folder and write structured JSON.

Deterministic: regex over the PDF text layer. No model, no network, and
NOTHING TO INSTALL — the text layer is read with whichever library is already
present, in this order: PyMuPDF (fitz) → pypdf → pdfminer.six → `pdftotext`.
Force one with TENDER_PDF_BACKEND=fitz|pypdf|pdfminer|pdftotext.

Usage:
    python tools/extract_tenders.py --input input/tenders --out outputs/tenders_extracted.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

AMOUNT = re.compile(r"^\d{1,3}(?:,\d{3})+$")
AMOUNT_TAIL = re.compile(r"^(.*?)\s+(\d{1,3}(?:,\d{3})+)$")
ITEM_NO = re.compile(r"^(\d{1,2}|P\d)$")
ITEM_INLINE = re.compile(r"^(\d{1,2}|P\d)\s+(.+)$")
NOTE_LINE = re.compile(r"^\d{1,2}[.、]\s*")
NOTE_KEYS = ("不包括", "不含", "另行", "實報實銷", "暫定數", "前提", "波動", "自行委聘", "恕不負責")
CJK = r"一-鿿"


# ----------------------------------------------------------------------------
# text layer — backend chain
# ----------------------------------------------------------------------------
def _norm(line: str) -> str:
    """NFKC folds Kangxi-radical glyph variants (⼯ ⽇ ⾒ ⾦) that some readers emit
    for Chrome-generated PDFs back to the ordinary ideographs, and folds
    full-width digits / punctuation, so keywords match whatever the reader."""
    s = unicodedata.normalize("NFKC", line)
    s = re.sub(rf"(?<=[{CJK}])\s+(?=[{CJK}])", "", s)  # "精 藝 室 內" -> "精藝室內"
    return re.sub(r"\s+", " ", s).strip()


def _read_fitz(pdf: Path) -> str:
    import fitz  # PyMuPDF
    return "\n".join(p.get_text() for p in fitz.open(pdf))


def _read_pypdf(pdf: Path) -> str:
    from pypdf import PdfReader
    return "\n".join((pg.extract_text() or "") for pg in PdfReader(str(pdf)).pages)


def _read_pdfminer(pdf: Path) -> str:
    from pdfminer.high_level import extract_text
    from pdfminer.layout import LAParams
    return extract_text(str(pdf), laparams=LAParams(boxes_flow=None))


def _read_pdftotext(pdf: Path) -> str:
    exe = shutil.which("pdftotext")
    if not exe:
        raise RuntimeError("pdftotext not on PATH")
    return subprocess.run([exe, "-layout", "-enc", "UTF-8", str(pdf), "-"], capture_output=True, text=True,
                          encoding="utf-8", timeout=60).stdout


BACKENDS = [("fitz", _read_fitz), ("pypdf", _read_pypdf), ("pdfminer", _read_pdfminer), ("pdftotext", _read_pdftotext)]


def read_pdf_variants(pdf: Path):
    """Yield (lines, backend) for every reader that is installed and returns text.
    The caller parses each and keeps the first whose line items reconcile with
    the stated total — so a reader with an awkward layout never wins by accident."""
    forced = os.environ.get("TENDER_PDF_BACKEND")
    chain = [b for b in BACKENDS if not forced or b[0] == forced]
    errors, produced = [], 0
    for name, fn in chain:
        try:
            text = fn(pdf)
        except Exception as e:  # library missing or failed — try the next one
            errors.append(f"{name}: {e.__class__.__name__}")
            continue
        lines = [_norm(l) for l in text.splitlines()]
        lines = [l for l in lines if l]
        if lines:
            produced += 1
            yield lines, name
    if not produced:
        sys.exit("no PDF text reader available (" + "; ".join(errors) + "). Install one of: pymupdf, pypdf, pdfminer.six, or poppler pdftotext.")


# ----------------------------------------------------------------------------
# parsing helpers
# ----------------------------------------------------------------------------
def _num(s: str | None) -> int | None:
    return int(s.replace(",", "")) if s else None


def _first(pattern: str, text: str, group: int = 1):
    m = re.search(pattern, text)
    return m.group(group) if m else None


def parse_items(lines: list[str]) -> list[dict]:
    """Assemble priced line items regardless of how the reader laid out the table:
       fitz      -> "1" / "desc" / "96,000"            (one cell per line)
       pdfminer  -> "1" / "96,000" / "desc"            (columns re-ordered)
       pypdf     -> "1 desc 96,000"                     (whole row on one line)
       wrapped   -> "P3 desc part…" / "cont." / "742,000" (any of the above, desc wrapped)
    """
    items, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]
        # (a) bare item number: gather amount + desc from the next few lines, any order
        if ITEM_NO.match(line):
            window = lines[i + 1:i + 5]
            amount_idx = next((k for k, w in enumerate(window) if AMOUNT.match(w)), None)
            if amount_idx is not None:
                before = [w for w in window[:amount_idx] if not ITEM_NO.match(w)]
                if before:
                    desc, consumed = "".join(before), amount_idx + 1
                elif amount_idx + 1 < len(window) and not ITEM_NO.match(window[amount_idx + 1]) and not AMOUNT.match(window[amount_idx + 1]):
                    desc, consumed = window[amount_idx + 1], amount_idx + 2   # pdfminer: desc after amount
                else:
                    desc, consumed = None, 0
                if desc:
                    items.append({"no": line, "desc": desc, "amount_hkd": _num(window[amount_idx])})
                    i += 1 + consumed
                    continue
        # (b) whole row on one line, possibly with the amount wrapped onto a following line
        m = ITEM_INLINE.match(line)
        if m and not AMOUNT.match(line):
            no, rest = m.group(1), m.group(2)
            mt = AMOUNT_TAIL.match(rest)
            if mt:
                items.append({"no": no, "desc": mt.group(1).strip(), "amount_hkd": _num(mt.group(2))})
                i += 1
                continue
            desc_parts, j, done = [rest], i + 1, False
            while j < min(n, i + 4):
                nxt = lines[j]
                if AMOUNT.match(nxt):
                    items.append({"no": no, "desc": "".join(desc_parts), "amount_hkd": _num(nxt)}); done = True; break
                mt2 = AMOUNT_TAIL.match(nxt)
                if mt2 and not ITEM_INLINE.match(nxt):
                    desc_parts.append(mt2.group(1).strip())
                    items.append({"no": no, "desc": "".join(desc_parts), "amount_hkd": _num(mt2.group(2))}); done = True; break
                if ITEM_INLINE.match(nxt) or ITEM_NO.match(nxt):
                    break
                desc_parts.append(nxt); j += 1
            if done:
                i = j + 1
                continue
        i += 1
    return items


def parse_payment(lines: list[str]) -> str | None:
    labels = ("保固金", "保修", "保修期", "保修承諾", "保險", "標書有效期", "報價有效期", "施工期", "有效期")
    for key in ("付款條款", "付款辦法"):
        for k, l in enumerate(lines):
            if l.startswith(key):   # label alone on its line, or label glued to the value
                parts = [] if l == key else [l[len(key):].lstrip(" :")]
                j = k + 1
                while j < len(lines) and j <= k + 3:
                    nxt = lines[j]
                    if nxt in labels or nxt.startswith(tuple(x + " " for x in labels)):
                        break
                    parts.append(nxt); j += 1
                    if len(nxt) > 12:      # a full line; anything after is a new cell
                        break
                if parts:
                    return "".join(parts)
    return None


def parse_tender(pdf: Path) -> dict:
    """Parse with each available reader in turn; keep the first result whose line
    items add up to the stated total, otherwise the best-scoring one."""
    best, best_score = None, -1
    for lines, backend in read_pdf_variants(pdf):
        t = _parse_lines(pdf, lines, backend)
        items_ok = bool(t["line_items"])
        if items_ok and t["total_source"] == "stated" and t["total_hkd"] == t["line_items_sum_hkd"]:
            return t                      # reconciles — done
        score = (2 if items_ok and t["total_source"] == "sum_of_items" else 1 if items_ok else 0)
        if score > best_score:
            best, best_score = t, score
    return best


def _parse_lines(pdf: Path, lines: list[str], backend: str) -> dict:
    flat = " ".join(lines)

    items = parse_items(lines)
    total = _num(_first(r"(?:投標總價|總價)[^\d]{0,40}?(\d{1,3}(?:,\d{3})+)", flat))
    total_source = "stated"
    if total is None and items:   # some readers separate the 總價 label from its figure
        total, total_source = sum(it["amount_hkd"] or 0 for it in items), "sum_of_items"

    weeks = _first(r"(\d+)\s*個?星期", flat)
    deposit = _first(r"(\d+)\s*%\s*訂金", flat)
    if deposit is None and re.search(r"(毋須|無須|不需|免)\s*訂\s*金", flat):
        deposit = "0"
    warranty_months = None
    m = re.search(r"保修[^\d]{0,30}?(\d+)\s*(個月|天|日)", flat)
    if m:
        v, unit = int(m.group(1)), m.group(2)
        warranty_months = v if unit == "個月" else round(v / 30, 1)
    validity = _first(r"有效期[^\d]{0,20}?(\d+)\s*天", flat)

    m_lab = re.match(r"Tender_([A-Za-z0-9]+)_(.+)$", pdf.stem)
    label = f"{m_lab.group(1)} · {m_lab.group(2)}" if m_lab else pdf.stem

    seen, notes = set(), []
    for l in lines:
        if (NOTE_LINE.match(l) or any(k in l for k in NOTE_KEYS)) and len(l) > 6 and l not in seen:
            seen.add(l); notes.append(l)

    return {
        "file": pdf.name,
        "label": label,
        "company": lines[0] if lines else pdf.stem,
        "date": _first(r"日期[:：]\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{4}|[0-9]{4} 年 [0-9]{1,2} 月 [0-9]{1,2} 日)", flat),
        "total_hkd": total,
        "total_source": total_source,
        "line_items": items,
        "line_items_sum_hkd": sum(it["amount_hkd"] or 0 for it in items),
        "duration_weeks": int(weeks) if weeks else None,
        "deposit_pct": int(deposit) if deposit is not None else None,
        "payment_terms": parse_payment(lines),
        "warranty_months": warranty_months,
        "validity_days": int(validity) if validity else None,
        "notes": notes,
        "pdf_reader": backend,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", default="input/tenders", help="folder containing tender PDFs")
    ap.add_argument("--out", default="outputs/tenders_extracted.json")
    a = ap.parse_args()

    folder = Path(a.input) if Path(a.input).is_absolute() else ROOT / a.input
    pdfs = sorted(folder.glob("*.pdf"))
    if not pdfs:
        sys.exit(f"no PDF found in {folder}")
    tenders = [parse_tender(p) for p in pdfs]

    out = Path(a.out) if Path(a.out).is_absolute() else ROOT / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"source_folder": str(folder), "tenders": tenders}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"EXTRACT  {len(tenders)} tender(s) from {folder}  [reader: {tenders[0]['pdf_reader']}]")
    for t in tenders:
        tot = f"HK${t['total_hkd']:,}" if t["total_hkd"] is not None else "—"
        chk = "OK" if t["total_hkd"] == t["line_items_sum_hkd"] else "CHECK"
        if t["total_source"] == "sum_of_items":
            chk = "sum-of-items"
        print(f"  - {t['label']:<18} total {tot}  items={len(t['line_items'])} sum={t['line_items_sum_hkd']:,} [{chk}]  notes={len(t['notes'])}")
    print(f"  -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
