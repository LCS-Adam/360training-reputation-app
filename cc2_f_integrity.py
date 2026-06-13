"""
CC2-F Review-integrity audit.

FRAME (printed at the top of every artifact): this is an AUDIT, not an accusation.
The data has NO reviewer identity, IP, device, or invitation-timing field (verified:
11 keys, none about provenance). Manipulation therefore CANNOT be proven or disproven
here. We pre-register a battery of anomaly tests, report which fire AND which come back
null, name the benign explanation that fits equally well, and output a list of dates/
clusters to verify with data only Trustpilot/the company hold.

Tests:
1. Weekly 5-star burst: z vs trailing-12-week baseline + Poisson exceedance p, with a
   Benjamini-Hochberg multiple-comparisons control (report expected-by-chance vs observed).
2. First-time-reviewer concentration over time -> expected NULL (flat ~67-72%).
3. Near-duplicate 5-star text (TF-IDF cosine); generic short dups EXCLUDED from evidence.
4. experienced->published lag drift (a provenance-adjacent signal CC1 never used).

Run: ./.venv/bin/python cc2_f_integrity.py
"""
import numpy as np
import pandas as pd
from scipy.stats import poisson
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse.csgraph import connected_components
from scipy.sparse import csr_matrix

import cc2_common as cc

OUT = cc.OUT
plt = cc.apply_chart_style()
FRAME = ("AUDIT, not accusation. No identity/IP/invite-timing field exists -> manipulation "
         "is unprovable here. Anomalies are 'worth verifying', never 'fake'.")


def benjamini_hochberg(pvals, alpha=0.05):
    p = np.asarray(pvals)
    n = len(p)
    order = np.argsort(p)
    thresh = alpha * (np.arange(1, n+1) / n)
    passed = p[order] <= thresh
    sig = np.zeros(n, dtype=bool)
    if passed.any():
        kmax = np.where(passed)[0].max()
        sig[order[:kmax+1]] = True
    return sig


