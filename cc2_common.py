"""
cc2_common.py — shared foundation for the CC2 advanced-analytics build.

ONE data loader + ONE theme taxonomy, lifted verbatim (semantically) from
cc1_analysis.py so every CC2 workstream reconciles with CC1. The regex theme
patterns are identical to CC1's matches; capture groups are rewritten as
non-capturing (?:...) only to silence pandas-3.0 str.contains warnings — they
match exactly the same text.

Provides:
  load_trustpilot()      -> DataFrame with parsed dates, month/quarter, neg, text,
                            has_reply, reply_lag_days, word_count, review_id, + th_* flags
  load_glitches()        -> the exam-glitch CSV (BOM-aware)
  THEMES / THEME_RX      -> the 10-theme taxonomy
  PARTIAL_MONTHS, MIN_N  -> partial-month set and small-n noise floor
  add_theme_flags(df)    -> attach th_<theme> boolean columns
  negatives(df)          -> df[df.neg]
  monthly_metrics(df)    -> the CC1 monthly aggregation (n, avg_rating, neg_share, ...)
"""
import json
import re
import hashlib
from collections import OrderedDict

import numpy as np
import pandas as pd

# ----------------------------------------------------------------- paths
SRC = "00_source_materials"
OUT = "01_analytics_outputs"
CHARTS = f"{OUT}/CC2_chart_pack"

# ----------------------------------------------------------------- constants (inherited from CC1)
PARTIAL_MONTHS = {"2014-07", "2026-06"}   # first observed (partial) + current (in-progress)
MIN_N = 40                                # below this, a monthly rate is noise-flagged
BASELINE_YEAR = "2023"                    # pre-decline reference window

# ----------------------------------------------------------------- taxonomy (single source of truth)
# Identical semantics to cc1_analysis.py THEMES; groups made non-capturing for pandas 3.0.
THEMES = OrderedDict([
    ("billing_refund",        [r"refund", r"\bcharg", r"money back", r"overcharg", r"double charg",
                               r"billing", r"\bdispute", r"chargeback", r"my money", r"reimburs"]),
    ("support_service",       [r"customer service", r"customer support", r"no help", r"unhelpful",
                               r"\brude\b", r"no response", r"never call(?:ed)? back",
                               r"no one (?:answers|responds|helps)",
                               r"poor service", r"horrible service", r"terrible service"]),
    ("phone_automation",      [r"\bautomated\b", r"\brobot", r"\bbot\b", r"\bivr\b", r"\bmachine\b",
                               r"recording", r"can'?t (?:reach|talk to) a (?:person|human)", r"no human",
                               r"automatic system", r"phone tree"]),
    ("language_barrier",      [r"language barrier", r"hard to understand", r"\baccent", r"broken english",
                               r"don'?t speak english", r"couldn'?t understand them"]),
    ("offshore",              [r"costa rica", r"offshore", r"overseas", r"outsourc", r"foreign call"]),
    ("exam_test_glitch",      [r"glitch", r"kicked me out", r"kicked out", r"\bfroze\b", r"freezes", r"freezing",
                               r"crash", r"\berror", r"\brestart", r"lost (?:my )?progress", r"timed out",
                               r"shut off", r"lock(?:ed)? up", r"start over"]),
    ("certificate_reporting", [r"certificate", r"\bcertif", r"report(?:ed)? to (?:the )?(?:state|tabc|dmv|board)",
                               r"not reported", r"never (?:got|received) (?:my )?certif", r"\blicense", r"\bdmv\b",
                               r"\btabc\b", r"completion (?:record|certif)"]),
    ("access_expiration",     [r"expir", r"\b60 day", r"\b30 day", r"\b6 month", r"locked out", r"time limit",
                               r"access (?:window|period|expired)", r"no longer access", r"only good for"]),
    ("scam_fraud",            [r"\bscam", r"\bfraud", r"rip(?:\s|-)?off", r"\bfake\b", r"predatory", r"\bcrook",
                               r"\bthief", r"steal", r"stole"]),
    ("course_content",        [r"outdated", r"\bboring\b", r"confusing", r"poor(?:ly)? (?:written|designed)",
                               r"content (?:is|was) (?:bad|poor|outdated)", r"typos?", r"grammatical"]),
])
THEME_RX = {t: re.compile("|".join(pats)) for t, pats in THEMES.items()}
THEME_COLS = [f"th_{t}" for t in THEMES]


def _review_id(row):
    """Deterministic join key. Include `page` so genuine duplicate submissions
    (same reviewer/text/date) remain DISTINCT rows — F's near-dup hunt needs that."""
    raw = f"{row.get('published_date','')}|{row.get('reviewer_name','')}|{row.get('review_text','')}|{row.get('page','')}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def add_theme_flags(df):
    for t, rx in THEME_RX.items():
        df[f"th_{t}"] = df["text"].str.contains(rx)
    return df


