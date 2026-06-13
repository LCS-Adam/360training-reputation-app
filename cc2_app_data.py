"""
cc2_app_data.py — tested DATA / COMPUTE layer for the CC2 Streamlit app (app.py).

The app is a THIN VIEW over this module: every data load and every live computation lives
here as a plain function, so the substance is verifiable WITHOUT rendering the UI. Run
`./.venv/bin/python cc2_app_data.py` for a self-test that asserts the key invariants
(forecast loads, backtest coverage ≈ 79/96, break-even reproduces the memo, RHI reweight
reproduces the published index, OSHA annual 24/47/78, resolution-gap 88.5%→0.5%).

The two live widgets import the SAME analytics code as the static exhibits, so a slider can
never contradict a published chart:
  • break-even  ← cc2_d_revenue.breakeven_x / recoverable_band
  • RHI reweight ← cc2_h_kpi component z's + WEIGHTS/SCALE (final step of normalize_and_index)
"""
import os
import functools

import numpy as np
import pandas as pd

# --- shared analytics code (widgets == static exhibits) -----------------------
from cc2_d_revenue import breakeven_x, recoverable_band
from cc2_h_kpi import WEIGHTS as RHI_WEIGHTS, COMPS as RHI_COMPS, RHI_SCALE, LABELS as RHI_LABELS

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "01_analytics_outputs")
CHARTS = os.path.join(OUT, "CC2_chart_pack")


def _csv(name):
    return pd.read_csv(os.path.join(OUT, name))


def chart(name):
    """Absolute path to a chart-pack PNG (for st.image)."""
    return os.path.join(CHARTS, name)


# ----------------------------------------------------------------- headline facts
HEADLINE = {
    "n_reviews": 10601, "n_negative": 2206, "neg_share": 0.208, "reply_coverage": 0.915,
    "date_range": "2014-07 → 2026-06 (2026-06 partial, excluded)",
    "extraction_cost": "$21.74", "extraction_errors": 0,
}

# ----------------------------------------------------------------- A · forecast
@functools.lru_cache(maxsize=1)
def forecast():
    return _csv("CC2_reputation_forecast.csv")


@functools.lru_cache(maxsize=1)
def backtest():
    return _csv("CC2_forecast_backtest.csv")


def backtest_coverage():
    bt = backtest()
    return {"n": int(len(bt)), "n_origins": int(bt["origin"].nunique()),
            "cov80": float(bt["covered80"].mean()), "cov95": float(bt["covered95"].mean())}


@functools.lru_cache(maxsize=1)
def counterfactual():
    return _csv("CC2_counterfactual_scenarios.csv")


@functools.lru_cache(maxsize=1)
def replyops():
    return _csv("CC2_replyops_trend.csv")


# ----------------------------------------------------------------- B · drivers
@functools.lru_cache(maxsize=1)
def drivers():
    return _csv("CC2_driver_odds_ratios.csv")


# ----------------------------------------------------------------- G · segments
@functools.lru_cache(maxsize=1)
def segments_quarterly():
    return _csv("CC2_productline_sentiment_timeseries.csv")


@functools.lru_cache(maxsize=1)
def osha_annual():
    q = segments_quarterly()
    q = q[q["product_line"] == "osha_safety"].copy()
    q["year"] = q["quarter"].str[:4]
    q["neg_count"] = (q["neg_share"] * q["n"]).round().astype(int)
    g = q.groupby("year").agg(n=("n", "sum"), neg=("neg_count", "sum")).reset_index()
    g["neg_share"] = g["neg"] / g["n"]
    return g[g["year"].isin(["2023", "2024", "2025"])].reset_index(drop=True)


# ----------------------------------------------------------------- F · integrity
@functools.lru_cache(maxsize=1)
def integrity_register():
    return _csv("CC2_anomaly_register.csv")


INTEGRITY_FACTS = {
    "weeks_scanned": 450, "raw_p05": 43, "expected_by_chance": 22, "survive_fdr": 15,
    "in_2024plus": 1, "firsttimer_range": "0.659–0.708 (flat, 2018–2026)",
    "verdict": "Audit, not accusation — manipulation is unprovable without identity/IP data; "
               "the first-timer NULL and the pre-2024 clustering of bursts make manipulation NOT the story.",
}


# ----------------------------------------------------------------- H · RHI
@functools.lru_cache(maxsize=1)
def rhi_timeseries():
    return _csv("CC2_rhi_timeseries.csv")


@functools.lru_cache(maxsize=1)
def rhi_sensitivity():
    return _csv("CC2_rhi_sensitivity.csv")


def rhi_reweight(weights):
    """Recompute the RHI trajectory from the STORED component z's under user weights —
    the final step of cc2_h_kpi.normalize_and_index (z-cap=3, σ-2023 frozen), reusing the
    published z columns so the widget is faithful to the static index. Returns df[month,RHI,year].
    With weights == RHI_WEIGHTS it reproduces the stored RHI column exactly."""
    ts = rhi_timeseries()
    wsum = sum(weights.values())
    det = np.zeros(len(ts))
    for c in RHI_COMPS:
        det += weights[c] * ts[f"z_{c}"].to_numpy() / wsum
    out = pd.DataFrame({"month": ts["month"], "RHI": 100.0 - RHI_SCALE * det})
    out["year"] = out["month"].str[:4]
    return out


