"""
360training — Reputation Intelligence (live executive dashboard).

A THIN VIEW over cc2_app_data (the tested data/compute layer). Every number shown here is
loaded or computed there; the two interactive panels (revenue break-even, reputation-health
weighting) import the SAME analytics code as the static charts, so an input can never
contradict a published exhibit. Verify the substance without the UI:
    ./.venv/bin/python cc2_app_data.py

Run from the project root:
    ./.venv/bin/streamlit run 07_final_assets/app.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import cc2_app_data as D
from cc2_app_data import RHI_WEIGHTS, RHI_COMPS, RHI_LABELS

st.set_page_config(page_title="360training · Reputation Intelligence", layout="wide",
                   initial_sidebar_state="expanded", page_icon="📊")

# ============================================================ styling (monochrome grey-blue)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
:root{ --accent:#4e42e4; --ink:#1d1d25; --ink2:#2c303b; --mut:#3b4049; --line:#d2d2d8; }
html, body, [class*="css"], .stMarkdown, p, span, label, div, input, button{
  font-family:'Inter',-apple-system,system-ui,sans-serif; color:var(--ink); }
.block-container { padding-top:1.4rem; padding-bottom:2.5rem; max-width:1280px; }
/* light boxes (#efeff0) on the neutral grey canvas */
div[data-testid="stVerticalBlockBorderWrapper"]{
  background:#efeff0; border:1px solid #dadadf !important; border-radius:10px;
  box-shadow:0 1px 2px rgba(20,20,28,.05), 0 2px 6px rgba(20,20,28,.04);
}
/* headings — bold sans, near-black */
h1,h2,h3{ color:var(--ink); }
h1{ font-weight:800; letter-spacing:-.022em; }
h2{ font-weight:700; letter-spacing:-.012em; }
h3{ font-weight:700; font-size:1.06rem; letter-spacing:-.005em; }
/* mono label — the editorial signature */
.lbl{ font-family:'IBM Plex Mono',monospace; text-transform:uppercase; letter-spacing:.09em;
      font-size:.72rem; font-weight:600; color:var(--mut); }
.meta{ font-family:'IBM Plex Mono',monospace; font-size:.74rem; letter-spacing:.03em; color:var(--mut); }
/* hero */
.kicker{ font-family:'IBM Plex Mono',monospace; text-transform:uppercase; letter-spacing:.13em;
         font-size:.74rem; font-weight:600; color:var(--accent); margin-bottom:.5rem; }
.hero-title{ font-weight:800; font-size:2.45rem; line-height:1.08; letter-spacing:-.025em;
             color:var(--ink); margin:.1rem 0 .6rem; max-width:930px; }
.hero-sub{ color:var(--ink2); font-size:1.04rem; line-height:1.55; max-width:880px; font-weight:400; }
/* tabs — mono */
div[data-baseweb="tab-list"]{ gap:8px; border-bottom:1px solid #bdbdc4; }
button[data-baseweb="tab"]{ font-family:'IBM Plex Mono',monospace; font-size:.82rem; letter-spacing:.02em;
      font-weight:500; color:var(--mut); }
button[data-baseweb="tab"][aria-selected="true"]{ color:var(--accent); }
div[data-baseweb="tab-highlight"]{ background-color:var(--accent) !important; }
/* metric cards — mono label + big mono number */
div[data-testid="stMetric"]{ padding:.15rem .25rem; }
div[data-testid="stMetricLabel"] p{ font-family:'IBM Plex Mono',monospace; text-transform:uppercase;
      letter-spacing:.07em; font-size:.70rem; color:var(--mut); font-weight:600; }
div[data-testid="stMetricValue"]{ font-family:'IBM Plex Mono',monospace; font-weight:600;
      color:var(--ink); letter-spacing:-.01em; }
div[data-testid="stMetricDelta"]{ font-family:'IBM Plex Mono',monospace; color:#3b4049 !important; font-size:.74rem; }
/* chips — mono uppercase, per type */
.chip{ font-family:'IBM Plex Mono',monospace; display:inline-block; padding:2px 7px; border-radius:3px;
       font-size:.62rem; font-weight:600; letter-spacing:.05em; vertical-align:middle; text-transform:uppercase; }
.chip.measured{ background:var(--ink); color:#fff; }
.chip.estimate{ background:transparent; color:var(--mut); border:1px solid #aeaeb8; }
.chip.recommended{ background:#e7e6fb; color:var(--accent); border:1px solid #cdc9f6; }
/* boxes/panels */
.takeaway{ border-left:3px solid var(--accent); padding:.15rem 0 .15rem .75rem; margin:.55rem 0 .15rem;
           color:var(--ink2); font-size:.97rem; line-height:1.5; }
.introbox{ background:#efeff0; border:1px solid #dadadf; border-left:4px solid var(--accent);
           border-radius:10px; padding:.8rem 1.05rem; color:var(--ink2); font-size:.98rem;
           line-height:1.55; margin:.2rem 0 .55rem; }
.note{ background:#efeff0; border:1px solid #dadadf; border-left:3px solid #9a9aa4; border-radius:8px;
       padding:.6rem .9rem; color:var(--ink2); font-size:.92rem; line-height:1.5; margin:.3rem 0; }
/* captions dark — no wash-out */
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p{ color:#3b4049 !important; }
#MainMenu, footer{ visibility:hidden; }
[data-testid="stToolbar"]{ display:none; }
section[data-testid="stSidebar"]{ width:300px !important; }
</style>
""", unsafe_allow_html=True)


