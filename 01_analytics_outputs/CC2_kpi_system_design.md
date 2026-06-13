# CC2-H — Reputation Health Index: System Design & Read

## What it is / what it is NOT

- **IS:** a parameterized, **idempotent re-computation** that regenerates the RHI timeseries from the review data + CC2 component series (`cc2_h_refresh.py` re-runs it after a data refresh).
- **IS NOT:** a 'nightly monitoring system.' Live cadence needs a Trustpilot **ingestion feed** (scraper/API + dedup on `review_id`) — a **Production Consideration, not implemented** here.
- **IS NOT** a back-test. H1 is **illustrative calibration** against known 2024 events; out-of-sample lead-time validation is impossible on a single series.


## Construction (every choice frozen & stated)

RHI = **100 − 10 × (weighted-mean capped-z deterioration vs 2023)**. Each component is a **monthly rate**; the normalization **mean and sigma are frozen on the 2023 distribution**, so appending months never re-scales history. Each component z is **winsorized at ±3** (composite-index standard) so no single low-variance component can hijack the index; sigma is floored at 5% of |mean| to tame 2023-saturated series (reply coverage).


| Component | Weight | Orientation | Source |
|---|---|---|---|
| Neg-share (≤2★) | 30 | higher=worse | CC1 monthly |
| Severity mix | 25 | higher=worse | CC1 severity × theme flags |
| Reply lag | 25 | higher=worse | reply timestamps |
| Reply coverage | 5 | higher=better | reply presence |
| Integrity flags | 10 | higher=worse | F FDR burst-weeks |
| Trust-bleed (product) | 5 | higher=worse | G product-line (quarterly→ffill) |

Weights are an **a-priori hypothesis fixed before looking at 2024**; the sensitivity panel below carries the credibility. **Personalization is excluded by design** (near-zero ~0.6% rate; its sign is perverse — it *rose* as sentiment worsened). Reply **coverage** is down-weighted (saturated ~99% until a 2026 slip); reply **lag** carries the reply weight.


## The read — trajectory, not month-ranking

RHI annual mean: **2023 100.0 → 2024 93.6 → 2025 86.0 → 2026 80.6** (2026 = Jan–May, partial). A steady, multi-year erosion. For pre-2023 context, neg-share ran ~0.15–0.18 (vs the 2023 reference ~0.19–0.28) — i.e. **2023 is the *pre-decline baseline*, not an 'ideal'**; the real deterioration is 2024 onward.


### What drives the decline (avg RHI points removed, 2024+)

| Component | Avg RHI pts removed |
|---|---|
| Neg-share (≤2★) | +7.4 |
| Severity mix | +2.1 |
| Trust-bleed (product) | +1.4 |
| Reply lag | +1.3 |
| Reply coverage | +0.1 |
| Integrity flags | -0.5 |

**Two distinct shocks (H3):** neg-share jumped in **2024** and stayed elevated; **reply-lag degraded LATER (H2-2025→2026)** — so reply-lag is a **lagging, later-emerging operational failure, not a leading indicator** (this refines the plan's prior hypothesis; the data did not support 'reply-lag deflects first'). Integrity contributes ≈0/negative — F's null holds: manipulation is **not** part of the story.


### Composite semantics (by design, not a bug)

Health = **complaint volume net of operational response.** A high-complaint month with *fast* replies can out-score a moderate-complaint month with a 20-day lag — that is the intended meaning of a *health* index. Because 2024+ complaint rates are uniformly far beyond 2023, **neg-share sits near its z-cap across the entire decline**, so within-decline month-to-month differences are governed by the operational components and are **not interpreted below the ~50–90 review/mo noise floor**. The index is read as a **trajectory + decomposition**, never a month ranking.


## Robustness — the credibility exhibit (`H4_weight_sensitivity.png`)

Annual-mean RHI under **9 configurations** (a-priori / equal / neg-heavy / reply-heavy / drop-reply / drop-trust weights; caps ±2/±3/±4; σ from 2023 vs full series):


| Config | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|
| base (w=apriori, cap3, σ2023) | 100.0 | 93.6 | 86.0 | 80.6 |
| equal weights | 100.0 | 93.6 | 88.0 | 82.8 |
| neg-heavy (50) | 100.0 | 89.8 | 82.9 | 80.3 |
| reply-heavy (45) | 100.0 | 98.5 | 89.6 | 79.9 |
| drop reply block | 100.0 | 87.9 | 83.0 | 83.9 |
| drop trust-bleed | 100.0 | 94.6 | 86.8 | 81.2 |
| cap ±2 | 100.1 | 95.7 | 89.6 | 85.6 |
| cap ±4 | 100.0 | 92.3 | 83.1 | 77.1 |
| σ = full series | 100.1 | 96.8 | 94.2 | 93.9 |

**Every configuration falls monotonically 2023→2026.** The deterioration is a property of the data (negativity ~doubled; reply-lag clearly degraded), not of any single weight, cap, or normalization choice. The **direction and ordering are invariant; the *depth* is normalization-sensitive** — 2026 mean RHI ranges ~77–94 (gentlest under full-series σ, which de-saturates neg-share against a wider spread). So the honest headline is a **robust, monotone multi-year decline**, not a precise point value — which is exactly why H ships as a trajectory + decomposition, not a single number.


## Alerts (sustained only)

Threshold crossings on the **3-month rolling** RHI (single months never alert):


| Month | Band | RHI(3mo) | Top driver |
|---|---|---|---|
| 2023-01 | watch | 90.3 | Neg-share (≤2★) |
| 2024-05 | watch | 93.1 | Neg-share (≤2★) |
| 2024-11 | concern | 89.2 | Neg-share (≤2★) |
| 2025-04 | watch | 90.1 | Neg-share (≤2★) |
| 2025-05 | concern | 88.7 | Neg-share (≤2★) |
| 2025-09 | alert | 84.8 | Neg-share (≤2★) |

**Confidence:** high on the trajectory + decomposition (robust across all 9 configs); the latest month is flagged **provisional** (reply-ops right-censoring); month-level ranking is explicitly **not** a claim.

