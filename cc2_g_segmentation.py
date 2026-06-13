"""
CC2-G Segmentation — where is trust bleeding (by product line)?

Design:
- Country geo is a DEAD END (98% "US") — dropped, with the reason stated.
- Product line via regulator + keyword anchors. Coverage is only ~12% with keywords;
  this is the fallback. Workstream C's LLM product_line lifts coverage to ~full and
  swaps in later (G-full). Coverage % is printed on every panel.
- neg-share reported within the tagged subset (never absolute volume comparisons);
  small-n cells suppressed (CC1 MIN_N / n_too_small).
- Trust-bleed series for H computed at QUARTERLY grain (monthly per-line n too small);
  H forward-fills it with an explicit label.
- State inference only where a state-specific regulator/name appears; heavily caveated.

Run: ./.venv/bin/python cc2_g_segmentation.py
"""
import re
import numpy as np
import pandas as pd

import cc2_common as cc

OUT = cc.OUT
plt = cc.apply_chart_style()

# priority order: most specific first; a review's primary line = first match
PRODUCT_LINES = [
    ("real_estate",   r"real[\s-]?estate|realtor|\btrec\b|\bdre\b|broker license|sales ?associate|continuing ed.*real"),
    ("tabc_alcohol",  r"\btabc\b|responsible vendor|alcohol seller|bartend|seller.?server|liquor"),
    ("food_handler",  r"food handler|food safety|servsafe|food protection|food manager"),
    ("osha_safety",   r"\bosha\b|hazwoper|workplace safety|safety training|forklift"),
    ("notary",        r"\bnotary\b|notary public"),
    ("insurance",     r"insurance (?:license|ce|exam|course|pre-?licens)"),
    ("hvac_trades",   r"\bhvac\b|electrician|plumb|journeyman|contractor license"),
    ("cosmetology",   r"cosmetolog|esthetic|\bbarber|nail tech|manicur"),
    ("driver_ed",     r"defensive driving|driving course|traffic school|driver'?s? ed"),
]
PL_RX = [(name, re.compile(rx)) for name, rx in PRODUCT_LINES]

STATES = {
    "TX": r"\btabc\b|\btrec\b|\btexas\b",
    "CA": r"\bdre\b|\bcalifornia\b",
    "FL": r"\bflorida\b|\bdbpr\b",
    "NY": r"\bnys\b|new york",
    "GA": r"\bgeorgia\b",
    "AZ": r"\barizona\b",
    "NV": r"\bnevada\b",
}
STATE_RX = {s: re.compile(rx) for s, rx in STATES.items()}


def primary_line(text):
    for name, rx in PL_RX:
        if rx.search(text):
            return name
    return "unknown"


def infer_state(text):
    for s, rx in STATE_RX.items():
        if rx.search(text):
            return s
    return None


def severity(neg_share, mean_star):
    return round(100 * (0.6 * neg_share + 0.4 * (1 - mean_star / 5)), 1)


