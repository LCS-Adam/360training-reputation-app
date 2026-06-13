"""
CC2-A Reputation forecast — where is the negative-review share headed?

Design:
- Model a time-varying LEVEL, NOT a global trend. The post-break series is a hump
  (rose to ~0.47 in 2024-12/2025-06, partially recovered to ~0.30). A trend line
  would falsely extrapolate the recovery; a local level honestly says "it persists
  near the recent level, with bands that widen."
- Weighted local-level Kalman filter on logit(neg_share). Per-month observation
  variance = phi / (n * p * (1-p)) (delta-method logit variance), where phi is an
  estimated OVERDISPERSION factor (reviews aren't iid within a month). Q (level
  innovation) and phi estimated jointly by MLE.
- Fit on the POST-BREAK window only (2024-03+, excl. partial 2026-06).
- Headline metric = rolling-origin empirical COVERAGE, not point accuracy. At
  n=50-90/mo we do NOT expect to beat a trailing-mean on point error; the claim is
  calibrated intervals.
- Counterfactual = associational recomposition (theme prevalence reverts to 2023,
  theme->neg association held fixed). Carries B's same-text + 58%-coverage caveats.
- Regime wording: CC1's DETECTED change-point is 2024-10; 2024-03 is the segment-
  comparison date. Both stated correctly.

Run: ./.venv/bin/python cc2_a_forecast.py
"""
import numpy as np
import pandas as pd
from scipy.special import expit, logit
from scipy.optimize import minimize
from scipy.stats import beta as beta_dist
from sklearn.linear_model import LogisticRegression

import cc2_common as cc

OUT = cc.OUT
plt = cc.apply_chart_style()
RNG = np.random.default_rng(42)

POST_START = "2024-03"      # post-break fit window start (first inflection / segment date)
DETECTED_BREAK = "2024-10"  # CC1's algorithmically-detected change-point
H_MAX = 6                   # forecast 6 months only
Z80, Z95 = 1.2815515594, 1.959963985


# ----------------------------------------------------------------- weighted local-level Kalman
def kalman_filter(y, base_var, Q, phi, diffuse=1e6):
    """Local level: a_t = a_{t-1}+eta (Var Q); y_t = a_t + eps (Var phi*base_var_t).
    Returns filtered a, P, one-step errors e, their variances F, loglik (diffuse-adjusted)."""
    T = len(y)
    a = np.zeros(T); P = np.zeros(T); e = np.zeros(T); F = np.zeros(T)
    a_pred, P_pred = y[0], diffuse
    ll = 0.0
    for t in range(T):
        if t > 0:
            a_pred = a[t-1]; P_pred = P[t-1] + Q
        H = phi * base_var[t]
        F[t] = P_pred + H
        e[t] = y[t] - a_pred
        if t > 0:  # skip diffuse first obs in the likelihood
            ll += -0.5 * (np.log(2*np.pi) + np.log(F[t]) + e[t]**2 / F[t])
        K = P_pred / F[t]
        a[t] = a_pred + K * e[t]
        P[t] = P_pred * (1 - K)
    return a, P, e, F, ll


def rts_smoother(a, P, Q):
    """Rauch-Tung-Striebel smoother for the local level."""
    T = len(a)
    a_s = a.copy(); P_s = P.copy()
    for t in range(T-2, -1, -1):
        P_pred = P[t] + Q
        C = P[t] / P_pred
        a_s[t] = a[t] + C * (a_s[t+1] - a[t])  # a_pred_{t+1}=a[t]
        P_s[t] = P[t] + C**2 * (P_s[t+1] - P_pred)
    return a_s, P_s


def fit_kalman(y, base_var):
    """MLE over (logQ, logphi)."""
    def nll(theta):
        Q, phi = np.exp(theta[0]), np.exp(theta[1])
        _, _, _, _, ll = kalman_filter(y, base_var, Q, phi)
        return -ll
    best = minimize(nll, x0=[np.log(0.02), np.log(1.0)], method="Nelder-Mead",
                    options=dict(xatol=1e-4, fatol=1e-4, maxiter=2000))
    Q, phi = np.exp(best.x[0]), np.exp(best.x[1])
    return Q, phi


