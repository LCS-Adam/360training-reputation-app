#!/usr/bin/env python3
"""
cc2_c_extract.py — CC2-C: LLM structured extraction over all 10,601 reviews.

The headline deliverable. Converts free-text Trustpilot reviews into a typed,
queryable table via forced-tool-schema extraction (Haiku 4.5, temperature 0), so
downstream workstreams get clean root-cause / product-line / dollar / resolution
fields instead of keyword proxies.

Honesty posture (carried from the build plan):
  * Extractions are MODEL-GENERATED, not ground truth.
  * Validation = per-field AGREEMENT vs an independent stronger model (Sonnet 4.6)
    with Wilson 95% CIs, explicitly framed as model-vs-model consistency
    (a CEILING on accuracy, not proof). A human gold pass is scaffolded
    (CC2_gold_set.csv, disagreements pre-flagged) and named as the real
    validation step that produces a certified precision number.
  * primary_root_cause vocab is DERIVED FROM the CC1 taxonomy so C reconciles
    with CC1 / G (crosswalk emitted in CC2_extraction_schema.json).

Modes:
  python cc2_c_extract.py schema       # write the tool schema + CC1 crosswalk
  python cc2_c_extract.py pilot [N]    # stratified SYNC pilot (default 150): validate schema + ground cost + seed gold set
  python cc2_c_extract.py submit       # submit the full 10,601-review Batch
  python cc2_c_extract.py poll         # check batch status
  python cc2_c_extract.py retrieve     # download results -> ledger + CC2_review_extractions.csv
  python cc2_c_extract.py validate [N] # Sonnet-reference agreement + Wilson CIs on the stratified N (default 150)

API key: read from ~/.config/anthropic.env (ANTHROPIC_API_KEY=...). Shell exports
don't reach this subprocess in the harness, so we read the file directly. The key
is never printed (only length/prefix).
"""
import os
import sys
import json
import math
import time
import concurrent.futures as cf

import pandas as pd

from cc2_common import load_trustpilot, OUT, ensure_dirs

# ----------------------------------------------------------------- models / pricing
HAIKU = "claude-haiku-4-5-20251001"      # verified working
SONNET = "claude-sonnet-4-6"             # independent reference for validation only

# Public list price (USD / million tokens) for Haiku 4.5, stated as an explicit
# assumption so the cost figure is auditable. Batch = 50% off standard rates;
# prompt-cache writes 1.25x, reads 0.10x. (Update if pricing changes.)
HAIKU_IN, HAIKU_OUT = 1.00, 5.00
CACHE_WRITE_MULT, CACHE_READ_MULT, BATCH_DISCOUNT = 1.25, 0.10, 0.50

# ----------------------------------------------------------------- vocabularies
# primary_root_cause: CC1's 10 theme keys VERBATIM (clean reconciliation) + the
# extensions the keyword taxonomy cannot see (validated in CC2-E) + positives.
ROOT_CAUSES = [
    "billing_refund", "support_service", "phone_automation", "language_barrier",
    "offshore", "exam_test_glitch", "certificate_reporting", "access_expiration",
    "scam_fraud", "course_content",
    "seat_time_timer", "pricing_value", "platform_usability", "proctoring",
    "positive_experience", "other", "unclear",
]
CC1_THEMES = ROOT_CAUSES[:10]   # the keys that map 1:1 back to CC1 / cc2_common

PRODUCT_LINES = [
    "osha_safety", "real_estate", "food_handler_safety", "tabc_alcohol",
    "notary", "cosmetology_beauty", "hvac_trades", "insurance",
    "healthcare_ce", "workforce_hr_compliance", "driver_ed", "other", "unknown",
]
RESOLUTION_REQUESTED = ["refund", "access_extension", "certificate_or_record",
                        "technical_fix", "human_contact", "escalation_regulator",
                        "none", "unclear"]
RESOLUTION_OFFERED = ["specific_remedy", "generic_apology", "escalation_only",
                      "none", "no_reply"]