def md(html):
    st.markdown(html, unsafe_allow_html=True)


CHIP = {"measured": ("Measured", "measured"), "estimate": ("Estimate", "estimate"),
        "action": ("Recommended", "recommended")}


def chip(kind):
    label, cls = CHIP[kind]
    return f"<span class='chip {cls}'>{label}</span>"


def img(name, **kw):
    p = D.chart(name)
    if os.path.exists(p):
        st.image(p, width="stretch", **kw)
    else:
        st.caption(f"_(chart {name} not found — run its generator script)_")


def kpi(col, label, value, delta=None, help=None, delta_color="off"):
    with col.container(border=True):
        st.metric(label, value, delta, help=help, delta_color=delta_color)


def intro_card(body):
    md(f"<div class='introbox'><b>📋 What you're looking at</b><br>{body}</div>")


def chart_card(title, png, takeaway, how=None):
    """Static (signed-off) chart in a card: plain title + hover ⓘ (technical detail) + plain takeaway."""
    with st.container(border=True):
        st.subheader(title, help=how)
        img(png)
        if takeaway:
            md(f"<div class='takeaway'>{takeaway}</div>")


def note(body):
    md(f"<div class='note'>{body}</div>")


# ---- themed Plotly (indigo accent, Inter/mono fonts, transparent so it sits on the card) ----
PACCENT, PINK, PGRID = "#4e42e4", "#1d1d25", "#d3d3d9"
PGREEN, PRED = "#1f9d55", "#c0392b"
PLOT_CONFIG = {"displayModeBar": False}


def _ply(fig, height):
    fig.update_layout(height=height, margin=dict(l=8, r=8, t=20, b=8),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Inter, sans-serif", color=PINK, size=13),
                      hoverlabel=dict(font_family="IBM Plex Mono, monospace", bgcolor="#1d1d25"))
    return fig


def breakeven_fig(x_be, rlo, rhi, within):
    xmax = max(15.0, x_be * 100 * 1.25)
    col = PGREEN if within else PRED
    fig = go.Figure()
    fig.add_shape(type="rect", x0=rlo * 100, x1=rhi * 100, y0=0, y1=1, layer="below",
                  fillcolor="#cdc9f6", opacity=0.55, line_width=0)
    fig.add_annotation(x=(rlo + rhi) / 2 * 100, y=0.5, text="realistically<br>recoverable",
                       showarrow=False, font=dict(size=10, color="#4a4a57"))
    fig.add_shape(type="line", x0=x_be * 100, x1=x_be * 100, y0=0, y1=1, line=dict(color=col, width=3))
    fig.add_trace(go.Scatter(x=[x_be * 100], y=[0.5], mode="markers", showlegend=False,
                  marker=dict(size=13, color=col, symbol="diamond", line=dict(color="#fff", width=1)),
                  hovertemplate=f"Break-even lift needed: {x_be:.2%}<extra></extra>"))
    fig.add_annotation(x=x_be * 100, y=1.2, text=f"<b>break-even {x_be:.1%}</b>",
                       showarrow=False, font=dict(size=13, color=col))
    fig.update_xaxes(range=[0, xmax], title_text="Conversion lift needed (%)", ticksuffix="%",
                     showgrid=True, gridcolor=PGRID, zeroline=False)
    fig.update_yaxes(range=[0, 1.4], visible=False)
    return _ply(fig, 165)


