"""
CC1 value-add analytics for the 360training executive research project.

ONE pipeline, ONE theme taxonomy (THEMES below), reused across deliverables 1, 5, 6.
All monthly rates carry n. Partial/sparse buckets are flagged, never silently used.
Business-impact tables are explicitly directional with NO fabricated absolute numbers.

Run:  ./.venv/bin/python cc1_analysis.py
Outputs land in 01_analytics_outputs/ (CSVs) and CC1_chart_pack/ (PNGs).
Summary .md narratives are written separately after the operator reviews raw tables.
"""
import json, csv, re, math
from collections import defaultdict, Counter
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SRC = "00_source_materials"
OUT = "01_analytics_outputs"
CHARTS = f"{OUT}/CC1_chart_pack"
TODAY = datetime(2026, 6, 12)  # session date; data ends 2026-06 (partial)

# ---------------------------------------------------------------- load
def load_trustpilot():
    with open(f"{SRC}/360training_trustpilot_ALL_reviews.json") as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    df["published_date"] = pd.to_datetime(df["published_date"], utc=True, format="ISO8601")
    df["company_reply_date"] = pd.to_datetime(df["company_reply_date"], utc=True, format="ISO8601")
    df["month"] = df["published_date"].dt.to_period("M").astype(str)
    df["quarter"] = df["published_date"].dt.to_period("Q").astype(str)
    df["star_rating"] = df["star_rating"].astype(int)
    df["neg"] = df["star_rating"] <= 2
    df["text"] = (df["review_title"].fillna("") + " . " + df["review_text"].fillna("")).str.lower()
    df["has_reply"] = df["company_reply"].notna() & (df["company_reply"].astype(str).str.len() > 0)
    df["reply_lag_days"] = (df["company_reply_date"] - df["published_date"]).dt.total_seconds() / 86400
    return df

def load_glitches():
    df = pd.read_csv(f"{SRC}/360training_exam_glitches.csv", encoding="utf-8-sig")
    df["published_date"] = pd.to_datetime(df["published_date"], utc=True, format="ISO8601")
    df["month"] = df["published_date"].dt.to_period("M").astype(str)
    df["quarter"] = df["published_date"].dt.to_period("Q").astype(str)
    df["star_rating"] = df["star_rating"].astype(int)
    df["text"] = (df["review_title"].fillna("") + " . " + df["review_text"].fillna("")).str.lower()
    return df

# ---------------------------------------------------------------- taxonomy (single source of truth)
# Keyword themes. word-boundary regex; tuned to reduce obvious false positives.
THEMES = {
    "billing_refund":        [r"refund", r"\bcharg", r"money back", r"overcharg", r"double charg",
                              r"billing", r"\bdispute", r"chargeback", r"my money", r"reimburs"],
    "support_service":       [r"customer service", r"customer support", r"no help", r"unhelpful",
                              r"\brude\b", r"no response", r"never call(ed)? back", r"no one (answers|responds|helps)",
                              r"poor service", r"horrible service", r"terrible service"],
    "phone_automation":      [r"\bautomated\b", r"\brobot", r"\bbot\b", r"\bivr\b", r"\bmachine\b",
                              r"recording", r"can'?t (reach|talk to) a (person|human)", r"no human",
                              r"automatic system", r"phone tree"],
    "language_barrier":      [r"language barrier", r"hard to understand", r"\baccent", r"broken english",
                              r"don'?t speak english", r"couldn'?t understand them"],
    "offshore":              [r"costa rica", r"offshore", r"overseas", r"outsourc", r"foreign call"],
    "exam_test_glitch":      [r"glitch", r"kicked me out", r"kicked out", r"\bfroze\b", r"freezes", r"freezing",
                              r"crash", r"\berror", r"\brestart", r"lost (my )?progress", r"timed out",
                              r"shut off", r"lock(ed)? up", r"start over"],
    "certificate_reporting": [r"certificate", r"\bcertif", r"report(ed)? to (the )?(state|tabc|dmv|board)",
                              r"not reported", r"never (got|received) (my )?certif", r"\blicense", r"\bdmv\b",
                              r"\btabc\b", r"completion (record|certif)"],
    "access_expiration":     [r"expir", r"\b60 day", r"\b30 day", r"\b6 month", r"locked out", r"time limit",
                              r"access (window|period|expired)", r"no longer access", r"only good for"],
    "scam_fraud":            [r"\bscam", r"\bfraud", r"rip(\s|-)?off", r"\bfake\b", r"predatory", r"\bcrook",
                              r"\bthief", r"steal", r"stole"],
    "course_content":        [r"outdated", r"\bboring\b", r"confusing", r"poor(ly)? (written|designed)",
                              r"content (is|was) (bad|poor|outdated)", r"typos?", r"grammatical"],
}
THEME_RX = {t: re.compile("|".join(pats)) for t, pats in THEMES.items()}

