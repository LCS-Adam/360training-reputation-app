# CC1 — Theme Severity & Timing Summary

**Source:** `360training_trustpilot_ALL_reviews.json` (n=10,601; 2014-07 → 2026-06). Themes tagged with one shared keyword taxonomy reused across the special-topic scan and exam-glitch crosswalk, so counts reconcile across CSVs. Keyword precision spot-checked at ~85–90% (negation/false-positive sampling); treat counts as directional, not exact.
**Companion data:** `CC1_theme_severity_timing.csv`.

## Severity ranking (severity_score = 0.6·%negative + 0.4·(1 − mean_star/5), directional 0–100)

| Theme | n | %neg | mean★ | severity | Read |
|---|---|---|---|---|---|
| scam_fraud | 149 | 94% | 1.20 | 86.8 | High-intensity distrust language; small but loud |
| billing_refund | 376 | 93% | 1.27 | 85.8 | **Largest high-severity theme**; refund/charge disputes |
| access_expiration | 194 | 79% | 1.75 | 73.6 | "Only good for 60 days / locked out" |
| support_service | 642 | 74% | 1.97 | 68.8 | **Highest negative volume** (21.6% of all negatives) |
| exam_test_glitch | 458 | 61% | 2.22 | 58.6 | Persistent irritant (see crosswalk) |
| phone_automation | 80 | 55% | 2.35 | 54.2 | Bot/IVR/"no human" friction |
| course_content | 345 | 50% | 2.60 | 49.1 | Mixed |
| certificate_reporting | 889 | 43% | 3.11 | 41.0 | **Highest raw volume**, but more mixed sentiment |

**Two low-n themes excluded from interpretation:** `offshore` (n=12, severity 92) and `language_barrier` (n=19). Directionally negative but the samples are too small to rank — reported only as qualitative texture, not a quantified theme.

## What matters
- **Billing/refund + scam/fraud is the severity core.** Together ~525 reviews at >93% negative and mean star ~1.2. This is the cluster most corrosive to trust and most likely to translate into chargebacks and "do not buy" warnings.
- **Support_service is the volume core.** 642 mentions, 21.6% of all negative reviews trace to support failures — the single biggest contributor to negative volume.
- **Certificate/reporting is high-volume but bimodal.** 889 mentions but only 43% negative — many are neutral/positive references to certificates. Don't over-read its raw count as a complaint signal.

## Timing (quarterly, to keep sparse themes stable; partial 2014-07 & 2026-06 excluded)
First inflection quarter (first 2024+ quarter at ≥1.5× the 2023 baseline and ≥3 negative mentions):
- **2024Q1:** support_service — earliest mover.
- **2024Q3–Q4:** scam_fraud, access_expiration, certificate_reporting.
- **2025Q1:** billing_refund (peak 2025Q1, 23 negative mentions).

> Caveat on `peak_quarter` in the CSV: a few themes show pre-2024 peak quarters purely because total review volume was higher in earlier years. For complaint-growth read the 2023-vs-2024/25 comparison in the special-topic scan, not the raw peak quarter.

**Confidence:** medium-high on the severity *ranking*; medium on exact inflection quarters (sparse per-theme monthly counts).