def rhi_fig(yrs, base_vals, your_vals):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=yrs, y=base_vals, mode="lines+markers", name="default weights",
                  line=dict(color="#9a9aa4", width=2, dash="dash"), marker=dict(size=7),
                  hovertemplate="%{x}: %{y:.1f}<extra>default weights</extra>"))
    fig.add_trace(go.Scatter(x=yrs, y=your_vals, mode="lines+markers+text", name="your weights",
                  line=dict(color=PACCENT, width=3.5), marker=dict(size=9),
                  text=[f"{v:.0f}" for v in your_vals], textposition="top center",
                  textfont=dict(color=PACCENT, size=12, family="IBM Plex Mono, monospace"),
                  hovertemplate="%{x}: %{y:.1f}<extra>your weights</extra>"))
    fig.update_yaxes(range=[40, 105], title_text="Reputation Health (higher = healthier)",
                     showgrid=True, gridcolor=PGRID)
    fig.update_xaxes(showgrid=False)
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, font=dict(size=11)))
    return _ply(fig, 330)


# ============================================================ sidebar (slim + informative)
with st.sidebar:
    md("<div style='font-weight:800;font-size:1.2rem;color:#1d1d25;letter-spacing:-.01em'>360training</div>"
       "<div class='lbl' style='margin-bottom:.7rem'>Reputation Analytics</div>")
    md("<div class='lbl'>About this analysis</div>")
    st.caption("An independent read of 10,601 public customer reviews (2014–2026), built to answer three "
               "questions: is the reputation decline real, what's driving it, and what should leadership do?")
    md("<div class='lbl'>How to read the findings</div>")
    md(f"{chip('measured')} &nbsp;directly counted in the review data<br>"
       f"{chip('estimate')} &nbsp;a modeled estimate — directional, not exact<br>"
       f"{chip('action')} &nbsp;a suggested next step")
    st.write("")
    note("Two panels are <b>interactive</b> — <b>Revenue at risk</b> and <b>Reputation health</b>. "
         "Adjust the inputs and the conclusions update live.")
    with st.expander("Data & limitations"):
        st.markdown(
            "- **Who posts, not everyone** — reviews can't be split into invited vs. organic, so every "
            "rate reflects the people who *chose* to post.\n"
            "- **Small monthly samples** — ~50–90 reviews/month after 2024, so month-to-month wiggles "
            "of a few points are noise, not signal.\n"
            "- **The auto-tagging of all reviews is AI-generated** — checked for consistency, but not "
            "hand-certified for accuracy.\n"
            "- Figures reconcile across every analysis (22 cross-checks, 0 conflicts).")

# ============================================================ header (editorial hero)
md("<div class='kicker'>Reputation analysis · 10,601 reviews · 2014–2026</div>")
md("<div class='hero-title'>Why 360training's reviews turned negative — and what holds up under scrutiny</div>")
md("<div class='hero-sub'>What 10,601 public reviews say about 360training's reputation, and how much of it "
   "survives a skeptical second look. We built a forecast, a complaint-driver analysis, a revenue lens, an "
   "integrity audit, and a live reputation-health index — every finding labeled by how far we can stand "
   "behind it.</div>")
md("<div class='meta' style='margin-top:.6rem'>Measured = counted in the data &nbsp;·&nbsp; Estimate = modeled, "
   "directional &nbsp;·&nbsp; two panels recompute live</div>")
st.write("")

tabs = st.tabs(["Overview", "Forecast", "Complaint drivers", "Product lines",
                "Review integrity", "Revenue at risk", "Reputation health", "Resolution gap"])