def load_trustpilot(path=None):
    path = path or f"{SRC}/360training_trustpilot_ALL_reviews.json"
    with open(path) as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    df["review_id"] = df.apply(_review_id, axis=1)
    df["published_date"] = pd.to_datetime(df["published_date"], utc=True, format="ISO8601")
    df["company_reply_date"] = pd.to_datetime(df["company_reply_date"], utc=True, format="ISO8601")
    df["experienced_date"] = pd.to_datetime(df["experienced_date"], utc=True, format="ISO8601")
    _pub_naive = df["published_date"].dt.tz_convert(None)
    df["month"] = _pub_naive.dt.to_period("M").astype(str)
    df["quarter"] = _pub_naive.dt.to_period("Q").astype(str)
    df["star_rating"] = df["star_rating"].astype(int)
    df["neg"] = df["star_rating"] <= 2
    df["text"] = (df["review_title"].fillna("") + " . " + df["review_text"].fillna("")).str.lower()
    df["word_count"] = df["review_text"].fillna("").str.split().apply(len)
    df["has_reply"] = df["company_reply"].notna() & (df["company_reply"].astype(str).str.len() > 0)
    df["reply_lag_days"] = (df["company_reply_date"] - df["published_date"]).dt.total_seconds() / 86400
    # experience -> publish lag (F integrity signal; unused by CC1)
    df["exp_post_lag_days"] = (df["published_date"] - df["experienced_date"]).dt.total_seconds() / 86400
    df = add_theme_flags(df)
    return df


def load_glitches(path=None):
    path = path or f"{SRC}/360training_exam_glitches.csv"
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["published_date"] = pd.to_datetime(df["published_date"], utc=True, format="ISO8601")
    _pub_naive = df["published_date"].dt.tz_convert(None)
    df["month"] = _pub_naive.dt.to_period("M").astype(str)
    df["quarter"] = _pub_naive.dt.to_period("Q").astype(str)
    df["star_rating"] = df["star_rating"].astype(int)
    df["text"] = (df["review_title"].fillna("") + " . " + df["review_text"].fillna("")).str.lower()
    return df


def negatives(df):
    return df[df["neg"]].copy()


def non_partial(df):
    return df[~df["month"].isin(PARTIAL_MONTHS)].copy()


def monthly_metrics(df):
    """CC1's monthly aggregation, recomputed (reconciles with CC1_monthly_metrics.csv)."""
    valid = non_partial(df)
    m = valid.groupby("month").agg(
        n=("star_rating", "size"),
        neg_count=("neg", "sum"),
        avg_rating=("star_rating", "mean"),
        neg_share=("neg", "mean"),
        reply_rate=("has_reply", "mean"),
    ).reset_index()
    lag = valid[valid["reply_lag_days"].notna()].groupby("month")["reply_lag_days"].median().rename("median_reply_lag")
    m = m.merge(lag, on="month", how="left")
    m["noisy_flag"] = m["n"] < MIN_N
    return m


def ensure_dirs():
    import os
    os.makedirs(CHARTS, exist_ok=True)


# Slide-ready matplotlib defaults (consistent across the CC2 chart pack)
def apply_chart_style():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "figure.dpi": 130, "savefig.dpi": 130, "font.size": 10,
        # match the app's card shade so charts sit flush (no floating-white rectangles)
        "figure.facecolor": "#efeff0", "savefig.facecolor": "#efeff0", "axes.facecolor": "#efeff0",
        "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlecolor": "#1d1d25",
        "axes.labelcolor": "#1d1d25", "text.color": "#1d1d25",
        "axes.edgecolor": "#9aa0aa", "xtick.color": "#3b4049", "ytick.color": "#3b4049",
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.alpha": 0.25, "grid.color": "#b8bcc4",
        "legend.facecolor": "#efeff0", "legend.edgecolor": "#cdced3", "legend.framealpha": 0.9,
    })
    return plt


# Palette
NAVY = "#1f4e79"
RED = "#c0392b"
ORANGE = "#e67e22"
GRAY = "#7f8c8d"
GREEN = "#27ae60"


if __name__ == "__main__":
    # Smoke test + reconciliation check against CC1.
    df = load_trustpilot()
    print(f"loaded n={len(df)}  distinct review_id={df['review_id'].nunique()}")
    print(f"neg n={int(df['neg'].sum())}  reply rate={df['has_reply'].mean():.3f}")
    print("theme counts (reconcile vs CC1):")
    for t in THEMES:
        print(f"  {t:24s} {int(df['th_'+t].sum()):5d}")
    m = monthly_metrics(df)
    print(f"monthly rows={len(m)}  post-2024-03 rows={len(m[m.month>='2024-03'])}")
    print(m[m.month >= "2024-09"][["month", "n", "neg_count", "neg_share", "median_reply_lag"]].to_string(index=False))