def rhi_annual(weights=None):
    return rhi_reweight(weights or dict(RHI_WEIGHTS)).groupby("year")["RHI"].mean()


# ----------------------------------------------------------------- D · revenue
@functools.lru_cache(maxsize=1)
def revenue_ledger():
    return _csv("CC2_revenue_at_risk_model.csv")


@functools.lru_cache(maxsize=1)
def revenue_params():
    """(low, base, high, type, source) per parameter, from the PUBLISHED ledger CSV."""
    led = revenue_ledger()
    return {r["parameter"]: (r["low"], r["base"], r["high"], r["type"], r["source"])
            for _, r in led.iterrows()}


def revenue_base():
    """Base-case value of each parameter (slider defaults)."""
    return {k: v[1] for k, v in revenue_params().items()}


def star_deltas_frozen():
    """Reconciled star drops sourced from the ledger (NOT recomputed live):
    sustained = star_drop low, trough = star_drop high."""
    sd = revenue_params()["star_drop"]
    return float(sd[0]), float(sd[2])


def breakeven(annual_rev, exposure, consult, fix_cost):
    """SHARED break-even formula (cc2_d_revenue.breakeven_x). Returns the conversion lift
    the fix must recover to pay for itself."""
    return breakeven_x(annual_rev, exposure, consult, fix_cost)


def recoverable():
    """(lo, hi) plausibly-recoverable conversion band (cc2_d_revenue.recoverable_band)."""
    d_sus, d_tr = star_deltas_frozen()
    return recoverable_band(revenue_params(), d_sus, d_tr)


@functools.lru_cache(maxsize=1)
def illustrative_range():
    return _csv("CC2_revenue_illustrative_range.csv")


# ----------------------------------------------------------------- C · resolution gap
@functools.lru_cache(maxsize=1)
def resolution_gap():
    g = _csv("CC2_resolution_gap.csv").set_index("metric")
    return {k: {"value": int(g.loc[k, "value"]), "pct_of_neg": float(g.loc[k, "pct_of_neg"])}
            for k in g.index}


# ================================================================= self-test
if __name__ == "__main__":
    results = []

    def check(name, cond, detail=""):
        results.append(bool(cond))
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}{('  ' + detail) if detail else ''}")

    print("cc2_app_data self-test — verifies SUBSTANCE without the UI\n")

    fc = forecast()
    check("forecast loads (observed + forecast rows)",
          set(fc["type"]) >= {"observed", "forecast"}, f"rows={len(fc)}")

    cov = backtest_coverage()
    check("backtest coverage ≈ 79% / 96%",
          abs(cov["cov80"] - 0.79) < 0.03 and abs(cov["cov95"] - 0.96) < 0.03,
          f"N={cov['n']} ({cov['n_origins']} origins) cov80={cov['cov80']:.1%} cov95={cov['cov95']:.1%}")

    oa = osha_annual()
    pj = {r["year"]: round(r["neg_share"] * 100) for _, r in oa.iterrows()}
    nj = {r["year"]: int(r["n"]) for _, r in oa.iterrows()}
    check("OSHA annual 24/47/78 (n 78/66/50)",
          pj == {"2023": 24, "2024": 47, "2025": 78} and nj == {"2023": 78, "2024": 66, "2025": 50},
          f"{pj} n={nj}")

    be = breakeven(50e6, 0.30, 0.75, 1.0e6)
    check("break-even base ≈ 8.9% (matches memo)", abs(be - 0.0889) < 0.002, f"{be:.2%}")
    rlo, rhi = recoverable()
    check("recoverable ceiling ≈ 6.5% (matches memo)", abs(rhi - 0.0655) < 0.005,
          f"band {rlo:.2%}–{rhi:.2%}")

    ts = rhi_timeseries()
    rw = rhi_reweight(dict(RHI_WEIGHTS))
    maxd = float(np.abs(rw["RHI"].to_numpy() - ts["RHI"].to_numpy()).max())
    check("RHI reweight(default) == published RHI", maxd < 0.05, f"max|Δ|={maxd:.5f}")
    ann = rhi_annual()
    check("RHI annual 100→93.6→86→80.6",
          abs(ann["2023"] - 100) < 0.6 and abs(ann["2025"] - 86.0) < 1.0,
          " → ".join(f"{y}:{ann[y]:.1f}" for y in ["2023", "2024", "2025", "2026"] if y in ann))

    rg = resolution_gap()
    check("resolution gap 88.5% actionable → 0.5% remedied",
          rg["actionable"]["value"] == 1953 and rg["specific_remedy_in_negatives"]["value"] == 11,
          f"actionable={rg['actionable']['pct_of_neg']:.1%} "
          f"specific|neg={rg['specific_remedy_in_negatives']['pct_of_neg']:.2%}")

    # widget extremes don't break the index (monotone-down should survive any weighting)
    neg_only = rhi_annual({**RHI_WEIGHTS, "neg_share": 100, "severity_rate": 0, "reply_lag": 0,
                           "reply_coverage": 0, "integrity": 0, "trust_bleed": 0})
    check("RHI stays monotone-down under neg-only weights",
          neg_only["2023"] > neg_only["2024"] > neg_only["2025"],
          " → ".join(f"{y}:{neg_only[y]:.1f}" for y in ["2023", "2024", "2025"]))

    print(f"\n{sum(results)}/{len(results)} checks passed")
    raise SystemExit(0 if all(results) else 1)