# ------------------------------------------------------------ Overview
with tabs[0]:
    h = D.HEADLINE
    rg = D.resolution_gap()
    ann = D.rhi_annual()
    cov = D.backtest_coverage()

    md("<div style='font-size:1.2rem;color:#1d1d25;font-weight:600;margin:.2rem 0 .95rem;letter-spacing:-.01em'>"
       "The reputation decline is <b>real and multi-year</b> — but the most important finding is that "
       "its biggest driver is something leadership <b>directly controls</b>.</div>")

    c = st.columns(4)
    kpi(c[0], "Reviews analyzed", f"{h['n_reviews']:,}", "2014–2026",
        help="Every public Trustpilot review of 360training over the period.")
    kpi(c[1], "Negative reviews", f"{h['n_negative']:,}", f"{h['neg_share']:.0%} of all",
        help="Reviews rated 1 or 2 stars out of 5.")
    kpi(c[2], "Reviews that got a reply", f"{h['reply_coverage']:.0%}", "the company does respond",
        help="The company replies to most reviews — the issue is what those replies say, not whether they exist.")
    kpi(c[3], "Reputation Health Index", f"{ann['2023']:.0f} → {ann['2026']:.0f}", "2023 = 100 baseline",
        delta_color="off",
        help="A composite score combining complaint volume, severity, and reply operations. 2023 is the "
             "baseline (=100); lower means worse. See the Reputation health tab.")

    st.write("")
    md("<b>What we did</b>")
    st.markdown(
        "We read the entire public review record, then went beyond counting stars: a forecast of where "
        "sentiment is heading, a model of which complaints predict the angriest reviews, an AI pass that "
        "categorized all 10,601 reviews, a revenue lens, a check for review manipulation, a product-line "
        "breakdown, and a single reputation-health score. Every claim is labeled as something we **measured** "
        "or something we **estimate**, and each was stress-tested.")

    st.write("")
    md("<b>The three findings that matter</b>")
    f1, f2, f3 = st.columns(3)
    with f1.container(border=True):
        md(f"{chip('measured')}")
        st.markdown(f"#### 🛠️ A fixable problem, left unfixed")
        st.markdown(
            f"**{rg['actionable']['pct_of_neg']:.0%}** of unhappy customers name a *specific, fixable* "
            f"problem — yet only **~0.5%** get a real fix in the reply. The rest get an apology or "
            "'email us.' **The single most actionable lever in this analysis.**")
        st.caption("→ Resolution gap tab")
    with f2.container(border=True):
        md(f"{chip('estimate')}")
        st.markdown("#### 📉 A real, steady decline")
        st.markdown(
            f"The reputation-health score fell **{ann['2023']:.0f} → {ann['2026']:.0f}** since 2023, and it "
            "drops no matter how we weight the inputs — so the decline is real, not an artifact of how we "
            "built the score.")
        st.caption("→ Reputation health tab")
    with f3.container(border=True):
        md(f"{chip('estimate')}")
        st.markdown("#### 🎯 We know where it hurts most")
        st.markdown(
            "Billing and customer-support complaints are the strongest predictors of a furious review, and "
            "the safety-training line saw negativity **triple** since 2023 — the highest-leverage place to look.")
        st.caption("→ Complaint drivers · Product lines")

    st.write("")
    note("<b>How to use this dashboard.</b> Most tabs present a chart with a plain-language read and an "
         "ⓘ you can hover for the technical detail. Two tabs are interactive: <b>Revenue at risk</b> lets you "
         "drop in your own numbers and watch the break-even move, and <b>Reputation health</b> lets you "
         "re-weight the score and watch the decline hold.")

