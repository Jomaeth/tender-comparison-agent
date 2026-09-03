#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""RENDER — build the OpenDeedigital-styled comparison report (HTML) and print it to PDF.

Deterministic: templating only. The PDF is produced by headless Chrome / Edge
(found automatically; override with CHROME_PATH); if none is installed it falls
back to reportlab (built-in CJK font, nothing to download). No model, no network.
Usage:
    python tools/render_comparison_pdf.py \
        --extracted outputs/tenders_extracted.json \
        --recommendation outputs/tender_recommendation.md \
        --out-pdf outputs/tender_comparison_report.pdf
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import html
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from compare_tenders import assess  # noqa: E402  (same deterministic logic as COMPARE)


def _resolve(p: str) -> Path:
    path = Path(p)
    return path if path.is_absolute() else ROOT / path


def hk(n) -> str:
    return "—" if n is None else f"HK${n:,.0f}"


def esc(s) -> str:
    return html.escape("" if s is None else str(s))


def md_to_html(md: str) -> str:
    """Minimal Markdown → HTML for the recommendation note (paragraphs, bullets, bold)."""
    out, in_list = [], False
    for raw in md.splitlines():
        line = raw.strip()
        if line.startswith("#"):
            continue  # headings are supplied by the template
        if line.startswith(("- ", "* ")):
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append(f"<li>{esc(line[2:])}</li>")
            continue
        if in_list:
            out.append("</ul>"); in_list = False
        if line:
            out.append(f"<p>{esc(line)}</p>")
    if in_list:
        out.append("</ul>")
    h = "\n".join(out)
    return h.replace("**", "")  # keep it plain; bold markers are noise in print


def find_chrome() -> str | None:
    env = os.environ.get("CHROME_PATH")
    if env and Path(env).exists():
        return env
    cands: list[str] = []
    sysname = platform.system()
    if sysname == "Windows":
        for base in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                     os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                     os.environ.get("LocalAppData", "")):
            cands += [rf"{base}\Google\Chrome\Application\chrome.exe",
                      rf"{base}\Microsoft\Edge\Application\msedge.exe"]
    elif sysname == "Darwin":
        cands += ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"]
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "msedge"):
        p = shutil.which(name)
        if p:
            cands.append(p)
    for c in cands:
        if c and Path(c).exists():
            return c
    return None


def html_to_pdf(html_path: Path, pdf_path: Path) -> bool:
    chrome = find_chrome()
    if not chrome:
        return False
    url = html_path.resolve().as_uri()
    for headless in ("--headless=new", "--headless"):
        cmd = [chrome, headless, "--disable-gpu", "--no-pdf-header-footer",
               f"--print-to-pdf={pdf_path.resolve()}", url]
        try:
            subprocess.run(cmd, capture_output=True, timeout=90)
        except Exception:
            continue
        if pdf_path.exists() and pdf_path.stat().st_size > 1000:
            return True
    return False


