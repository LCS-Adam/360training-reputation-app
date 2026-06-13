#!/usr/bin/env python3
"""
cc2_consistency.py — cross-workstream numeric consistency pass (pre-packaging gate).

Pulls the HEADLINE numbers each workstream (A-H) stands on, recomputes the base
facts from raw data as ground truth, and cross-checks that the workstreams agree
with each other and with CC1. Prints a reconciliation report + writes a consolidated
findings ledger (CC2_findings_ledger.md) for sign-off before the app/PDF/deck.

A skeptical panel's first probe is "do your own numbers agree?" — this answers it.
"""
import numpy as np
import pandas as pd
from cc2_common import load_trustpilot, THEMES, OUT

OK, FLAG = "  ok ", "FLAG "
rows = []          # (check, value, cross_ref, status)
def chk(name, value, cross_ref, ok):
    rows.append((name, value, cross_ref, OK if ok else FLAG))

df = load_trustpilot()
N = len(df)
neg = int(df["neg"].sum())
neg_share = neg / N

# ---- base population (ground truth from raw) ----
chk("total reviews", f"{N:,}", "CLAUDE.md says 10,601", N == 10601)
chk("negatives (<=2*)", f"{neg:,}", "B/F/H base = 2,206", neg == 2206)
chk("overall neg-share", f"{neg_share:.3f}", "= neg/total", True)
chk("reply coverage", f"{df['has_reply'].mean():.3f}", "CC1 ~0.915", abs(df['has_reply'].mean() - 0.915) < 0.02)

# ---- star deltas (D's spine: baseline 4.02 / sustained 3.49 / trough 3.12) ----
df["_y"] = df["month"].str[:4]
base23 = df[df["_y"] == "2023"]["star_rating"].mean()
sustained = df[(df["month"] >= "2024-03") & (df["month"] <= "2025-12")]["star_rating"].mean()
q4_24 = df[df["month"].isin(["2024-10", "2024-11", "2024-12"])]["star_rating"].mean()
chk("2023 baseline star", f"{base23:.2f}", "D says 4.02", abs(base23 - 4.02) < 0.05)
chk("sustained star (24-03..25-12)", f"{sustained:.2f}", "D says 3.49", abs(sustained - 3.49) < 0.05)
chk("Q4-2024 trough star", f"{q4_24:.2f}", "D says 3.12", abs(q4_24 - 3.12) < 0.05)
chk("sustained star delta", f"{sustained - base23:+.2f}", "D says -0.53", abs((sustained - base23) + 0.53) < 0.05)
chk("trough star delta", f"{q4_24 - base23:+.2f}", "D says -0.91", abs((q4_24 - base23) + 0.91) < 0.05)

# ---- neg-share rise (A's counterfactual: 2023 -> post-break, +0.160) ----
ns23 = df[df["_y"] == "2023"]["neg"].mean()
ns_post = df[df["month"] >= "2024-03"]["neg"].mean()
chk("2023 neg-share", f"{ns23:.3f}", "A baseline", True)
chk("post-break neg-share (24-03+)", f"{ns_post:.3f}", "A post-break", True)
chk("neg-share rise", f"{ns_post - ns23:+.3f}", "A says +0.160", abs((ns_post - ns23) - 0.160) < 0.02)

# ---- theme counts: cc2_common (C/H base) vs CC1 severity file ----
cc1sev = pd.read_csv(f"{OUT}/CC1_theme_severity_timing.csv").set_index("theme")["n"]
for t in ["billing_refund", "support_service", "exam_test_glitch", "certificate_reporting"]:
    common_n = int(df[f"th_{t}"].sum())
    chk(f"theme {t} (keyword)", f"{common_n}", f"CC1={int(cc1sev[t])}", common_n == int(cc1sev[t]))

# ---- C spine: does it exist & reconcile to the same population ----
try:
    c = pd.read_csv(f"{OUT}/CC2_review_extractions.csv")
    chk("C extractions rows", f"{len(c):,}", "= total reviews", len(c) == N)
    # C primary 'positive_experience' should track the 4-5 star share roughly
    pos_share = (c["primary_root_cause"] == "positive_experience").mean()
    star45 = (df["star_rating"] >= 4).mean()
    chk("C positive_experience share", f"{pos_share:.1%}", f"4-5* share={star45:.1%}", abs(pos_share - star45) < 0.08)
    # resolution-gap headline
    rem = int((c["resolution_offered_in_reply"] == "specific_remedy").sum())
    chk("C specific_remedy replies", f"{rem}", "memo says 23 (0.2%)", rem == 23)
    # actionable among negatives
    act = (c[c["neg"]]["is_actionable"] == True).mean()
    chk("C actionable | negative", f"{act:.1%}", "memo says 88.5%", abs(act - 0.885) < 0.02)
    # C primary vs CC1 keyword (different by design: primary<=any-mention) -- report, not gate
    c["_sec"] = c["secondary_themes"].fillna("").astype(str)
    cmp_rows = []
    for t in ["billing_refund", "support_service", "exam_test_glitch", "certificate_reporting", "scam_fraud"]:
        prim = int((c["primary_root_cause"] == t).sum())
        anym = int((c["primary_root_cause"] == t).sum() + c["_sec"].str.contains(t).sum())
        cmp_rows.append((t, prim, anym, int(cc1sev[t])))
except FileNotFoundError:
    cmp_rows = []
    chk("C extractions", "MISSING", "run cc2_c_extract", False)

# ---- A forecast level vs H recent neg-share ----
try:
    h = pd.read_csv(f"{OUT}/CC2_rhi_timeseries.csv")
    recent_ns = h[h["month"] >= "2025-09"]["neg_share"].mean()
    chk("recent neg-share (H, 25-09+)", f"{recent_ns:.3f}", "A forecast level ~0.32", abs(recent_ns - 0.32) < 0.06)
    chk("RHI 2023 mean", f"{h[h.month.str.startswith('2023')]['RHI'].mean():.1f}", "anchor = 100", abs(h[h.month.str.startswith('2023')]['RHI'].mean() - 100) < 0.5)
except FileNotFoundError:
    chk("H timeseries", "MISSING", "run cc2_h_kpi", False)

# ---- print ----
print("=" * 92)
print("CROSS-WORKSTREAM CONSISTENCY PASS")
print("=" * 92)
print(f"{'check':38s} {'value':>14s}  {'cross-ref':28s} status")
print("-" * 92)
for name, val, ref, status in rows:
    print(f"{name:38s} {val:>14s}  {ref:28s} {status}")
nflag = sum(1 for r in rows if r[3] == FLAG)
print("-" * 92)
print(f"{len(rows)} checks, {nflag} FLAGGED")

if cmp_rows:
    print("\nC primary_root_cause vs CC1 keyword (EXPECTED to differ: primary<=any-mention<=keyword-regex):")
    print(f"  {'theme':24s} {'C primary':>10s} {'C any':>8s} {'CC1 kw':>8s}")
    for t, p, a, k in cmp_rows:
        print(f"  {t:24s} {p:>10d} {a:>8d} {k:>8d}")