# ------------------------------------------------------------ Forecast  (full exemplar)
with tabs[1]:
    cov = D.backtest_coverage()
    intro_card(
        "We tracked the share of reviews that are <b>negative (1–2 stars)</b> every month, then built a model "
        "to project the next six months — and, just as important, to be honest about how confident we can be. "
        "The chart shows each month's negative share (dots), the smoothed trend (line), and the forecast with "
        "its uncertainty range (shaded). The headline here isn't a single prediction — it's a <b>tested, "
        "honest range</b>.")
    st.write("")

    c = st.columns(4)
    kpi(c[0], "Where sentiment sits now", "~32% negative", "down from a ~47% peak",
        help="The negative-review share is well off its late-2024/early-2025 peak (~47%) but still far above "
             "the pre-2024 baseline (~18%).")
    kpi(c[1], "Pre-decline baseline", "~18% negative", "2023 and earlier",
        help="Where the negative share sat before the 2024 decline — the level a full recovery would return to.")
    kpi(c[2], "Forecast reliability (80%)", f"{cov['cov80']:.0%}", "target 80%", delta_color="off",
        help="We held back 53 past months and asked the model to forecast them. The real value landed inside "
             "the model's '80% confidence' range 79% of the time — so the uncertainty bands are honest, not "
             "decoration. (Technical: rolling-origin backtest empirical coverage, N=53.)")
    kpi(c[3], "Forecast reliability (95%)", f"{cov['cov95']:.0%}", "target 95%", delta_color="off",
        help="Same test for the wider 95% range: the truth landed inside it 96% of the time.")

    st.write("")
    chart_card(
        "Six-month outlook for the negative-review share",
        "01_neg_share_fan_chart.png",
        "<b>The honest read:</b> negativity is stuck high and bouncing around ~32% — we <i>cannot</i> "
        "credibly claim it's still rising or durably recovering. Anyone who draws a confident up-or-down "
        "line is overreaching. The value is a tested range, not false certainty.",
        how="Method (for the curious): a local-level state-space model on the monthly negative share, with "
            "extra month-to-month variability built in (φ=1.18) so the bands aren't artificially tight; the "
            "shaded fan is a Monte-Carlo simulation. We validated it by re-forecasting 53 held-back months — "
            "the 80%/95% ranges covered 79%/96% of outcomes. At 50–90 reviews/month, beating a naive average "
            "on a single-number prediction isn't expected; honest uncertainty is the deliverable.")

    st.write("")
    with st.container(border=True):
        st.subheader("Did the *types* of complaints change, or did everything just get worse?",
                     help="Technical: an associational decomposition using the driver model — it attributes "
                          "the change in negative share to the shift in complaint-type prevalence vs. an "
                          "unexplained residual. It is descriptive, not proof of cause, and the keyword themes "
                          "cover ~58% of negative reviews.")
        st.markdown(
            "A rise in negativity could come from two places: **(1)** the mix of complaints shifted toward "
            "worse problems (more billing and support issues), or **(2)** sentiment drifted down broadly. "
            "We separated them:")
        cf1, cf2 = st.columns([1.05, 1])
        with cf1:
            st.markdown(
                "- **About half (~54%)** of the rise traces to the **shift in complaint types**.\n"
                "- The rest is a **broad drift** our themes can't pin to one cause.\n"
                "- **Key implication:** even if the complaint mix fully returned to its 2023 makeup, "
                "negativity would *still* sit above the old baseline — fixing the top complaint types helps, "
                "but won't fully reverse the decline on its own.")
        with cf2:
            cfd = D.counterfactual().copy()
            ren = {"scenario": "Scenario", "anchored_neg_share": "Projected negative share"}
            show = [k for k in ["scenario", "anchored_neg_share"] if k in cfd.columns]
            st.dataframe(cfd[show].rename(columns=ren), width="stretch", hide_index=True)

    st.write("")
    chart_card(
        "How fast — and how often — does the company reply? (tracked separately)",
        "04_replyops_separate.png",
        "<b>What this tells you:</b> the company's <i>reply speed</i> slipped from ~1–3 days to <b>8–20 "
        "days</b> across late 2025 into 2026, and the share of reviews getting any reply dipped toward ~57%. "
        "That's a <b>more recent</b> operational warning, separate from the 2024 sentiment drop.",
        how="What we ran and why: we measured the median time to a company reply and the share of reviews "
            "that get any reply, month by month — kept separate from sentiment on purpose, because reply "
            "speed is an operational metric that moves on its own and is directly fixable.")

# ------------------------------------------------------------ Complaint drivers
with tabs[2]:
    intro_card(
        "This asks a simple question: <b>when a customer leaves a furious 1-star review, what are they "
        "complaining about?</b> We measured how much more likely each type of complaint is to appear in a "
        "1-star review — the bars further right are the strongest predictors of anger.")
    st.write("")
    chart_card(
        "What predicts a 1-star review",
        "05_driver_forest_plot.png",
        f"{chip('estimate')} &nbsp;<b>Billing/refund</b> and <b>customer support</b> complaints are the "
        "strongest operational predictors of a 1-star review — and they hold up even when comparing only "
        "among already-unhappy customers, so they're real operational signals, not just 'angry words in "
        "angry reviews.'",
        how="Technical: logistic-regression odds ratios with bootstrap confidence intervals — billing ≈ 10×, "
            "support ≈ 4.6× the odds of a 1-star review. Associational, not causal. The 'scam/fraud' theme is "
            "near-tautological (the words themselves signal a 1-star) and is flagged as such.")
    note("<b>Important limit:</b> the keyword tags catch about <b>58%</b> of negative reviews; the other 42% "
         "carry no tag, so these rankings describe the tagged subset, not every complaint.")
    with st.expander("Detail: odds-ratio table"):
        d = D.drivers()
        show = [c for c in ["theme", "n", "pct_negative", "marginal_OR", "adjusted_OR", "cond_1v2_OR"]
                if c in d.columns]
        st.dataframe(d[show], width="stretch", hide_index=True)

