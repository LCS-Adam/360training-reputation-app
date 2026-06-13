# CC2-D — Revenue-at-Risk Memo (honest sizing of the stakes)

> **Scope & honesty boundary.** The only data we hold is public review sentiment — **no conversion, traffic, AOV, or customer-count data.** So the **load-bearing claim is a break-even threshold** the company evaluates against its own numbers (it needs *no* revenue assumption) — and it is the **only** figure presented in the main body. For those who still want a rough magnitude, an **explicitly ILLUSTRATIVE** Monte-Carlo range is **demoted to Appendix A** at the end — clearly **not** a measurement — accompanied by a **sensitivity** showing which assumption matters most. Every company placeholder is **ILLUSTRATIVE** — the live Streamlit model lets the company drop in real figures.

**Companion data:** `CC2_revenue_at_risk_model.csv` (parameter ledger), `CC2_revenue_illustrative_range.csv` (range percentiles). Charts: `CC2_breakeven_threshold.png` (the decision chart — **the claim**), `CC2_revenue_at_risk_tornado.png` (sensitivity), `CC2_revenue_illustrative_range.png` (illustrative magnitude).

## The measured fact we stand behind
Volume-weighted average rating fell from a **2023 baseline of 4.02★** to a **sustained 3.49★ (−0.53★)** across 2024-03→2025-12, dipping to **3.12★ (−0.91★) at the Q4-2024 trough** (reconciled from CC1 monthly metrics). That star delta is real and internal; everything downstream is explicitly labeled.

## The spine: a break-even inversion (needs NO borrowed elasticity)
Rather than assert "we are losing $X" (which a CFO will rightly shred), we invert:

> **The reputation fix pays for itself if it recovers even an X% relative lift in conversion on the review-exposed segment**, where **X = annual fix cost ÷ exposed revenue.**

This requires **only company numbers** (fix cost, revenue, exposure) — no restaurant elasticity. The decision chart plots that break-even threshold against the **plausibly-recoverable band (≈1–7%)** implied by the rating drop:

- A **low-cost fix (~$0.3M)** breaks even across almost the entire recoverable band → **obviously worth it.**
- A **$1M fix** pencils only if review-exposed revenue share is high.
- A **$2M fix** mostly does **not** clear the recoverable band on illustrative numbers.

The CFO reads their own decision off the chart — we assert a *threshold to sanity-check*, never a fabricated loss.

## Illustrative magnitude → see Appendix A (deliberately demoted)
For readers who want a rough dollar figure, an **explicitly illustrative** Monte-Carlo range (~$0.2–0.6M/yr, median ~$0.34M) is given in **Appendix A** at the end of this memo. It is **demoted on purpose**: the break-even threshold above is the claim; that dollar range is scaffolding for intuition, built entirely on placeholder inputs, and is **not** a measurement.

## The parameter ledger (every input typed and sourced)
| Parameter | Type | Source / note |
|---|---|---|
| star_drop −0.53 / −0.91 | **INTERNAL-measured** | CC1 (sustained / Q4-2024 trough) |
| elasticity 5–9%/star | **EXTERNAL-sourced** | Luca, HBS WP 12-016 (Yelp) |
| review-consult rate ~75% | **EXTERNAL-sourced** | BrightLocal Local Consumer Review Survey 2024 |
| mandated context discount 0.3–0.8 | **JUDGMENT** | compliance training is often *mandated/B2B* → more inelastic than restaurants |
| revenue, exposure, AOV, traffic, fix cost | **COMPANY-placeholder** | ILLUSTRATIVE — replace with internal figures |

## The demoted elasticity — caveated, one bar only
Luca's +1★ → +5–9% revenue is a **restaurant/Yelp** finding; he himself shows the effect is **larger for independents and minimal for established chains**, and 360training sells frequently **mandated, often employer-paid** training. So we apply a **context discount** and use the elasticity *only* to draw the recoverable band — never as a point estimate. The tornado confirms the answer hinges most on **exposure fraction** and **revenue base** (company-known), not on the borrowed elasticity — which is exactly why the break-even framing is robust.

## The single highest-value ask to the company
**Provide the new-enrollment / conversion time series.** If it bends around the early- and late-2024 review inflections, these scenarios harden from "plausible" to "evidenced," the recoverable band narrows, and the break-even decision becomes near-certain. That one internal series removes most of the remaining uncertainty.

**Confidence:** high on the star delta and the break-even *structure*; the dollar magnitudes are explicitly illustrative and **not** claimed.

---
*Sources: [Luca, "Reviews, Reputation, and Revenue: The Case of Yelp.com," HBS Working Paper 12-016](https://www.hbs.edu/faculty/Pages/item.aspx?num=41233); [BrightLocal Local Consumer Review Survey 2024](https://www.brightlocal.com/research/local-consumer-review-survey-2024/).*

---

## Appendix A — Illustrative magnitude (explicitly NOT a measurement; demoted from the main analysis)
*Placed in an appendix deliberately: the break-even threshold is the load-bearing claim and needs **none** of the assumptions below. This range exists only to answer a CFO's "so, roughly how much?" — every input is a placeholder or external benchmark, **none is 360training's actual revenue, exposure, or conversion.***

We Monte-Carlo the parameter ledger — each input drawn from a **triangular(low, base, high)** so the base case is weighted and the interval does **not** compound worst-case × worst-case — and report **percentiles, never a point**:

| | Illustrative annual reputation-linked revenue-at-risk |
|---|---|
| Median | **≈ $0.34M** |
| 25th–75th | **$0.24M – $0.47M** |
| 10th–90th | **$0.17M – $0.62M** |

So: **order ~$0.2–0.6M / year, illustrative.** The figure scales ~linearly with revenue × exposure; replace those two placeholders with real numbers and the range tightens by ~an order of magnitude. Tension worth surfacing: at the **base** placeholders the break-even lift needed (~8.9%) sits just **above** the ~6.5% recoverable ceiling — i.e. a $1M fix pencils only if revenue/exposure run higher than base, exactly the call the company makes with its own numbers. **This is scaffolding for intuition, not a claim.**