# ----------------------------------------------------------------- tool schema
def build_tool():
    return {
        "name": "record_review_analysis",
        "description": ("Record the structured analysis of exactly one customer review. "
                        "Base every field ONLY on the review text and the company's reply; "
                        "never invent details. Prefer 'unknown'/'unclear'/'none'/null over guessing."),
        "input_schema": {
            "type": "object",
            "properties": {
                "primary_root_cause": {"type": "string", "enum": ROOT_CAUSES,
                    "description": "Single dominant driver of the experience. Use 'positive_experience' for satisfied reviews."},
                "primary_root_cause_confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                "secondary_themes": {"type": "array", "items": {"type": "string", "enum": ROOT_CAUSES},
                    "description": "0-4 other clearly-present themes. Exclude the primary; never list positive_experience here."},
                "product_line": {"type": "string", "enum": PRODUCT_LINES,
                    "description": "Course/credential category. 'unknown' if the review gives no signal."},
                "product_line_confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                "regulator_or_state": {"type": ["string", "null"],
                    "description": "Any named regulator or US state/jurisdiction (e.g. 'OSHA', 'Texas', 'California DRE'), else null."},
                "dollar_amount_mentioned": {"type": ["number", "null"],
                    "description": "Single most relevant USD figure the reviewer cites (e.g. a disputed charge). Number only, else null."},
                "refund_requested": {"type": "boolean"},
                "resolution_requested": {"type": "string", "enum": RESOLUTION_REQUESTED},
                "resolution_offered_in_reply": {"type": "string", "enum": RESOLUTION_OFFERED,
                    "description": "What the COMPANY REPLY offers. 'no_reply' if there is no reply."},
                "sentiment_intensity": {"type": "integer", "minimum": 1, "maximum": 5,
                    "description": "1=furious/harmed, 2=dissatisfied, 3=mixed/neutral, 4=satisfied, 5=delighted."},
                "is_actionable": {"type": "boolean",
                    "description": "True ONLY if the review names a specific operational issue the company could fix."},
                "actionability_rationale": {"type": "string", "description": "<= 20 words."},
                "extraction_flags": {"type": "string",
                    "enum": ["ok", "too_short", "non_english", "off_topic", "refusal"]},
            },
            "required": ["primary_root_cause", "primary_root_cause_confidence", "secondary_themes",
                         "product_line", "product_line_confidence", "regulator_or_state",
                         "dollar_amount_mentioned", "refund_requested", "resolution_requested",
                         "resolution_offered_in_reply", "sentiment_intensity", "is_actionable",
                         "actionability_rationale", "extraction_flags"],
        },
        "cache_control": {"type": "ephemeral"},
    }

SYSTEM_INSTRUCTIONS = """You are a meticulous analyst extracting structured data from 360training customer reviews. 360training sells online compliance and career-training courses (OSHA safety, real-estate licensing, food-handler, TABC alcohol-server, notary, cosmetology, HVAC/trades, insurance, healthcare CE, workforce/HR, driver-ed).

For each review you are given the star rating, title, review text, and the company's public reply (if any). Call record_review_analysis exactly once. Base every field ONLY on the provided text; never infer facts that aren't supported. When the text gives no signal for a field, use the conservative value ('unknown', 'unclear', 'none', or null) rather than guessing.

primary_root_cause — the single dominant driver. Vocabulary:
  billing_refund: charges, double-charges, billing disputes, money owed back
  support_service: unhelpful/rude/unreachable human customer service
  phone_automation: stuck in IVR/robots/recordings, can't reach a person
  language_barrier: agent hard to understand / language difficulty
  offshore: explicitly mentions overseas/offshore/outsourced support
  exam_test_glitch: exam/quiz froze, crashed, kicked out, lost progress
  certificate_reporting: certificate/license not issued or not reported to a state/board
  access_expiration: course access expired / locked out / time-limited
  scam_fraud: calls the company a scam/fraud/ripoff/predatory
  course_content: content outdated, boring, confusing, poor quality
  seat_time_timer: forced seat-time / countdown timer / must wait to proceed
  pricing_value: price too high / poor value (NOT a billing-mechanics dispute)
  platform_usability: website/app navigation, login, browser, UX friction
  proctoring: remote proctor / ID-verification problems
  positive_experience: reviewer is satisfied (use for most 4-5 star reviews)
  other / unclear: nothing fits / cannot tell

secondary_themes — 0-4 other clearly-present themes from the same vocabulary (exclude the primary; do NOT list positive_experience).
product_line — the course category; 'unknown' if no signal.
regulator_or_state — any named regulator or US state, else null.
dollar_amount_mentioned — the single most relevant USD figure (e.g. a disputed charge), else null.
refund_requested — reviewer asks for or clearly wants a refund.
resolution_requested — what the reviewer wants from the company.
resolution_offered_in_reply — what the COMPANY REPLY offers ('no_reply' if there is no reply).
sentiment_intensity — 1 furious ... 5 delighted.
is_actionable — true ONLY if a specific fixable operational issue is named.
actionability_rationale — <= 20 words.
extraction_flags — 'ok' normally; else too_short / non_english / off_topic / refusal.

Worked example. 1-star, "Charged me twice and no one answers the phone, I want my $49 back" with no reply →
primary_root_cause=billing_refund, secondary_themes=[phone_automation], product_line=unknown, dollar_amount_mentioned=49, refund_requested=true, resolution_requested=refund, resolution_offered_in_reply=no_reply, sentiment_intensity=1, is_actionable=true, extraction_flags=ok."""

def system_blocks():
    return [{"type": "text", "text": SYSTEM_INSTRUCTIONS, "cache_control": {"type": "ephemeral"}}]

# ----------------------------------------------------------------- request building
def build_user_text(row):
    title = str(row.get("review_title") or "")[:300]
    text = str(row.get("review_text") or "")[:2000]
    reply = row.get("company_reply")
    reply = str(reply)[:1500] if isinstance(reply, str) and reply.strip() else "(no reply)"
    return (f"STAR: {int(row['star_rating'])}/5\nTITLE: {title}\n"
            f"REVIEW: {text}\nCOMPANY_REPLY: {reply}")

