# CC2-F — Review-Integrity Audit Summary

> **This is an AUDIT, not an accusation.** The dataset has **no reviewer-identity, IP, device, or invitation-timing field** (verified: 11 keys, none about provenance). Review manipulation therefore **cannot be proven or disproven here.** Below is a pre-registered battery of anomaly tests; we report what fires **and what comes back null**, name the benign explanation that fits equally well, and hand leadership a *verify-list* — never a verdict. Some negative reviews in the corpus allege "fake 5-star batches"; this audit tests that claim rigorously rather than amplifying or dismissing it.

**Companion data:** `CC2_anomaly_register.csv` (the verify-list), `CC2_burst_weeks.csv`, `CC2_near_dup_clusters.csv`.

## Test 1 — Weekly 5★ burst detection, with multiple-comparisons control
Weekly 5★ counts vs a trailing-12-week baseline (z-score + one-sided Poisson exceedance). Critically, a z-scan over **450 weeks** will fire by chance, so we apply a **Benjamini-Hochberg FDR** control:

- **43 weeks** raw p<0.05 — but **~22 are expected by pure chance**. Reporting all 43 would be a Rorschach test.
- **15 weeks survive FDR correction.** These are genuine bursts.
- **Decoupled from the decline:** **only 1 of the 15** falls in the 2024+ deterioration window; the rest cluster in **2018–2023** (notably 2023-03, 2023-09/10). If anything, burst activity is a *historical* pattern, not something timed to mask the 2024 collapse.

## Test 2 — First-time-reviewer concentration (the NULL anchor)
If 5★ bursts were fake accounts, first-timer share should spike around them. It does **not**: first-timer share of 5★ reviews is **flat at 0.659–0.708 every year 2018–2026 (range 0.048)** — including pristine pre-decline years.

> **This NULL is the most credibility-building result in the audit.** A test run *against* the manipulation hypothesis comes back negative, and we report it as prominently as any hit. Flat first-timer share is fully consistent with normal Trustpilot behavior and **does not support** the fake-review claim.

## Test 3 — Near-duplicate 5★ text
Clusters of ≥3 near-identical 5★ reviews (TF-IDF cosine ≥0.9): **81 are generic-short** ("great course", "easy") — **excluded from evidence** because prompted-review programs produce exactly this. Only **6 are longer/specific**, and even those are weak (customers reuse template phrases, or one reviewer took several courses).

## Test 4 — Experience→post lag (a provenance-adjacent signal CC1 never used)
Median lag from `experienced_date` to `published_date` is **2.3 days**, with **~18% posted within a day** and the pattern stable over time — consistent with **invitation-at-completion** (a benign, solicited review flow), not a manipulation fingerprint.

## Verdict
Genuine 5★ bursts exist (15 survive FDR), but they are **overwhelmingly pre-2024**, the **first-timer test is null**, near-dups are **generic/benign**, and lag patterns look **solicited-normal**. The single explanation consistent with *all* of this is mundane: **Trustpilot invitation / course-completion email batches** generate same-week bursts of short generic praise from first-time reviewers — **indistinguishable from padding with this data.**

**What would resolve it (the verify-list):** Trustpilot invitation logs, review-source flags (organic vs invited), IP/device, and completion timestamps — data only Trustpilot and 360training hold. Until then, manipulation is **neither supported nor refuted**, and we make no claim that it occurred.

**Confidence:** high that the *public* data does not evidence manipulation; the question is genuinely unresolvable here, and that limit is the finding.