def tag_themes(text):
    return {t: bool(rx.search(text)) for t, rx in THEME_RX.items()}

def add_theme_flags(df):
    flags = df["text"].apply(lambda x: pd.Series(tag_themes(x)))
    return pd.concat([df, flags.add_prefix("th_")], axis=1)

# ---------------------------------------------------------------- helpers
PARTIAL_MONTHS = {"2014-07", "2026-06"}  # first observed (likely partial) + current (in-progress)
MIN_N = 40  # below this, monthly rates flagged as noisy

def ensure_dirs():
    import os
    os.makedirs(CHARTS, exist_ok=True)

# ================================================================ 1. THEME SEVERITY + TIMING
def deliverable_theme_severity(df):
    rows = []
    total = len(df)
    for t in THEMES:
        col = f"th_{t}"
        sub = df[df[col]]
        n = len(sub)
        if n == 0:
            continue
        neg = sub["neg"].mean()
        mean_star = sub["star_rating"].mean()
        share_of_all = n / total
        share_of_neg = (sub["neg"].sum()) / df["neg"].sum()
        # severity score: blend of how negative the theme skews and its volume (0-100, directional)
        severity = round(100 * (neg * 0.6 + (1 - mean_star / 5) * 0.4), 1)
        rows.append(dict(theme=t, n=n, n_too_small=(n < 30), share_of_all=round(share_of_all, 4),
                         mean_star=round(mean_star, 2), pct_negative=round(neg, 4),
                         share_of_all_negative=round(share_of_neg, 4), severity_score=severity))
    tdf = pd.DataFrame(rows).sort_values("severity_score", ascending=False)

    # timing: per-theme negative-volume by quarter (quarter chosen for stability on sparse themes)
    valid = df[~df["month"].isin(PARTIAL_MONTHS)]
    timing = []
    for t in THEMES:
        col = f"th_{t}"
        # quarterly count of negative theme mentions
        q = valid[valid[col] & valid["neg"]].groupby("quarter").size()
        qall = valid[valid[col]].groupby("quarter").size()
        if q.empty:
            continue
        # baseline = mean quarterly neg volume in 2023 (pre-decline reference)
        base = q[[i for i in q.index if i.startswith("2023")]]
        base_mean = base.mean() if len(base) else q.iloc[:4].mean()
        # first inflection quarter = first quarter (>=2024) at >=1.5x baseline and >=3 mentions
        infl = None
        for qtr in sorted(q.index):
            if qtr >= "2024Q1" and q[qtr] >= max(3, 1.5 * (base_mean if not math.isnan(base_mean) else 0)):
                infl = qtr; break
        peak_q = q.idxmax()
        timing.append(dict(theme=t, total_neg_mentions=int(q.sum()),
                           baseline_2023_q_avg=round(float(base_mean), 1) if not math.isnan(base_mean) else None,
                           first_inflection_quarter=infl, peak_quarter=peak_q,
                           peak_q_neg_mentions=int(q.max())))
    timing_df = pd.DataFrame(timing)
    merged = tdf.merge(timing_df, on="theme", how="left")
    merged.to_csv(f"{OUT}/CC1_theme_severity_timing.csv", index=False)
    return merged

