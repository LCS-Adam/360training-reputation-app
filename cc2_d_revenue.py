"""
CC2-D Revenue-at-risk — sizing the stakes of the reputation decline, HONESTLY.

Design: we have ONLY public review data — no conversion, traffic, AOV, or
customer counts. So:
- The SPINE and only load-bearing claim is a BREAK-EVEN INVERSION: "the reputation fix
  pays for itself if it recovers even X% relative conversion on the review-exposed
  segment." This needs NO external elasticity — only company placeholders.
- The Luca restaurant elasticity (5-9%/star) is DEMOTED to one context bar + a caveated
  sensitivity input, never a headline number. Category-error caveat stated on the chart.
- The star-trough statistic each scenario scales is PINNED: BASE = sustained -0.53*,
  HIGH = quarterly-trough -0.91* (both reconciled from CC1 monthly metrics).
- Parameter ledger tags every input INTERNAL / EXTERNAL / COMPANY-placeholder / JUDGMENT.
- NO headline revenue point or range. Company placeholders are ILLUSTRATIVE.

External benchmarks (verified 2026-06):
- Luca, HBS WP 12-016 "Reviews, Reputation, and Revenue: The Case of Yelp.com":
  +1 star -> +5-9% revenue; effect LARGER for independents, minimal for chains.
- BrightLocal Local Consumer Review Survey 2024: ~75% of consumers always/regularly
  read reviews before purchasing; only 3% never.

Run: ./.venv/bin/python cc2_d_revenue.py
"""
import numpy as np
import pandas as pd

import cc2_common as cc

OUT = cc.OUT
plt = cc.apply_chart_style()


def star_deltas():
    """Reconcile the rating drop from CC1 monthly metrics (volume-weighted)."""
    m = cc.monthly_metrics(cc.load_trustpilot())
    base = m[(m.month >= "2023-01") & (m.month <= "2023-12")]
    sustained = m[(m.month >= "2024-03") & (m.month <= "2025-12")]
    q4 = m[(m.month >= "2024-10") & (m.month <= "2024-12")]
    b = np.average(base.avg_rating, weights=base.n)
    s = np.average(sustained.avg_rating, weights=sustained.n)
    t = np.average(q4.avg_rating, weights=q4.n)
    return b, b - s, b - t   # baseline, sustained drop, trough drop


# ----------------------------------------------------------------- parameters
# COMPANY placeholders are ILLUSTRATIVE — the live Streamlit app lets the company
# replace them. Values are (low, base, high).
def get_params(star_sustained, star_trough):
    return {
        # name: (low, base, high, type, source)
        "annual_online_revenue_$": (20e6, 50e6, 120e6, "COMPANY-placeholder", "ILLUSTRATIVE — replace"),
        "exposure_fraction":       (0.15, 0.30, 0.50, "COMPANY-placeholder",
                                    "share of revenue from review-consulting, non-mandated buyers"),
        "review_consult_rate":     (0.65, 0.75, 0.80, "EXTERNAL-sourced", "BrightLocal 2024 (~75%)"),
        "elasticity_per_star":     (0.05, 0.07, 0.09, "EXTERNAL-sourced", "Luca HBS WP 12-016 (5-9%/star)"),
        "mandated_context_discount": (0.30, 0.55, 0.80, "JUDGMENT",
                                    "haircut: compliance training is often mandated/B2B -> more inelastic than restaurants"),
        "star_drop":               (star_sustained, star_sustained, star_trough, "INTERNAL-measured",
                                    "CC1: -0.53 sustained (base/low), -0.91 Q4-2024 trough (high)"),
        "annual_fix_cost_$":       (0.3e6, 1.0e6, 2.0e6, "COMPANY-placeholder", "ILLUSTRATIVE — replace"),
    }


def implied_revenue_at_risk(p):
    """Demoted metric (used ONLY for sensitivity/context, never headlined):
    exposed revenue * effective conversion impact of the rating drop."""
    exposed = p["annual_online_revenue_$"] * p["exposure_fraction"] * p["review_consult_rate"]
    conv_impact = p["elasticity_per_star"] * p["star_drop"] * p["mandated_context_discount"]
    return exposed * conv_impact, exposed, conv_impact


def illustrative_range(P, n=40000, seed=42):
    """ILLUSTRATIVE magnitude range — NOT a measurement. Monte-Carlo over the parameter
    ledger (triangular(low, base, high) per input, so the BASE is weighted and the central
    interval does NOT compound all extremes the way a naive low×low / high×high would). We
    report percentiles, never a point. The break-even inversion remains the load-bearing claim."""
    rng = np.random.default_rng(seed)
    def tri(v):
        lo, ba, hi = v[0], v[1], v[2]
        return np.full(n, lo) if lo == hi else rng.triangular(lo, min(max(ba, lo), hi), hi, n)
    rar = (tri(P["annual_online_revenue_$"]) * tri(P["exposure_fraction"]) * tri(P["review_consult_rate"])
           * tri(P["elasticity_per_star"]) * tri(P["star_drop"]) * tri(P["mandated_context_discount"]))
    pct = {q: float(np.percentile(rar, q)) for q in (10, 25, 50, 75, 90)}
    return rar, pct


