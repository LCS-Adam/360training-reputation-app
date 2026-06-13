# 360training · Reputation Analytics (CC2) — Final Assets

Three deliverables, one analytical backbone. Every figure reconciles across all of them
(`cc2_consistency.py`: 22/22) and every claim is tagged **evidence / inference /
recommendation** with its load-bearing caveat.

| Asset | File | What it's for |
|---|---|---|
| **Live app** | `app.py` | Interactive walkthrough; two live "what-if" widgets |
| **PDF report** | `360training_Analytics_Report.pdf` | Self-contained read for a CEO/panel |
| **Slide deck** | `360training_Exec_Deck.pptx` | Editable money-chart deck (~12–15 slides) |

## Run the app

From the **project root** (so the data paths resolve):

```bash
./.venv/bin/streamlit run 07_final_assets/app.py
```

Then open the URL it prints (default <http://localhost:8501>).

### The two live widgets (and why they're trustworthy)
- **⑥ Revenue → break-even.** Drag in your own revenue / exposure / fix-cost; the break-even
  conversion lift updates live and is compared to the recoverable band. It imports the *same*
  `breakeven_x` formula that drew the static chart — slider and chart cannot disagree.
- **⑦ Health Index → weight sensitivity.** Re-weight the six RHI components however you like; the
  decline stays monotone-down. It reweights the *published* component z-scores (the final step of
  the static index), so with the default weights it reproduces the published RHI exactly.

## Verify the substance without the UI

The app is a thin view over a tested data/compute layer. To check every load and computation
(forecast coverage, break-even vs. the memo, RHI reweight vs. the published index, OSHA annual,
resolution-gap) without rendering anything:

```bash
./.venv/bin/python cc2_app_data.py     # 9/9 checks
```

## Regenerate the static charts / PDF / deck

```bash
./.venv/bin/python cc2_c_resolution_gap.py   # C1 resolution-gap exhibit
./.venv/bin/python cc2_g_segmentation.py     # G1/G2/G3 (incl. annual OSHA)
./.venv/bin/python build_report.py           # → 360training_Analytics_Report.pdf
./.venv/bin/python build_slides.py           # → 360training_Exec_Deck.pptx
```

## What the data cannot support (stated up front)
- **No provenance field** → solicited vs. organic reviews can't be separated; all rates are
  conditional on who chose to post (this caps the integrity audit).
- **Limited power** → ~27 post-break monthly points; monthly moves under ~5–7 pts are noise; no
  sub-segment with n < ~40/quarter is interpretable.
- **The LLM extraction is model-generated** — validated by model–model *agreement*
  (reproducibility), **not** human-certified accuracy. The B-v2/G-full precision gate stays
  unresolved; those upgrades remain v1.
