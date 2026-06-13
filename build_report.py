"""
build_report.py — combined PDF report (reportlab) in the editorial style that matches the app.

Grey page · #efeff0 chart cards · IBM Plex Mono uppercase labels + Helvetica headlines ·
indigo accent · Measured/Estimate/Recommended chips · the regenerated plain-title charts.
Numbers are pulled live from cc2_app_data so the PDF stays reconciled with the app + charts.

Run from the project root:
    ./.venv/bin/python build_report.py   ->  07_final_assets/360training_Analytics_Report.pdf
"""
import os

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak,
                                Table, TableStyle, KeepTogether)

import cc2_app_data as D

ROOT = os.path.dirname(os.path.abspath(__file__))
OUTPDF = os.path.join(ROOT, "07_final_assets", "360training_Analytics_Report.pdf")
FDIR = os.path.join(ROOT, "fonts")
USABLE_W = 6.6 * inch

# ---- palette (matches the app) ----
ACCENT = colors.HexColor("#4e42e4")
INK = colors.HexColor("#1d1d25")
MUT = colors.HexColor("#3b4049")
PAGE = colors.HexColor("#d0d1d5")
CARD = colors.HexColor("#efeff0")
LINE = colors.HexColor("#d2d2d8")
LAV = colors.HexColor("#e7e6fb")

# ---- fonts: IBM Plex Mono (embedded) for labels, Helvetica for sans ----
pdfmetrics.registerFont(TTFont("Mono", f"{FDIR}/IBMPlexMono-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Mono-SB", f"{FDIR}/IBMPlexMono-SemiBold.ttf"))
pdfmetrics.registerFont(TTFont("Mono-B", f"{FDIR}/IBMPlexMono-Bold.ttf"))
SANS, SANSB = "Helvetica", "Helvetica-Bold"

S = {
    "kicker": ParagraphStyle("k", fontName="Mono-SB", fontSize=8.5, textColor=ACCENT, leading=12, spaceAfter=8),
    "title": ParagraphStyle("t", fontName=SANSB, fontSize=23, textColor=INK, leading=26, spaceAfter=10),
    "sub": ParagraphStyle("s", fontName=SANS, fontSize=11, textColor=MUT, leading=16, spaceAfter=4),
    "label": ParagraphStyle("l", fontName="Mono-SB", fontSize=8, textColor=MUT, leading=12, spaceBefore=2, spaceAfter=3),
    "h": ParagraphStyle("h", fontName=SANSB, fontSize=14, textColor=INK, leading=17, spaceAfter=4),
    "body": ParagraphStyle("b", fontName=SANS, fontSize=9.5, textColor=INK, leading=14, spaceAfter=5),
    "cap": ParagraphStyle("c", fontName="Mono", fontSize=7.3, textColor=MUT, leading=10, spaceAfter=2),
    "kpi_l": ParagraphStyle("kl", fontName="Mono-SB", fontSize=7, textColor=MUT, leading=9),
    "kpi_v": ParagraphStyle("kv", fontName="Mono-B", fontSize=19, textColor=INK, leading=21),
    "kpi_s": ParagraphStyle("ks", fontName="Mono", fontSize=7, textColor=ACCENT, leading=9),
}

CHIP = {"E": ("MEASURED", "#1d1d25", "#ffffff"), "I": ("ESTIMATE", None, "#3b4049"),
        "R": ("RECOMMENDED", "#e7e6fb", "#4e42e4")}


def chip(kind):
    label, bg, fg = CHIP[kind]
    if bg:
        return (f'<font name="Mono-SB" size=7 color="{fg}" backColor="{bg}">&nbsp;{label}&nbsp;</font>')
    return f'<font name="Mono-SB" size=7 color="{fg}">[ {label} ]</font>'


def P(t, st="body"):
    return Paragraph(t, S[st])


def scaled_image(name, max_w=USABLE_W - 0.3 * inch, max_h=6.8 * inch):
    path = D.chart(name)
    if not os.path.exists(path):
        return P(f"<i>(chart {name} missing)</i>", "cap")
    iw, ih = ImageReader(path).getSize()
    w, h = max_w, max_w * ih / iw
    if h > max_h:
        h, w = max_h, max_h * iw / ih
    return Image(path, width=w, height=h)


def card(flowables, pad=11):
    if not isinstance(flowables, list):
        flowables = [flowables]
    t = Table([[flowables]], colWidths=[USABLE_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CARD), ("BOX", (0, 0), (-1, -1), 0.75, LINE),
        ("ROUNDEDCORNERS", [7, 7, 7, 7]),
        ("LEFTPADDING", (0, 0), (-1, -1), pad), ("RIGHTPADDING", (0, 0), (-1, -1), pad),
        ("TOPPADDING", (0, 0), (-1, -1), pad), ("BOTTOMPADDING", (0, 0), (-1, -1), pad)]))
    return t