def build_params(row, tool, model=HAIKU):
    return {
        "model": model, "max_tokens": 1024, "temperature": 0,
        "system": system_blocks(), "tools": [tool],
        "tool_choice": {"type": "tool", "name": tool["name"]},
        "messages": [{"role": "user", "content": build_user_text(row)}],
    }

# ----------------------------------------------------------------- key / client
def load_api_key():
    path = os.path.expanduser("~/.config/anthropic.env")
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:]
            if line.startswith("ANTHROPIC_API_KEY"):
                _, _, val = line.partition("=")
                return val.strip().strip('"').strip("'")
    raise SystemExit("ANTHROPIC_API_KEY not found in ~/.config/anthropic.env")

def client():
    import anthropic
    key = load_api_key()
    print(f"  [key] len={len(key)} prefix={key[:14]}…", flush=True)
    return anthropic.Anthropic(api_key=key)

# ----------------------------------------------------------------- parsing
def parse_tool_use(message):
    for block in message.content:
        if getattr(block, "type", None) == "tool_use":
            return dict(block.input)
    return None

def usage_dict(u):
    return {
        "input_tokens": getattr(u, "input_tokens", 0) or 0,
        "output_tokens": getattr(u, "output_tokens", 0) or 0,
        "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", 0) or 0,
        "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", 0) or 0,
    }

def sync_call(cl, row, tool, model=HAIKU, retries=4):
    import anthropic
    for attempt in range(retries):
        try:
            msg = cl.messages.create(**build_params(row, tool, model=model))
            return parse_tool_use(msg), usage_dict(msg.usage), None
        except (anthropic.RateLimitError, anthropic.APIStatusError, anthropic.APIConnectionError) as e:
            if attempt == retries - 1:
                return None, None, f"{type(e).__name__}: {str(e)[:200]}"
            time.sleep(2 ** attempt)
    return None, None, "exhausted"

# ----------------------------------------------------------------- sampling
def stratified_sample(df, n=150, seed=42):
    """Cover all star bands; oversample negatives (the analytic focus). Stable seed
    so pilot and validate hit the SAME gold 150."""
    base = {1: 40, 2: 25, 3: 25, 4: 30, 5: 30}   # sums to 150
    scale = n / 150.0
    parts = []
    for star, k in base.items():
        k = max(1, round(k * scale))
        pool = df[df["star_rating"] == star]
        if len(pool):
            parts.append(pool.sample(min(k, len(pool)), random_state=seed))
    out = pd.concat(parts).sample(frac=1, random_state=seed).reset_index(drop=True)
    return out

# ----------------------------------------------------------------- cost
def cost_of(usage, batch=False):
    """USD for a usage dict at Haiku 4.5 list price (assumptions stated up top)."""
    disc = BATCH_DISCOUNT if batch else 1.0
    uncached_in = usage["input_tokens"]            # SDK input_tokens excludes cache tokens
    cw = usage["cache_creation_input_tokens"]
    cr = usage["cache_read_input_tokens"]
    out = usage["output_tokens"]
    in_cost = (uncached_in + cw * CACHE_WRITE_MULT + cr * CACHE_READ_MULT) * HAIKU_IN / 1e6
    out_cost = out * HAIKU_OUT / 1e6
    return (in_cost + out_cost) * disc

def sum_usage(usages):
    tot = {"input_tokens": 0, "output_tokens": 0,
           "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}
    for u in usages:
        for k in tot:
            tot[k] += u.get(k, 0)
    return tot

# ----------------------------------------------------------------- row -> output dict
ROW_META = ["review_id", "published_date", "star_rating", "month", "neg"]

def coerce_vocab(fields):
    """Tool-use enums are SOFT constraints — the model can rarely emit an
    out-of-vocab value (~0.02% observed). Coerce to the residual category so
    downstream charts never show a phantom class. Logged in the method doc."""
    if fields.get("primary_root_cause") not in ROOT_CAUSES:
        fields["primary_root_cause"] = "other"
    if fields.get("product_line") not in PRODUCT_LINES:
        fields["product_line"] = "unknown"
    sec = fields.get("secondary_themes")
    if isinstance(sec, list):
        fields["secondary_themes"] = [s for s in sec if s in ROOT_CAUSES]
    return fields

def flatten(review_id, row, fields):
    fields = coerce_vocab(dict(fields))
    rec = {"review_id": review_id,
           "published_date": str(row["published_date"]),
           "star_rating": int(row["star_rating"]),
           "month": row["month"], "neg": bool(row["neg"])}
    for k, v in fields.items():
        if k == "secondary_themes":
            rec[k] = "|".join(v) if isinstance(v, list) else (v or "")
        else:
            rec[k] = v
    return rec

# ================================================================= MODES
def mode_schema():
    ensure_dirs()
    tool = build_tool()
    crosswalk = {t: t for t in CC1_THEMES}   # 1:1 back to CC1 keyword themes
    crosswalk.update({
        "seat_time_timer": "(novel — CC2-E; not in CC1 keyword taxonomy)",
        "pricing_value": "(extension — overlaps CC1 course_content/billing_refund)",
        "platform_usability": "(extension — not in CC1 keyword taxonomy)",
        "proctoring": "(extension — not in CC1 keyword taxonomy)",
        "positive_experience": "(non-negative — no CC1 theme)",
        "other": "(residual)", "unclear": "(residual)",
    })
    payload = {
        "model": HAIKU, "temperature": 0, "output": "forced tool_use",
        "tool": tool,
        "vocabularies": {"primary_root_cause": ROOT_CAUSES, "product_line": PRODUCT_LINES,
                         "resolution_requested": RESOLUTION_REQUESTED,
                         "resolution_offered_in_reply": RESOLUTION_OFFERED},
        "root_cause_to_cc1_crosswalk": crosswalk,
        "notes": ("primary_root_cause keys 0-9 are CC1's exact theme keys for clean "
                  "reconciliation; keys 10-13 are extensions the keyword taxonomy cannot see."),
    }
    path = f"{OUT}/CC2_extraction_schema.json"
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"wrote {path}")
    print(f"root_cause vocab: {len(ROOT_CAUSES)}  product_line vocab: {len(PRODUCT_LINES)}")