def reportlab_pdf(data: dict, cfg: dict, brand: dict, recommendation_md: str | None, logo_path: Path | None, out: Path) -> bool:
    """Fallback when no Chrome/Edge is installed: same content, simpler layout, pure Python.
    Uses reportlab's built-in CJK CID font, so no font files are needed."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except Exception:
        return False
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    F = "STSong-Light"
    P, S, A, D, L = (colors.HexColor(brand[k]) for k in ("primary_color", "secondary_color", "accent_color", "dark_color", "light_color"))
    st = brand.get("status_colors", {"go": "#1F9D55", "control": "#E5A823", "stop": "#D7263D"})
    tenders = data["tenders"]
    results = [(t, assess(t, cfg)) for t in tenders]
    cheapest_l4l = min(results, key=lambda tr: tr[1]["like_for_like_hkd"])[0]["label"]
    cheapest_headline = min(tenders, key=lambda t: t["total_hkd"] or 1e12)["label"]

    h1 = ParagraphStyle("h1", fontName=F, fontSize=18, leading=22, textColor=colors.white)
    sub = ParagraphStyle("sub", fontName=F, fontSize=9.5, leading=12, textColor=colors.white)
    h2 = ParagraphStyle("h2", fontName=F, fontSize=12.5, leading=16, textColor=S, spaceBefore=10, spaceAfter=4)
    h3 = ParagraphStyle("h3", fontName=F, fontSize=10.5, leading=13, textColor=D, spaceBefore=6)
    body = ParagraphStyle("b", fontName=F, fontSize=9, leading=12, textColor=D)
    small = ParagraphStyle("s", fontName=F, fontSize=8, leading=10.5, textColor=colors.HexColor("#6B7280"))
    draft = ParagraphStyle("d", fontName=F, fontSize=9, leading=11, textColor=A)

    doc = SimpleDocTemplate(str(out), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=14 * mm, bottomMargin=16 * mm,
                            title=f"標書比較報告 — {cfg['project']}", author=brand["name"])
    story = []
    band_cells = [[Paragraph("標書比較報告", h1), ""]]
    band_cells.append([Paragraph(esc(cfg["project"]), sub), ""])
    if logo_path and logo_path.exists():
        try:
            band_cells[0][1] = Image(str(logo_path), width=40 * mm, height=6.25 * mm)
        except Exception:
            pass
    band = Table(band_cells, colWidths=[130 * mm, 52 * mm])
    band.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), S), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                              ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                              ("ALIGN", (1, 0), (1, 0), "RIGHT"), ("SPAN", (1, 0), (1, 1))]))
    story += [band, Spacer(1, 4), Paragraph("DRAFT · 待審批", draft),
              Paragraph(f"產生日期 {dt.date.today():%Y-%m-%d} · 補回項目為估算 · 基準：{esc(cfg['benchmark_source'])}", small)]

    story.append(Paragraph("一、同一比較基準", h2))
    head = ["公司", "表面總價", "補回", "可比較總成本", "工期", "訂金", "保修", "有效期", "風險"]
    rows = [head]
    for t, r in results:
        fill_sum = sum(f["benchmark_hkd"] for f in r["fills"]); wm = t["warranty_months"]
        rows.append([t["label"], hk(t["total_hkd"]), ("+ " + hk(fill_sum)) if fill_sum else "—", hk(r["like_for_like_hkd"]),
                     f"{t['duration_weeks'] or '—'} 週", f"{t['deposit_pct'] if t['deposit_pct'] is not None else '—'}%",
                     f"{wm:g} 個月" if wm is not None else "—", f"{t['validity_days'] or '—'} 天", f"{len(r['flags'])} 項"])
    tbl = Table(rows, colWidths=[34 * mm, 25 * mm, 22 * mm, 28 * mm, 14 * mm, 12 * mm, 16 * mm, 16 * mm, 14 * mm], repeatRows=1)
    ts = [("FONTNAME", (0, 0), (-1, -1), F), ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("BACKGROUND", (0, 0), (-1, 0), S),
          ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("LINEBELOW", (0, 1), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
          ("ALIGN", (1, 1), (3, -1), "RIGHT"), ("TEXTCOLOR", (3, 1), (3, -1), S), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
    for idx, (t, r) in enumerate(results, start=1):
        if t["label"] == cheapest_l4l:
            ts.append(("BACKGROUND", (0, idx), (-1, idx), L))
        c = st["stop"] if len(r["flags"]) >= 3 else (st["control"] if r["flags"] else st["go"])
        ts.append(("TEXTCOLOR", (8, idx), (8, idx), colors.HexColor(c)))
    tbl.setStyle(TableStyle(ts))
    story += [tbl, Paragraph(f"表面最平：{esc(cheapest_headline)} · 補回不包括項目後最平：{esc(cheapest_l4l)}", small)]

    story.append(Paragraph("二、每份標書：補回明細與風險條款", h2))
    for t, r in results:
        story.append(Paragraph(f"{esc(t['label'])} — 表面 {hk(t['total_hkd'])} → 可比較 {hk(r['like_for_like_hkd'])}", h3))
        if r["fills"]:
            for f in r["fills"]:
                story.append(Paragraph(f"• {esc(f['label'])}：+{hk(f['benchmark_hkd'])}（估算 · 基準 {esc(f['benchmark_ref'])}）— 證據：「{esc(f['evidence'][:60])}」", body))
        else:
            story.append(Paragraph("• 補回項目：無 — 分項已覆蓋全部基準範圍", body))
        story.append(Paragraph("風險條款：" + ("；".join(esc(x) for x in r["flags"]) if r["flags"] else "未見"), body))
        if t["payment_terms"]:
            story.append(Paragraph("付款：" + esc(t["payment_terms"]), small))

    story.append(Paragraph("三、建議（初稿）", h2))
    if recommendation_md:
        for raw in recommendation_md.splitlines():
            line = raw.strip().replace("**", "")
            if not line or line.startswith("#"):
                continue
            story.append(Paragraph(("• " + line[2:]) if line.startswith(("- ", "* ")) else line, body))
    else:
        story.append(Paragraph("（建議初稿待 agent 依 SKILL.md 第 3 步填寫）", small))

    story += [Spacer(1, 8), Paragraph("審批關卡 · Human-IN — 本報告不構成中標決定。決定人請確認補回估算、向投標者澄清（由人發出）、然後決定並簽名。", body)]
    sig = Table([["審核人 / 決定人", "簽名", "日期"]], colWidths=[60 * mm, 60 * mm, 60 * mm])
    sig.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), F), ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("LINEABOVE", (0, 0), (-1, 0), 0.6, D), ("TOPPADDING", (0, 0), (-1, -1), 14)]))
    story += [Spacer(1, 10), sig, Spacer(1, 6), Paragraph(f"{esc(brand['name'])} · Tender Comparison Agent · {esc(brand.get('footer', ''))}", small)]
    doc.build(story)
    return out.exists() and out.stat().st_size > 1000


def build_html(data: dict, cfg: dict, brand: dict, recommendation_md: str | None, logo_b64: str | None) -> str:
    tenders = data["tenders"]
    results = [(t, assess(t, cfg)) for t in tenders]
    cheapest_headline = min(tenders, key=lambda t: t["total_hkd"] or 1e12)["label"]
    cheapest_l4l = min(results, key=lambda tr: tr[1]["like_for_like_hkd"])[0]["label"]
    most_flags = max(results, key=lambda tr: len(tr[1]["flags"]))[0]["label"]
    P, S, A, D, L = (brand["primary_color"], brand["secondary_color"], brand["accent_color"],
                     brand["dark_color"], brand["light_color"])
    st = brand.get("status_colors", {"go": "#1F9D55", "control": "#E5A823", "stop": "#D7263D"})
    today = dt.date.today().strftime("%Y-%m-%d")

    rows = []
    for t, r in results:
        fill_sum = sum(f["benchmark_hkd"] for f in r["fills"])
        is_l4l = t["label"] == cheapest_l4l
        is_head = t["label"] == cheapest_headline
        wm = t["warranty_months"]
        flag_cls = "stop" if len(r["flags"]) >= 3 else ("control" if r["flags"] else "go")
        rows.append(f"""
        <tr class="{'hl' if is_l4l else ''}">
          <td class="co">{esc(t['label'])}</td>
          <td class="num">{hk(t['total_hkd'])}{' <span class="tag">表面最平</span>' if is_head else ''}</td>
          <td class="num">{('+ ' + hk(fill_sum)) if fill_sum else '—'}</td>
          <td class="num strong">{hk(r['like_for_like_hkd'])}{' <span class="tag ok">可比較最平</span>' if is_l4l else ''}</td>
          <td>{t['duration_weeks'] or '—'} 週</td>
          <td>{t['deposit_pct'] if t['deposit_pct'] is not None else '—'}%</td>
          <td>{(f'{wm:g} 個月' if wm is not None else '—')}</td>
          <td>{t['validity_days'] or '—'} 天</td>
          <td><span class="pill {flag_cls}">{len(r['flags'])} 項</span></td>
        </tr>""")

    cards = []
    for t, r in results:
        fills = "".join(
            f"<li><b>{esc(f['label'])}</b>：+{hk(f['benchmark_hkd'])}<span class='muted'>（估算 · 基準 {esc(f['benchmark_ref'])}）</span>"
            f"<div class='evidence'>證據：「{esc(f['evidence'][:70])}」</div></li>" for f in r["fills"]
        ) or "<li class='muted'>無 —— 分項已覆蓋全部基準範圍</li>"
        flags = "".join(f"<li>{esc(x)}</li>" for x in r["flags"]) or "<li class='muted'>未見</li>"
        cards.append(f"""
        <section class="card">
          <h3>{esc(t['label'])} <span class="muted small">{esc(t['company'])}</span></h3>
          <div class="kv"><span>表面總價</span><b>{hk(t['total_hkd'])}</b><span>可比較總成本</span><b>{hk(r['like_for_like_hkd'])}</b></div>
          <div class="two">
            <div><h4>補回不包括項目</h4><ul>{fills}</ul></div>
            <div><h4>風險條款</h4><ul>{flags}</ul><h4>付款</h4><p class="small">{esc(t['payment_terms'] or '—')}</p></div>
          </div>
        </section>""")

    rec_html = md_to_html(recommendation_md) if recommendation_md else \
        "<p class='muted'>（建議初稿待 agent 依 SKILL.md 第 3 步填寫）</p>"
    logo_img = f'<img class="logo" src="data:image/png;base64,{logo_b64}" alt="{esc(brand["name"])}">' if logo_b64 else ""

    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<title>標書比較報告 — {esc(cfg['project'])}</title>
<style>
  @page {{ size: A4; margin: 14mm 14mm 16mm; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: {brand['font_stack']}; color: {D}; margin: 0; font-size: 10.5pt; line-height: 1.45; }}
  .band {{ background: linear-gradient(90deg, {S} 0%, {P} 100%); color: #fff; padding: 14px 18px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; }}
  .band h1 {{ margin: 0; font-size: 20pt; font-weight: 800; letter-spacing: .02em; }}
  .band .sub {{ margin-top: 4px; font-size: 10pt; opacity: .95; }}
  .logo {{ height: 34px; background: #fff; padding: 5px 9px; border-radius: 6px; }}
  .draft {{ display: inline-block; margin-top: 10px; background: {L}; color: {A}; border: 1.5px solid {A}; font-weight: 800; padding: 3px 10px; border-radius: 4px; letter-spacing: .12em; font-size: 9pt; }}
  h2 {{ color: {S}; font-size: 13pt; margin: 18px 0 8px; padding-left: 10px; border-left: 5px solid {P}; }}
  h3 {{ margin: 0 0 4px; font-size: 11.5pt; color: {D}; }}
  h4 {{ margin: 8px 0 4px; font-size: 9.5pt; color: {P}; text-transform: uppercase; letter-spacing: .06em; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 9.5pt; }}
  th {{ background: {S}; color: #fff; padding: 7px 8px; text-align: left; font-weight: 700; }}
  td {{ padding: 7px 8px; border-bottom: 1px solid #E5E7EB; vertical-align: top; }}
  tr.hl td {{ background: {L}; }}
  td.co {{ font-weight: 700; white-space: nowrap; }}
  td.num {{ text-align: right; white-space: nowrap; }}
  td.strong {{ font-weight: 800; color: {S}; }}
  .tag {{ display: inline-block; font-size: 7.5pt; font-weight: 700; color: {A}; border: 1px solid {A}; border-radius: 3px; padding: 0 5px; margin-left: 5px; vertical-align: middle; }}
  .tag.ok {{ color: {st['go']}; border-color: {st['go']}; }}
  .pill {{ display: inline-block; padding: 1px 8px; border-radius: 10px; color: #fff; font-weight: 700; font-size: 8.5pt; }}
  .pill.go {{ background: {st['go']}; }} .pill.control {{ background: {st['control']}; }} .pill.stop {{ background: {st['stop']}; }}
  .meta {{ font-size: 9pt; color: #6B7280; margin: 6px 0 0; }}
  .card {{ border: 1px solid #E5E7EB; border-top: 4px solid {P}; border-radius: 8px; padding: 10px 12px; margin: 8px 0; page-break-inside: avoid; }}
  .kv {{ display: grid; grid-template-columns: auto 1fr auto 1fr; gap: 4px 10px; font-size: 9.5pt; margin: 4px 0 6px; }}
  .kv span {{ color: #6B7280; }} .kv b {{ color: {S}; }}
  .two {{ display: grid; grid-template-columns: 1.25fr 1fr; gap: 12px; }}
  ul {{ margin: 2px 0; padding-left: 16px; }} li {{ margin-bottom: 3px; }}
  .evidence {{ font-size: 8.5pt; color: #6B7280; }}
  .muted {{ color: #6B7280; }} .small {{ font-size: 9pt; font-weight: 400; }}
  .rec {{ background: {L}; border: 1px solid {P}; border-radius: 8px; padding: 10px 14px; }}
  .gate {{ margin-top: 14px; border: 1.5px dashed {S}; border-radius: 8px; padding: 10px 14px; page-break-inside: avoid; }}
  .sig {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin-top: 10px; font-size: 9pt; }}
  .sig div {{ border-top: 1px solid {D}; padding-top: 4px; }}
  .foot {{ margin-top: 12px; font-size: 8pt; color: #6B7280; display: flex; justify-content: space-between; border-top: 1px solid #E5E7EB; padding-top: 6px; }}
</style></head><body>
<div class="band">
  <div><h1>標書比較報告</h1><div class="sub">{esc(cfg['project'])}</div></div>
  {logo_img}
</div>
<div class="draft">DRAFT · 待審批</div>
<p class="meta">產生日期 {today} · 由 tender-comparison-agent 以確定性工具產生 · 補回項目為估算，基準：{esc(cfg['benchmark_source'])}</p>

<h2>一、同一比較基準</h2>
<table>
  <tr><th>公司</th><th style="text-align:right">表面總價</th><th style="text-align:right">補回不包括項目</th><th style="text-align:right">可比較總成本</th><th>工期</th><th>訂金</th><th>保修</th><th>有效期</th><th>風險標記</th></tr>
  {''.join(rows)}
</table>
<p class="meta">表面最平：<b>{esc(cheapest_headline)}</b> · 補回不包括項目後最平：<b>{esc(cheapest_l4l)}</b> · 風險標記最多：<b>{esc(most_flags)}</b></p>

<h2>二、每份標書：補回明細與風險條款</h2>
{''.join(cards)}

<h2>三、建議（初稿）</h2>
<div class="rec">{rec_html}</div>

<div class="gate">
  <b>審批關卡 · Human-IN</b> — 本報告不構成中標決定。決定人請確認補回估算、向投標者澄清（由人發出）、然後決定並簽名。
  <div class="sig"><div>審核人 / 決定人</div><div>簽名</div><div>日期</div></div>
</div>
<div class="foot"><span>{esc(brand['name'])} · Tender Comparison Agent</span><span>{esc(brand.get('footer', ''))}</span></div>
</body></html>"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--extracted", default="outputs/tenders_extracted.json")
    ap.add_argument("--config", default="config/scope_benchmarks.json")
    ap.add_argument("--brand", default="config/brand.json")
    ap.add_argument("--recommendation", default="outputs/tender_recommendation.md")
    ap.add_argument("--out-html", default="outputs/tender_comparison_report.html")
    ap.add_argument("--out-pdf", default="outputs/tender_comparison_report.pdf")
    a = ap.parse_args()

    data = json.loads(_resolve(a.extracted).read_text(encoding="utf-8"))
    cfg = json.loads(_resolve(a.config).read_text(encoding="utf-8"))
    brand = json.loads(_resolve(a.brand).read_text(encoding="utf-8"))
    rec_path = _resolve(a.recommendation)
    rec_md = rec_path.read_text(encoding="utf-8") if rec_path.exists() else None
    logo_path = _resolve(brand.get("logo_path", ""))
    logo_b64 = base64.b64encode(logo_path.read_bytes()).decode() if logo_path.exists() else None

    out_html = _resolve(a.out_html); out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(build_html(data, cfg, brand, rec_md, logo_b64), encoding="utf-8")
    print(f"RENDER   HTML -> {out_html}")

    out_pdf = _resolve(a.out_pdf)
    force = os.environ.get("TENDER_PDF_WRITER")  # chrome | reportlab (testing / override)
    if force != "reportlab" and html_to_pdf(out_html, out_pdf):
        print(f"RENDER   PDF  -> {out_pdf}  ({out_pdf.stat().st_size // 1024} KB, A4, OpenDeedigital style, via Chrome)")
    elif reportlab_pdf(data, cfg, brand, rec_md, logo_path if logo_path.exists() else None, out_pdf):
        print(f"RENDER   PDF  -> {out_pdf}  ({out_pdf.stat().st_size // 1024} KB, A4, OpenDeedigital style, via reportlab — no Chrome found)")
    else:
        print("RENDER   PDF  -> not produced: neither Chrome/Edge nor reportlab is available. The HTML above is complete — open it and print to PDF. Do not install anything to work around this.")
    if rec_md is None:
        print("         note: recommendation file not found — PDF carries a placeholder; re-run after writing it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