# ----------------------------------------------- SHARED break-even (spine) — module level
# These are imported by the Streamlit app (via cc2_app_data) so the live break-even widget
# and the static break-even chart are LITERALLY the same formula and cannot disagree.
def breakeven_x(annual_rev, exposure, consult, fix_cost):
    """The reputation fix recovers its cost if it lifts exposed-segment conversion by
    fix_cost / exposed_revenue, where exposed = annual_rev * exposure * review_consult_rate.
    Needs NO elasticity — only company numbers. This is the only load-bearing D claim."""
    exposed = annual_rev * exposure * consult
    return fix_cost / exposed if exposed else float("nan")


def recoverable_band(P, d_sustained, d_trough):
    """Plausibly-recoverable conversion impact implied by the rating drop (the DEMOTED,
    caveated elasticity transfer). Returns (lo, hi). P is the (low, base, high, ...) param
    ledger. lo = elasticity_lo × sustained_drop × discount_lo; hi = elasticity_hi × trough ×
    discount_hi. Used only to draw the comparison band, never as a point estimate."""
    rec_lo = P["elasticity_per_star"][0] * d_sustained * P["mandated_context_discount"][0]
    rec_hi = P["elasticity_per_star"][2] * d_trough * P["mandated_context_discount"][2]
    return rec_lo, rec_hi


