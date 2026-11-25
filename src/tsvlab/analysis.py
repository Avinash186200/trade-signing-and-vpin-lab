"""Per-session analysis: signing accuracy, VPIN series, alarms and order-flow features.

Everything here works on one simulated session at a time. ``bench.py`` pools the
sessions, makes the development-only choices and writes the results.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .bars import bucket_sums, make_buckets, make_time_bars, time_bar_sums
from .signing import (TRADE_METHODS, buy_fraction, bvc_buy_fraction, prevailing_quotes,
                      sign_trades)
from .sim import KIND_INFORMED, Session, report_times
from .vpin import detect_episodes, lagged_corr, mask_intervals, on_grid, pearson, vpin

VPIN_METHODS = ("truth",) + TRADE_METHODS + ("bvc",)
GRID_STEP = 60.0             # seconds; VPIN and the planted share are compared on a 1-minute grid
BVC_LOOKBACK = 50            # bars of history for the BVC price-change scale
EVENT_OFFSETS_MIN = (-30, -15, -5, 0, 5, 10, 15, 20, 30, 45, 60)
LAGS_MIN = np.arange(-30, 31)


@dataclass
class Observed:
    """What a desk sees after trades are reported late, with each rule's signs."""
    session: Session
    delay: float
    t_rep: np.ndarray
    bid: np.ndarray
    ask: np.ndarray
    signs: dict


def observe(s: Session, delay: float) -> Observed:
    t_rep = report_times(s.t, delay, s.seed)
    bid, ask = prevailing_quotes(t_rep, s.q_t, s.q_bid, s.q_ask)
    signs = {m: sign_trades(m, s.price, bid, ask) for m in TRADE_METHODS}
    return Observed(session=s, delay=delay, t_rep=t_rep, bid=bid, ask=ask, signs=signs)


# ---------------------------------------------------------------- accuracy

def trade_accuracy(signs: np.ndarray, truth: np.ndarray, mask: np.ndarray | None = None) -> dict:
    """Share of trades signed correctly; an unclassified trade counts as half right."""
    if mask is not None:
        signs, truth = signs[mask], truth[mask]
    n = int(signs.size)
    if n == 0:
        return dict(n=0, accuracy=None, unclassified=None)
    correct = float(np.mean(signs == truth))
    uncl = float(np.mean(signs == 0))
    return dict(n=n, accuracy=correct + 0.5 * uncl, unclassified=uncl)


def trade_conditions(s: Session, ob: Observed) -> dict:
    """Masks for the condition table. Conditions use the true prevailing quote."""
    at_quote = (s.price == s.bid) | (s.price == s.ask)
    at_mid = 2 * s.price == s.bid + s.ask
    return {
        "all": np.ones(s.n_trades, dtype=bool),
        "at_quote": at_quote,
        "inside_not_mid": ~at_quote & ~at_mid,
        "at_mid": at_mid,
        "low_vol": s.regime == 0,
        "high_vol": s.regime == 1,
    }


def volume_accuracy(est_buy: np.ndarray, true_buy: np.ndarray, vol: np.ndarray) -> float:
    """Bar-level volume accuracy: sum of min(est, true) over buy and sell volume / total volume."""
    est_sell, true_sell = vol - est_buy, vol - true_buy
    good = np.minimum(est_buy, true_buy) + np.minimum(est_sell, true_sell)
    return float(good.sum() / vol.sum())


def bucket_buys(s: Session, ob: Observed, bucket_volume: float):
    """Buy volume per bucket for the truth and every method, plus the informed volume."""
    b = make_buckets(s.size, ob.t_rep, s.price, bucket_volume)
    buys = {"truth": bucket_sums(s.size, buy_fraction(s.side), b)}
    for m in TRADE_METHODS:
        buys[m] = bucket_sums(s.size, buy_fraction(ob.signs[m]), b)
    buys["bvc"] = bvc_buy_fraction(b.close_price, BVC_LOOKBACK) * bucket_volume
    informed = bucket_sums(s.size, (s.kind == KIND_INFORMED).astype(float), b)
    return b, buys, informed