# ================================================================ 2. CHANGE-POINT / STRUCTURAL BREAK
def mean_shift_break(series_df, value_col, weight_col="n"):
    """Find month that maximizes |mean_after - mean_before|, weighted, excluding tails."""
    s = series_df.reset_index(drop=True)
    best = None
    for i in range(4, len(s) - 4):  # need >=4 months each side
        before = s.iloc[:i]; after = s.iloc[i:]
        mb = np.average(before[value_col], weights=before[weight_col])
        ma = np.average(after[value_col], weights=after[weight_col])
        diff = ma - mb
        if best is None or abs(diff) > abs(best[1]):
            best = (s.iloc[i]["month"], diff, round(mb, 3), round(ma, 3))
    return best

def deliverable_change_point(df):
    valid = df[~df["month"].isin(PARTIAL_MONTHS)].copy()
    m = valid.groupby("month").agg(n=("star_rating", "size"),
                                   avg_rating=("star_rating", "mean"),
                                   neg_share=("neg", "mean"),
                                   reply_rate=("has_reply", "mean")).reset_index()
    # reply lag monthly (median)
    lag = valid[valid["reply_lag_days"].notna()].groupby("month")["reply_lag_days"].median().rename("median_reply_lag")
    m = m.merge(lag, on="month", how="left")
    # restrict change-point search to the analytically relevant window (>=2022) where volume is stable
    win = m[m["month"] >= "2022-01"].reset_index(drop=True)

    results = []
    for metric in ["avg_rating", "neg_share", "median_reply_lag"]:
        sub = win.dropna(subset=[metric])
        b = mean_shift_break(sub.rename(columns={metric: "v"}), "v")
        if b:
            results.append(dict(metric=metric, break_month=b[0], shift=round(b[1], 3),
                                mean_before=b[2], mean_after=b[3],
                                method="weighted mean-shift (max |after-before|), >=4 mo/side, window>=2022-01"))
    # pre/post March-2024 explicit comparison (the inherited hypothesis)
    for label, lo, hi in [("pre_2024-03", "2023-01", "2024-02"), ("post_2024-03", "2024-03", "2026-05")]:
        seg = m[(m["month"] >= lo) & (m["month"] <= hi)]
        w = seg["n"]
        results.append(dict(metric=f"avg_rating::{label}", break_month="2024-03",
                            shift=None, mean_before=None,
                            mean_after=round(float(np.average(seg["avg_rating"], weights=w)), 3),
                            method=f"segment mean {lo}..{hi} (n={int(seg['n'].sum())})"))
        results.append(dict(metric=f"neg_share::{label}", break_month="2024-03",
                            shift=None, mean_before=None,
                            mean_after=round(float(np.average(seg["neg_share"], weights=w)), 4),
                            method=f"segment mean {lo}..{hi} (n={int(seg['n'].sum())})"))
    cp = pd.DataFrame(results)
    cp.to_csv(f"{OUT}/CC1_change_point_table.csv", index=False)
    m["noisy_flag"] = m["n"] < MIN_N
    m.to_csv(f"{OUT}/CC1_monthly_metrics.csv", index=False)
    return cp, m

# ================================================================ 3. REPLY TEMPLATE + QUALITY
APOLOGY_RX = re.compile(r"\b(sorry|apolog|regret|unfortunate)")
ESCALATE_RX = re.compile(r"(email|contact|reach out|customercare|call us|customer care|cust(\.|omer) care|@360training)")
OFFER_RX = re.compile(r"(refund|extend|reset|replace|credit|resolve|correct|fix|reactivat|restor|waive)")
PERSONAL_RX = re.compile(r"\b(your (course|exam|certif|refund|account|order)|specifically|in your case)")

