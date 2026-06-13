# CC2 — Consolidated Findings Ledger (for sign-off before packaging)

Every claim below is tagged **EVIDENCE** (measured), **INFERENCE** (modeled/associational), or
**RECOMMENDATION**, with a **confidence** label and its load-bearing **caveat**. All headline numbers
passed the cross-workstream consistency pass (`cc2_consistency.py`: **22/22 reconcile, 0 flags**).

**Base facts (raw, ground truth):** 10,601 reviews · 2,206 negative (≤2★, 20.8%) · 91.5% have a company reply ·
date range 2014-07 → 2026-06 (2026-06 partial, excluded).

---

## A — Reputation forecast  ·  `cc2_a_forecast.py`
- **EVIDENCE (high):** Rolling-origin backtest calibration is the headline — over **N = 53 out-of-sample forecasts** (20 origins × horizons 1/3/6; overlapping, so ≈20 independent), **80% bands covered 79% (42/53), 95% covered 96% (51/53)**. Overdispersion **φ = 1.18**.
- **INFERENCE (medium):** Negativity is **elevated and noisy around ~0.32** (off the late-2024/2025 peak ~0.47, far above the pre-decline ~0.18). 6-month forecast holds ~0.32 with a widening fan.
- **Honest crux:** the trend **direction is deliberately left uncertain** — the data supports "elevated/noisy," not a confident up or down. Reply-ops forecast **separately** (distinct process).
- **Counterfactual (INFERENCE, directional):** complaint-**mix shift explains ~54%** (+0.086) of the +0.157 neg-share rise; residual +0.075 is untagged drift. Even full mix-reversion leaves ~0.26 (> 0.18 baseline). Carries B's 58%-coverage + same-text caveats.

## B — Driver model  ·  `cc2_b_drivers.py`
- **INFERENCE (medium-high, associational NOT causal):** odds of a 1★ (vs rest) given a theme — **billing_refund OR ≈ 10.4**, **support_service ≈ 4.6**.
- **Lead exhibit:** in the **1★-vs-2★** conditional model (both already negative), **billing and support ORs survive** → operational signal, not "negative words in negative reviews." `scam_fraud` flagged near-tautological.
- **Load-bearing caveat (stated first in the memo):** keyword themes flag only **58% of negatives**; the other 42% carry no flag — these ORs characterize the **tagged subset**, not all negativity. PR-AUC 0.635 (3.8× lift).

## C — LLM structured extraction  ·  `cc2_c_extract.py`  *(headline deliverable)*
- **EVIDENCE (high):** all **10,601** reviews typed into 19 fields (Haiku 4.5, forced schema, Batch API, **$21.74**, 0 errors).
- **Value over keywords:** **1,103 reviews** have a primary cause the regex taxonomy can't see (`seat_time_timer` 451, `platform_usability` 450, `proctoring` 161); product-line coverage **20.8%** (vs ~11% keyword). C diverges from regex in interpretable ways — **+recall** on support (1,024 vs 642), **+precision** on certificate (452 vs 889 — regex over-matches positive "certificate").
- **New CEO-grade finding (EVIDENCE):** company replies offered a **specific remedy (refund/credit/reopen/access-restored) in only 23/10,601 (0.2%)** — corpus-wide 75% generic apology, 16% "email-us" deflection, 9% none; **among replies to *negatives* specifically the mix shifts to 73% deflection / 26% apology — the company deflects complaints in particular** — while **88.5% of negatives are *actionable*** (name a fixable issue). A quantified resolution gap. *Stress-tested this session against the raw reply text:* 0.2% is a **conservative upper bound** — of 9,672 non-specific replies only 207 even contain a remedy word and on inspection nearly all are false positives ("**comp**liance", "**extend** our apologies"), so *missed* remedies ≈ 0; and several of the 23 are process-improvement promises ("we'll review the course"), so genuine per-customer fixes number **< 23**. Restricting to the **2,206 negative reviews**, only **11 (~0.5%)** received a specific remedy — vanishingly rare under any denominator.
- **Honesty boundary:** extractions are model-generated. Sonnet-reference **agreement** (root-cause 87%, product-line 96% [unknown-inflated; specific classes ≥87%]) measures **consistency, likely OVERSTATING accuracy** (same-family correlated errors) — it is **not** precision. The B-v2/G-full precision gate (≥0.85, human-certified) stays **UNRESOLVED → those stay v1**; gold set scaffolds the human pass.

