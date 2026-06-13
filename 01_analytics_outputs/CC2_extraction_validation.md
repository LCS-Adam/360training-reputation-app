# CC2-C — Extraction Validation (model–model agreement)

> **What this is, precisely.** Haiku 4.5 produced the extractions; an independent model (Sonnet 4.6) re-extracted the same stratified 150 from scratch. Below is **per-field agreement between the two models, with Wilson 95% CIs.** Agreement measures **reproducibility/consistency, NOT accuracy.** It is neither an upper nor a lower bound on accuracy: two models can share a blind spot and agree on a *wrong* label (agreement > accuracy), or disagree on an item one of them got right (accuracy > agreement). Critically, Haiku and Sonnet **share a model lineage, so their errors are likely correlated — which makes this agreement rate most plausibly an OPTIMISTIC proxy that OVERSTATES true accuracy.** The certified precision number comes only from the **human gold pass** scaffolded in `CC2_gold_set.csv` (blank `human_*` columns; the **19 root-cause disagreements are pre-sorted to the top** for efficient adjudication — the plan's 'Sonnet triages disagreements to human review' role). κ is not reported: with two same-family raters and no certified truth, an agreement RATE is the honest statistic.


**Paired sample:** 150 reviews (stratified across all star bands).


## Per-field agreement (Haiku vs Sonnet)

| Field | Agree | n | Rate | Wilson 95% CI |
|---|---|---|---|---|
| primary_root_cause | 131 | 150 | 87.3% | 81.1%–91.7% |
| product_line | 144 | 150 | 96.0% | 91.5%–98.2% |
| resolution_requested | 120 | 150 | 80.0% | 72.9%–85.6% |
| resolution_offered_in_reply | 113 | 150 | 75.3% | 67.9%–81.5% |
| refund_requested | 144 | 150 | 96.0% | 91.5%–98.2% |
| is_actionable | 142 | 150 | 94.7% | 89.8%–97.3% |
| extraction_flags | 132 | 150 | 88.0% | 81.8%–92.3% |
| sentiment_intensity | 126 | 150 | 84.0% | 77.3%–89.0% |
| secondary_themes (Jaccard≥0.5) | 120 | 150 | 80.0% | 72.9%–85.6% |
| dollar_amount (±1% or both-null) | 150 | 150 | 100.0% | 97.5%–100.0% |

## product_line agreement by class (where Haiku assigned the class)

| Haiku class | Agree | n | Rate | Wilson 95% CI |
|---|---|---|---|---|
| osha_safety | 14 | 15 | 93.3% | 70.2%–98.8% |
| real_estate | 5 | 5 | 100.0% | 56.6%–100.0% |
| food_handler_safety | 7 | 8 | 87.5% | 52.9%–97.8% |
| tabc_alcohol | 5 | 5 | 100.0% | 56.6%–100.0% |
| healthcare_ce | 2 | 3 | 66.7% | 20.8%–93.9% |
| unknown | 108 | 109 | 99.1% | 95.0%–99.8% |

*The 96% headline product_line agreement (per-field table) is dominated by both models agreeing on the majority `unknown` class (109/150 of the sample). The meaningful signal is the specific-class agreement above — osha_safety / real_estate / tabc_alcohol / food_handler all ≥ 87.5% (healthcare_ce is only n=3, so its CI is wide).*

## Honesty boundary

- **Agreement ≠ accuracy, and here it most likely OVERSTATES it** (correlated same-family errors). Treat the rates as a reproducibility / triage signal, never a precision claim.
- **The B-v2 / G-full gate (product_line precision ≥ 0.85) is UNRESOLVED.** That bar is defined on human-certified precision, which this autonomous run cannot produce; agreement is not precision. → **B-v2 and G-full stay at v1 by default.** C's value here is standalone descriptive enrichment (richer 17-way root-cause distribution incl. novel themes; product-line coverage ~27% vs ~11% keyword; new dollar / resolution-gap / actionability fields), **not** unlocking the gated upgrades.
- The gold set is **deliberately negative-oversampled** (40/25/25/30/30 by star) to exercise failure modes, so these agreement rates are **not population-weighted** and over-represent 1–2★.
- Fields with low agreement (inspect the table) are the least trustworthy for downstream use.

