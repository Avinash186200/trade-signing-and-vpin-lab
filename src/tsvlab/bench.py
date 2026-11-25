"""The full run: simulate, choose VPIN settings on development seeds, score held-out seeds once.

Writes ``results/{data,accuracy,vpin,ofi}.json`` and ``results/RESULTS.md``.

What is decided where:

* Development seeds (informed 1-8, control 101-108): the bucket volume grid is
  scaled from their mean session volume; each signing method's bucket size and
  window are chosen by mean correlation with the planted informed share on the
  development informed seeds; each method's alarm threshold is the 90th
  percentile of its VPIN on the development control seeds.
* Held-out seeds (informed 1001-1008, control 2001-2008): every reported VPIN,
  alarm, accuracy and order-flow number. Nothing is chosen on them.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np

from . import analysis as A
from .signing import LABELS, TRADE_METHODS
from .sim import SimConfig, simulate

SEEDS = {"dev": {"informed": tuple(range(1, 9)), "control": tuple(range(101, 109))},
         "holdout": {"informed": tuple(range(1001, 1009)), "control": tuple(range(2001, 2009))}}
DEFAULT_DELAY = 0.5
DELAYS = (0.0, 0.1, 0.25, 0.5, 1.0, 2.0)
BUCKETS_PER_SESSION = (50, 100, 200, 400, 800, 1600)
WINDOWS = (1, 2, 5, 10, 25, 50)
MAX_WINDOW_SHARE = 0.25     # a window may span at most a quarter of a session's buckets
ALARM_QUANTILE = 0.90
BAR_VOLUMES = (2_000, 10_000, 50_000)
NOISE_SCALES = (0.0, 0.25, 0.5, 1.0)
RESULT_FILES = ("data", "accuracy", "vpin", "ofi")
CONDITIONS = {"all": "all trades", "at_quote": "at the quote", "inside_not_mid": "inside the spread, not at the mid",
              "at_mid": "at the midpoint", "low_vol": "low-volatility regime", "high_vol": "high-volatility regime"}


def _mean_se(xs) -> dict:
    a = np.asarray([x for x in xs if x is not None and np.isfinite(x)], dtype=float)
    if a.size == 0:
        return {"mean": None, "se": None, "n": 0}
    se = float(a.std(ddof=1) / np.sqrt(a.size)) if a.size > 1 else None
    return {"mean": float(a.mean()), "se": se, "n": int(a.size)}


def _r(x, nd=6):
    """Round floats for stable JSON; recurse into containers."""
    if isinstance(x, dict):
        return {k: _r(v, nd) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_r(v, nd) for v in x]
    if isinstance(x, (float, np.floating)):
        x = float(x)
        return None if not np.isfinite(x) else round(x, nd)
    if isinstance(x, np.integer):
        return int(x)
    return x


def _sessions(base: SimConfig, seeds: dict) -> dict:
    return {split: {mode: [simulate(base.with_mode(mode), s) for s in seeds[split][mode]]
                    for mode in seeds[split]} for split in seeds}


# ---------------------------------------------------------------- sections

def data_section(base, seeds, ses) -> dict:
    out = {"config": base.to_dict(), "seeds": seeds, "default_delay_s": DEFAULT_DELAY, "stats": {}}
    for split in ses:
        for mode, lst in ses[split].items():
            per = [A.session_stats(s) for s in lst]
            out["stats"][f"{split}_{mode}"] = {k: float(np.mean([p[k] for p in per])) for k in per[0]}
    return out


def accuracy_section(base, seeds, ses, obs) -> dict:
    out = {"delay_grid": {}, "conditions": {}, "bars": {}, "bvc_noise_sensitivity": {}}
    for mode in ("informed", "control"):
        lst = ses["holdout"][mode]
        grid = {}
        for d in DELAYS:
            per = {m: [] for m in TRADE_METHODS}
            uncl = []
            for s in lst:
                ob = obs["holdout"][mode][s.seed] if d == DEFAULT_DELAY else A.observe(s, d)
                for m in TRADE_METHODS:
                    per[m].append(A.trade_accuracy(ob.signs[m], s.side)["accuracy"])
                uncl.append(A.trade_accuracy(ob.signs["quote"], s.side)["unclassified"])
            grid[str(d)] = {m: _mean_se(v) for m, v in per.items()}
            grid[str(d)]["quote_unclassified"] = _mean_se(uncl)
        out["delay_grid"][mode] = grid

        cond = {}
        for d in (0.0, DEFAULT_DELAY):
            rows = {}
            for s in lst:
                ob = obs["holdout"][mode][s.seed] if d == DEFAULT_DELAY else A.observe(s, d)
                for c, mask in A.trade_conditions(s, ob).items():
                    r = rows.setdefault(c, {"share": [], **{m: [] for m in TRADE_METHODS}})
                    r["share"].append(float(mask.mean()))
                    for m in TRADE_METHODS:
                        r[m].append(A.trade_accuracy(ob.signs[m], s.side, mask)["accuracy"])
            cond[str(d)] = {c: {k: _mean_se(v) for k, v in r.items()} for c, r in rows.items()}
        out["conditions"][mode] = cond

        bars = {}
        for bv in BAR_VOLUMES:
            per = {}
            for s in lst:
                res = A.bar_accuracy(s, obs["holdout"][mode][s.seed], bv)
                for k, v in res.items():
                    per.setdefault(k, []).append(v)
            bars[str(bv)] = {k: _mean_se(v) for k, v in per.items()}
        out["bars"][mode] = bars

    # how much BVC depends on price changes being driven by order flow
    for scale in NOISE_SCALES:
        cfg = replace(base, sigma_low=base.sigma_low * scale, sigma_high=base.sigma_high * scale)
        per = {}
        for seed in seeds["holdout"]["informed"]:
            s = simulate(cfg, seed)
            ob = A.observe(s, DEFAULT_DELAY)
            ba = A.bar_accuracy(s, ob, BAR_VOLUMES[1])
            om = A.ofi_metrics(A.ofi_features(s, ob))
            for m in ("tick", "lee_ready", "bvc"):
                per.setdefault(f"bar_accuracy_{m}", []).append(ba[m])
                per.setdefault(f"ofi_corr_{m}", []).append(om[m]["corr_with_true"])
            per.setdefault("bar_accuracy_naive", []).append(ba["naive"])
        out["bvc_noise_sensitivity"][str(scale)] = {k: _mean_se(v) for k, v in per.items()}
    return out


def vpin_section(seeds, ses, obs, log, dev_only=False) -> dict:
    dev_vol = np.mean([s.size.sum() for mode in ses["dev"] for s in ses["dev"][mode]])
    bucket_vol = {B: float(round(dev_vol / B, -2)) for B in BUCKETS_PER_SESSION}
    out = {"dev_mean_session_volume": float(dev_vol), "bucket_volume": {str(B): v for B, v in bucket_vol.items()},
           "alarm_quantile": ALARM_QUANTILE, "grid": {}, "selected": {}, "thresholds": {}}

    # 1. grid on development informed seeds
    corr = {}
    for B in BUCKETS_PER_SESSION:
        for s in ses["dev"]["informed"]:
            ser = A.vpin_series(s, obs["dev"]["informed"][s.seed], bucket_vol[B], WINDOWS)
            for m in A.VPIN_METHODS:
                for n in WINDOWS:
                    corr.setdefault((m, B, n), []).append(A.vpin_alpha_corr(s, ser, m, n))
    combos = [(B, n) for B in BUCKETS_PER_SESSION for n in WINDOWS if n <= MAX_WINDOW_SHARE * B]
    out["grid_combos"] = [f"{B}x{n}" for B, n in combos]
    for m in A.VPIN_METHODS:
        out["grid"][m] = {f"{B}x{n}": _mean_se(corr[(m, B, n)]) for B, n in combos}
        best = max(combos, key=lambda k: np.mean(corr[(m, k[0], k[1])]))
        out["selected"][m] = {"buckets_per_session": best[0], "bucket_volume": bucket_vol[best[0]],
                              "window": best[1], "dev_corr": float(np.mean(corr[(m, *best)]))}
    log("selected", {m: (v["buckets_per_session"], v["window"]) for m, v in out["selected"].items()})

    # 2. alarm thresholds from development control seeds
    for m in A.VPIN_METHODS:
        sel = out["selected"][m]
        vals = []
        for s in ses["dev"]["control"]:
            ser = A.vpin_series(s, obs["dev"]["control"][s.seed], sel["bucket_volume"], (sel["window"],))
            _, v, _ = A.grid_view(s, ser, m, sel["window"])
            vals.append(v[np.isfinite(v)])
        out["thresholds"][m] = float(np.quantile(np.concatenate(vals), ALARM_QUANTILE))
    if dev_only:
        return out

    # 3. held-out seeds, run once with the settings above
    ho = {}
    for m in A.VPIN_METHODS:
        sel, thr = out["selected"][m], out["thresholds"][m]
        bv, n = sel["bucket_volume"], sel["window"]
        acc = {"corr_alpha": [], "lagcurve": [], "episodes": [], "profile": [],
               "inf_alarm_in_episode": [], "inf_alarm_no_episode": [], "inf_false_spells": [],
               "ctl_alarm_share": [], "ctl_alarm_burst": [], "ctl_alarm_no_burst": [], "ctl_false_spells": [],
               "placebo": []}
        for s in ses["holdout"]["informed"]:
            ser = A.vpin_series(s, obs["holdout"]["informed"][s.seed], bv, (n,))
            acc["corr_alpha"].append(A.vpin_alpha_corr(s, ser, m, n))
            grid, v, a = A.grid_view(s, ser, m, n)
            acc["lagcurve"].append(A.lead_lag(v, a))
            st = A.alarm_stats(s, grid, v, thr)
            acc["episodes"] += st["episodes"]
            acc["inf_alarm_in_episode"].append(st["alarm_share_in_episode"])
            acc["inf_alarm_no_episode"].append(st["alarm_share_no_episode"])
            acc["inf_false_spells"].append(st["false_spells"])
            acc["profile"] += A.event_profile(grid, v, s.episodes)
        for s in ses["holdout"]["control"]:
            ser = A.vpin_series(s, obs["holdout"]["control"][s.seed], bv, (n,))
            grid, v, a = A.grid_view(s, ser, m, n)
            st = A.alarm_stats(s, grid, v, thr)
            acc["ctl_alarm_share"].append(st["alarm_share"])
            acc["ctl_alarm_burst"].append(st["alarm_share_burst"])
            acc["ctl_alarm_no_burst"].append(st["alarm_share_no_episode_no_burst"])
            acc["ctl_false_spells"].append(st["false_spells"])
            # placebo: the same episode windows were placed in control sessions, with no informed traders
            acc["placebo"] += A.detect_episodes(np.isfinite(v) & (v >= thr), grid, s.episode_windows)
        curve = np.nanmean(np.array(acc["lagcurve"]), axis=0)
        lags = A.LAGS_MIN.tolist()
        eps = acc["episodes"]
        delays = [e["delay_min"] for e in eps if e["detected"]]
        prof = np.array(acc["profile"])
        ho[m] = {
            "corr_alpha": _mean_se(acc["corr_alpha"]),
            "lead_lag": {"lags_min": lags, "mean_corr": curve.tolist(),
                         "peak_lag_min": int(A.LAGS_MIN[int(np.nanargmax(curve))]),
                         "peak_corr": float(np.nanmax(curve)),
                         "corr_lag0": float(curve[lags.index(0)]),
                         "corr_vpin_leads_10": float(curve[lags.index(-10)]),
                         "corr_vpin_lags_10": float(curve[lags.index(10)])},
            "episodes": {"n": len(eps), "detected": int(sum(e["detected"] for e in eps)),
                         "detection_rate": float(np.mean([e["detected"] for e in eps])),
                         "already_alarm_at_start": int(sum(e["at_start"] for e in eps)),
                         "median_delay_min": float(np.median(delays)) if delays else None,
                         "mean_duration_min": float(np.mean([e["duration_min"] for e in eps]))},
            "placebo_episodes": {"n": len(acc["placebo"]),
                                 "detected": int(sum(e["detected"] for e in acc["placebo"])),
                                 "detection_rate": float(np.mean([e["detected"] for e in acc["placebo"]]))
                                 if acc["placebo"] else None},
            "informed_alarm_share_in_episode": _mean_se(acc["inf_alarm_in_episode"]),
            "informed_alarm_share_no_episode": _mean_se(acc["inf_alarm_no_episode"]),
            "informed_false_spells_per_session": _mean_se(acc["inf_false_spells"]),
            "control_alarm_share": _mean_se(acc["ctl_alarm_share"]),
            "control_alarm_share_in_burst": _mean_se(acc["ctl_alarm_burst"]),
            "control_alarm_share_no_burst": _mean_se(acc["ctl_alarm_no_burst"]),
            "control_false_spells_per_session": _mean_se(acc["ctl_false_spells"]),
            "event_profile": {"offsets_min": list(A.EVENT_OFFSETS_MIN),
                              "mean_vpin": np.nanmean(prof, axis=0).tolist(), "threshold": thr},
        }
    out["holdout"] = ho
    return out


def ofi_section(ses, obs) -> dict:
    out = {"bar_seconds": A.OFI_BAR, "window_bars": A.OFI_WINDOW, "horizon_bars": A.OFI_HORIZON}
    for mode in ("informed", "control"):
        per = {}
        for s in ses["holdout"][mode]:
            met = A.ofi_metrics(A.ofi_features(s, obs["holdout"][mode][s.seed]))
            for m, d in met.items():
                for k, v in d.items():
                    per.setdefault(m, {}).setdefault(k, []).append(v)
        out[mode] = {m: {k: _mean_se(v) for k, v in d.items()} for m, d in per.items()}
    return out


# ---------------------------------------------------------------- driver

def run(out_dir, base: SimConfig | None = None, seeds: dict | None = None, log=print,
        dev_only: bool = False) -> dict:
    base = base or SimConfig()
    seeds = seeds or SEEDS
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    splits = ("dev",) if dev_only else ("dev", "holdout")
    seeds = {k: seeds[k] for k in splits}
    log("simulating", sum(len(v) for sp in seeds.values() for v in sp.values()), "sessions")
    ses = _sessions(base, seeds)
    obs = {sp: {mode: {s.seed: A.observe(s, DEFAULT_DELAY) for s in ses[sp][mode]}
                for mode in ses[sp]} for sp in ses}
    res = {"data": data_section(base, seeds, ses)}
    res["vpin"] = vpin_section(seeds, ses, obs, log, dev_only=dev_only)
    if not dev_only:
        log("accuracy")
        res["accuracy"] = accuracy_section(base, seeds, ses, obs)
        log("order-flow features")
        res["ofi"] = ofi_section(ses, obs)
    res = {k: _r(v) for k, v in res.items()}
    for k, v in res.items():
        with open(out_dir / f"{k}.json", "w", encoding="utf-8", newline="\n") as f:
            json.dump(v, f, indent=1, sort_keys=True)
            f.write("\n")
    if not dev_only:
        write_report(out_dir)  # rendered from the JSON on disk, exactly as `tsvlab report` does
    return res


def load(out_dir) -> dict:
    return {k: json.loads((Path(out_dir) / f"{k}.json").read_text(encoding="utf-8")) for k in RESULT_FILES}


# ---------------------------------------------------------------- RESULTS.md

def _f(x, nd=3):
    return "-" if x is None else f"{x:.{nd}f}"


def _ms(d, nd=3):
    if d is None or d.get("mean") is None:
        return "-"
    return f"{d['mean']:.{nd}f} ± {d['se']:.{nd}f}" if d.get("se") is not None else f"{d['mean']:.{nd}f}"


def _pct(d):
    return "-" if d is None or d.get("mean") is None else f"{100 * d['mean']:.1f}%"


def render(res: dict) -> str:
    D, AC, V, O = res["data"], res["accuracy"], res["vpin"], res["ofi"]
    L = ["# Results", "",
         "Synthetic data from `tsvlab.sim`. Rebuild with `make bench`. Means over seeds; ± is one "
         "standard error across seeds (8 per mode and split). Trade reporting delay "
         f"{D['default_delay_s']} s unless a table says otherwise.", ""]

    L += ["## Data (mean per session)", "",
          "| split | mode | trades | volume | quotes | mean spread (ticks) | at the quote | inside, not at mid | at mid | informed trades | burst trades | high-vol time | episodes | bursts |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for key in ("dev_informed", "dev_control", "holdout_informed", "holdout_control"):
        if key not in D["stats"]:
            continue
        st = D["stats"][key]
        sp, mode = key.split("_")
        L.append(f"| {sp} | {mode} | {st['trades']:,.0f} | {st['volume']:,.0f} | {st['quotes']:,.0f} | "
                 f"{st['mean_spread_ticks']:.2f} | {st['at_quote_share']:.3f} | {st['inside_not_mid_share']:.3f} | "
                 f"{st['at_mid_share']:.3f} | {st['informed_trade_share']:.3f} | {st['burst_trade_share']:.3f} | "
                 f"{st['high_vol_time_share']:.3f} | {st['episodes']:.2f} | {st['bursts']:.2f} |")

    tm = list(TRADE_METHODS)
    for mode in ("informed", "control"):
        L += ["", f"## Trade-level accuracy by reporting delay (held-out, {mode})", "",
              "| delay (s) | " + " | ".join(LABELS[m] for m in tm) + " | quote rule unclassified |",
              "|---" * (len(tm) + 2) + "|"]
        for d in map(str, DELAYS):
            row = AC["delay_grid"][mode][d]
            L.append(f"| {d} | " + " | ".join(_ms(row[m]) for m in tm) + f" | {_ms(row['quote_unclassified'])} |")
    for mode in ("informed", "control"):
        for d in (str(0.0), str(DEFAULT_DELAY)):
            rows = AC["conditions"][mode][d]
            L += ["", f"## Trade-level accuracy by condition (held-out, {mode}, delay {d} s)", "",
                  "| condition | share of trades | " + " | ".join(LABELS[m] for m in tm) + " |",
                  "|---" * (len(tm) + 2) + "|"]
            for c in CONDITIONS:
                r = rows[c]
                L.append(f"| {CONDITIONS[c]} | {_f(r['share']['mean'])} | " + " | ".join(_ms(r[m]) for m in tm) + " |")
    for mode in ("informed", "control"):
        L += ["", f"## Volume accuracy on volume bars (held-out, {mode})", "",
              "| shares per bar | bars scored per session | " + " | ".join(LABELS[m] for m in tm + ["bvc"]) + " | naive 50/50 |",
              "|---" * (len(tm) + 4) + "|"]
        for bv in map(str, BAR_VOLUMES):
            r = AC["bars"][mode][bv]
            L.append(f"| {int(bv):,} | {r['n_bars']['mean']:.0f} | " + " | ".join(_ms(r[m]) for m in tm + ["bvc"])
                     + f" | {_ms(r['naive'])} |")
    L += ["", "## BVC and how much price moves come from order flow (held-out informed seeds)", "",
          "Efficient-price noise scaled by the factor below (1.0 is the base simulator). 10,000-share bars; "
          "OFI correlation is the 5-minute imbalance against the true-sign version.", "",
          "| noise scale | bar accuracy: tick | Lee-Ready | BVC | naive 50/50 | OFI corr: tick | Lee-Ready | BVC |",
          "|---|---|---|---|---|---|---|---|"]
    for sc in map(str, NOISE_SCALES):
        r = AC["bvc_noise_sensitivity"][sc]
        L.append(f"| {sc} | {_ms(r['bar_accuracy_tick'])} | {_ms(r['bar_accuracy_lee_ready'])} | "
                 f"{_ms(r['bar_accuracy_bvc'])} | {_ms(r['bar_accuracy_naive'])} | {_ms(r['ofi_corr_tick'])} | "
                 f"{_ms(r['ofi_corr_lee_ready'])} | {_ms(r['ofi_corr_bvc'])} |")

    vm = list(A.VPIN_METHODS)
    L += ["", "## VPIN settings chosen on development seeds", "",
          f"Bucket volume = development mean session volume ({V['dev_mean_session_volume']:,.0f} shares) / buckets per session, "
          f"rounded to 100 shares. Criterion: mean correlation of VPIN with the planted informed share on a 1-minute grid. "
          f"Threshold: {V['alarm_quantile']:.0%} quantile of VPIN on the development control seeds (1-minute grid).", "",
          "| signing | buckets per session | shares per bucket | window (buckets) | dev correlation | alarm threshold |",
          "|---|---|---|---|---|---|"]
    for m in vm:
        s = V["selected"][m]
        L.append(f"| {LABELS[m]} | {s['buckets_per_session']} | {s['bucket_volume']:,.0f} | {s['window']} | "
                 f"{s['dev_corr']:.3f} | {V['thresholds'][m]:.3f} |")
    L += ["", "Development correlation grid (rows: buckets per session; columns: window):", ""]
    for m in vm:
        L += [f"{LABELS[m]}:", "", "| buckets \\ window | " + " | ".join(str(n) for n in WINDOWS) + " |",
              "|---" * (len(WINDOWS) + 1) + "|"]
        for B in BUCKETS_PER_SESSION:
            cells = [_f(V["grid"][m][f"{B}x{n}"]["mean"]) if f"{B}x{n}" in V["grid"][m] else "n/a" for n in WINDOWS]
            L.append(f"| {B} | " + " | ".join(cells) + " |")
        L.append("")

    H = V["holdout"]
    L += ["## VPIN on held-out seeds (run once)", "",
          "| signing | corr with planted share | peak lag (min) | corr at peak | corr with the share 10 min later | corr with the share 10 min earlier | episodes detected | median delay (min) | placebo windows flagged (control) | alarm share in episodes | alarm share, informed mode away from episodes | alarm share, control | control: in bursts | control: no burst |",
          "|---" * 14 + "|"]
    for m in vm:
        h = H[m]
        e = h["episodes"]
        L.append(f"| {LABELS[m]} | {_ms(h['corr_alpha'])} | {h['lead_lag']['peak_lag_min']} | "
                 f"{h['lead_lag']['peak_corr']:.3f} | {h['lead_lag']['corr_vpin_leads_10']:.3f} | "
                 f"{h['lead_lag']['corr_vpin_lags_10']:.3f} | {e['detected']}/{e['n']} | {_f(e['median_delay_min'], 1)} | "
                 f"{h['placebo_episodes']['detected']}/{h['placebo_episodes']['n']} | "
                 f"{_pct(h['informed_alarm_share_in_episode'])} | {_pct(h['informed_alarm_share_no_episode'])} | "
                 f"{_pct(h['control_alarm_share'])} | {_pct(h['control_alarm_share_in_burst'])} | "
                 f"{_pct(h['control_alarm_share_no_burst'])} |")
    L += ["", "False alarm spells per session (alarm onsets away from informed episodes):", "",
          "| signing | informed mode | control |", "|---|---|---|"]
    for m in vm:
        L.append(f"| {LABELS[m]} | {_ms(H[m]['informed_false_spells_per_session'], 2)} | "
                 f"{_ms(H[m]['control_false_spells_per_session'], 2)} |")
    offs = H["truth"]["event_profile"]["offsets_min"]
    L += ["", "Mean VPIN around the start of held-out informed episodes (minutes from start):", "",
          "| signing | threshold | " + " | ".join(f"{o:+d}" for o in offs) + " |", "|---" * (len(offs) + 2) + "|"]
    for m in vm:
        p = H[m]["event_profile"]
        L.append(f"| {LABELS[m]} | {p['threshold']:.3f} | " + " | ".join(_f(x) for x in p["mean_vpin"]) + " |")

    for mode in ("informed", "control"):
        L += ["", f"## Order-flow imbalance features (held-out, {mode})", "",
              f"Trailing {O['window_bars']}-minute imbalance (B - S) / (B + S) on 1-minute bars; forward return = "
              f"quote-midpoint change over the next {O['horizon_bars']} minutes.", "",
              "| signing | corr with true-sign OFI | mean abs error | corr with forward return |", "|---|---|---|---|"]
        for m in vm:
            r = O[mode][m]
            L.append(f"| {LABELS[m]} | {_ms(r['corr_with_true'])} | {_ms(r['mean_abs_error'])} | "
                     f"{_ms(r['corr_with_fwd_return'])} |")
    return "\n".join(L) + "\n"


def write_report(out_dir, res: dict | None = None) -> None:
    res = res or load(out_dir)
    with open(Path(out_dir) / "RESULTS.md", "w", encoding="utf-8", newline="\n") as f:
        f.write(render(res))
