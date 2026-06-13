# CC1 — Special-Topic Scan Summary

**Source:** same shared taxonomy as the theme-severity deliverable (counts reconcile). **Growth is measured as the topic's _share of each window's reviews_** — 2023 (12 mo) vs 2024-03→2025-12 (22 mo) — which normalizes for both the unequal window lengths and the ~halving of monthly review volume. (The two windows happen to hold near-equal totals: 1,759 vs 1,789 reviews, so raw-count and share ratios coincide here — but share is the defensible basis.) Keyword precision ~85–90%; directional.
**Companion data:** `CC1_special_topic_scan.csv` (`share_2023`, `share_2024_03_to_2025_12`, `growth_ratio_share`, `n_too_small`).

| Topic | n | %neg | share 2023 → post | growth | Read |
|---|---|---|---|---|---|
| certificate_reporting | 889 | 43% | 7.7% → 12.0% | 1.57× | High volume, mixed sentiment — not a pure complaint signal |
| billing_refund | 376 | 93% | 3.4% → 7.0% | **2.05×** | Largest high-severity topic; near-uniformly negative |
| access_expiration | 194 | 79% | 1.5% → 3.6% | **2.33×** | "only good for 60 days / locked out" |
| scam_fraud_chargeback | 149 | 94% | 0.9% → 3.6% | **3.93×** | Fastest-rising distrust language |
| phone_automation | 80 | 55% | 0.8% → 0.9% | 1.19× | Roughly flat; bot/IVR/"no human" |
| language_barrier | 19 | 32% | 0.06% → 0.06% | ~1.0× | **Too small to quantify** (n_too_small) — qualitative only |
| offshore_costa_rica | 12 | 100% | 0% → 0.17% | n/a | **Too small to quantify** (n_too_small) — qualitative only |

## What matters
- **"Scam/fraud/chargeback" language grew ~3.9× as a share of reviews** (0.9%→3.6%) and runs 94% negative. The most reputationally dangerous trajectory — customers escalating from dissatisfaction to allegations of bad faith and payment disputes.
- **Access/expiration grew ~2.3×** (1.5%→3.6%). The "60-day access then pay again" mechanic is a recurring, specific, fixable grievance (sample: *"only good for 60 days no warning then they want you to buy it again"*).
- **Billing/refund grew ~2.05×** (3.4%→7.0%) and is the largest high-severity topic.

## Honest limits
- **Phone-automation, language-barrier, offshore are real in the qualitative text but statistically thin** (n=80 / 19 / 12; the last two carry `n_too_small=True`). Several "offshore" mentions co-occur with billing complaints ("response team is outsourced to another country"). Present these as *texture and hypotheses to validate*, not as quantified themes. Do not put a percentage on offshore/language-barrier in exec materials.
- The `peak_quarter` field can point pre-2024 for high-volume topics purely because total review flow was higher then; use the `growth_ratio_share` column for the growth story, not peak quarter.

**Confidence:** high on billing/refund, scam/fraud, access/expiration growth; low on phone/language/offshore magnitude (small n).