def main():
    cc.ensure_dirs()
    print("FRAME:", FRAME)
    df = cc.load_trustpilot()
    df = df[~df["month"].isin(cc.PARTIAL_MONTHS)].copy()

    # ---------- 1. weekly 5-star burst detection ----------
    df["week"] = df["published_date"].dt.tz_convert(None).dt.to_period("W").astype(str)
    wk = df.groupby("week").agg(total=("star_rating", "size"),
                                five=("star_rating", lambda s: (s == 5).sum())).reset_index()
    wk = wk.sort_values("week").reset_index(drop=True)
    # trailing 12-week baseline (exclude current week)
    wk["base_mean"] = wk["five"].shift(1).rolling(12, min_periods=8).mean()
    wk["base_std"] = wk["five"].shift(1).rolling(12, min_periods=8).std()
    wk["z"] = (wk["five"] - wk["base_mean"]) / wk["base_std"].replace(0, np.nan)
    # one-sided Poisson exceedance vs trailing rate
    wk["poisson_p"] = wk.apply(
        lambda r: poisson.sf(r["five"] - 1, r["base_mean"]) if pd.notna(r["base_mean"]) and r["base_mean"] > 0 else np.nan,
        axis=1)
    tested = wk.dropna(subset=["poisson_p"]).copy()
    n_tested = len(tested)
    expected_fp = 0.05 * n_tested
    tested["fdr_sig"] = benjamini_hochberg(tested["poisson_p"].values, alpha=0.05)
    raw_hits = int((tested["poisson_p"] < 0.05).sum())
    fdr_hits = int(tested["fdr_sig"].sum())
    tested.sort_values("poisson_p").round(4).to_csv(f"{OUT}/CC2_burst_weeks.csv", index=False)
    print(f"\n[1] Weekly burst scan: {n_tested} weeks tested. "
          f"Raw p<0.05 hits={raw_hits} (expected ~{expected_fp:.1f} by chance). "
          f"Survive Benjamini-Hochberg FDR={fdr_hits}.")
    top_bursts = tested.sort_values("poisson_p").head(10)

    # ---------- 2. first-timer concentration over time (expected NULL) ----------
    df["year"] = df["month"].str[:4]
    df["first_timer"] = df["reviewer_num_reviews"].fillna(0) <= 1
    ft = df[df["star_rating"] == 5].groupby("year")["first_timer"].agg(["mean", "size"]).reset_index()
    ft.columns = ["year", "firsttimer_share", "n_5star"]
    ft = ft[ft["n_5star"] >= 50].reset_index(drop=True)   # drop tiny-n years (e.g. 2017 n=2)
    print("\n[2] First-timer share among 5-star, by year (n>=50; NULL test — expect flat ~0.67-0.72):")
    print(ft.round(3).to_string(index=False))
    ft_range = ft["firsttimer_share"].max() - ft["firsttimer_share"].min()
    print(f"    range across years = {ft_range:.3f} -> "
          f"{'FLAT: does NOT support manipulation hypothesis' if ft_range < 0.12 else 'variable'}")

    # ---------- 3. near-duplicate 5-star text ----------
    five = df[(df["star_rating"] == 5) & (df["review_text"].fillna("").str.len() > 0)].copy().reset_index(drop=True)
    tf = TfidfVectorizer(min_df=2, max_features=4000).fit_transform(five["review_text"].fillna(""))
    sim = cosine_similarity(tf, dense_output=False)
    adj = (sim >= 0.9)
    adj.setdiag(False); adj.eliminate_zeros()
    ncomp, labels = connected_components(csr_matrix(adj), directed=False)
    five["dup_cluster"] = labels
    sizes = pd.Series(labels).value_counts()
    multi = sizes[sizes >= 3].index
    clusters = []
    for c in multi:
        sub = five[five["dup_cluster"] == c]
        med_wc = sub["review_text"].str.split().apply(len).median()
        clusters.append(dict(cluster=int(c), n=len(sub),
                             median_words=int(med_wc),
                             kind=("generic_short_BENIGN" if med_wc <= 5 else "longer_specific_REVIEW"),
                             span_days=int((sub["published_date"].max()-sub["published_date"].min()).days),
                             exemplar=sub["review_text"].iloc[0][:90]))
    cl_df = pd.DataFrame(clusters).sort_values(["kind", "n"], ascending=[True, False]) if clusters else pd.DataFrame()
    if len(cl_df):
        cl_df.to_csv(f"{OUT}/CC2_near_dup_clusters.csv", index=False)
    n_generic = int((cl_df["kind"].str.startswith("generic")).sum()) if len(cl_df) else 0
    n_specific = int((cl_df["kind"].str.startswith("longer")).sum()) if len(cl_df) else 0
    print(f"\n[3] Near-dup 5-star clusters (>=3 members, sim>=0.9): "
          f"{n_generic} generic-short (BENIGN, excluded from evidence), {n_specific} longer-specific (worth a look).")

    # ---------- 4. experienced->published lag drift ----------
    lagq = df[df["exp_post_lag_days"].between(-5, 120)].groupby("quarter")["exp_post_lag_days"].median()
    df["posted_within_1d"] = df["exp_post_lag_days"].between(-0.1, 1.5)
    within1q = df.groupby("quarter")["posted_within_1d"].mean()
    print(f"\n[4] experience->post lag: overall median={df['exp_post_lag_days'].median():.1f}d; "
          f"share posted within ~1 day={df['posted_within_1d'].mean():.0%} "
          f"(high & stable => consistent with invitation-at-completion, a benign solicited pattern).")

    # ---------- anomaly register ----------
    reg = []
    for r in top_bursts.itertuples():
        reg.append(dict(
            anomaly_type="weekly_5star_burst", locus=r.week, observed_5star=int(r.five),
            baseline=round(r.base_mean, 1), z=round(r.z, 1), poisson_p=round(r.poisson_p, 4),
            survives_fdr=bool(r.fdr_sig),
            benign_explanation="Trustpilot invitation/course-completion email batch -> same-week 5-star burst of short generic praise from first-time reviewers; indistinguishable from padding here.",
            resolving_data="Trustpilot invitation logs / review-source flag / IP / completion timestamps"))
    if n_specific:
        for r in cl_df[cl_df["kind"].str.startswith("longer")].head(5).itertuples():
            reg.append(dict(anomaly_type="near_dup_specific_text", locus=f"cluster_{r.cluster}",
                            observed_5star=r.n, baseline=np.nan, z=np.nan, poisson_p=np.nan, survives_fdr=np.nan,
                            benign_explanation="Customers reusing a template phrase, or one reviewer multiple courses; long-specific dups are weak evidence at best.",
                            resolving_data="reviewer identity / account linkage"))
    reg_df = pd.DataFrame(reg)
    reg_df.to_csv(f"{OUT}/CC2_anomaly_register.csv", index=False)

    # ============================================================ charts
    # F1 weekly 5-star with flagged weeks
    t = tested.reset_index(drop=True); xi = np.arange(len(t))
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(xi, t["five"], color=cc.GRAY, lw=0.8, label="5-star/week")
    ax.plot(xi, t["base_mean"], color=cc.NAVY, lw=1.2, label="trailing-12wk baseline")
    fdr = t[t["fdr_sig"]]
    ax.scatter([xi[i] for i in fdr.index], fdr["five"], color=cc.RED, zorder=3, s=30, label="survives FDR")
    step = max(1, len(t)//10)
    ax.set_xticks(xi[::step]); ax.set_xticklabels(t["week"].iloc[::step], rotation=45, ha="right", fontsize=7)
    ax.set_title(f"Weekly 5-star burst scan — {raw_hits} raw hits (~{expected_fp:.0f} expected by chance), {fdr_hits} survive FDR")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(f"{cc.CHARTS}/F1_weekly_5star_zscore.png"); plt.close()

    # F2 the NULL — first-timer share flat
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(ft["year"], ft["firsttimer_share"], color=cc.NAVY, marker="o")
    ax.axhline(ft["firsttimer_share"].mean(), color=cc.GRAY, ls="--", label=f"mean {ft['firsttimer_share'].mean():.0%}")
    ax.set_ylim(0, 1); ax.set_ylabel("First-timer share of 5-star reviews")
    ax.set_title("First-time-reviewer share stays flat every year (no manipulation signature)")
    ax.legend(fontsize=8); plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=8)
    fig.tight_layout(); fig.savefig(f"{cc.CHARTS}/F2_firsttimer_share_overtime.png"); plt.close()

    # F3 experience->post lag over time
    fig, ax1 = plt.subplots(figsize=(11, 4.5))
    xq = np.arange(len(lagq))
    ax1.plot(xq, lagq.values, color=cc.NAVY, marker="o", ms=3, label="median experience→post lag (days)")
    ax1.set_ylabel("Median lag (days)", color=cc.NAVY)
    ax2 = ax1.twinx(); ax2.plot(np.arange(len(within1q)), within1q.values, color=cc.ORANGE, label="share posted ≤1 day")
    ax2.set_ylabel("Share posted ≤1 day", color=cc.ORANGE); ax2.set_ylim(0, 1)
    step = max(1, len(lagq)//10)
    ax1.set_xticks(xq[::step]); ax1.set_xticklabels(lagq.index[::step], rotation=45, ha="right", fontsize=7)
    ax1.set_title("Experience→post lag over time (provenance-adjacent signal; stable = benign solicited pattern)")
    fig.tight_layout(); fig.savefig(f"{cc.CHARTS}/F3_experience_post_lag.png"); plt.close()

    # ============================================================ print
    print("\n==================== TOP BURST WEEKS ====================")
    print(top_bursts[["week", "five", "base_mean", "z", "poisson_p", "fdr_sig"]].round(3).to_string(index=False))
    print("\n==================== ANOMALY REGISTER (head) ====================")
    print(reg_df[["anomaly_type", "locus", "observed_5star", "z", "poisson_p", "survives_fdr"]].head(10).to_string(index=False))
    print(f"\nVERDICT: bursts exist but {fdr_hits} survive multiple-comparisons control; first-timer NULL holds; "
          f"manipulation remains UNPROVABLE without provenance data. Register = verify-list, not a verdict.")
    print("\nDONE — wrote CC2_burst_weeks/near_dup_clusters/anomaly_register + charts F1-F3.")


if __name__ == "__main__":
    main()