def deliverable_reply(df):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
    reps = df[df["has_reply"]].copy()
    reps["reply_l"] = reps["company_reply"].astype(str).str.lower()
    reps["apology"] = reps["reply_l"].str.contains(APOLOGY_RX)
    reps["escalation"] = reps["reply_l"].str.contains(ESCALATE_RX)
    reps["offer"] = reps["reply_l"].str.contains(OFFER_RX)
    reps["personalized"] = reps["reply_l"].str.contains(PERSONAL_RX)
    reps["apology_only"] = reps["apology"] & ~reps["offer"] & ~reps["escalation"]
    reps["escalation_only"] = reps["escalation"] & ~reps["offer"]
    reps["reply_len"] = reps["company_reply"].astype(str).str.split().apply(len)

    # cluster reply text into templates
    X = TfidfVectorizer(stop_words="english", max_features=2000, ngram_range=(1, 2)).fit_transform(reps["reply_l"])
    k = 8
    km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X)
    reps["template_cluster"] = km.labels_
    # similarity: share in the single largest cluster = dominant-template concentration
    cluster_sizes = reps["template_cluster"].value_counts()

    # quality scores per cluster
    qrows = []
    for c, size in cluster_sizes.items():
        sub = reps[reps["template_cluster"] == c]
        # exemplar: shortest reply nearest cluster behavior
        exemplar = sub.iloc[0]["company_reply"]
        qrows.append(dict(template_cluster=int(c), n_replies=int(size),
                          share_of_replies=round(size / len(reps), 4),
                          personalization_rate=round(sub["personalized"].mean(), 3),
                          remedy_offer_rate=round(sub["offer"].mean(), 3),
                          apology_rate=round(sub["apology"].mean(), 3),
                          escalation_only_rate=round(sub["escalation_only"].mean(), 3),
                          apology_only_rate=round(sub["apology_only"].mean(), 3),
                          mean_reply_words=round(sub["reply_len"].mean(), 1),
                          exemplar=exemplar[:300].replace("\n", " ")))
    qdf = pd.DataFrame(qrows).sort_values("n_replies", ascending=False)
    qdf.to_csv(f"{OUT}/CC1_reply_template_variations.csv", index=False)

    # overall reply quality scores (and by star, and over time)
    overall = dict(metric="ALL", n=len(reps),
                   personalization_rate=round(reps["personalized"].mean(), 3),
                   remedy_offer_rate=round(reps["offer"].mean(), 3),
                   apology_rate=round(reps["apology"].mean(), 3),
                   escalation_only_rate=round(reps["escalation_only"].mean(), 3),
                   apology_only_rate=round(reps["apology_only"].mean(), 3),
                   mean_reply_words=round(reps["reply_len"].mean(), 1),
                   distinct_templates_k=k,
                   dominant_template_share=round(cluster_sizes.iloc[0] / len(reps), 3))
    by_star = []
    for s in [1, 2, 3, 4, 5]:
        sub = reps[reps["star_rating"] == s]
        if len(sub):
            by_star.append(dict(metric=f"star_{s}", n=len(sub),
                                personalization_rate=round(sub["personalized"].mean(), 3),
                                remedy_offer_rate=round(sub["offer"].mean(), 3),
                                apology_rate=round(sub["apology"].mean(), 3),
                                escalation_only_rate=round(sub["escalation_only"].mean(), 3),
                                apology_only_rate=round(sub["apology_only"].mean(), 3),
                                mean_reply_words=round(sub["reply_len"].mean(), 1),
                                distinct_templates_k="", dominant_template_share=""))
    qscore = pd.DataFrame([overall] + by_star)
    qscore.to_csv(f"{OUT}/CC1_reply_quality_scores.csv", index=False)
    return qdf, qscore, reps