# ----------------------------------------------------------------- main
def main():
    cc.ensure_dirs()
    df = cc.load_trustpilot()
    m = cc.monthly_metrics(df)                       # excludes partial months already
    post = m[m["month"] >= POST_START].reset_index(drop=True)
    months = post["month"].tolist()
    n = post["n"].values.astype(float)
    p_hat = post["neg_share"].values
    neg = post["neg_count"].values.astype(float)

    y = logit(p_hat)
    base_var = 1.0 / (n * p_hat * (1 - p_hat))       # delta-method logit obs variance

    Q, phi = fit_kalman(y, base_var)
    a, P, e, F, ll = kalman_filter(y, base_var, Q, phi)
    a_s, P_s = rts_smoother(a, P, Q)
    print(f"Fitted local-level: Q={Q:.4f}  overdispersion phi={phi:.2f}  loglik={ll:.2f}")
    print(f"(phi>1 => reviews are over-dispersed within a month; bands widened accordingly)")

    # ---- 6-month forecast (predictive distribution of an OBSERVED future month)
    n_future = float(np.median(n[-6:]))              # assume recent monthly volume
    aT, PT = a[-1], P[-1]
    p_med = expit(aT)
    fc_rows = []
    last_period = pd.Period(months[-1], "M")
    for h in range(1, H_MAX + 1):
        var_latent = PT + h * Q
        b_future = 1.0 / (n_future * p_med * (1 - p_med))
        var_pred = var_latent + phi * b_future        # incl. obs noise -> honest for coverage
        lo80, hi80 = expit(aT - Z80*np.sqrt(var_pred)), expit(aT + Z80*np.sqrt(var_pred))
        lo95, hi95 = expit(aT - Z95*np.sqrt(var_pred)), expit(aT + Z95*np.sqrt(var_pred))
        fc_rows.append(dict(month=str(last_period + h), type="forecast", n=np.nan,
                            observed_neg_share=np.nan, level_p=p_med,
                            forecast_p=p_med, lo80=lo80, hi80=hi80, lo95=lo95, hi95=hi95))

    obs_rows = []
    for i, mo in enumerate(months):
        # per-month Beta-binomial 80% credible interval for the observed share
        lo = beta_dist.ppf(0.10, 1 + neg[i], 1 + (n[i] - neg[i]))
        hi = beta_dist.ppf(0.90, 1 + neg[i], 1 + (n[i] - neg[i]))
        obs_rows.append(dict(month=mo, type="observed", n=n[i],
                             observed_neg_share=p_hat[i], level_p=expit(a_s[i]),
                             forecast_p=np.nan, lo80=lo, hi80=hi, lo95=np.nan, hi95=np.nan))
    fc_df = pd.DataFrame(obs_rows + fc_rows)
    fc_df.round(4).to_csv(f"{OUT}/CC2_reputation_forecast.csv", index=False)

    # ---- rolling-origin backtest (params fixed from full fit; state filtered out-of-sample)
    bt = []
    for origin in range(6, len(post) - 1):            # need >=6 pts to start
        y_tr = y[:origin+1]; bv_tr = base_var[:origin+1]
        a_o, P_o, _, _, _ = kalman_filter(y_tr, bv_tr, Q, phi)
        aT_o, PT_o, p_o = a_o[-1], P_o[-1], expit(a_o[-1])
        n_f = float(np.median(n[max(0, origin-5):origin+1]))
        for h in (1, 3, 6):
            tgt = origin + h
            if tgt >= len(post):
                continue
            var_pred = PT_o + h*Q + phi/(n_f*p_o*(1-p_o))
            lo80, hi80 = expit(aT_o - Z80*np.sqrt(var_pred)), expit(aT_o + Z80*np.sqrt(var_pred))
            lo95, hi95 = expit(aT_o - Z95*np.sqrt(var_pred)), expit(aT_o + Z95*np.sqrt(var_pred))
            actual = p_hat[tgt]
            naive = p_hat[origin]                      # last-value naive
            naive3 = np.mean(p_hat[max(0, origin-2):origin+1])
            bt.append(dict(origin=months[origin], horizon=h, predicted_p=p_o,
                           lo80=lo80, hi80=hi80, lo95=lo95, hi95=hi95, actual_p=actual,
                           covered80=int(lo80 <= actual <= hi80), covered95=int(lo95 <= actual <= hi95),
                           abs_err=abs(p_o-actual), naive_abs_err=abs(naive-actual),
                           naive3_abs_err=abs(naive3-actual)))
    bt_df = pd.DataFrame(bt)
    bt_df.round(4).to_csv(f"{OUT}/CC2_forecast_backtest.csv", index=False)
    cov80 = bt_df["covered80"].mean(); cov95 = bt_df["covered95"].mean()
    mae = bt_df["abs_err"].mean(); mae_n = bt_df["naive_abs_err"].mean(); mae_n3 = bt_df["naive3_abs_err"].mean()

    # ---- counterfactual recomposition (associational; theme->neg held fixed)
    assoc = LogisticRegression(penalty="l2", C=1.0, max_iter=2000)
    Xall = df[cc.THEME_COLS].astype(int).values
    assoc.fit(Xall, df["neg"].astype(int).values)
    yr23 = df[(df["month"] >= "2023-01") & (df["month"] <= "2023-12")]
    ypost = df[(df["month"] >= POST_START) & (df["month"] <= "2025-12")]
    prev23 = yr23[cc.THEME_COLS].mean().values
    prevpost = ypost[cc.THEME_COLS].mean().values

    def implied_neg(prev, nsim=4000):
        sims = (RNG.random((nsim, len(prev))) < prev).astype(int)
        pp = assoc.predict_proba(sims)[:, 1]
        # bootstrap band over the simulated mean
        means = [pp[RNG.integers(0, nsim, nsim)].mean() for _ in range(300)]
        return pp.mean(), np.percentile(means, 2.5), np.percentile(means, 97.5)

    # Anchor to the ACTUAL observed levels so the scenarios reconcile with the forecast.
    # The mix model omits co-occurrence + the 42% untagged negatives, so it UNDER-predicts
    # the absolute level; we therefore use it for the DELTA (mix-attributable change) only
    # and apply that delta to the observed post-window level.
    obs_post = float(ypost["neg"].mean())
    obs_2023 = float(yr23["neg"].mean())
    mix_sq = implied_neg(prevpost)[0]
    cf = []
    for label, frac in [("status_quo (no revert)", 0.0), ("half revert to 2023", 0.5), ("full revert to 2023", 1.0)]:
        prev = prevpost + frac * (prev23 - prevpost)
        mu, lo, hi = implied_neg(prev)
        delta = mu - mix_sq                       # mix-attributable change vs status-quo mix
        anchored = obs_post + delta
        cf.append(dict(scenario=label, mix_model_implied=round(mu, 4),
                       delta_vs_statusquo=round(delta, 4), anchored_neg_share=round(anchored, 4),
                       caveat="DELTA only is used (mix omits co-occurrence + 42% untagged); anchored to observed; associational, not causal"))
    cf_df = pd.DataFrame(cf)
    cf_df.to_csv(f"{OUT}/CC2_counterfactual_scenarios.csv", index=False)
    mix_attrib = cf_df["delta_vs_statusquo"].iloc[2]            # full-revert delta (negative)
    total_rise = obs_post - obs_2023
    print(f"\nDECOMPOSITION: observed rise 2023->post = {total_rise:+.3f}; "
          f"complaint-mix shift explains {-mix_attrib:+.3f} (full revert); "
          f"residual {total_rise + mix_attrib:+.3f} = untagged / base-sentiment drift.")

    # ---- reply-ops trend (SEPARATE process)
    ro = m[m["month"] >= "2024-01"][["month", "median_reply_lag", "reply_rate", "n"]].copy()
    ro.round(3).to_csv(f"{OUT}/CC2_replyops_trend.csv", index=False)

    # ============================================================ charts
    obs = fc_df[fc_df.type == "observed"]; fc = fc_df[fc_df.type == "forecast"]
    xall = list(obs["month"]) + list(fc["month"])
    xi = np.arange(len(xall)); split = len(obs)
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.scatter(xi[:split], obs["observed_neg_share"], s=obs["n"]*0.8, color=cc.RED, alpha=0.6, label="observed (size∝n)")
    ax.plot(xi[:split], obs["level_p"], color=cc.NAVY, lw=2, label="estimated level (smoothed)")
    xf = xi[split-1:]; pf = [obs["level_p"].iloc[-1]] + list(fc["forecast_p"])
    lo80f = [obs["level_p"].iloc[-1]] + list(fc["lo80"]); hi80f = [obs["level_p"].iloc[-1]] + list(fc["hi80"])
    lo95f = [obs["level_p"].iloc[-1]] + list(fc["lo95"]); hi95f = [obs["level_p"].iloc[-1]] + list(fc["hi95"])
    ax.fill_between(xf, lo95f, hi95f, color=cc.NAVY, alpha=0.12, label="95% predictive")
    ax.fill_between(xf, lo80f, hi80f, color=cc.NAVY, alpha=0.22, label="80% predictive")
    ax.plot(xf, pf, color=cc.NAVY, lw=2, ls="--")
    if DETECTED_BREAK in xall:
        ax.axvline(xall.index(DETECTED_BREAK), color=cc.GRAY, ls=":", lw=1)
        ax.text(xall.index(DETECTED_BREAK), 0.5, " detected break 2024-10", color=cc.GRAY, fontsize=7)
    ax.set_xticks(xi[::3]); ax.set_xticklabels([xall[i] for i in range(0, len(xall), 3)], rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Negative-review share (1–2★)"); ax.set_ylim(0, 0.6)
    ax.set_title("Share of negative reviews (1–2★), with 6-month forecast")
    ax.legend(fontsize=7, loc="upper left", ncol=2)
    ax.text(0.99, 0.02, f"backtest 80% coverage={cov80:.0%}  •  trend sign uncertain (partial recovery)",
            transform=ax.transAxes, ha="right", fontsize=7, color=cc.GRAY)
    fig.tight_layout(); fig.savefig(f"{cc.CHARTS}/01_neg_share_fan_chart.png"); plt.close()

    # backtest coverage calibration
    fig, ax = plt.subplots(figsize=(7, 5))
    nominal = [0.80, 0.95]; empirical = [cov80, cov95]
    ax.plot([0, 1], [0, 1], ls="--", color=cc.GRAY)
    ax.scatter(nominal, empirical, s=90, color=cc.NAVY, zorder=3)
    for nm, em in zip(nominal, empirical):
        ax.annotate(f"{em:.0%}", (nm, em), textcoords="offset points", xytext=(8, -4), fontsize=9)
    ax.set_xlabel("Nominal coverage"); ax.set_ylabel("Empirical coverage (rolling-origin)")
    ax.set_xlim(0.7, 1.0); ax.set_ylim(0.5, 1.0)
    ax.set_title(f"Calibration — the headline metric (n={len(bt_df)} backtest forecasts)")
    fig.tight_layout(); fig.savefig(f"{cc.CHARTS}/02_backtest_coverage.png"); plt.close()

    # counterfactual scenarios
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    yps = np.arange(len(cf_df))
    ax.barh(yps, cf_df["anchored_neg_share"], color=[cc.RED, cc.ORANGE, cc.GREEN], alpha=0.8)
    for i, v in enumerate(cf_df["anchored_neg_share"]):
        ax.text(v + 0.005, i, f"{v:.0%}", va="center", fontsize=9)
    ax.axvline(obs_post, color=cc.NAVY, ls="--", label=f"observed post-window ({obs_post:.0%})")
    ax.axvline(obs_2023, color=cc.GRAY, ls=":", label=f"2023 actual ({obs_2023:.0%})")
    ax.set_yticks(yps); ax.set_yticklabels(cf_df["scenario"]); ax.set_xlabel("Anchored negative share (observed + mix-attributable delta)")
    ax.set_title("Counterfactual — mix-shift DELTA anchored to observed (associational, not causal)"); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(f"{cc.CHARTS}/03_counterfactual_bands.png"); plt.close()

    # reply-ops separate
    fig, ax1 = plt.subplots(figsize=(11, 4.5))
    xi2 = np.arange(len(ro))
    ax1.plot(xi2, ro["median_reply_lag"], color=cc.RED, marker="o", ms=3, label="median reply lag (days)")
    ax1.set_ylabel("Median reply lag (days)", color=cc.RED)
    ax2 = ax1.twinx(); ax2.plot(xi2, ro["reply_rate"], color=cc.NAVY, label="reply coverage")
    ax2.set_ylabel("Reply coverage", color=cc.NAVY); ax2.set_ylim(0.4, 1.02)
    ax1.set_xticks(xi2[::2]); ax1.set_xticklabels(ro["month"].iloc[::2], rotation=45, ha="right", fontsize=8)
    ax1.set_title("Company reply speed and coverage over time")
    fig.tight_layout(); fig.savefig(f"{cc.CHARTS}/04_replyops_separate.png"); plt.close()

    # ============================================================ print for spot-review
    pd.set_option("display.width", 200)
    print(f"\nForecast window: {months[0]}..{months[-1]} ({len(months)} months), n_future={n_future:.0f}")
    print("\n6-MONTH FORECAST (predictive incl. obs noise):")
    print(fc[["month", "forecast_p", "lo80", "hi80", "lo95", "hi95"]].round(3).to_string(index=False))
    print(f"\nBACKTEST: 80% coverage={cov80:.0%}  95% coverage={cov95:.0%}  (n={len(bt_df)} forecasts)")
    print(f"  point MAE: model={mae:.4f}  last-value={mae_n:.4f}  trailing-3mo={mae_n3:.4f}  "
          f"(model {'beats' if mae<mae_n3 else 'ties/loses to'} naive — coverage is the claim, not point error)")
    print("\nCOUNTERFACTUAL (mix-shift delta anchored to observed):")
    print(cf_df.to_string(index=False))
    print("\nDONE — wrote CC2_reputation_forecast/backtest/counterfactual/replyops + charts 01-04.")


if __name__ == "__main__":
    main()