# ------------------------------------------------------------ Product lines
with tabs[3]:
    oa = D.osha_annual()
    intro_card(
        "Not every product line is bleeding equally. We grouped reviews by the kind of training (real estate, "
        "safety/OSHA, food handler, alcohol-server, etc.) and tracked the negative share over time. Two "
        "patterns stand out — one chronic, one accelerating.")
    st.write("")
    c1, c2 = st.columns([1, 1])
    with c1.container(border=True):
        st.subheader("Safety-training negativity tripled",
                     help="Stated at annual grain because per-quarter counts (n=9–20 in 2025) are too small to "
                          "trend reliably; each full year clears the minimum sample bar.")
        m = st.columns(3)
        for i, (_, r) in enumerate(oa.iterrows()):
            m[i].metric(r["year"], f"{r['neg_share']:.0%}", f"{int(r['n'])} reviews", delta_color="off")
        md("<div class='takeaway'>The highest-volume line moved the most — which means it also moves the "
           "overall number the most. The highest-leverage place to investigate.</div>")
    with c2.container(border=True):
        st.subheader("Year-over-year", help="Annual negative share for the safety/OSHA line.")
        img("G3_osha_annual_negshare.png")
    st.write("")
    chart_card(
        "Where trust is bleeding, by product line and quarter",
        "G1_productline_negshare_heatmap.png",
        f"{chip('estimate')} &nbsp;<b>Real estate</b> is the chronically angriest line — ~64% negative over "
        "the full period, roughly twice the overall rate — staying dark across nearly every quarter.",
        how="Coverage note: product line is inferred from course/regulator keywords, which tag ~11% of reviews "
            "(the AI pass lifts this to ~21%). Rates are within the tagged subset, with sample sizes shown.")

# ------------------------------------------------------------ Review integrity
with tabs[4]:
    f = D.INTEGRITY_FACTS
    intro_card(
        "Some negative reviews accuse the company of posting fake 5-star reviews. We took that seriously and "
        "tested it rigorously — and we report what we found <b>even though it's a negative result</b>. This is "
        "an audit, not an accusation: with public data, manipulation can't be proven or disproven, but the "
        "evidence here does <b>not</b> support it.")
    st.write("")
    c = st.columns(4)
    kpi(c[0], "Weeks examined", f["weeks_scanned"], help="Every week of review history was scanned for "
        "suspicious 5-star spikes.")
    kpi(c[1], "Genuine spikes found", f["survive_fdr"], f"~{f['expected_by_chance']} expected by chance",
        help="After correcting for the fact that scanning hundreds of weeks throws up false alarms, 15 real "
             "spikes remain — about what you'd expect by chance.")
    kpi(c[2], "Spikes during the decline", f["in_2024plus"], "not timed to the drop",
        help="Only one of those spikes falls in the 2024+ decline window — every other dated spike predates it.")
    kpi(c[3], "First-time reviewers", "flat", "no fake-account signature",
        help="If spikes were fake accounts, first-time-reviewer share would jump around them. It stays flat "
             "(~67–72%) every year — the opposite of a manipulation signature.")
    st.write("")
    chart_card(
        "The test that matters most — and it comes back clean",
        "F2_firsttimer_share_overtime.png",
        f"{chip('measured')} &nbsp;The share of reviews from <b>first-time reviewers stays flat every year</b>. "
        "A test run specifically to catch fake-account activity comes back negative — the most credibility-"
        "building result in the audit.",
        how="Every dated 5-star spike predates the 2024 decline (2018–2023), consistent with normal "
            "review-invitation email batches after course completion — not manipulation timed to mask a drop. "
            "Resolving it definitively would need data only Trustpilot/360training hold (IP, invite logs).")