## D — Revenue-at-risk  ·  `cc2_d_revenue.py`
- **EVIDENCE (high):** volume-weighted star fell **4.02 → 3.49 (−0.53)** sustained (2024-03→2025-12), trough **3.12 (−0.91)** in Q4-2024. *(Both verified to the cent in the consistency pass.)*
- **Spine (INFERENCE, structural):** a **break-even inversion** — the fix pays for itself if it recovers X% conversion, X = cost ÷ exposed-revenue — needing **only company numbers, no borrowed elasticity.** Luca restaurant elasticity demoted to one caveated sensitivity bar.
- **Illustrative magnitude (INFERENCE, explicitly NOT a measurement — DEMOTED to a memo appendix):** Monte-Carlo over the placeholder ledger → **~$0.2–0.6M/yr** (10–90th), median **$0.34M**. Every input is a placeholder/benchmark, not 360training data. Per this session's findings-walk it is **moved out of the headline into Appendix A** of `CC2_revenue_at_risk_memo.md` (and shown only as an appendix panel in the app/deck); the break-even threshold is the sole load-bearing claim.

## E — Topic model  ·  `cc2_e_topics.py`
- **EVIDENCE (medium):** embedding clusters (KMeans-14; HDBSCAN under-clustered) **corroborate the keyword taxonomy** and surfaced the novel **seat-time/timer** theme — later confirmed at **451 reviews** corpus-wide by C. Framed as a coverage/validation view, not a competing model.

## F — Integrity audit  ·  `cc2_f_integrity.py`
- **EVIDENCE (high) — a deliberate NULL:** first-time-reviewer share is **flat (~67–72%)**, not concentrated; of 450 weeks scanned, **15 survive FDR, only 1 in the 2024+ window** (vs ~22 expected by chance). **Manipulation is not the story.** Framed as **audit, not accusation** — provenance is genuinely unprovable without identity/IP data.

## G — Segmentation  ·  `cc2_g_segmentation.py`
- **INFERENCE (medium, coverage-limited):** within the keyword-tagged subset (~11% coverage; C lifts to 20.8%), **real-estate runs 64% negative (all-time, n=221) vs OSHA/safety 34% all-time**. The OSHA deterioration is temporal and is stated at **annual grain** — each year clears the ~40/yr floor, whereas per-quarter 2025 cells are only n=9–20 (too thin to trend): **neg-share tripled 24% (2023, n=78) → 47% (2024, n=66) → 78% (2025, n=50).** Country geo dropped (98% US). Coverage printed on every cut.

## H — Reputation Health Index  ·  `cc2_h_kpi.py` + `cc2_h_refresh.py`
- **INFERENCE (high on trajectory):** composite RHI (2023 = 100 frozen anchor) falls **100 → 93.6 → 86.0 → 80.6**. Component z's winsorized at ±3 so no single one hijacks; neg-share dominates the decline (+7.4 pts avg), reply-lag +1.3.
- **Credibility exhibit:** **9-config sensitivity panel — all fall monotonically.** Direction invariant; depth normalization-sensitive (2026 RHI 77–94).
- **Finding (H3):** reply-lag degraded **later** (H2-2025+) than the neg-share jump (2024) — a lagging, later operational shock.
- **Framing:** "**illustrative calibration, not back-test**"; "**idempotent recompute, not a nightly system**"; read as **trajectory + decomposition, never a month ranking** (50–90 reviews/mo noise floor).

---

## Cross-cutting caveats (the "what this data cannot support" box)
- **Provenance:** no invited/verified/organic flag exists → solicited vs organic can't be separated; all rates are conditional on who chose to post. Caps F.
- **Power:** ~27 post-break monthly points, 8–40 negatives/mo → monthly moves under ~5–7 points are noise; no sub-segment with n < ~40/quarter is interpretable.
- **Definition drift (stated side-by-side):** A targets `neg_share` (≤2★); B targets `1★ vs rest`. Different populations.
- **C is model-generated**, validated by agreement (consistency), not human-certified accuracy.

## The single highest-value ask to the company
Provide the **new-enrollment / conversion time series.** If it bends at the 2024 review inflections, the revenue scenarios harden from "plausible" to "evidenced" and the break-even decision becomes near-certain.
