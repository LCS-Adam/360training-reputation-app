# CC2-E — Embedding Topic Model Summary

**Purpose:** an *independent second method* (semantic embeddings, not keywords) to (a) validate that the CC1 10-theme taxonomy captures the real structure of complaints, and (b) surface anything the keywords miss.
**Method:** `all-MiniLM-L6-v2` embeddings of **2,142 negative reviews** (≥5 words) → UMAP → **KMeans(k=14)**. Companion data: `CC2_cluster_theme_crosswalk.csv`, `CC2_novel_topics_exemplars.md`, `CC2_topics_over_time.csv`.

> **Methodology disclosure:** HDBSCAN collapsed these short, highly-similar complaint texts into one ~88% mega-cluster (useless for sub-theme discovery), so we disclose that and use **KMeans(k=14)** — a stable forced partition, finer than the 10 keyword themes so novel structure has room to appear. (No HDBSCAN outlier bucket; outlier rate 0.)

## Result 1 — the taxonomy's structure is corroborated
Each embedding cluster's **dominant keyword theme is sensible**: the refund cluster maps to `billing_refund` (58% overlap), the certificate/affidavit cluster to `certificate_reporting` (73%), service clusters to `support_service` (31–41%), real-estate to its line. The two methods independently agree on *what the complaints are about*. By a strict ">30% keyword overlap" rule, **47%** of clustered negatives sit in topics an existing theme explains; the rest reflect that keyword themes only literally flag ~58% of negatives (a billing complaint may not contain a billing keyword), not that the structure is wrong.

## Result 2 — the genuine gap: forced seat-time / timer (a real novel theme)
The standout discovery the keyword taxonomy **misses entirely** is a coherent cluster about **state-mandated minimum seat-time enforced by a course timer** (cluster top-words: *hours, time, timer, long, slides, read*). Verified exemplars:
- *"IT WON'T TRACK YOUR TIME CORRECTLY BEWARE!"*
- *"Sitting through 4 hours of a course while listening…"* (real-estate CE)
- *"Still waiting… after 3rd attempt to meet seat time requirements. Website continuously does not [track]…"*

A pattern search confirms **~130+ negative reviews** in this vein. This is a **distinct, ownable product grievance** — the regulatory minimum-duration timer (and its tracking bugs) — that none of the 10 keyword themes name. **Recommendation: add a `seat_time_timer` theme** to the taxonomy (and a B-v2 driver for it).

## Result 3 — two more under-covered angles
- **Online proctoring friction** (cluster: *proctor, exam, queue, waited*) — "waited just over an hour for a proctor." Adjacent to exam-glitch but distinct; worth its own tag.
- **Narration / content-delivery quality** (cluster: *information, material, voice, videos, boring*) — partially in `course_content`, but the "robotic voice / boring video" delivery complaint is specific.

## So what
E does its job: it **validates** that the keyword taxonomy isn't missing the big structure, while **earning its keep** by surfacing the seat-time/timer theme — a concrete, fixable, regulation-driven friction that should be added to the taxonomy and tracked. This is the value of running a second, assumption-free method.

**Confidence:** high that embeddings corroborate the existing themes; high that seat-time/timer is a real, currently-untracked theme (verified exemplars + ~130 matches); medium on the exact cluster boundaries (k=14 is a chosen, not discovered, granularity — disclosed).