def main():
    cc.ensure_dirs()
    base_rating, d_sustained, d_trough = star_deltas()
    print(f"Star deltas (reconciled from CC1): 2023 baseline={base_rating:.2f}; "
          f"sustained drop={d_sustained:.2f}; Q4-2024 trough drop={d_trough:.2f}")
    P = get_params(d_sustained, d_trough)

    base = {k: v[1] for k, v in P.items()}
    # high scenario uses trough star_drop
    base_rar, exposed_base, conv_base = implied_revenue_at_risk(base)

    # ---- parameter ledger CSV
    ledger = pd.DataFrame([
        dict(parameter=k, low=v[0], base=v[1], high=v[2], type=v[3], source=v[4])
        for k, v in P.items()])
    ledger.to_csv(f"{OUT}/CC2_revenue_at_risk_model.csv", index=False)

    # ---- BREAK-EVEN INVERSION (the spine) — needs NO elasticity
    # fix breaks even if it recovers x% relative conversion on the exposed segment:
    #   x_breakeven = annual_fix_cost / exposed_revenue
    def breakeven_x(annual_rev, exposure, consult, fix_cost):
        exposed = annual_rev * exposure * consult
        return fix_cost / exposed
    x_be_base = breakeven_x(base["annual_online_revenue_$"], base["exposure_fraction"],
                            base["review_consult_rate"], base["annual_fix_cost_$"])
    # plausibly-recoverable conversion impact from the reputation decline (demoted elasticity)
    rec_lo = P["elasticity_per_star"][0] * d_sustained * P["mandated_context_discount"][0]
    rec_hi = P["elasticity_per_star"][2] * d_trough * P["mandated_context_discount"][2]
    print(f"\nBREAK-EVEN (spine): fix recovers cost if it lifts exposed-segment conversion by "
          f"{x_be_base:.1%} (illustrative).")
    print(f"Plausibly-recoverable conversion impact from the rating drop (demoted elasticity, caveated): "
          f"{rec_lo:.1%}–{rec_hi:.1%}.")
    print(f"  -> On illustrative placeholders, break-even {x_be_base:.1%} "
          f"{'sits BELOW' if x_be_base < rec_hi else 'sits ABOVE'} the recoverable ceiling "
          f"{rec_hi:.1%} (company fills real numbers to decide).")

    # ---- tornado: swing in implied RAR from each parameter low<->high (others at base)
    tor = []
    for k in P:
        lo = dict(base); lo[k] = P[k][0]
        hi = dict(base); hi[k] = P[k][2]
        rar_lo = implied_revenue_at_risk(lo)[0]
        rar_hi = implied_revenue_at_risk(hi)[0]
        tor.append({"parameter": k, "low_usd": min(rar_lo, rar_hi), "high_usd": max(rar_lo, rar_hi),
                    "swing_usd": abs(rar_hi - rar_lo)})
    tor_df = pd.DataFrame(tor).sort_values("swing_usd", ascending=False)

    # ============================================================ charts
    # tornado
    fig, ax = plt.subplots(figsize=(9, 5))
    td = tor_df.sort_values("swing_usd")
    yps = np.arange(len(td))
    ax.barh(yps, (td["high_usd"] - td["low_usd"]) / 1e6, left=td["low_usd"] / 1e6, color=cc.NAVY, alpha=0.85)
    ax.axvline(base_rar / 1e6, color=cc.RED, ls="--", label=f"base case (illustrative ${base_rar/1e6:.2f}M)")
    ax.set_yticks(yps); ax.set_yticklabels(td["parameter"], fontsize=8)
    ax.set_xlabel("Implied annual revenue-at-risk ($M) — ILLUSTRATIVE, NOT a headline figure")
    ax.set_title("Which assumption the answer depends on most")
    ax.text(0.99, 0.02, "elasticity transfer (restaurants→mandated e-learning) is the weakest link — caveat applied",
            transform=ax.transAxes, ha="right", fontsize=7, color=cc.GRAY)
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(f"{cc.CHARTS}/CC2_revenue_at_risk_tornado.png"); plt.close()

    # break-even decision chart
    exposure_grid = np.linspace(0.10, 0.60, 50)
    fig, ax = plt.subplots(figsize=(9, 5))
    for fix_cost, c in [(0.3e6, cc.GREEN), (1.0e6, cc.NAVY), (2.0e6, cc.RED)]:
        xbe = [breakeven_x(base["annual_online_revenue_$"], e, base["review_consult_rate"], fix_cost)
               for e in exposure_grid]
        ax.plot(exposure_grid, np.array(xbe) * 100, color=c, label=f"fix cost ${fix_cost/1e6:.1f}M")
    ax.axhspan(rec_lo * 100, rec_hi * 100, color=cc.ORANGE, alpha=0.2,
               label=f"plausibly recoverable {rec_lo:.0%}–{rec_hi:.0%}")
    ax.set_xlabel("Exposure fraction (share of revenue subject to review-driven conversion)")
    ax.set_ylabel("Break-even conversion lift needed (%)")
    ax.set_title("Break-even — below the band, the fix pays for itself")
    ax.legend(fontsize=8); ax.set_ylim(0, 15)
    fig.tight_layout(); fig.savefig(f"{cc.CHARTS}/CC2_breakeven_threshold.png"); plt.close()

    # ============================================================ ILLUSTRATIVE range (Monte Carlo)
    rar_samples, pct = illustrative_range(P)
    pd.DataFrame([{"percentile": f"p{q}", "annual_rar_usd": round(v)} for q, v in pct.items()]).to_csv(
        f"{OUT}/CC2_revenue_illustrative_range.csv", index=False)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(rar_samples / 1e6, bins=80, color=cc.NAVY, alpha=0.8)
    ymax = ax.get_ylim()[1]
    for q, c, lab in [(10, cc.GRAY, "10th"), (50, cc.RED, "median"), (90, cc.GRAY, "90th")]:
        ax.axvline(pct[q] / 1e6, color=c, ls="--", lw=1.8 if q == 50 else 1)
        ax.text(pct[q] / 1e6, ymax * 0.9, f"{lab}\n${pct[q]/1e6:.2f}M", fontsize=7, ha="center", color=c)
    ax.set_xlim(0, np.percentile(rar_samples, 97) / 1e6)
    ax.set_xlabel("Illustrative annual reputation-linked revenue-at-risk ($M)")
    ax.set_ylabel("Monte-Carlo draws")
    ax.set_title("Illustrative magnitude only — modeled from placeholder inputs", fontsize=11)
    ax.text(0.98, 0.55, "Every input is a placeholder/benchmark,\nNOT 360training data. Replace revenue\n& exposure and this range collapses.",
            transform=ax.transAxes, ha="right", fontsize=7, color=cc.GRAY)
    fig.tight_layout(); fig.savefig(f"{cc.CHARTS}/CC2_revenue_illustrative_range.png"); plt.close()
    print(f"\nILLUSTRATIVE annual revenue-at-risk (Monte-Carlo, NOT a measurement): "
          f"median ${pct[50]/1e6:.2f}M | 10-90th ${pct[10]/1e6:.2f}M-${pct[90]/1e6:.2f}M | "
          f"25-75th ${pct[25]/1e6:.2f}M-${pct[75]/1e6:.2f}M")

    # ============================================================ print
    print("\n==================== PARAMETER LEDGER ====================")
    print(ledger.to_string(index=False))
    print("\n==================== SENSITIVITY TORNADO (illustrative $) ====================")
    print(tor_df.assign(low_M=lambda d: (d["low_usd"]/1e6).round(2), high_M=lambda d: (d["high_usd"]/1e6).round(2),
                        swing_M=lambda d: (d["swing_usd"]/1e6).round(2))[["parameter", "low_M", "high_M", "swing_M"]].to_string(index=False))
    print(f"\nTop sensitivity: {tor_df.iloc[0]['parameter']} and {tor_df.iloc[1]['parameter']} "
          f"-> these are what the company must pin down first.")
    print("\nDONE — wrote CC2_revenue_at_risk_model.csv + tornado/breakeven charts. NO headline $ figure (by design).")


if __name__ == "__main__":
    main()