# ================================================================ 4. REVIEWER VALIDITY HEURISTICS (NOT fake detection)
def deliverable_credibility(df):
    d = df.copy()
    d["word_count"] = d["review_text"].fillna("").str.split().apply(len)
    d["has_numbers"] = d["text"].str.contains(r"\d")
    d["has_concrete_ref"] = d["text"].str.contains(
        r"(tabc|dmv|osha|food handler|notary|real estate|cosmetolog|hvac|exam|certificate|refund|\$\d)")
    d["is_generic_short"] = d["word_count"] <= 4
    d["first_time_reviewer"] = d["reviewer_num_reviews"].fillna(0) <= 1
    # validity score 0-100: rewards specificity/operational detail, NOT a fakeness verdict
    d["validity_score"] = (
        (d["word_count"].clip(0, 60) / 60 * 40) +
        (d["has_concrete_ref"].astype(int) * 30) +
        (d["has_numbers"].astype(int) * 15) +
        ((~d["is_generic_short"]).astype(int) * 15)
    ).round(1)
    d["low_info_flag"] = d["validity_score"] < 25  # informational, NOT authenticity

    flags = d[["star_rating", "month", "reviewer_name", "reviewer_num_reviews", "word_count",
               "has_concrete_ref", "has_numbers", "is_generic_short", "first_time_reviewer",
               "validity_score", "low_info_flag", "review_title"]].copy()
    flags.to_csv(f"{OUT}/CC1_review_credibility_flags.csv", index=False)

    # summary stats by star band
    summ = d.groupby(d["star_rating"]).agg(
        n=("validity_score", "size"),
        mean_validity=("validity_score", "mean"),
        pct_low_info=("low_info_flag", "mean"),
        mean_words=("word_count", "mean"),
        pct_concrete=("has_concrete_ref", "mean"),
        pct_first_time=("first_time_reviewer", "mean")).round(3).reset_index()
    return flags, summ, d

# ================================================================ 5. SPECIAL-TOPIC SCANS (reuse taxonomy + extra)
SPECIAL = {
    "phone_automation": "th_phone_automation",
    "language_barrier": "th_language_barrier",
    "offshore_costa_rica": "th_offshore",
    "certificate_reporting": "th_certificate_reporting",
    "scam_fraud_chargeback": "th_scam_fraud",
    "access_expiration": "th_access_expiration",
    "billing_refund": "th_billing_refund",
}
def deliverable_special(df):
    valid = df[~df["month"].isin(PARTIAL_MONTHS)]
    # window-share growth normalizes for BOTH window length and the ~halving of monthly volume.
    w_pre = df[(df["month"] >= "2023-01") & (df["month"] <= "2023-12")]              # 12 mo
    w_post = df[(df["month"] >= "2024-03") & (df["month"] <= "2025-12")]             # 22 mo
    n_pre, n_post = len(w_pre), len(w_post)
    rows = []
    for label, col in SPECIAL.items():
        sub = df[df[col]]
        n = len(sub)
        neg = sub["neg"].mean() if n else float("nan")
        share_pre = w_pre[col].mean()    # share of that window's reviews mentioning the topic
        share_post = w_post[col].mean()
        ratio = (share_post / share_pre) if share_pre else float("nan")
        rows.append(dict(topic=label, n_mentions=n, n_too_small=(n < 30),
                         pct_of_all=round(n / len(df), 4), pct_negative=round(neg, 3),
                         share_2023=round(share_pre, 4), share_2024_03_to_2025_12=round(share_post, 4),
                         growth_ratio_share=round(ratio, 2),
                         peak_quarter=(valid[valid[col]].groupby("quarter").size().idxmax()
                                       if valid[valid[col]].shape[0] else None)))
    sdf = pd.DataFrame(rows).sort_values("n_mentions", ascending=False)
    sdf.attrs["window_totals"] = (n_pre, n_post)
    sdf.to_csv(f"{OUT}/CC1_special_topic_scan.csv", index=False)
    return sdf

# ================================================================ 6. EXAM-GLITCH CROSSWALK
def deliverable_glitch(df, glitch):
    # glitch dataset timing vs in-corpus exam_test_glitch theme
    valid = df[~df["month"].isin(PARTIAL_MONTHS)]
    corpus_glitch = valid[valid["th_exam_test_glitch"]]
    g_q = glitch[~glitch["month"].isin(PARTIAL_MONTHS)].groupby("quarter").size().rename("glitch_csv_n")
    c_q = corpus_glitch.groupby("quarter").size().rename("corpus_glitch_theme_n")
    allneg_q = valid[valid["neg"]].groupby("quarter").size().rename("all_negative_n")
    cross = pd.concat([g_q, c_q, allneg_q], axis=1).fillna(0).astype(int).reset_index()
    cross = cross[cross["quarter"] >= "2023Q1"]
    cross.to_csv(f"{OUT}/CC1_exam_glitch_crosswalk.csv", index=False)

    stats = dict(
        glitch_csv_total=len(glitch),
        glitch_csv_pct_1_2_star=round((glitch["star_rating"] <= 2).mean(), 3),
        corpus_glitch_theme_total=int(corpus_glitch.shape[0]),
        corpus_glitch_pct_negative=round(corpus_glitch["neg"].mean(), 3),
        glitch_reply_rate=round(glitch["company_reply"].notna().mean(), 3),
    )
    return cross, stats