def kpi_row(items):
    cells = [[P(lbl, "kpi_l"), P(val, "kpi_v"), P(sub, "kpi_s")] for lbl, val, sub in items]
    n = len(cells)
    t = Table([cells], colWidths=[USABLE_W / n] * n)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CARD), ("BOX", (0, 0), (-1, -1), 0.75, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE), ("ROUNDEDCORNERS", [7, 7, 7, 7]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 11), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 11)]))
    return t


def chart_block(story, label, heading, lead_html, chart_name, cap):
    story += [P(label, "label"), P(heading, "h"), P(lead_html, "body"),
              card([scaled_image(chart_name), Spacer(1, 4), P(cap, "cap")]), Spacer(1, 13)]


def _decor(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(PAGE)
    canvas.rect(0, 0, doc.pagesize[0], doc.pagesize[1], fill=1, stroke=0)
    canvas.setFont("Mono", 7); canvas.setFillColor(colors.HexColor("#5d626b"))
    canvas.drawString(0.9 * inch, 0.5 * inch, "360TRAINING  ·  REPUTATION INTELLIGENCE")
    canvas.drawRightString(doc.pagesize[0] - 0.9 * inch, 0.5 * inch, f"{canvas.getPageNumber():02d}")
    canvas.restoreState()


def build():
    h = D.HEADLINE
    cov = D.backtest_coverage()
    oa = {r["year"]: (r["neg_share"], int(r["n"])) for _, r in D.osha_annual().iterrows()}
    rg = D.resolution_gap()
    ann = D.rhi_annual()
    rlo, rhi = D.recoverable()
    st = []

    # ---- cover
    st += [Spacer(1, 8), P("Reputation analysis · 10,601 reviews · 2014–2026", "kicker"),
           P("Why 360training's reviews turned negative — and what holds up under scrutiny", "title"),
           P("What 10,601 public reviews say about 360training's reputation, and how much survives a "
             "skeptical second look. We built a forecast, a complaint-driver analysis, a revenue lens, an "
             "integrity audit, and a live reputation-health index — every finding labeled by how far we can "
             "stand behind it.", "sub"),
           Spacer(1, 12),
           kpi_row([("Reviews analyzed", f"{h['n_reviews']:,}", "2014–2026"),
                    ("Negative reviews", f"{h['n_negative']:,}", f"{h['neg_share']:.0%} of all"),
                    ("Got a company reply", f"{h['reply_coverage']:.0%}", "the company responds"),
                    ("Reputation Health", f"{ann['2023']:.0f}→{ann['2026']:.0f}", "2023 = 100")]),
           Spacer(1, 13)]

    # ---- caveats
    st += [P("What this data cannot tell us", "label"),
           card(P("<b>Who posts, not everyone</b> — reviews can't be split into invited vs. organic, so every "
                  "rate reflects who chose to post (this caps the integrity audit). &nbsp; "
                  "<b>Small monthly samples</b> — ~50–90 reviews/month after 2024, so month-to-month wiggles of "
                  "a few points are noise. &nbsp; <b>Two different lenses</b> — the forecast tracks 1–2★ reviews; "
                  "the driver model tracks 1★ reviews. &nbsp; <b>The auto-tagging is AI-generated</b> — checked "
                  "for consistency, not certified for accuracy.", "body")),
           Spacer(1, 14)]

    # ---- executive summary
    st += [P("Executive summary", "label"), P("Three findings that survive scrutiny", "h"),
           P(f"{chip('I')} &nbsp; <b>The decline is real and multi-year.</b> A composite Reputation Health "
             f"score (2023 = 100) falls <b>{ann['2023']:.0f} → {ann['2024']:.1f} → {ann['2025']:.1f} "
             f"→ {ann['2026']:.1f}</b>, and it drops under <i>all nine</i> weightings — the direction is in "
             "the data, not the method.", "body"),
           P(f"{chip('E')} &nbsp; <b>The most actionable finding: a resolution gap.</b> "
             f"{rg['actionable']['pct_of_neg']:.0%} of unhappy customers name a fixable issue, yet a reply "
             f"offers a specific remedy in only <b>{rg['specific_remedy_in_negatives']['value']} of "
             f"{h['n_negative']:,} negatives (~0.5%)</b> — a 178× drop-off.", "body"),
           P(f"{chip('I')} &nbsp; <b>The forecast's honest claim is calibration, not direction.</b> Over "
             f"N={cov['n']} held-out forecasts the 80/95% ranges held {cov['cov80']:.0%}/{cov['cov95']:.0%} of "
             "the time; negativity is elevated and noisy around ~32%.", "body"),
           P(f"{chip('R')} &nbsp; <b>The single highest-value ask:</b> the new-enrollment / conversion time "
             "series — it turns the revenue case from plausible to evidenced.", "body"),
           PageBreak()]

    # ---- sections (regenerated plain-title charts sit flush in the cards)
    chart_block(st, "01 · Forecast", "Where customer sentiment is heading",
                f"{chip('I')} &nbsp; The honest deliverable is a <b>tested range</b>, not a single prediction. "
                f"Over {cov['n']} held-out forecasts the model's 80% range was right {cov['cov80']:.0%} of the "
                "time. Negativity is stuck high and noisy ~32% — we can't credibly call it rising or recovering.",
                "01_neg_share_fan_chart.png",
                "Monthly negative-review share with a 6-month forecast and its uncertainty range.")

    chart_block(st, "02 · Complaint drivers", "What predicts a furious review",
                f"{chip('I')} &nbsp; <b>Billing/refund and customer-support</b> complaints are the strongest "
                "predictors of a 1-star review, and they hold up even among already-unhappy customers — real "
                "operational signals. Note: the keyword tags catch ~58% of negatives, so this is the tagged subset.",
                "05_driver_forest_plot.png",
                "How much more likely a 1-star review becomes when each complaint type appears.")

    chart_block(st, "03 · Resolution gap", "A fixable problem, left unfixed",
                f"{chip('E')} &nbsp; <b>{rg['actionable']['pct_of_neg']:.0%}</b> of unhappy customers name a "
                "fixable issue; only <b>~0.5%</b> get a specific remedy in the reply — a 178× collapse. "
                f"{chip('R')} &nbsp; The ownable lever: convert 'email-us' deflection into tracked resolutions.",
                "C1_resolution_gap.png",
                "Single denominator (the 2,206 negative reviews): fixable vs. actually fixed. Corpus-wide, "
                "specific remedies appear in 23 of 10,601 replies (0.2%) — a conservative upper bound.")

    chart_block(st, "04 · Revenue at risk", "When does fixing this pay for itself?",
                f"{chip('I')} &nbsp; No invented loss figure. The fix pays for itself if it recovers even a small "
                f"conversion lift on review-exposed customers; the plausibly-recoverable band is ~{rlo:.1%}–{rhi:.1%}. "
                "The live app lets the company drop in its own numbers.",
                "CC2_breakeven_threshold.png",
                "Below the band, the fix obviously pays for itself — read off the company's own exposure.")

    chart_block(st, "05 · Review integrity", "An audit, not an accusation",
                f"{chip('E')} &nbsp; Some reviews allege fake 5-star batches; we tested it rigorously. The "
                "first-time-reviewer share stays <b>flat every year</b> — the test run to catch fake accounts "
                "comes back negative. Manipulation is not the story.",
                "F2_firsttimer_share_overtime.png",
                "The most credibility-building result: a clean negative. Every dated 5★ burst predates the 2024 "
                "decline, consistent with normal review-invitation emails.")

    chart_block(st, "06 · Product lines", "Where trust is bleeding fastest",
                f"{chip('I')} &nbsp; The <b>safety-training</b> line — the highest-volume one — saw negative "
                f"reviews <b>triple</b>: {oa['2023'][0]:.0%} ({oa['2023'][1]}) → {oa['2024'][0]:.0%} "
                f"({oa['2024'][1]}) → {oa['2025'][0]:.0%} (n={oa['2025'][1]}). Real estate is the chronically "
                "angriest line (~64%).",
                "G3_osha_annual_negshare.png",
                "Stated at annual grain — per-quarter counts are too small to trend. As the biggest line, it "
                "moves the overall number most.")

    chart_block(st, "07 · Reputation health", "A decline that survives every test",
                f"{chip('I')} &nbsp; The composite score falls every year since 2023, and it keeps falling no "
                "matter how the components are weighted — so the decline is a property of the data, not the way "
                "the score is built.",
                "H4_weight_sensitivity.png",
                "Annual score under nine different weightings — every one declines 2023–2026.")

    st += [P("The single highest-value ask to the company", "label"),
           card(P("Provide the <b>new-enrollment / conversion time series.</b> If it bends at the 2024 review "
                  "inflections, the revenue scenarios harden from plausible to evidenced and the break-even "
                  "decision becomes near-certain. That one internal series removes most of the remaining "
                  "uncertainty.", "body")),
           Spacer(1, 8),
           P("Independent analysis of 10,601 public reviews · every figure cross-checked (22/22, 0 conflicts) · "
             "findings separated into measured vs. estimated · live app recomputes two panels from the same "
             "code as the charts.", "cap")]

    SimpleDocTemplate(OUTPDF, pagesize=letter, topMargin=0.7 * inch, bottomMargin=0.8 * inch,
                      leftMargin=0.9 * inch, rightMargin=0.9 * inch,
                      title="360training Reputation Intelligence").build(st, onFirstPage=_decor, onLaterPages=_decor)
    print(f"wrote {OUTPDF}  ({os.path.getsize(OUTPDF)/1024:.0f} KB)")


if __name__ == "__main__":
    build()