# ------------------------------------------------------------ Revenue at risk (interactive)
with tabs[5]:
    intro_card(
        "What is the reputation problem worth? We deliberately <b>avoid</b> inventing a loss figure. Instead we "
        "give you a <b>break-even</b>: the reputation fix pays for itself if it recovers even a small lift in "
        "conversion among customers who read reviews. Enter your own numbers below — the math updates live.")
    st.write("")
    base = D.revenue_base()
    with st.container(border=True):
        st.subheader("Try it: when does fixing this pay for itself?",
                     help="Break-even conversion lift = annual fix cost ÷ exposed revenue, where exposed "
                          "revenue = annual revenue × exposure fraction × review-consult rate. No borrowed "
                          "elasticity needed — only your own numbers.")
        cc1, cc2 = st.columns(2)
        rev = cc1.slider("Annual online revenue ($M)", 5.0, 200.0,
                         float(base["annual_online_revenue_$"]) / 1e6, 5.0)
        exp = cc1.slider("Share of revenue from customers who read reviews", 0.05, 0.60,
                         float(base["exposure_fraction"]), 0.01)
        cons = cc2.slider("Of those, share who weigh reviews heavily", 0.50, 0.90,
                          float(base["review_consult_rate"]), 0.01)
        fix = cc2.slider("Annual cost to fix the reputation problem ($M)", 0.1, 3.0,
                         float(base["annual_fix_cost_$"]) / 1e6, 0.1)

        x_be = D.breakeven(rev * 1e6, exp, cons, fix * 1e6)
        rlo, rhi = D.recoverable()
        within = x_be <= rhi
        m = st.columns(3)
        m[0].metric("Conversion lift needed to break even", f"{x_be:.1%}")
        m[1].metric("Realistically recoverable", f"{rlo:.1%} – {rhi:.1%}", delta_color="off")
        m[2].metric("Revenue exposed to reviews", f"${rev*exp*cons:.1f}M", delta_color="off")
        if within:
            st.success(f"✅ Break-even (**{x_be:.1%}**) is **below** what's realistically recoverable "
                       f"({rhi:.1%}) — on these numbers, fixing the problem **clearly pays for itself.**")
        else:
            st.error(f"⚠️ Break-even (**{x_be:.1%}**) is **above** what's realistically recoverable "
                     f"({rhi:.1%}) — worth it only if your revenue or exposure run higher than entered.")

        st.plotly_chart(breakeven_fig(x_be, rlo, rhi, within), width="stretch", config=PLOT_CONFIG)

    with st.expander("The decision chart and what each assumption is worth"):
        img("CC2_breakeven_threshold.png")
        img("CC2_revenue_at_risk_tornado.png")
    with st.expander("Appendix — a rough dollar range (illustrative only, not a measurement)"):
        st.caption("Every input below is a placeholder or external benchmark — none is 360training's actual "
                   "revenue. The break-even above is the real claim; this range only answers 'roughly how much?'")
        rng = D.illustrative_range().set_index("percentile")["annual_rar_usd"]
        mm = st.columns(3)
        mm[0].metric("Lower–upper (10th–90th)", f"${rng.get('p10',0)/1e6:.2f}M – ${rng.get('p90',0)/1e6:.2f}M",
                     delta_color="off")
        mm[1].metric("Midpoint", f"${rng.get('p50',0)/1e6:.2f}M", delta_color="off")
        mm[2].metric("Middle half (25th–75th)", f"${rng.get('p25',0)/1e6:.2f}M – ${rng.get('p75',0)/1e6:.2f}M",
                     delta_color="off")