# ================================================================ 7. BUSINESS-IMPACT (DIRECTIONAL ONLY, no $ fabricated)
def deliverable_business_impact(df, monthly):
    # everything here is an observed driver metric + a labeled directional mechanism. NO absolute $.
    # Driver windows use SHARE of each window's reviews so length/volume don't bias the comparison.
    w_pre = df[(df["month"] >= "2023-01") & (df["month"] <= "2024-02")]
    w_post = df[(df["month"] >= "2024-03") & (df["month"] <= "2025-12")]
    refund_pre = (w_pre["th_billing_refund"] | w_pre["th_scam_fraud"]).mean()
    refund_post = (w_post["th_billing_refund"] | w_post["th_scam_fraud"]).mean()
    rows = [
        dict(channel="Trust erosion -> conversion drag",
             observed_driver="negative review share (share of window reviews <=2 star)",
             pre_2024_03=round(w_pre["neg"].mean(), 3), post_2024_03=round(w_post["neg"].mean(), 3),
             direction="higher visible negativity on Trustpilot depresses click-through/conversion for prospects who check reviews",
             magnitude_label="DIRECTIONAL - no conversion data available",
             confidence="medium (driver observed; revenue link inferred)"),
        dict(channel="Support friction -> retention/repeat drag",
             observed_driver="support_service reviews as share of all window reviews",
             pre_2024_03=round(w_pre["th_support_service"].mean(), 3),
             post_2024_03=round(w_post["th_support_service"].mean(), 3),
             direction="unresolved support lowers repeat purchase / renewal in a recurring-cert market",
             magnitude_label="DIRECTIONAL - no retention data available",
             confidence="medium"),
        dict(channel="Refund friction -> chargebacks/revenue leakage",
             observed_driver="billing_refund + scam_fraud as share of all window reviews",
             pre_2024_03=round(refund_pre, 3),
             post_2024_03=round(refund_post, 3),
             direction="refund disputes + public 'scam/chargeback' language raise dispute rate and processor risk",
             magnitude_label="DIRECTIONAL - no chargeback data available",
             confidence="medium-low (chargeback intent inferred from language)"),
        dict(channel="Reply failure -> reputation spillover",
             observed_driver="templated/escalation-only replies on negative reviews",
             pre_2024_03="see reply_quality_scores", post_2024_03="see reply_quality_scores",
             direction="generic public replies that don't resolve issues amplify rather than contain reputational damage",
             magnitude_label="DIRECTIONAL - qualitative",
             confidence="medium"),
    ]
    bdf = pd.DataFrame(rows)
    bdf.to_csv(f"{OUT}/CC1_business_impact_scenarios.csv", index=False)
    return bdf

