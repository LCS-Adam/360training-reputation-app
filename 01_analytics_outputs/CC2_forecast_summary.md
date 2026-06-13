# CC2-A — Reputation Forecast Summary

**Question:** where is 360training's negative-review share (≤2★) headed over the next 6 months?
**Method:** weighted **local-level Kalman filter on logit(neg_share)**, fit on the post-break window (2024-03 → 2026-05; partial 2026-06 excluded). Per-month observation variance = φ/(n·p̂·(1−p̂)) with **overdispersion φ estimated jointly with the level-innovation Q by MLE**. We model a time-varying **level, not a trend** — the series is a *hump*, not a step, so a trend line would falsely extrapolate the partial recovery.
**Companion data:** `CC2_reputation_forecast.csv`, `CC2_forecast_backtest.csv`, `CC2_counterfactual_scenarios.csv`, `CC2_replyops_trend.csv`.

## Headline = calibration, not a point prediction
The deliverable is **honest uncertainty**, validated by a rolling-origin backtest (53 out-of-sample forecasts at h=1/3/6):

| Nominal band | Empirical coverage |
|---|---|
| 80% | **79%** |
| 95% | **96%** |

Near-perfect calibration — when the model says "80% confident," the truth lands inside ~80% of the time. On **point** error the model (MAE 0.064) ties a trailing-3-month mean (0.065) and beats last-value (0.077); at 50–90 reviews/month **beating a naive mean on point error is not expected and is not the claim** — calibrated intervals are.

## The forecast (and the honest crux)
The estimated level peaked at ~0.39 (turn of 2025) and has **partially recovered to ~0.32**. The 6-month forecast holds at **≈0.32** with a widening fan: **80% band ≈ 0.22–0.44, 95% ≈ 0.18–0.50** by month 6.

> **The trend sign is genuinely ambiguous.** Negativity is well off its late-2024/early-2025 peak (~0.47–0.48) but still far above the pre-decline ~0.18. We cannot honestly say it is still worsening *or* durably recovering — the data supports "elevated and noisy around ~0.32," not a confident direction. A forecast that drew a line up or down would be overclaiming. **φ = 1.18** confirms mild within-month overdispersion (review bursts), and the bands are widened for it.

Regime note: CC1's *algorithmically-detected* change-point is **2024-10** (marked on the chart); **2024-03** is the first-inflection / segment-comparison date. Both are stated correctly — they are different things.

## Counterfactual — a decomposition of the rise (NOT causal)
"How much of the rise in negativity since 2023 traces to a shift in the *mix* of complaints?" The mix model (logistic neg~themes) under-predicts the absolute level because it omits theme co-occurrence and the 42% of negatives no keyword flags — so we use it for the **delta only** and anchor that delta to the **observed** level (reconciles with the forecast):

| Scenario | Anchored neg-share | Δ vs status-quo |
|---|---|---|
| Status quo (no revert) | **0.34** (= observed) | — |
| Half revert to 2023 mix | 0.30 | −0.04 |
| Full revert to 2023 mix | 0.26 | −0.09 |

**Decomposition:** negativity rose **+0.160** from 2023 to the post-break window. The **complaint-mix shift explains +0.086** of that (≈ 54%); the **residual +0.075 is untagged / base-sentiment drift** the keyword themes can't see. So even a full reversion of the *mix* to 2023 would leave neg-share around **0.26 — still well above the ~0.18 pre-decline level.**

**Heavy caveats (inherited from B):** *associational*, not causal — it does **not** say fixing themes will move ratings; the theme→neg association is measured on the same text; keyword themes cover only 58% of negatives (hence the delta-only, anchored framing). Directional, not a promise.

## Reply operations — forecast SEPARATELY (distinct process)
Reply lag and coverage are an *operational* series, not sentiment, and are **never folded into the neg-share model.** They tell their own story (see `04_replyops_separate.png` / `CC2_replyops_trend.csv`): median reply lag degraded from ~1–3 days to **8–20 days** across H2-2025→2026 and coverage slipped toward ~57% in 2026-04 — a more recent operational red flag than the 2024 sentiment hump.

**Confidence:** high on the calibration result and "elevated/noisy ~0.32"; the *direction* is deliberately left uncertain; the counterfactual is explicitly directional.
