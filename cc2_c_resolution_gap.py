"""
cc2_c_resolution_gap.py — THE resolution-gap exhibit (CC2-C's headline CEO finding).

The chart pack was missing a visual for C's most actionable finding: negative reviewers
overwhelmingly name a FIXABLE issue, yet company replies almost never deliver a specific
remedy. Built on a SINGLE denominator (the 2,206 negative reviews) so the collapse from
"88.5% actionable" to "~0.5% remedied" is honest, not a denominator trick. Reconciles to
CC2_review_extractions.csv (specific_remedy = 23 corpus-wide / 11 among negatives).

Run: ./.venv/bin/python cc2_c_resolution_gap.py
"""
import numpy as np
import pandas as pd

import cc2_common as cc

OUT = cc.OUT
plt = cc.apply_chart_style()


def truthy(s):
    return s.astype(str).str.strip().str.lower().isin(["1", "1.0", "true", "yes"])


def main():
    cc.ensure_dirs()
    ext = pd.read_csv(f"{OUT}/CC2_review_extractions.csv")
    neg = ext[ext["neg"] == True].copy()           # noqa: E712 — pandas bool column
    n_neg = len(neg)

    actionable = int(truthy(neg["is_actionable"]).sum())
    requested = int((~neg["resolution_requested"].astype(str).str.lower()
                     .isin(["none", "unclear", "nan"])).sum())
    specific_neg = int((neg["resolution_offered_in_reply"] == "specific_remedy").sum())
    specific_all = int((ext["resolution_offered_in_reply"] == "specific_remedy").sum())
    collapse = actionable / max(specific_neg, 1)

    stages = [("Negative reviews (≤2★)", n_neg),
              ("Name a fixable issue (actionable)", actionable),
              ("Explicitly request a resolution", requested),
              ("Reply offers a SPECIFIC remedy", specific_neg)]
    counts = [c for _, c in stages]
    pcts = [c / n_neg for c in counts]

    # reply composition among negatives WITH a reply
    rep = neg[neg["resolution_offered_in_reply"] != "no_reply"]
    comp_order = ["generic_apology", "escalation_only", "none", "specific_remedy"]
    comp_lab = {"generic_apology": "Generic apology", "escalation_only": "“Email-us” deflection",
                "none": "Reply, no resolution", "specific_remedy": "Specific remedy"}
    comp_n = {k: int((rep["resolution_offered_in_reply"] == k).sum()) for k in comp_order}
    comp_total = max(sum(comp_n.values()), 1)

    # ---- reconcile CSV
    pd.DataFrame([
        {"metric": "negative_reviews", "value": n_neg, "pct_of_neg": 1.0},
        {"metric": "actionable", "value": actionable, "pct_of_neg": actionable / n_neg},
        {"metric": "requested_resolution", "value": requested, "pct_of_neg": requested / n_neg},
        {"metric": "specific_remedy_in_negatives", "value": specific_neg, "pct_of_neg": specific_neg / n_neg},
        {"metric": "specific_remedy_all_reviews", "value": specific_all, "pct_of_neg": specific_all / len(ext)},
    ]).to_csv(f"{OUT}/CC2_resolution_gap.csv", index=False)

    # ============================================================ figure
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.5, 5.6),
                                   gridspec_kw={"width_ratios": [1.35, 1]})

    # --- Panel A: the funnel collapse (centered bars, single denominator)
    cols = [cc.NAVY, cc.NAVY, cc.ORANGE, cc.RED]
    ys = [3, 2, 1, 0]
    for y, (lab, _), c, p, n in zip(ys, stages, cols, pcts, counts):
        axL.barh(y, p, height=0.60, left=(1 - p) / 2, color=c, alpha=0.92)
        axL.text(0.5, y, f"{p:.1%}   ·   n = {n:,}", ha="center", va="center",
                 color="white" if p > 0.25 else cc.RED, fontsize=10.5, fontweight="bold")
        axL.text(-0.03, y, lab, ha="right", va="center", fontsize=9.5)
    axL.text(0.5, -0.85, f"↓  {collapse:.0f}× drop-off: most fixable complaints get no concrete fix",
             ha="center", va="center", fontsize=9.5, color=cc.RED, fontweight="bold")
    axL.set_xlim(-0.62, 1.05); axL.set_ylim(-1.2, 3.7); axL.axis("off")
    axL.set_title("The resolution gap (within the 2,206 negative reviews)", fontsize=11.5, fontweight="bold")

    # --- Panel B: reply composition among replied negatives (100% stacked)
    left = 0.0
    bcolors = {"generic_apology": cc.GRAY, "escalation_only": cc.ORANGE,
               "none": "#c2b280", "specific_remedy": cc.GREEN}
    for k in comp_order:
        w = comp_n[k] / comp_total
        axR.barh(0, w, left=left, height=0.5, color=bcolors[k], edgecolor="white",
                 label=f"{comp_lab[k]} — {w:.1%}  (n={comp_n[k]:,})")
        if w > 0.07:
            axR.text(left + w / 2, 0, f"{w:.0%}", ha="center", va="center",
                     color="white", fontsize=11, fontweight="bold")
        left += w
    spec_w = comp_n["specific_remedy"] / comp_total
    axR.annotate(f"Specific remedy: {spec_w:.1%}  (n={comp_n['specific_remedy']})",
                 xy=(1 - spec_w / 2, 0.25), xytext=(0.55, 0.85),
                 arrowprops=dict(arrowstyle="->", color=cc.GREEN, lw=1.5),
                 fontsize=9.5, color="#1a7d3c", fontweight="bold", ha="center")
    axR.set_xlim(0, 1); axR.set_ylim(-0.75, 1.05); axR.axis("off")
    axR.set_title("Where the reply effort goes\n(company replies to negative reviews)", fontsize=11.5, fontweight="bold")
    axR.legend(loc="lower center", bbox_to_anchor=(0.5, -0.34), fontsize=8.3, ncol=2, frameon=False)

    fig.suptitle("The resolution gap — most complaints are fixable, almost none get fixed",
                 fontsize=13, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(f"{cc.CHARTS}/C1_resolution_gap.png", dpi=140)
    plt.close()

    print(f"negatives={n_neg} | actionable={actionable} ({actionable/n_neg:.1%}) | "
          f"requested={requested} ({requested/n_neg:.1%}) | "
          f"specific_remedy(neg)={specific_neg} ({specific_neg/n_neg:.2%}) | "
          f"specific_remedy(all)={specific_all} ({specific_all/len(ext):.2%}) | collapse={collapse:.0f}x")
    print("reply composition (replied negatives): "
          + ", ".join(f"{comp_lab[k]} {comp_n[k]} ({comp_n[k]/comp_total:.1%})" for k in comp_order))
    print("wrote C1_resolution_gap.png + CC2_resolution_gap.csv")


if __name__ == "__main__":
    main()
