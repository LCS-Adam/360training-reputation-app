# CC2-B — Driver Model Summary (which complaints drive a 1-star)

> **Coverage limit, stated first (the load-bearing honesty number):** the 10 keyword themes flag only **58.3%** of negative reviews (1,285 / 2,206); **41.7% carry no theme flag.** These odds ratios characterize *drivers within the keyword-tagged subset*, not all dissatisfaction. Workstream C (LLM extraction) is the fix — it will tag ~all reviews and power a B-v2.
>
> **Posture:** ASSOCIATIONAL / DESCRIPTIVE, **not causal.** Themes are keyword-derived from the *same text* that drives the rating, so these ORs say which complaints *accompany* the worst ratings — they are **not** evidence that fixing a theme raises ratings (that needs an intervention or the company's internal pre/post data).

**Method:** L2 logistic regression, target = 1★ vs rest. Odds ratios with **400-sample percentile bootstrap CIs**. Controls: log word-count, log reviewer-review-count, decline-regime dummies. GBT + permutation importance as a robustness check. Data: `cc2_common` (reconciles with CC1). Companion CSVs: `CC2_driver_odds_ratios.csv`, `CC2_driver_importance_gbt.csv`, `CC2_driver_temporal_stability.csv`, `CC2_theme_cooccurrence.csv`.

## The anti-tautology rebuttal (answer the obvious objection with data)
"Of course complaint-words predict bad ratings — that's circular." No: if it were pure sentiment-circularity, every theme would be equally negative. They are **not** — theme negativity ranges **32% → 100%** (language_barrier 32%, certificate 43%, course 50%, exam-glitch 61%, support 74%, access 79%, billing 93%, scam 94%, offshore 100%). That spread is differential **operational** signal, not generic negative affect.

## Lead exhibit — 1★ vs 2★ among negatives only (`08_1star_vs_2star_drivers.png`)
The cleanest anti-circularity test: among reviews that are *already negative*, what separates the **furious (1★)** from the merely **annoyed (2★)**? Only operational themes survive:

| Theme | OR (1★ vs 2★) | 95% CI | Reads as |
|---|---|---|---|
| billing_refund | **2.72** | 1.89–4.16 | a billing complaint nearly triples the odds of *furious* vs annoyed |
| support_service | **1.92** | 1.42–2.59 | support failures escalate anger |
| access_expiration | 1.48 | 0.94–2.51 | suggestive, CI crosses 1 |
| certificate_reporting | 1.22 | 0.92–1.63 | not distinguishing |
| exam_test_glitch | 0.84 | 0.64–1.16 | **does not** separate furious from annoyed |
| course_content | 0.77 | 0.54–1.12 | does not separate |

*(scam_fraud OR 5.76 is shown but flagged **evaluative/near-tautological** — "scam" is essentially a 1★ word, so it is not an actionable operational driver.)*

## Full adjusted drivers (1★ vs all — `05_driver_forest_plot.png`)
Ranked by adjusted OR (topical themes, excludes the two n<30 unstable themes):

| Theme | Adjusted OR | 95% CI | Marginal OR | Note |
|---|---|---|---|---|
| billing_refund | **10.4** | 7.4–14.8 | 34.4 | largest actionable driver |
| support_service | **4.6** | 3.7–5.9 | 11.9 | highest negative *volume* (CC1) |
| access_expiration | 3.0 | 2.1–4.5 | 11.8 | "60-day then pay again" |
| course_content | 1.6 | 1.2–2.2 | 3.0 | |
| exam_test_glitch | 1.6 | 1.2–2.0 | 5.0 | OR shrinks sharply once co-occurrence controlled |
| certificate_reporting | 1.4 | 1.2–1.8 | 3.2 | high volume, modest per-review effect |

*(scam_fraud adjusted OR 18.5 — evaluative, caveated. offshore/language_barrier excluded: n=12/19, near-separated, ORs unstable.)*

**Marginal vs adjusted (`06_...`):** the gap is the **co-occurrence correction** — e.g. exam_test_glitch's marginal OR 5.0 collapses to 1.6 adjusted, because glitch complaints co-occur with billing/support; its standalone signal is largely those companions. Reporting both is the honest move.

## Robustness & validation
- **GBT permutation importance** independently ranks billing_refund #1, scam_fraud #2, support_service #3 — corroborating the logistic ranking under a nonlinear model.
- **Temporal stability:** 9/10 themes keep their sign across pre-2025 vs 2025+; only phone_automation flips (OR≈1, weak). billing/support/scam are stable.
- **5-fold PR-AUC = 0.635** vs a 1★ base rate of 0.166 — a **3.8× lift**, solid for a 10-feature keyword model.
- **Controls matter:** log word-count OR 2.36 (longer reviews skew 1★ — the length confound was real and is now absorbed); regime_deep OR 2.54 (base negativity rose in the deep-decline period, absorbed so theme ORs aren't inflated by the 2024 shift).

## So what (for leadership)
**Billing/refund and support are the actionable 1★ engines** — they drive the worst ratings *and* survive the strictest (1★-vs-2★) test. Exam glitches generate volume but, once you control for the billing/support complaints they travel with, add little *marginal* push to the very-worst ratings. **Confidence:** high on billing/support as top drivers; medium on exact OR magnitudes (keyword tagging, 58% coverage); the C-powered B-v2 will tighten this.
