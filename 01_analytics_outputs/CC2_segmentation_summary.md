# CC2-G — Segmentation Summary (where is trust bleeding?)

**Country geography is a dead end and is dropped:** `reviewer_location` is **98% "US"**, so a country cut carries no signal. Instead we segment by **product line**, inferred from regulator + course keywords (OSHA, TABC, real-estate/TREC, food-handler, etc.).

> **Coverage caveat (printed on every panel):** keyword/regulator anchors tag only **10.9%** of reviews (1,155 / 10,573). All product-line rates are **within the tagged subset**; small-n cells (n<5 on the heatmap, n<30 in tables) are suppressed/flagged. Workstream **C's LLM `product_line` lifts coverage toward ~100%** and swaps in as G-full, with the regulator anchors becoming a validation check on C.

**Companion data:** `CC2_productline_sentiment_timeseries.csv`, `CC2_trustbleed_quarterly.csv` (the monthly/quarterly input H consumes), `CC2_state_inference.csv`.

## Headline: real estate is the standout, and OSHA/safety is deteriorating fast
| Product line | n | % negative | mean ★ | Read |
|---|---|---|---|---|
| **real_estate** | 221 | **64%** | 2.36 | **Chronically the angriest vertical** — ~2× the overall negative rate |
| food_handler | 184 | 39% | 3.29 | mid |
| **osha_safety** | 607 | **34%** all-time | 3.40 | **Biggest line by volume; neg-share tripled 24%→47%→78% across 2023→25 (annual n=78/66/50)** |
| tabc_alcohol | 121 | 31% | 3.50 | least negative |
| insurance | 17 | 77% | 2.00 | **n<30 — flagged, not quantified** |

*(cosmetology n=2, hvac n=3 — too small to report.)*

## Two findings worth a CEO's attention
1. **Real-estate CE buyers are markedly angrier** (64% negative vs OSHA's 34% baseline), and stay dark across nearly every quarter on the heatmap (`G1`). This is a *specific, ownable* segment to investigate — likely a content/exam/CE-credit-reporting fit problem unique to real-estate licensing.
2. **OSHA/safety — the highest-volume line — broke down recently.** Pooled to **annual grain** (where n clears the ~40/yr interpretability floor), its negative share **roughly tripled: 24% (2023, n=78) → 47% (2024, n=66) → 78% (2025, n=50)** — visible as the heatmap row darkening from 2024Q2 on, and shown directly in `G3_osha_annual_negshare.png`. *(Per-quarter 2025 cells are n=9–20, below the floor, so the trend is read year-over-year, not quarter-to-quarter — the quarterly series is actually flat-to-noisy within 2025.)* Because it's the largest line, a swing here moves the overall number most; this is the **highest-leverage** place to look for the driver of the recent elevated negativity.

## State inference (secondary, heavily caveated)
Where a state-specific regulator/name appears (~few hundred reviews): **TX** dominates (n=146, TABC-driven, 36% neg); **CA** (n=16) and **NY** (n=13) are small but skew heavily negative and real-estate-dominated (>90%). Reported as directional only — **no rates on cells with n<10**, and this is inferred, not a reliable geographic field.

**Confidence:** medium on the *ranking* (real-estate worst, OSHA rising) given ~11% coverage; the magnitudes will tighten once C's full-coverage `product_line` lands. The country-geo drop is definitive.
