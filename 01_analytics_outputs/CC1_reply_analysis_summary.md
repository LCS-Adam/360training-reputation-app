# CC1 — Company Reply Template & Quality Summary

**Source:** 9,695 company replies (91.5% of all reviews). Templates via TF-IDF (1–2 grams) + KMeans (k=8). Quality flags via keyword rules; "remedy_offer" counts remedy *language* and overstates real fixes because the dominant negative-reply template literally contains "we would like the opportunity to resolve your issues" — read offer-rate as *promise* language, not confirmed resolution.
**Companion data:** `CC1_reply_template_variations.csv`, `CC1_reply_quality_scores.csv`.

## Headline: this is a reply-*quality* problem, not a reply-*speed* or reply-*coverage* problem (historically)
The inherited "reply failure" story needs correcting. The company replies to **86% of 1★** and **89% of 2★** reviews (vs 93% of 5★), historically within ~1–3 days. The failure is in **what** the replies say, not whether/when they appear:

- **Personalization is effectively zero: 0.6% overall, 1.3% even on 1★ replies.** Replies are templated to the point of near-total interchangeability.
- **8 clusters, but ~74% of all replies fall into 4 generic positive-acknowledgement templates** (clusters 2/0/5/3) that contain no apology and no remedy — these answer 5★ praise.
- **The negative-review response is itself one dominant template** (cluster 1, "Hi [name], …sorry…would like the opportunity to resolve…email CustomerCare@360training.com"): 98.8% "offer" language but it is **escalation to email**, not a public resolution.
- **Escalation-only template** (cluster 6) accounts for 4.3% of replies at 98.3% escalation-only — "we've shared your feedback with management, email us."

## Quality by star band
| Star | n | personalization | remedy-language | apology | escalation-only |
|---|---|---|---|---|---|
| 1★ | 1,512 | 1.3% | 74.7% | 78.6% | 12.3% |
| 2★ | 395 | 1.0% | 55.9% | 51.4% | 21.8% |
| 3★ | 634 | 0.8% | 27.0% | 19.9% | 27.4% |
| 4★ | 1,416 | 0.4% | 3.7% | 1.8% | 5.8% |
| 5★ | 5,738 | 0.4% | 0.3% | 0.2% | 0.5% |

The company does scale apology/remedy *language* with severity — but it never personalizes, and the "remedy" is overwhelmingly **"email CustomerCare@360training.com"**, which moves the problem off the public record without visibly solving it.

## Why it matters
- **Reviewers have noticed the tactic.** Negative reviews explicitly warn: *"Don't be fooled by 360's replies asking the reviewer to email…"* The templated escalation is now itself a credibility liability, not damage control.
- **Public-record optics:** a prospect reading Trustpilot sees dozens of identical "sorry, email us" replies under unresolved complaints — this reads as process, not care, and amplifies rather than contains reputational damage.
- **Pairs with the late-2025 reply-ops degradation** (see change-point summary): the one thing that *was* working — speed/coverage — started slipping in H2 2025.

**Confidence:** high on personalization ≈0% and template concentration; medium on remedy-rate (language proxy, not confirmed resolution).