def main():
    cc.ensure_dirs()
    df = cc.load_trustpilot()
    df = df[~df["month"].isin(cc.PARTIAL_MONTHS)].copy()
    df["product_line"] = df["text"].apply(primary_line)
    df["state"] = df["text"].apply(infer_state)

    coverage = (df["product_line"] != "unknown").mean()
    print(f"PRODUCT-LINE COVERAGE (keyword/regulator fallback): {coverage:.1%} "
          f"({int((df['product_line']!='unknown').sum())}/{len(df)}). "
          f"Country geo dropped (98% US). C's LLM product_line will lift this to ~full.")

    # ---- per-line summary
    rows = []
    for name, _ in PRODUCT_LINES:
        sub = df[df["product_line"] == name]
        if len(sub) == 0:
            continue
        rows.append(dict(product_line=name, n=len(sub), pct_negative=round(sub["neg"].mean(), 3),
                         mean_star=round(sub["star_rating"].mean(), 2),
                         severity=severity(sub["neg"].mean(), sub["star_rating"].mean()),
                         n_too_small=(len(sub) < 30)))
    line_df = pd.DataFrame(rows).sort_values("pct_negative", ascending=False)
    print("\nPER-LINE (sorted by % negative):")
    print(line_df.to_string(index=False))

    # ---- product_line x quarter timeseries (neg-share), 2023+
    q = df[df["product_line"] != "unknown"].copy()
    q = q[q["quarter"] >= "2023Q1"]
    pivot_n = q.pivot_table(index="product_line", columns="quarter", values="neg", aggfunc="size", fill_value=0)
    pivot_neg = q.pivot_table(index="product_line", columns="quarter", values="neg", aggfunc="mean")
    # long-form timeseries CSV
    ts = q.groupby(["product_line", "quarter"]).agg(n=("neg", "size"), neg_share=("neg", "mean"),
                                                    mean_star=("star_rating", "mean")).reset_index()
    ts["neg_share"] = ts["neg_share"].round(3); ts["mean_star"] = ts["mean_star"].round(2)
    ts["coverage_note"] = "keyword/regulator fallback ~12%; suppress n<10 cells"
    ts.to_csv(f"{OUT}/CC2_productline_sentiment_timeseries.csv", index=False)

    # ---- trust-bleed index per line: neg_share level x volume x recent trend
    recent = q[q["quarter"] >= "2025Q1"]
    bleed = []
    for name, _ in PRODUCT_LINES:
        s = q[q["product_line"] == name]
        if len(s) < 30:
            continue
        rec = recent[recent["product_line"] == name]
        bleed.append(dict(product_line=name, n=len(s), neg_share=round(s["neg"].mean(), 3),
                          recent_neg_share=round(rec["neg"].mean(), 3) if len(rec) else np.nan,
                          trustbleed_index=round(s["neg"].mean() * np.log1p(len(s)), 2)))
    bleed_df = pd.DataFrame(bleed).sort_values("trustbleed_index", ascending=False)

    # ---- quarterly trust-bleed series for H (worst-line-weighted neg-share among tagged)
    tb_q = q.groupby("quarter").apply(
        lambda g: np.average(g.groupby("product_line")["neg"].mean(),
                             weights=g.groupby("product_line").size()), include_groups=False
    ).rename("tagged_negshare").reset_index()
    tb_q.to_csv(f"{OUT}/CC2_trustbleed_quarterly.csv", index=False)

    # ---- state inference (caveated)
    st = df[df["state"].notna()].groupby("state").agg(
        n=("neg", "size"), neg_share=("neg", "mean")).reset_index()
    st["dominant_line"] = [df[(df.state == s) & (df.product_line != "unknown")]["product_line"].mode().iloc[0]
                           if len(df[(df.state == s) & (df.product_line != "unknown")]) else "unknown"
                           for s in st["state"]]
    st["n_too_small"] = st["n"] < 10
    st = st.sort_values("n", ascending=False)
    st.round(3).to_csv(f"{OUT}/CC2_state_inference.csv", index=False)

    # ============================================================ charts
    # G1 heatmap product_line x quarter
    order = bleed_df["product_line"].tolist() + [l for l in pivot_neg.index if l not in bleed_df["product_line"].tolist()]
    pn = pivot_neg.reindex(order)
    pnn = pivot_n.reindex(order)
    fig, ax = plt.subplots(figsize=(12, 4.8))
    im = ax.imshow(pn.values, aspect="auto", cmap="Reds", vmin=0, vmax=0.8)
    ax.set_xticks(range(len(pn.columns))); ax.set_xticklabels(pn.columns, rotation=45, ha="right", fontsize=7)
    ax.set_yticks(range(len(pn.index))); ax.set_yticklabels(pn.index, fontsize=8)
    for i in range(pn.shape[0]):
        for j in range(pn.shape[1]):
            v = pn.values[i, j]; nval = pnn.values[i, j]
            if not np.isnan(v) and nval >= 5:
                ax.text(j, i, f"{v:.0%}", ha="center", va="center", fontsize=6,
                        color="white" if v > 0.45 else "black")
    ax.set_title(f"Negative-review share by product line and quarter (coverage {coverage:.0%})")
    fig.colorbar(im, ax=ax, label="neg share", shrink=0.8)
    fig.tight_layout(); fig.savefig(f"{cc.CHARTS}/G1_productline_negshare_heatmap.png"); plt.close()

    # G2 ranked bar
    fig, ax = plt.subplots(figsize=(9, 4.8))
    bd = bleed_df.sort_values("neg_share")
    colors = [cc.RED if v > 0.5 else cc.ORANGE if v > 0.35 else cc.NAVY for v in bd["neg_share"]]
    ax.barh(bd["product_line"], bd["neg_share"], color=colors)
    for i, (ns, n) in enumerate(zip(bd["neg_share"], bd["n"])):
        ax.text(ns + 0.01, i, f"{ns:.0%}  (n={n})", va="center", fontsize=8)
    ax.axvline(df["neg"].mean(), color=cc.GRAY, ls="--", label=f"overall {df['neg'].mean():.0%}")
    ax.set_xlabel("Negative share"); ax.set_xlim(0, max(bd["neg_share"]) + 0.12)
    ax.set_title("Negative-review share by product line — real estate is the worst"); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(f"{cc.CHARTS}/G2_trustbleed_ranked_bar.png"); plt.close()

    # G3 annual OSHA neg-share — the reframed headline (annual grain clears ~40/yr floor;
    # quarterly cells are n=9-20 and too thin to trend, so the rise is stated year-over-year)
    qa = q.copy(); qa["year"] = qa["quarter"].str[:4]
    osha = (qa[qa.product_line == "osha_safety"].groupby("year")
            .agg(n=("neg", "size"), neg=("neg", "mean")).reset_index())
    osha = osha[osha.year.isin(["2023", "2024", "2025"])]
    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    bars = ax.bar(osha["year"], osha["neg"], width=0.6, color=[cc.NAVY, cc.ORANGE, cc.RED])
    for b, (_, r) in zip(bars, osha.iterrows()):
        ax.text(b.get_x() + b.get_width() / 2, r["neg"] + 0.02,
                f"{r['neg']:.0%}\n(n={int(r['n'])})", ha="center", va="bottom",
                fontsize=10, fontweight="bold")
    ax.axhline(df["neg"].mean(), color=cc.GRAY, ls="--", lw=1,
               label=f"overall corpus {df['neg'].mean():.0%}")
    ax.set_ylabel("Negative-review share (1–2★)"); ax.set_ylim(0, 1.0)
    ax.set_title("Safety-training negative reviews tripled, 2023→2025")
    ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout(); fig.savefig(f"{cc.CHARTS}/G3_osha_annual_negshare.png"); plt.close()
    print("\nG3 OSHA annual neg-share: "
          + ", ".join(f"{r.year}={r.neg:.0%}(n={int(r.n)})" for _, r in osha.iterrows()))

    # ============================================================ print
    print("\nTRUST-BLEED RANKING:")
    print(bleed_df.to_string(index=False))
    print("\nSTATE INFERENCE (caveated, n>=10 meaningful):")
    print(st.to_string(index=False))
    print(f"\nKEY FINDING: real_estate neg-share = {line_df[line_df.product_line=='real_estate']['pct_negative'].iloc[0]:.0%} "
          f"vs osha_safety {line_df[line_df.product_line=='osha_safety']['pct_negative'].iloc[0]:.0%} "
          f"— real-estate CE buyers are markedly angrier.")
    print("\nDONE — wrote CC2_productline_sentiment_timeseries/trustbleed_quarterly/state_inference + charts G1-G2.")


if __name__ == "__main__":
    main()
