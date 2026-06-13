"""
CC2-B Driver model — which complaint themes accompany a 1-star rating.

Honesty posture (carried into every artifact):
- ASSOCIATIONAL / DESCRIPTIVE, not causal. Themes are keyword-derived from the
  SAME text that drives the rating, so ORs describe which complaints accompany
  low ratings — NOT that fixing a theme raises ratings.
- Keyword themes flag only ~58% of negative reviews; ORs characterize the tagged
  subset, not all negativity. (Reported up front.)
- The lead exhibit is the 1-star-vs-2-star conditional model: both classes are
  already negative, so a surviving OR is operational signal, not "negative word
  in negative review."
- scam_fraud is flagged near-tautological (≈ a 1-star sentiment word).

Run: ./.venv/bin/python cc2_b_drivers.py
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import average_precision_score

import cc2_common as cc

OUT = cc.OUT
plt = cc.apply_chart_style()

THEME_ORDER = list(cc.THEMES.keys())
EVALUATIVE = {"scam_fraud"}                      # near-tautological (a 1-star word)
TINY = {"offshore", "language_barrier"}          # n<30: near-separated, unstable OR
B_BOOT = 400
RNG = np.random.default_rng(42)


# ----------------------------------------------------------------- feature build
def build_features(df):
    X = pd.DataFrame(index=df.index)
    for t in THEME_ORDER:
        X[t] = df[f"th_{t}"].astype(int)
    X["log_word_count"] = np.log1p(df["word_count"])
    X["log_num_reviews"] = np.log1p(df["reviewer_num_reviews"].fillna(0))
    # regime dummies (reference = pre_break), absorbs the level shift in base negativity
    regime = np.where(df["month"] < "2024-03", "pre_break",
                      np.where(df["month"] < "2024-10", "early_decline", "deep_decline"))
    X["regime_early"] = (regime == "early_decline").astype(int)
    X["regime_deep"] = (regime == "deep_decline").astype(int)
    return X

CONTROLS = ["log_word_count", "log_num_reviews", "regime_early", "regime_deep"]


def fit_or(X, y):
    """Return dict feature->OR from an L2 logistic (C=1.0)."""
    m = LogisticRegression(penalty="l2", C=1.0, max_iter=2000, solver="lbfgs")
    m.fit(X, y)
    return dict(zip(X.columns, np.exp(m.coef_[0])))


def bootstrap_or(X, y, B=B_BOOT):
    """Percentile bootstrap CIs for ORs of an L2 logistic. Returns point + lo/hi per feature."""
    point = fit_or(X, y)
    n = len(X)
    Xv, yv = X.values, np.asarray(y)
    cols = list(X.columns)
    draws = {c: [] for c in cols}
    for _ in range(B):
        idx = RNG.integers(0, n, n)
        m = LogisticRegression(penalty="l2", C=1.0, max_iter=2000, solver="lbfgs")
        try:
            m.fit(Xv[idx], yv[idx])
            for c, o in zip(cols, np.exp(m.coef_[0])):
                draws[c].append(o)
        except Exception:
            continue
    out = {}
    for c in cols:
        arr = np.array(draws[c])
        out[c] = (point[c], np.percentile(arr, 2.5), np.percentile(arr, 97.5))
    return out


def marginal_or(df, y):
    """Single-theme logistic (no controls) per theme -> marginal OR + bootstrap CI."""
    res = {}
    for t in THEME_ORDER:
        X = df[[f"th_{t}"]].astype(int).rename(columns={f"th_{t}": t})
        res[t] = bootstrap_or(X, y, B=B_BOOT)[t]
    return res


# ----------------------------------------------------------------- main
def main():
    cc.ensure_dirs()
    df = cc.load_trustpilot()
    neg = cc.negatives(df)

    # coverage caveat (the load-bearing honesty number)
    neg_any_theme = neg[cc.THEME_COLS].any(axis=1).mean()
    print(f"COVERAGE: {neg_any_theme:.1%} of negative reviews carry >=1 keyword theme "
          f"({int(neg[cc.THEME_COLS].any(axis=1).sum())}/{len(neg)}); "
          f"{1-neg_any_theme:.1%} are untagged -> ORs describe the tagged subset only.")

    # theme negativity spread (the empirical anti-tautology rebuttal)
    spread = {t: df.loc[df[f"th_{t}"], "neg"].mean() for t in THEME_ORDER}
    print("\nTheme negativity spread (rebuttal: if circular, all ~equal):")
    for t, v in sorted(spread.items(), key=lambda x: x[1]):
        print(f"  {t:24s} {v:.0%}  (n={int(df['th_'+t].sum())})")

    X_all = build_features(df)
    y_1star = (df["star_rating"] == 1).astype(int)
    y_neg = df["neg"].astype(int)

    # ---- adjusted (multivariable) ORs, 1-star target
    print("\nFitting adjusted model (1-star ~ themes + controls), bootstrap CIs ...")
    adj = bootstrap_or(X_all, y_1star)
    # robustness: <=2 star target
    adj_neg = bootstrap_or(X_all, y_neg)
    # ---- marginal ORs
    print("Fitting marginal (univariate) ORs ...")
    marg = marginal_or(df, y_1star)

    # ---- 1-star vs 2-star conditional model (the lead anti-circularity exhibit)
    print("Fitting 1-star-vs-2-star conditional model (negatives only) ...")
    Xn = build_features(neg)
    y_1v2 = (neg["star_rating"] == 1).astype(int)
    cond = bootstrap_or(Xn, y_1v2)

    # ---- assemble OR table
    rows = []
    for t in THEME_ORDER:
        mp, ml, mh = marg[t]
        ap, al, ah = adj[t]
        anp, anl, anh = adj_neg[t]
        cp, cl, ch = cond[t]
        rows.append(dict(
            theme=t, n=int(df[f"th_{t}"].sum()), pct_negative=round(spread[t], 3),
            theme_type=("evaluative" if t in EVALUATIVE else "topical"),
            n_too_small=(t in TINY),
            marginal_OR=round(mp, 2), marginal_lo=round(ml, 2), marginal_hi=round(mh, 2),
            adjusted_OR=round(ap, 2), adjusted_lo=round(al, 2), adjusted_hi=round(ah, 2),
            adjusted_OR_neg2star=round(anp, 2),
            cond_1v2_OR=round(cp, 2), cond_1v2_lo=round(cl, 2), cond_1v2_hi=round(ch, 2),
        ))
    or_df = pd.DataFrame(rows).sort_values("adjusted_OR", ascending=False)
    or_df.to_csv(f"{OUT}/CC2_driver_odds_ratios.csv", index=False)

    # control ORs (reported separately, not in the forest plot) — adj[c] is (point, lo, hi)
    ctrl = {c: adj[c][0] for c in CONTROLS}

    # ---- GBT robustness (permutation importance)
    print("Fitting GBT + permutation importance (robustness) ...")
    gbt = GradientBoostingClassifier(random_state=42, n_estimators=200, max_depth=3)
    gbt.fit(X_all, y_1star)
    pi = permutation_importance(gbt, X_all, y_1star, n_repeats=10, random_state=42, scoring="average_precision")
    imp = pd.DataFrame({"feature": X_all.columns, "perm_importance": pi.importances_mean,
                        "perm_std": pi.importances_std})
    imp = imp[imp["feature"].isin(THEME_ORDER)].sort_values("perm_importance", ascending=False)
    imp["rank_gbt"] = range(1, len(imp) + 1)
    imp.round(5).to_csv(f"{OUT}/CC2_driver_importance_gbt.csv", index=False)

    # ---- co-occurrence matrix (themes within negatives)
    co = pd.DataFrame(index=THEME_ORDER, columns=THEME_ORDER, dtype=int)
    M = neg[cc.THEME_COLS].astype(int).values
    co.iloc[:, :] = M.T @ M
    co.to_csv(f"{OUT}/CC2_theme_cooccurrence.csv")

    # ---- temporal OR stability (adjusted, pre-2025 vs 2025+)
    print("Fitting temporal stability (pre-2025 vs 2025+) ...")
    pre = df[df["month"] < "2025-01"]
    post = df[(df["month"] >= "2025-01") & (~df["month"].isin(cc.PARTIAL_MONTHS))]
    or_pre = fit_or(build_features(pre), (pre["star_rating"] == 1).astype(int))
    or_post = fit_or(build_features(post), (post["star_rating"] == 1).astype(int))
    stab = pd.DataFrame([
        dict(theme=t, OR_pre2025=round(or_pre[t], 2), OR_2025plus=round(or_post[t], 2),
             stable=bool((or_pre[t] > 1) == (or_post[t] > 1)))
        for t in THEME_ORDER]).sort_values("OR_2025plus", ascending=False)
    stab.to_csv(f"{OUT}/CC2_driver_temporal_stability.csv", index=False)

    # ---- validation: stratified CV PR-AUC + base rate
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    proba = cross_val_predict(
        LogisticRegression(penalty="l2", C=1.0, max_iter=2000),
        X_all, y_1star, cv=skf, method="predict_proba")[:, 1]
    pr_auc = average_precision_score(y_1star, proba)
    base_rate = y_1star.mean()

    # ============================================================ charts
    forest = or_df.sort_values("adjusted_OR")
    colors = [cc.GRAY if r.n_too_small else (cc.ORANGE if r.theme_type == "evaluative" else cc.NAVY)
              for r in forest.itertuples()]
    fig, ax = plt.subplots(figsize=(9, 5.5))
    yps = np.arange(len(forest))
    ax.hlines(yps, forest["adjusted_lo"], forest["adjusted_hi"], color=colors, lw=2)
    ax.scatter(forest["adjusted_OR"], yps, color=colors, zorder=3, s=40)
    ax.axvline(1.0, color="black", lw=1, ls="--")
    ax.set_yticks(yps); ax.set_yticklabels([f"{r.theme}{' *' if r.n_too_small else ''}" for r in forest.itertuples()])
    ax.set_xscale("log"); ax.set_xlabel("How much each theme raises the odds of a 1-star review (log scale)")
    ax.set_title("What predicts a 1-star review")
    ax.text(0.99, 0.02, "navy=topical  orange=evaluative(near-tautological)  grey *=n<30 unstable",
            transform=ax.transAxes, ha="right", fontsize=7, color=cc.GRAY)
    fig.tight_layout(); fig.savefig(f"{cc.CHARTS}/05_driver_forest_plot.png"); plt.close()

    # marginal vs adjusted
    mva = or_df[~or_df["n_too_small"]].sort_values("adjusted_OR")
    fig, ax = plt.subplots(figsize=(9, 5))
    yps = np.arange(len(mva)); h = 0.36
    ax.barh(yps + h/2, mva["marginal_OR"], height=h, color=cc.GRAY, label="marginal (univariate)")
    ax.barh(yps - h/2, mva["adjusted_OR"], height=h, color=cc.NAVY, label="adjusted (multivariable)")
    ax.axvline(1.0, color="black", lw=1, ls="--")
    ax.set_yticks(yps); ax.set_yticklabels(mva["theme"]); ax.set_xlabel("Odds ratio for 1-star")
    ax.set_title("Marginal vs adjusted ORs — the gap is the co-occurrence correction"); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(f"{cc.CHARTS}/06_marginal_vs_adjusted.png"); plt.close()

    # GBT importance
    fig, ax = plt.subplots(figsize=(8.5, 5))
    impp = imp.sort_values("perm_importance")
    ax.barh(impp["feature"], impp["perm_importance"], xerr=impp["perm_std"], color=cc.NAVY)
    ax.set_xlabel("Permutation importance (Δ PR-AUC)")
    ax.set_title("Robustness check — gradient-boosted importance corroborates the OR ranking")
    fig.tight_layout(); fig.savefig(f"{cc.CHARTS}/07_robustness_importance.png"); plt.close()

    # 1-star vs 2-star conditional (the lead exhibit)
    cnd = or_df[~or_df["n_too_small"]].sort_values("cond_1v2_OR")
    colors2 = [cc.ORANGE if r.theme_type == "evaluative" else cc.RED for r in cnd.itertuples()]
    fig, ax = plt.subplots(figsize=(9, 5))
    yps = np.arange(len(cnd))
    ax.hlines(yps, cnd["cond_1v2_lo"], cnd["cond_1v2_hi"], color=colors2, lw=2)
    ax.scatter(cnd["cond_1v2_OR"], yps, color=colors2, zorder=3, s=40)
    ax.axvline(1.0, color="black", lw=1, ls="--")
    ax.set_yticks(yps); ax.set_yticklabels(cnd["theme"]); ax.set_xscale("log")
    ax.set_xlabel("OR for 1-star vs 2-star (among negative reviews only, log scale)")
    ax.set_title("Anti-circularity exhibit — what separates furious (1★) from annoyed (2★)")
    fig.tight_layout(); fig.savefig(f"{cc.CHARTS}/08_1star_vs_2star_drivers.png"); plt.close()

    # ============================================================ print for spot-review
    pd.set_option("display.width", 220, "display.max_columns", 30)
    print("\n==================== ODDS-RATIO TABLE (sorted by adjusted OR) ====================")
    print(or_df.to_string(index=False))
    print("\nControl ORs (adjusted model):", {k: round(v, 3) for k, v in ctrl.items()})
    print("\n==================== GBT IMPORTANCE ====================")
    print(imp.round(4).to_string(index=False))
    print("\n==================== TEMPORAL STABILITY ====================")
    print(stab.to_string(index=False))
    print(f"\nValidation: 5-fold PR-AUC = {pr_auc:.3f} (base rate 1-star = {base_rate:.3f}, "
          f"lift = {pr_auc/base_rate:.2f}x)")
    print(f"Coverage of negatives by >=1 theme: {neg_any_theme:.1%}")

    # stash scalars for the summary + downstream A counterfactual
    pd.DataFrame([dict(neg_theme_coverage=round(neg_any_theme, 4), pr_auc=round(pr_auc, 4),
                       base_rate_1star=round(base_rate, 4),
                       neg_spread_min=round(min(spread.values()), 3),
                       neg_spread_max=round(max(spread.values()), 3))]
                 ).to_csv(f"{OUT}/CC2_driver_meta.csv", index=False)
    print("\nDONE — wrote CC2_driver_*.csv and charts 05-08.")


if __name__ == "__main__":
    main()