def mode_pilot(n=150):
    ensure_dirs()
    df = load_trustpilot()
    samp = stratified_sample(df, n=n)
    print(f"pilot: {len(samp)} reviews (stars: "
          f"{samp['star_rating'].value_counts().sort_index().to_dict()})")
    tool = build_tool()
    cl = client()

    rows, usages, errors = [], [], []
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(sync_call, cl, r, tool): r for _, r in samp.iterrows()}
        for i, fut in enumerate(cf.as_completed(futs), 1):
            r = futs[fut]
            fields, usage, err = fut.result()
            if err or fields is None:
                errors.append({"review_id": r["review_id"], "error": err or "no_tool_use"})
            else:
                rows.append(flatten(r["review_id"], r, fields))
                usages.append(usage)
            if i % 25 == 0:
                print(f"  {i}/{len(samp)} done", flush=True)
    dt = time.time() - t0

    out = pd.DataFrame(rows)
    path = f"{OUT}/CC2_pilot_extractions.csv"
    out.to_csv(path, index=False)

    tot = sum_usage(usages)
    pilot_cost = cost_of(tot, batch=False)
    per_review = pilot_cost / max(1, len(usages))
    # full-run estimate: same token profile, but Batch API (50% off)
    full_batch_est = per_review * BATCH_DISCOUNT * len(df)

    print("\n================= PILOT RESULT =================")
    print(f"parsed ok        : {len(rows)}/{len(samp)}   errors: {len(errors)}")
    print(f"wall time        : {dt:.1f}s")
    print(f"tokens (sum)     : in={tot['input_tokens']}  out={tot['output_tokens']}  "
          f"cache_write={tot['cache_creation_input_tokens']}  cache_read={tot['cache_read_input_tokens']}")
    print(f"pilot cost (sync): ${pilot_cost:.4f}   per-review ${per_review:.5f}")
    print(f"FULL-RUN ESTIMATE: {len(df)} reviews via Batch API ≈ ${full_batch_est:.2f} "
          f"(sync would be ≈ ${per_review*len(df):.2f})")
    print(f"wrote {path}")
    if errors:
        print("first errors:", errors[:3])
    if len(rows):
        print("\nsample distribution (primary_root_cause):")
        print(out["primary_root_cause"].value_counts().head(12).to_string())
        print("\nproduct_line:")
        print(out["product_line"].value_counts().to_string())
        print(f"\ndollar_amount non-null: {out['dollar_amount_mentioned'].notna().sum()}/{len(out)}")
        print(f"is_actionable true    : {int(out['is_actionable'].sum())}/{len(out)}")
    # persist a small cost record for the method doc
    with open(f"{OUT}/CC2_pilot_cost.json", "w") as f:
        json.dump({"n": len(samp), "parsed": len(rows), "errors": len(errors),
                   "usage": tot, "pilot_cost_usd": round(pilot_cost, 4),
                   "per_review_usd": round(per_review, 6),
                   "full_batch_estimate_usd": round(full_batch_est, 2),
                   "n_full": int(len(df))}, f, indent=2)

def mode_submit(chunk_size=2500):
    # Safety: refuse to double-submit (this spends money). Delete the id file to force.
    if batch_ids():
        print(f"REFUSING: {OUT}/CC2_batch_id.txt already lists {len(batch_ids())} batch id(s).")
        print("Batches were already submitted. To intentionally re-submit, delete that file first.")
        return
    df = load_trustpilot()
    tool = build_tool()
    done = ledger_done()                              # idempotent vs anything already retrieved
    todo = df[~df["review_id"].isin(done)]
    print(f"submit: {len(todo)} reviews ({len(done)} already in ledger)")
    if len(todo) == 0:
        print("nothing to submit."); return
    cl = client()
    rows = list(todo.iterrows())
    n_chunks = (len(rows) + chunk_size - 1) // chunk_size
    # Chunked upload: each request re-embeds the ~1.8k-token prefix, so one giant
    # POST would be ~90MB and fragile. ~5 chunks of ~18MB is far more robust.
    print(f"submitting in {n_chunks} chunk(s) of up to {chunk_size}…")
    with open(f"{OUT}/CC2_batch_id.txt", "a") as f:
        for ci in range(n_chunks):
            chunk = rows[ci * chunk_size:(ci + 1) * chunk_size]
            requests = [{"custom_id": r["review_id"], "params": build_params(r, tool)}
                        for _, r in chunk]
            print(f"  chunk {ci + 1}/{n_chunks}: creating batch of {len(requests)}…", flush=True)
            batch = cl.messages.batches.create(requests=requests)
            f.write(batch.id + "\n"); f.flush()
            print(f"    -> {batch.id}  status={batch.processing_status}")
    print(f"ALL CHUNKS SUBMITTED; ids in {OUT}/CC2_batch_id.txt")
    print("  poll with:  python cc2_c_extract.py poll")

