# CC2-C — LLM Structured Extraction: Method & Cost

**Model:** `claude-haiku-4-5-20251001` (Haiku 4.5), `temperature=0`, forced single-tool output (`tool_choice` pinned to `record_review_analysis`) so every response is schema-valid JSON.

**Scale:** 10,601 reviews extracted (0 errored) via the **Message Batches API**, submitted in 5 chunks (idempotent JSONL ledger, `custom_id = review_id`). All five batches ended in ~4 minutes.


## What we extracted, and why it beats the keyword pass

14 typed fields per review (`CC2_extraction_schema.json`): `primary_root_cause` (+confidence), `secondary_themes[]`, `product_line` (+confidence), `regulator_or_state`, `dollar_amount_mentioned`, `refund_requested`, `resolution_requested`, `resolution_offered_in_reply`, `sentiment_intensity`, `is_actionable` (+rationale), `extraction_flags`. The `primary_root_cause` vocabulary is **CC1's exact 10 keyword themes** (so counts reconcile) **plus** four themes the regex taxonomy is blind to — `seat_time_timer`, `platform_usability`, `proctoring`, `pricing_value` — validated in CC2-E. Those four are the single dominant driver in **1,103 reviews** the keyword pass could not classify. Product-line coverage is **20.8%** (vs ~11% for the G-v1 keyword anchors), with the model assigning `unknown` rather than guessing when no signal exists.


## Cost (actual, from the ledger — not an estimate)

| | input tok | output tok | USD |
|---|---|---|---|
| Full batch (10,601 reviews) | 26,449,570 | 3,405,488 | **$21.74** |
| Pilot (150, sync) | — | — | $0.62 |

Pricing assumptions (stated for audit): Haiku 4.5 at $1.00/$5.00 per MTok in/out, Batch API −50%. **Prompt caching did not engage**: the system+tool prefix (~1.8k tokens) sits under Haiku's 2,048-token cache minimum, and batch cache hits are best-effort regardless — so the figure above reflects no cache discount (measured `cache_read = 0`). Honest, not optimized.


## Validation & the honest limit (see `CC2_extraction_validation.md`)

An independent model (Sonnet 4.6) re-extracted the stratified 150. Per-field **agreement** with Wilson 95% CIs: `primary_root_cause` 87%, `product_line` 96% (unknown-inflated; specific classes ≥87%), `is_actionable` 95%, `refund_requested` 96%, `dollar_amount` 100%. **Agreement measures reproducibility, not accuracy — and because the two raters share a model lineage, it most likely OVERSTATES accuracy.** The B-v2/G-full precision gate (≥0.85, human-certified) is therefore **unresolved**; those upgrades stay at v1. C stands as descriptive enrichment. A human gold pass is scaffolded in `CC2_gold_set.csv` (19 disagreements pre-sorted for adjudication).


## Known limitations

- Tool-use enums are **soft** constraints: ~0.02% of outputs (2 reviews) emitted an out-of-vocab `primary_root_cause`; coerced to `other` at the spine-build step.
- `primary_root_cause` is the *single* dominant driver — a review mentioning billing + support is counted once as primary; use `secondary_themes` to recover multi-theme prevalence.
- Extractions are model-generated; treat as a high-quality first pass, not adjudicated ground truth.

