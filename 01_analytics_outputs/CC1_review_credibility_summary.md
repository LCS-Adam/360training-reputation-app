# CC1 — Reviewer Validity Heuristics Summary

**Framing (important):** this is **validity / information-richness scoring, NOT fake-review detection.** The score rewards specificity, operational detail, concrete references (TABC/DMV/OSHA/exam/refund/$), and length. It says how *substantive and checkable* a review is — it makes **no claim about authenticity.** `reviewer_num_reviews` is a deliberately weak input: ~68–75% of reviewers in every star band are first-time reviewers, so it does not discriminate and must not be read as a fakeness signal.
**Companion data:** `CC1_review_credibility_flags.csv` (per-review), validity_score 0–100, `low_info_flag` = score<25 (informational only).

## Headline: the negative reviews are the *more* substantive ones — which strengthens, not weakens, the complaint signal
| Star | n | mean validity | % low-info | mean words | % concrete ref |
|---|---|---|---|---|---|
| 1★ | 1,761 | **64.9** | 11.9% | 71.9 | 47.2% |
| 2★ | 445 | 58.5 | 11.0% | 60.5 | 32.8% |
| 3★ | 688 | 49.4 | 18.9% | 44.4 | 24.3% |
| 4★ | 1,536 | 37.4 | 37.5% | 27.0 | 16.7% |
| 5★ | 6,171 | 26.9 | **60.0%** | 15.3 | 10.5% |

- **1★ reviews are long, detailed, and reference concrete artifacts** (specific exams, certificates, dollar amounts, agencies) nearly half the time. They read like real operational accounts.
- **5★ reviews are short and generic** ("Excellent service", "Easy"): 60% are low-info, averaging ~15 words. The positive base is real but thin in evidentiary content.

## Defensive implication
A skeptical exec will ask "aren't the complaints just angry noise?" The data answers: **the negative reviews carry more checkable detail than the positive ones**, so the complaint themes are *better*-evidenced than the praise — the opposite of the dismissal.

## A flag to handle carefully, NOT to over-claim
Several negative reviews allege batches of *"fake good reviews"* and the bimodal 5★/1★ split plus the thin, generic 5★ content is *consistent with* (but does **not prove**) review-padding. **State this as an open question for leadership to verify, never as a finding.** We have no reviewer-identity or timing-burst evidence here to substantiate manipulation.

**Confidence:** high that negative reviews are more information-rich; the review-padding allegation is **unverified** and labeled as such.
