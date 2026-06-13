# CC1 — Business-Impact Scenario Summary

**Read this first — scope and honesty boundary.** We have **only public Trustpilot review data**. There is **no** conversion, retention, revenue, customer-count, or chargeback data in this corpus. Every item below is a **directional mechanism linking an *observed* review-side driver to a *plausible* commercial effect.** No absolute dollar figures, conversion percentages, or churn rates are stated or implied — inventing them would be the fastest way to lose a skeptical exec. Use these as scenario framing and as a prompt for the company to supply the real internal metrics.
**Companion data:** `CC1_business_impact_scenarios.csv`.

All "pre vs post" figures below are **share of each window's reviews** (pre = 2023-01…2024-02; post = 2024-03…2025-12), so window length and the volume halving don't bias them.

| Impact channel | Observed driver (from this data) | Pre vs post 2024-03 | Directional effect | Confidence |
|---|---|---|---|---|
| **Trust erosion → conversion drag** | Negative review share (% of window reviews ≤2★) | 18.3% → 34.3% | Prospects who check Trustpilot meet ~2× the negative signal at the moment of choice → downward pressure on conversion | Medium (driver solid; revenue link inferred) |
| **Support friction → retention/repeat drag** | Support-tagged reviews as % of all window reviews | 4.2% → 9.6% (~2.3×) | In a renewal-driven cert market, unresolved support lowers repeat purchase and renewal | Medium |
| **Refund friction → chargebacks / revenue leakage** | billing_refund + scam_fraud as % of all window reviews | 4.0% → 9.0% (~2.2×) | Refund disputes plus public "scam/chargeback" language raise dispute rates and payment-processor risk | Medium-low (chargeback intent inferred from language, not transaction data) |
| **Reply failure → reputation spillover** | Templated / escalation-only replies (0.6% personalization) | qualitative | Identical "sorry, email us" replies under unresolved complaints amplify rather than contain public reputational damage | Medium |

*(Exact share figures are in `CC1_business_impact_scenarios.csv`; the support row previously read "66%→84%" — that was negativity **within** support-tagged reviews, a different and easily-misread metric, now restated as support-share of all reviews.)*

## How to use these
- Each row pairs a **number we can stand behind** (the review-side driver) with a **mechanism we cannot quantify** (the commercial effect). Present them that way — never collapse the two.
- **The single highest-leverage validation ask to the company:** does the conversion / refund-rate / chargeback-rate / renewal-rate time series bend around early-2024 and again late-2024, matching the review inflections? If yes, these scenarios harden from "plausible" to "evidenced."

**Confidence:** the drivers are high-confidence and directly measured; the business impacts are explicitly **illustrative and directional**, pending internal data.
