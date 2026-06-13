# CC1 — Change-Point / Structural-Break Summary

**Method:** weighted mean-shift detection — for each metric, find the month that maximizes |mean_after − mean_before|, requiring ≥4 months on each side, searching only the volume-stable window from 2022-01. Reported alongside an explicit pre/post 2024-03 segment comparison. Partial months (2014-07, 2026-06) excluded from all slope math. Monthly counts of 50–90 in 2024–25 are noise-prone — every rate carries its n in `CC1_monthly_metrics.csv` (noise floor flagged at n<40).
**Companion data:** `CC1_change_point_table.csv`, `CC1_monthly_metrics.csv`.

## Headline: the decline is real but its shape is a two-step, not a single March-2024 cliff

| Metric | Pre 2024-03 | Post 2024-03 | Biggest single mean-shift |
|---|---|---|---|
| Avg rating | 4.02 (n=2,054) | 3.50 (n=2,147) | **2024-10** (4.00 → 3.41) |
| Negative share (≤2★) | 18.3% | 34.0% | **2024-10** (19.2% → 36.3%) |
| Median reply lag (days) | ~2 | rising | **2025-12** (3.2 → 11.1) |

**Refinement of the inherited narrative (value-add):** the source memos frame March 2024 as *the* break. The data supports March 2024 as the **first visible inflection** (neg share 19.8%→33.3%, rating 3.93→3.54), but the **deepest, most sustained deterioration arrives Oct 2024–Jan 2025** — Dec 2024 (n=65) and Jan 2025 (n=82) hit ~47–48% negative share, the worst readings in the series. The algorithmic single-break lands on Oct-2024, not March. Treat it as **a step in early 2024 followed by a larger step in late 2024**, not one event.

## Second, independent break: reply *operations* degraded in late 2025 — a new finding
Median reply lag was ~1.3–3 days through mid-2025, then climbs sharply: 2025-08 (12.9d), 2025-10 (9.1d), 2025-12 (12.0d), 2026-03 (13.5d), **2026-04 (20.1d)**. Reply *coverage* also slips from ~100% to **57% in 2026-04**. So the historically fast/near-universal reply machine started breaking down in H2 2025 — a more recent operational signal than the 2024 sentiment break and worth a direct leadership question.

## Caveats
- 2026-04 reply-rate (0.57) and lag (20d) ride on n=61 and recent records that may still be accruing replies; flagged as preliminary.
- The Oct-2024 single-break is sensitive to ±1 month; the *direction and magnitude* (≈0.6★ drop, +17pt negative share) are robust, the exact month is not.

**Confidence:** high on "sustained two-step decline, worst in late-2024"; medium on the precise break month; medium on the late-2025 reply-ops degradation (recent, partially-accruing data).