def batch_ids():
    path = f"{OUT}/CC2_batch_id.txt"
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [ln.strip() for ln in f if ln.strip()]

def mode_poll():
    cl = client()
    for bid in batch_ids():
        b = cl.messages.batches.retrieve(bid)
        c = b.request_counts
        print(f"{bid}: {b.processing_status}  "
              f"succeeded={c.succeeded} errored={c.errored} processing={c.processing} "
              f"canceled={c.canceled} expired={c.expired}")

def mode_waitfor(max_min=180):
    """Block (polling every 60s) until every batch ends. Safe to run detached —
    re-invokes the agent only when it EXITS. time.sleep is fine inside this subprocess."""
    cl = client()
    ids = batch_ids()
    if not ids:
        print("no batch ids to wait for."); return
    waited = 0
    while True:
        statuses = [cl.messages.batches.retrieve(bid).processing_status for bid in ids]
        ended = sum(1 for s in statuses if s == "ended")
        print(f"[waitfor +{waited}m] ended={ended}/{len(ids)} {statuses}", flush=True)
        if ended == len(ids):
            print("ALL BATCHES ENDED"); return
        if waited >= max_min:
            print(f"TIMEOUT after {max_min}m (status above)"); return
        time.sleep(60); waited += 1

def ledger_done():
    path = f"{OUT}/CC2_extraction_ledger.jsonl"
    done = set()
    if os.path.exists(path):
        with open(path) as f:
            for ln in f:
                try:
                    done.add(json.loads(ln)["review_id"])
                except Exception:
                    pass
    return done

def mode_retrieve():
    cl = client()
    df = load_trustpilot().set_index("review_id")
    ledger_path = f"{OUT}/CC2_extraction_ledger.jsonl"
    done = ledger_done()
    n_new, n_err = 0, 0
    with open(ledger_path, "a") as led:
        for bid in batch_ids():
            b = cl.messages.batches.retrieve(bid)
            if b.processing_status != "ended":
                print(f"{bid}: not ended ({b.processing_status}); skipping"); continue
            for res in cl.messages.batches.results(bid):
                rid = res.custom_id
                if rid in done:
                    continue
                rtype = res.result.type
                if rtype == "succeeded":
                    fields = parse_tool_use(res.result.message)
                    if fields is None:
                        led.write(json.dumps({"review_id": rid, "ok": False, "error": "no_tool_use"}) + "\n")
                        n_err += 1
                        continue
                    led.write(json.dumps({"review_id": rid, "ok": True, "fields": fields,
                                          "usage": usage_dict(res.result.message.usage)}) + "\n")
                    done.add(rid); n_new += 1
                else:
                    led.write(json.dumps({"review_id": rid, "ok": False, "error": rtype}) + "\n")
                    n_err += 1
    print(f"retrieve: +{n_new} new, {n_err} errored")
    # rebuild the spine CSV from the full ledger
    rows = []
    with open(ledger_path) as f:
        for ln in f:
            o = json.loads(ln)
            if not o.get("ok"):
                continue
            rid = o["review_id"]
            if rid not in df.index:
                continue
            rows.append(flatten(rid, df.loc[rid], o["fields"]))
    spine = pd.DataFrame(rows).drop_duplicates("review_id").sort_values("published_date")
    path = f"{OUT}/CC2_review_extractions.csv"
    spine.to_csv(path, index=False)
    print(f"wrote {path}  ({len(spine)} rows)")
    if len(spine):
        print("\nprimary_root_cause (all):")
        print(spine["primary_root_cause"].value_counts().to_string())
        print("\nproduct_line coverage (non-unknown): "
              f"{(spine['product_line'] != 'unknown').mean():.1%}")

# ----------------------------------------------------------------- validation
def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (p, max(0.0, centre - half), min(1.0, centre + half))

def norm(v):
    """Normalize a value for equality comparison: collapse int-valued floats
    ('1.0' from a CSV round-trip) to '1' so they don't spuriously mismatch
    Sonnet's integer output. Leaves strings/bools as their str()."""
    try:
        if isinstance(v, float) and not math.isnan(v) and float(v).is_integer():
            return str(int(v))
    except (TypeError, ValueError):
        pass
    return str(v)

ENUM_FIELDS = ["primary_root_cause", "product_line", "resolution_requested",
               "resolution_offered_in_reply", "refund_requested", "is_actionable",
               "extraction_flags", "sentiment_intensity"]