def bar_accuracy(s: Session, ob: Observed, bucket_volume: float, skip: int = BVC_LOOKBACK) -> dict:
    """Volume accuracy of each method on volume bars, after the BVC warm-up bars."""
    b, buys, _ = bucket_buys(s, ob, bucket_volume)
    sl = slice(skip, None)
    vol = np.full(b.n, bucket_volume)[sl]
    out = {m: volume_accuracy(buys[m][sl], buys["truth"][sl], vol) for m in TRADE_METHODS + ("bvc",)}
    # baseline: call half of every bar's volume buys, whatever happened
    out["naive"] = volume_accuracy(0.5 * vol, buys["truth"][sl], vol)
    out["n_bars"] = int(vol.size)
    return out


# ---------------------------------------------------------------- VPIN

def minute_grid(s: Session) -> np.ndarray:
    return GRID_STEP * np.arange(1, int(s.cfg.duration // GRID_STEP) + 1)


def vpin_series(s: Session, ob: Observed, bucket_volume: float, windows) -> dict:
    """VPIN at bucket close for every method and window, with the planted share there."""
    b, buys, _ = bucket_buys(s, ob, bucket_volume)
    close_true_t = s.t[b.close_idx]
    out = {"close_t": b.close_t, "alpha": s.alpha_at(close_true_t), "n_buckets": b.n}
    for m in VPIN_METHODS:
        for n in windows:
            out[(m, n)] = vpin(buys[m], bucket_volume, n)
    return out


def vpin_alpha_corr(s: Session, series: dict, method: str, n: int) -> float:
    """Correlation of VPIN with the planted informed share on the 1-minute grid.

    Every bucket size and window is sampled on the same clock grid, so settings are
    compared on the same points; a stale VPIN (big buckets in a quiet market) counts
    against its setting.
    """
    _, v, a = grid_view(s, series, method, n)
    return pearson(v, a)


def grid_view(s: Session, series: dict, method: str, n: int):
    grid = minute_grid(s)
    v = on_grid(series[(method, n)], series["close_t"], grid)
    return grid, v, s.alpha_at(grid)


def lead_lag(v: np.ndarray, a: np.ndarray) -> np.ndarray:
    ok = ~np.isnan(v)
    first = int(np.argmax(ok)) if ok.any() else v.size
    return lagged_corr(v[first:], a[first:], LAGS_MIN)


def event_profile(grid: np.ndarray, v: np.ndarray, episodes: list) -> list:
    """VPIN at fixed offsets (minutes) from each episode start; NaN where unavailable."""
    rows = []
    for e in episodes:
        row = []
        for off in EVENT_OFFSETS_MIN:
            tt = e["start"] + 60.0 * off
            i = int(np.searchsorted(grid, tt, side="right")) - 1
            row.append(float(v[i]) if 0 <= i < v.size and np.isfinite(v[i]) else float("nan"))
        rows.append(row)
    return rows


def alarm_stats(s: Session, grid: np.ndarray, v: np.ndarray, threshold: float) -> dict:
    valid = np.isfinite(v)
    alarm = valid & (v >= threshold)
    ep_mask = mask_intervals(grid, s.episodes)
    # after an episode ends, VPIN's window still holds its buckets: leave 30 minutes out
    ep_shadow = mask_intervals(grid, s.episodes, pad_after=1800.0)
    burst_mask = mask_intervals(grid, s.bursts, pad_after=1800.0)
    out = dict(valid_minutes=int(valid.sum()), alarm_minutes=int(alarm.sum()),
               alarm_share=float(alarm[valid].mean()) if valid.any() else None)
    quiet = valid & ~ep_shadow
    out["alarm_share_no_episode"] = float(alarm[quiet].mean()) if quiet.any() else None
    inside = valid & ep_mask
    out["alarm_share_in_episode"] = float(alarm[inside].mean()) if inside.any() else None
    nb = valid & ~ep_shadow & ~burst_mask
    out["alarm_share_no_episode_no_burst"] = float(alarm[nb].mean()) if nb.any() else None
    bm = valid & ~ep_shadow & burst_mask
    out["alarm_share_burst"] = float(alarm[bm].mean()) if bm.any() else None
    # alarm spells that start away from any informed episode
    starts = alarm & ~np.concatenate([[False], alarm[:-1]])
    out["false_spells"] = int(np.sum(starts & ~ep_shadow))
    out["episodes"] = detect_episodes(alarm, grid, s.episodes)
    return out


# ---------------------------------------------------------------- order-flow imbalance features

OFI_BAR = 60.0       # seconds
OFI_WINDOW = 5       # bars in the trailing imbalance
OFI_HORIZON = 5      # bars ahead for the forward return
OFI_SKIP = 30        # first bars left out (BVC warm-up)


def ofi_features(s: Session, ob: Observed) -> dict:
    """Trailing 5-minute order-flow imbalance (B - S) / (B + S) on 1-minute bars, per method.

    Trades are assigned to bars by reported time for every method, the truth included,
    so the only difference between columns is the signing. The forward return is the
    change in the quote midpoint over the next 5 minutes (ticks).
    """
    bars = make_time_bars(ob.t_rep, s.size, s.price, OFI_BAR, s.cfg.duration)
    vol = bars.volume
    buys = {"truth": time_bar_sums(ob.t_rep, s.size, buy_fraction(s.side), bars)}
    for m in TRADE_METHODS:
        buys[m] = time_bar_sums(ob.t_rep, s.size, buy_fraction(ob.signs[m]), bars)
    buys["bvc"] = bvc_buy_fraction(bars.last_price, 60) * vol

    def trailing(x):
        c = np.concatenate([[0.0], np.cumsum(x)])
        out = np.full(x.size, np.nan)
        out[OFI_WINDOW - 1:] = c[OFI_WINDOW:] - c[:-OFI_WINDOW]
        return out

    tv = trailing(vol)
    ofi = {}
    for m, b in buys.items():
        with np.errstate(invalid="ignore", divide="ignore"):
            ofi[m] = trailing(2.0 * b - vol) / tv
    mid = s.mid_at(bars.end_t)
    fwd = np.full(bars.n, np.nan)
    fwd[:-OFI_HORIZON] = mid[OFI_HORIZON:] - mid[:-OFI_HORIZON]
    keep = np.arange(bars.n) >= OFI_SKIP
    return {"ofi": {m: v[keep] for m, v in ofi.items()}, "fwd": fwd[keep]}


def ofi_metrics(f: dict) -> dict:
    truth = f["ofi"]["truth"]
    out = {}
    for m, v in f["ofi"].items():
        ok = np.isfinite(v) & np.isfinite(truth)
        out[m] = dict(corr_with_true=pearson(v, truth),
                      mean_abs_error=float(np.mean(np.abs(v[ok] - truth[ok]))),
                      corr_with_fwd_return=pearson(v, f["fwd"]))
    return out


# ---------------------------------------------------------------- descriptive stats

def session_stats(s: Session) -> dict:
    spread = s.ask - s.bid
    at_quote = (s.price == s.bid) | (s.price == s.ask)
    at_mid = 2 * s.price == s.bid + s.ask
    T = s.cfg.duration
    hv = sum(min(e, T) - a for a, e, r in zip(s.seg_start, np.append(s.seg_start[1:], T), s.seg_regime) if r)
    return dict(trades=s.n_trades, volume=int(s.size.sum()), quotes=int(s.q_t.size),
                mean_spread_ticks=float(spread.mean()), at_quote_share=float(at_quote.mean()),
                at_mid_share=float(at_mid.mean()),
                inside_not_mid_share=float((~at_quote & ~at_mid).mean()),
                buy_share=float((s.side > 0).mean()),
                informed_trade_share=float((s.kind == KIND_INFORMED).mean()),
                burst_trade_share=float((s.kind == 2).mean()),
                high_vol_time_share=float(hv / T),
                episodes=len(s.episodes), bursts=len(s.bursts),
                price_range_ticks=int(s.price.max() - s.price.min()))
