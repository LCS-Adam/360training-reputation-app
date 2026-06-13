#!/usr/bin/env python3
"""
cc2_h_refresh.py — idempotent RHI recompute.

Run this after refreshing `00_source_materials/360training_trustpilot_ALL_reviews.json`
(and re-running the upstream CC2 component scripts) to regenerate the RHI timeseries
on the SAME frozen-2023 normalization — so historical RHI values do not move.

This is the "refresh" half of H. It is NOT a live monitor: a true nightly cadence
needs a Trustpilot ingestion feed (scraper/API + dedup on review_id), named as a
Production Consideration in CC2_kpi_system_design.md and NOT implemented here.
"""
from cc2_h_kpi import (build_components, assemble, sensitivity, alert_log,
                       write_timeseries, write_thresholds_yaml, write_design_doc,
                       chart_h1, chart_h2, chart_h3, chart_sensitivity, OUT)
from cc2_common import ensure_dirs

if __name__ == "__main__":
    ensure_dirs()
    comp = build_components()
    full = assemble(comp)
    sens = sensitivity(comp)
    al = alert_log(full)
    write_timeseries(full)
    write_thresholds_yaml()
    al.to_csv(f"{OUT}/CC2_alert_log.csv", index=False)
    sens.to_csv(f"{OUT}/CC2_rhi_sensitivity.csv", index=False)
    chart_h1(full); chart_h2(full); chart_h3(full); chart_sensitivity(sens)
    write_design_doc(full, sens, al)
    print(f"RHI recomputed (frozen 2023 reference unchanged): {len(full)} months, "
          f"latest {full['month'].iloc[-1]} RHI={full['RHI'].iloc[-1]:.1f}")