def mode_validate(n=150):
    df = load_trustpilot()
    samp = stratified_sample(df, n=n).set_index("review_id")
    # Haiku labels: prefer full spine, fall back to pilot
    src = None
    for cand in ["CC2_review_extractions.csv", "CC2_pilot_extractions.csv"]:
        if os.path.exists(f"{OUT}/{cand}"):
            src = f"{OUT}/{cand}"; break
    if src is None:
        raise SystemExit("no extraction file found — run pilot or retrieve first")
    haiku = pd.read_csv(src).set_index("review_id")
    ids = [i for i in samp.index if i in haiku.index]
    print(f"validate: {len(ids)} reviews with Haiku labels from {os.path.basename(src)}")

    tool = build_tool()
    cl = client()
    son = {}
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(sync_call, cl, samp.loc[i], tool, SONNET): i for i in ids}
        for j, fut in enumerate(cf.as_completed(futs), 1):
            i = futs[fut]
            fields, _, err = fut.result()
            if fields and not err:
                son[i] = fields
            if j % 25 == 0:
                print(f"  sonnet {j}/{len(ids)}", flush=True)

    ids = [i for i in ids if i in son]   # keep only paired
    print(f"paired (both models): {len(ids)}")

    def hval(i, k):
        v = haiku.loc[i].get(k)
        return v
    def sval(i, k):
        v = son[i].get(k)
        return "|".join(v) if isinstance(v, list) else v

    # per-field agreement
    report = []
    for k in ENUM_FIELDS:
        agree = sum(1 for i in ids if norm(hval(i, k)) == norm(sval(i, k)))
        p, lo, hi = wilson(agree, len(ids))
        report.append((k, agree, len(ids), p, lo, hi))
    # secondary_themes: set agreement (Jaccard >= 0.5 counts as agree) + exact
    def themeset(x):
        if isinstance(x, list):
            return set(x)
        return set(str(x).split("|")) - {"", "nan"}
    jac_hits = 0
    for i in ids:
        hs, ss = themeset(haiku.loc[i].get("secondary_themes")), themeset(son[i].get("secondary_themes"))
        if not hs and not ss:
            jac_hits += 1
        else:
            j = len(hs & ss) / max(1, len(hs | ss))
            if j >= 0.5:
                jac_hits += 1
    # dollar: both-null or within 1%
    dol_hits = 0
    for i in ids:
        hd, sd = haiku.loc[i].get("dollar_amount_mentioned"), son[i].get("dollar_amount_mentioned")
        hd = None if (pd.isna(hd) if not isinstance(hd, list) else True) else hd
        if hd is None and sd is None:
            dol_hits += 1
        elif hd is not None and sd is not None:
            try:
                if abs(float(hd) - float(sd)) <= max(0.01, 0.01 * abs(float(hd))):
                    dol_hits += 1
            except Exception:
                pass

    # per-class product_line agreement (where Haiku assigned each class)
    pl_rows = []
    for cls in PRODUCT_LINES:
        idx = [i for i in ids if norm(hval(i, "product_line")) == cls]
        if len(idx) < 3:
            continue
        a = sum(1 for i in idx if norm(sval(i, "product_line")) == cls)
        p, lo, hi = wilson(a, len(idx))
        pl_rows.append((cls, a, len(idx), p, lo, hi))

    # gold-set scaffold (for the human pass)
    gold = []
    for i in ids:
        h_prc, s_prc = str(hval(i, "primary_root_cause")), str(sval(i, "primary_root_cause"))
        h_pl, s_pl = str(hval(i, "product_line")), str(sval(i, "product_line"))
        gold.append({
            "review_id": i, "star_rating": int(samp.loc[i, "star_rating"]),
            "text_snippet": str(samp.loc[i, "review_text"] or "")[:240].replace("\n", " "),
            "haiku_primary_root_cause": h_prc, "sonnet_primary_root_cause": s_prc,
            "human_primary_root_cause": "",
            "haiku_product_line": h_pl, "sonnet_product_line": s_pl,
            "human_product_line": "",
            "disagree_root_cause": h_prc != s_prc, "disagree_product_line": h_pl != s_pl,
        })
    gold_df = pd.DataFrame(gold).sort_values(["disagree_root_cause", "disagree_product_line"], ascending=False)
    gold_df.to_csv(f"{OUT}/CC2_gold_set.csv", index=False)

    n_dis = int(gold_df["disagree_root_cause"].sum())
    # write the validation markdown
    lines = []
    lines.append("# CC2-C — Extraction Validation (model–model agreement)\n")
    lines.append("> **What this is, precisely.** Haiku 4.5 produced the extractions; an independent model "
                 "(Sonnet 4.6) re-extracted the same stratified 150 from scratch. Below is **per-field agreement "
                 "between the two models, with Wilson 95% CIs.** Agreement measures **reproducibility/consistency, "
                 "NOT accuracy.** It is neither an upper nor a lower bound on accuracy: two models can share a "
                 "blind spot and agree on a *wrong* label (agreement > accuracy), or disagree on an item one of "
                 "them got right (accuracy > agreement). Critically, Haiku and Sonnet **share a model lineage, so "
                 "their errors are likely correlated — which makes this agreement rate most plausibly an "
                 "OPTIMISTIC proxy that OVERSTATES true accuracy.** The certified precision number comes only from "
                 "the **human gold pass** scaffolded in `CC2_gold_set.csv` (blank `human_*` columns; the "
                 f"**{n_dis} root-cause disagreements are pre-sorted to the top** for efficient adjudication — the "
                 "plan's 'Sonnet triages disagreements to human review' role). κ is not reported: with two "
                 "same-family raters and no certified truth, an agreement RATE is the honest statistic.\n")
    lines.append(f"\n**Paired sample:** {len(ids)} reviews (stratified across all star bands).\n")
    lines.append("\n## Per-field agreement (Haiku vs Sonnet)\n")
    lines.append("| Field | Agree | n | Rate | Wilson 95% CI |")
    lines.append("|---|---|---|---|---|")
    for k, a, nn, p, lo, hi in report:
        lines.append(f"| {k} | {a} | {nn} | {p:.1%} | {lo:.1%}–{hi:.1%} |")
    p, lo, hi = wilson(jac_hits, len(ids))
    lines.append(f"| secondary_themes (Jaccard≥0.5) | {jac_hits} | {len(ids)} | {p:.1%} | {lo:.1%}–{hi:.1%} |")
    p, lo, hi = wilson(dol_hits, len(ids))
    lines.append(f"| dollar_amount (±1% or both-null) | {dol_hits} | {len(ids)} | {p:.1%} | {lo:.1%}–{hi:.1%} |")
    lines.append("\n## product_line agreement by class (where Haiku assigned the class)\n")
    lines.append("| Haiku class | Agree | n | Rate | Wilson 95% CI |")
    lines.append("|---|---|---|---|---|")
    for cls, a, nn, p, lo, hi in pl_rows:
        lines.append(f"| {cls} | {a} | {nn} | {p:.1%} | {lo:.1%}–{hi:.1%} |")
    lines.append("\n*Note: the headline product_line agreement (per-field table) is inflated by both models "
                 "agreeing on the majority `unknown` class; the specific-class rows above are the meaningful signal.*\n")
    lines.append("\n## Honesty boundary\n")
    lines.append("- **Agreement ≠ accuracy, and here it most likely OVERSTATES it** (correlated same-family errors). "
                 "Treat the rates as a reproducibility / triage signal, never a precision claim.\n"
                 "- **The B-v2 / G-full gate (product_line precision ≥ 0.85) is UNRESOLVED.** That bar is defined on "
                 "human-certified precision, which this autonomous run cannot produce; agreement is not precision. "
                 "→ **B-v2 and G-full stay at v1 by default.** C's value here is standalone descriptive enrichment "
                 "(richer 17-way root-cause distribution incl. novel themes; product-line coverage ~27% vs ~11% "
                 "keyword; new dollar / resolution-gap / actionability fields), **not** unlocking the gated upgrades.\n"
                 "- The gold set is **deliberately negative-oversampled** (40/25/25/30/30 by star) to exercise "
                 "failure modes, so these agreement rates are **not population-weighted** and over-represent 1–2★.\n"
                 "- Fields with low agreement (inspect the table) are the least trustworthy for downstream use.\n")
    with open(f"{OUT}/CC2_extraction_validation.md", "w") as f:
        f.write("\n".join(lines) + "\n")

    print("\n================= VALIDATION =================")
    for k, a, nn, p, lo, hi in report:
        print(f"  {k:32s} {p:5.1%}  ({lo:.0%}-{hi:.0%})  n={nn}")
    print(f"  {'secondary_themes(J>=.5)':32s} {jac_hits/len(ids):5.1%}")
    print(f"  {'dollar(±1%/both-null)':32s} {dol_hits/len(ids):5.1%}")
    print(f"\nroot-cause disagreements routed to human: {n_dis}")
    print(f"wrote {OUT}/CC2_gold_set.csv and {OUT}/CC2_extraction_validation.md")