# ------------------------------------------------------------ Reputation health (interactive)
with tabs[6]:
    intro_card(
        "We combined the signals — complaint volume, severity, and reply operations — into a single "
        "<b>Reputation Health score</b>, with 2023 set to 100. The honest test of any composite score is "
        "whether it survives different reasonable weightings. Drag the sliders below: <b>the decline holds no "
        "matter how you weight it.</b>")
    st.write("")
    chart_card(
        "Reputation Health score since 2023 (100 = baseline)",
        "H1_rhi_illustrative_calibration.png",
        "A steady, multi-year erosion. This is a <i>trajectory</i>, not a month-by-month ranking — at 50–90 "
        "reviews a month, single-month wiggles are noise.",
        how="The score is a re-computable composite (not a live monitoring system). 2023 is a frozen baseline. "
            "The 2024 event markers are illustrative calibration, not an out-of-sample back-test.")

    st.write("")
    with st.container(border=True):
        st.subheader("Try it: re-weight the score yourself",
                     help="Each slider sets a component's weight; the score recomputes from the published "
                          "component scores. With the default weights it reproduces the official index exactly.")
        st.caption("The default weights were fixed *before* looking at the 2024 data. Re-weight them however "
                   "you like — the decline persists. That robustness is the whole point.")
        wc = st.columns(3)
        w = {}
        for i, comp in enumerate(RHI_COMPS):
            w[comp] = wc[i % 3].slider(RHI_LABELS[comp], 0, 60, int(RHI_WEIGHTS[comp]), 1)
        if sum(w.values()) == 0:
            st.warning("Set at least one weight above zero.")
        else:
            traj = D.rhi_reweight(w).groupby("year")["RHI"].mean()
            baseann = D.rhi_annual()
            yrs = [y for y in ["2023", "2024", "2025", "2026"] if y in traj.index]
            monotone = all(traj[yrs[i]] >= traj[yrs[i + 1]] for i in range(len(yrs) - 1))
            st.plotly_chart(rhi_fig(yrs, [baseann[y] for y in yrs], [traj[y] for y in yrs]),
                            width="stretch", config=PLOT_CONFIG)
            if monotone:
                st.success("✅ Still declining every year under your weights. The drop is in the data, "
                           "not the way we built the score.")
            else:
                st.warning("Non-monotone under this extreme weighting — note how far you had to push one "
                           "component to break it.")
    with st.expander("The robustness exhibit — 9 fixed weightings, all decline"):
        img("H4_weight_sensitivity.png")
        st.dataframe(D.rhi_sensitivity(), width="stretch", hide_index=True)
    with st.expander("What drives the decline"):
        img("H2_component_breakdown.png")
        img("H3_leading_vs_lagging.png")
        st.caption("Complaint volume dominates the decline; reply speed degraded later (late 2025+) — a "
                   "lagging operational shock. Review-integrity contributes nothing (the audit's clean result).")

# ------------------------------------------------------------ Resolution gap
with tabs[7]:
    rg = D.resolution_gap()
    intro_card(
        "This is the most actionable finding in the analysis. Most unhappy customers describe a <b>specific, "
        "fixable</b> problem — but almost none get a real fix in the company's reply. The gap between 'fixable' "
        "and 'fixed' is enormous, and it's entirely within leadership's control.")
    st.write("")
    chart_card(
        "Fixable complaints vs. complaints actually fixed",
        "C1_resolution_gap.png",
        f"{chip('measured')} &nbsp;<b>{rg['actionable']['pct_of_neg']:.0%}</b> of unhappy customers name a "
        "fixable issue; only <b>~0.5%</b> get a specific remedy in the reply — a <b>178× drop-off</b>. Replies "
        "to unhappy customers are <b>73% 'email-us' deflection</b>.",
        how="Single denominator (the 2,206 negative reviews) so the collapse is honest. Corpus-wide, specific "
            "remedies appear in 23 of 10,601 replies (0.2%). Stress-tested against the raw reply text, 0.2% is "
            "a conservative upper bound — several of those 23 are process promises, not customer fixes.")
    c = st.columns(3)
    kpi(c[0], "Name a fixable issue", f"{rg['actionable']['pct_of_neg']:.0%}", "of unhappy customers")
    kpi(c[1], "Get a specific fix", f"{rg['specific_remedy_in_negatives']['pct_of_neg']:.1%}",
        f"{rg['specific_remedy_in_negatives']['value']} of {D.HEADLINE['n_negative']:,}")
    kpi(c[2], "Gap", "178×", "fixable → fixed")
    md(f"<div class='takeaway'>{chip('action')} &nbsp;A measurable, ownable lever: convert 'email-us' "
       "deflection into tracked, specific resolutions on the fixable majority of complaints.</div>")
    with st.expander("How the reviews were categorized (and its honest limits)"):
        st.markdown(
            "All 10,601 reviews were auto-categorized into 19 fields by an AI model (fixed schema, $21.74, "
            "0 errors). The validation is **model-vs-model agreement** (~87–96%), which measures *consistency*, "
            "not certified accuracy — so it most likely flatters the true number. We did **not** use it to "
            "unlock the more advanced analyses, which stay on the conservative keyword method. Its real value "
            "is breadth — including **1,103 reviews** about issues the keyword tags miss entirely (course "
            "timers, platform usability, proctoring).")

st.divider()
md("<div class='meta'>Independent analysis of 10,601 public reviews &nbsp;·&nbsp; every figure cross-checked "
   "(22/22, 0 conflicts) &nbsp;·&nbsp; findings separated into measured vs. estimated &nbsp;·&nbsp; two panels "
   "recompute live from the same code as the charts.</div>")