# ================================================================ 8. CHARTS + EXECUTIVE TABLES
def charts(monthly, theme_df, special_df, reply_q, glitch_cross):
    mv = monthly[monthly["month"] >= "2022-01"].copy()
    # chart 1: monthly avg rating + neg share with March 2024 marker
    fig, ax1 = plt.subplots(figsize=(11, 5))
    ax1.plot(mv["month"], mv["avg_rating"], color="#1f4e79", label="Avg rating")
    ax1.set_ylabel("Avg rating", color="#1f4e79"); ax1.set_ylim(2, 5)
    ax2 = ax1.twinx()
    ax2.plot(mv["month"], mv["neg_share"], color="#c0392b", label="Neg share (<=2*)")
    ax2.set_ylabel("Negative share", color="#c0392b")
    ax1.axvline("2024-03", color="gray", ls="--"); ax1.text("2024-03", 4.8, " Mar-2024", color="gray")
    step = max(1, len(mv)//12)
    ax1.set_xticks(mv["month"][::step]); ax1.set_xticklabels(mv["month"][::step], rotation=45, ha="right", fontsize=8)
    plt.title("360training Trustpilot: avg rating vs negative share by month")
    fig.tight_layout(); fig.savefig(f"{CHARTS}/01_rating_vs_negshare.png", dpi=130); plt.close()

    # chart 2: theme severity bar
    td = theme_df.sort_values("severity_score").tail(10)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(td["theme"], td["severity_score"], color="#c0392b")
    for i, (n, s) in enumerate(zip(td["n"], td["severity_score"])):
        ax.text(s + 0.5, i, f"n={n}", va="center", fontsize=8)
    ax.set_xlabel("Severity score (directional 0-100)"); plt.title("Complaint theme severity")
    fig.tight_layout(); fig.savefig(f"{CHARTS}/02_theme_severity.png", dpi=130); plt.close()

    # chart 3: exam glitch crosswalk
    gc = glitch_cross
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(gc["quarter"], gc["glitch_csv_n"], color="#e67e22", label="Exam-glitch reviews (CSV)")
    ax.plot(gc["quarter"], gc["corpus_glitch_theme_n"], color="#1f4e79", marker="o", label="Corpus glitch-theme")
    ax.set_xticklabels(gc["quarter"], rotation=45, ha="right", fontsize=8)
    ax.legend(); plt.title("Exam/test glitch signal by quarter")
    fig.tight_layout(); fig.savefig(f"{CHARTS}/03_exam_glitch_timing.png", dpi=130); plt.close()

    # chart 4: monthly volume (context for noise)
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.bar(mv["month"], mv["n"], color="#7f8c8d")
    ax.axhline(MIN_N, color="red", ls=":", label=f"noise floor n={MIN_N}")
    ax.set_xticks(mv["month"][::step]); ax.set_xticklabels(mv["month"][::step], rotation=45, ha="right", fontsize=8)
    ax.legend(); plt.title("Monthly review volume (sample-size context)")
    fig.tight_layout(); fig.savefig(f"{CHARTS}/04_monthly_volume.png", dpi=130); plt.close()

# ---------------------------------------------------------------- main
def main():
    ensure_dirs()
    df = load_trustpilot()
    df = add_theme_flags(df)
    glitch = load_glitches()

    theme_df = deliverable_theme_severity(df)
    cp, monthly = deliverable_change_point(df)
    reply_var, reply_q, reps = deliverable_reply(df)
    cred_flags, cred_summ, _ = deliverable_credibility(df)
    special_df = deliverable_special(df)
    glitch_cross, glitch_stats = deliverable_glitch(df, glitch)
    biz = deliverable_business_impact(df, monthly)
    charts(monthly, theme_df, special_df, reply_q, glitch_cross)

    # ---- print raw tables for operator review (before writing _summary.md narratives)
    pd.set_option("display.width", 200, "display.max_columns", 30)
    print("\n#################### 1. THEME SEVERITY + TIMING ####################")
    print(theme_df.to_string(index=False))
    print("\n#################### 2. CHANGE-POINT ####################")
    print(cp.to_string(index=False))
    print("\n-- monthly (2024+ tail) --")
    print(monthly[monthly["month"] >= "2024-01"].to_string(index=False))
    print("\n#################### 3. REPLY TEMPLATES ####################")
    print(reply_var.to_string(index=False))
    print("\n-- reply quality scores --")
    print(reply_q.to_string(index=False))
    print("\n#################### 4. REVIEWER VALIDITY (by star) ####################")
    print(cred_summ.to_string(index=False))
    print("\n#################### 5. SPECIAL-TOPIC SCANS ####################")
    print(special_df.to_string(index=False))
    print("\n#################### 6. EXAM-GLITCH CROSSWALK ####################")
    print(glitch_cross.to_string(index=False))
    print("stats:", glitch_stats)
    print("\n#################### 7. BUSINESS IMPACT (directional) ####################")
    print(biz.to_string(index=False))
    print("\nDONE. CSVs in", OUT, "| charts in", CHARTS)

if __name__ == "__main__":
    main()