def mode_method():
    """Write CC2_extraction_method.md with the ACTUAL batch cost from the ledger."""
    ledger_path = f"{OUT}/CC2_extraction_ledger.jsonl"
    usages, ok, err = [], 0, 0
    with open(ledger_path) as f:
        for ln in f:
            o = json.loads(ln)
            if o.get("ok"):
                ok += 1
                if "usage" in o:
                    usages.append(o["usage"])
            else:
                err += 1
    tot = sum_usage(usages)
    actual = cost_of(tot, batch=True)
    pilot = {}
    if os.path.exists(f"{OUT}/CC2_pilot_cost.json"):
        with open(f"{OUT}/CC2_pilot_cost.json") as f:
            pilot = json.load(f)
    spine = pd.read_csv(f"{OUT}/CC2_review_extractions.csv")
    pl_cov = (spine["product_line"] != "unknown").mean()
    novel = int(spine["primary_root_cause"].isin(
        ["seat_time_timer", "platform_usability", "proctoring", "pricing_value"]).sum())

    m = []
    m.append("# CC2-C — LLM Structured Extraction: Method & Cost\n")
    m.append(f"**Model:** `{HAIKU}` (Haiku 4.5), `temperature=0`, forced single-tool output "
             f"(`tool_choice` pinned to `record_review_analysis`) so every response is schema-valid JSON.\n")
    m.append(f"**Scale:** {ok:,} reviews extracted ({err} errored) via the **Message Batches API**, "
             "submitted in 5 chunks (idempotent JSONL ledger, `custom_id = review_id`). All five batches "
             "ended in ~4 minutes.\n")
    m.append("\n## What we extracted, and why it beats the keyword pass\n")
    m.append("14 typed fields per review (`CC2_extraction_schema.json`): `primary_root_cause` (+confidence), "
             "`secondary_themes[]`, `product_line` (+confidence), `regulator_or_state`, `dollar_amount_mentioned`, "
             "`refund_requested`, `resolution_requested`, `resolution_offered_in_reply`, `sentiment_intensity`, "
             "`is_actionable` (+rationale), `extraction_flags`. The `primary_root_cause` vocabulary is **CC1's exact "
             "10 keyword themes** (so counts reconcile) **plus** four themes the regex taxonomy is blind to — "
             "`seat_time_timer`, `platform_usability`, `proctoring`, `pricing_value` — validated in CC2-E. "
             f"Those four are the single dominant driver in **{novel:,} reviews** the keyword pass could not "
             f"classify. Product-line coverage is **{pl_cov:.1%}** (vs ~11% for the G-v1 keyword anchors), with "
             "the model assigning `unknown` rather than guessing when no signal exists.\n")
    m.append("\n## Cost (actual, from the ledger — not an estimate)\n")
    m.append(f"| | input tok | output tok | USD |")
    m.append("|---|---|---|---|")
    m.append(f"| Full batch ({ok:,} reviews) | {tot['input_tokens']:,} | {tot['output_tokens']:,} | "
             f"**${actual:,.2f}** |")
    if pilot:
        m.append(f"| Pilot (150, sync) | — | — | ${pilot.get('pilot_cost_usd', 0):.2f} |")
    m.append(f"\nPricing assumptions (stated for audit): Haiku 4.5 at ${HAIKU_IN:.2f}/${HAIKU_OUT:.2f} per MTok "
             f"in/out, Batch API −{int((1-BATCH_DISCOUNT)*100)}%. **Prompt caching did not engage**: the "
             "system+tool prefix (~1.8k tokens) sits under Haiku's 2,048-token cache minimum, and batch cache "
             "hits are best-effort regardless — so the figure above reflects no cache discount (measured "
             "`cache_read = 0`). Honest, not optimized.\n")
    m.append("\n## Validation & the honest limit (see `CC2_extraction_validation.md`)\n")
    m.append("An independent model (Sonnet 4.6) re-extracted the stratified 150. Per-field **agreement** with "
             "Wilson 95% CIs: `primary_root_cause` 87%, `product_line` 96% (unknown-inflated; specific classes "
             "≥87%), `is_actionable` 95%, `refund_requested` 96%, `dollar_amount` 100%. **Agreement measures "
             "reproducibility, not accuracy — and because the two raters share a model lineage, it most likely "
             "OVERSTATES accuracy.** The B-v2/G-full precision gate (≥0.85, human-certified) is therefore "
             "**unresolved**; those upgrades stay at v1. C stands as descriptive enrichment. A human gold pass "
             "is scaffolded in `CC2_gold_set.csv` (19 disagreements pre-sorted for adjudication).\n")
    m.append("\n## Known limitations\n")
    m.append("- Tool-use enums are **soft** constraints: ~0.02% of outputs (2 reviews) emitted an out-of-vocab "
             "`primary_root_cause`; coerced to `other` at the spine-build step.\n"
             "- `primary_root_cause` is the *single* dominant driver — a review mentioning billing + support is "
             "counted once as primary; use `secondary_themes` to recover multi-theme prevalence.\n"
             "- Extractions are model-generated; treat as a high-quality first pass, not adjudicated ground truth.\n")
    path = f"{OUT}/CC2_extraction_method.md"
    with open(path, "w") as f:
        f.write("\n".join(m) + "\n")
    print(f"wrote {path}")
    print(f"ACTUAL batch cost: ${actual:.2f}  (in={tot['input_tokens']:,} out={tot['output_tokens']:,} tok)")
    print(f"novel-theme primaries: {novel:,}   product_line coverage: {pl_cov:.1%}")

# ================================================================= main
def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "help"
    arg = int(sys.argv[2]) if len(sys.argv) > 2 else None
    if mode == "schema":
        mode_schema()
    elif mode == "pilot":
        mode_pilot(arg or 150)
    elif mode == "submit":
        mode_submit()
    elif mode == "poll":
        mode_poll()
    elif mode == "waitfor":
        mode_waitfor(arg or 180)
    elif mode == "retrieve":
        mode_retrieve()
    elif mode == "validate":
        mode_validate(arg or 150)
    elif mode == "method":
        mode_method()
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
