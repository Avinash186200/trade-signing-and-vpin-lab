"""VPIN on volume buckets, and the tools to judge it against the planted truth.

VPIN (Easley, Lopez de Prado and O'Hara 2012) at bucket tau is the mean, over the
last n buckets, of |buy volume - sell volume| / bucket volume. It is computed at
bucket close from buckets up to and including tau only.
"""

from __future__ import annotations

import numpy as np


def vpin(buy: np.ndarray, bucket_volume: float, n: int) -> np.ndarray:
    """Rolling VPIN; NaN until n buckets are available."""
    buy = np.asarray(buy, dtype=float)
    oi = np.abs(2.0 * buy - bucket_volume) / bucket_volume
    out = np.full(oi.size, np.nan)
    if oi.size >= n:
        c = np.concatenate([[0.0], np.cumsum(oi)])
        out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


def on_grid(values: np.ndarray, times: np.ndarray, grid: np.ndarray) -> np.ndarray:
    """Value of the last observation stamped at or before each grid time (NaN before any)."""
    ok = ~np.isnan(values)
    v, tt = np.asarray(values)[ok], np.asarray(times)[ok]
    idx = np.searchsorted(tt, grid, side="right") - 1
    out = np.full(grid.size, np.nan)
    out[idx >= 0] = v[idx[idx >= 0]]
    return out


def pearson(x: np.ndarray, y: np.ndarray) -> float:
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = np.asarray(x)[ok], np.asarray(y)[ok]
    if x.size < 3 or x.std() == 0 or y.std() == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def lagged_corr(v: np.ndarray, a: np.ndarray, lags: np.ndarray) -> np.ndarray:
    """corr(v[t], a[t - k]) for each lag k (grid steps). k > 0: v responds k steps after a."""
    out = np.empty(len(lags))
    n = v.size
    for i, k in enumerate(lags):
        if k >= 0:
            out[i] = pearson(v[k:], a[:n - k])
        else:
            out[i] = pearson(v[:n + k], a[-k:])
    return out


def alarm_runs(alarm: np.ndarray) -> int:
    """Number of separate alarm spells (False -> True switches, counting a start in alarm)."""
    a = np.asarray(alarm, dtype=bool)
    if a.size == 0:
        return 0
    return int(a[0]) + int(np.sum(a[1:] & ~a[:-1]))


def detect_episodes(alarm: np.ndarray, grid: np.ndarray, episodes: list) -> list[dict]:
    """For each episode: was there an alarm minute inside it, and how long after the start."""
    out = []
    for e in episodes:
        inside = (grid >= e["start"]) & (grid <= e["end"])
        hits = np.flatnonzero(inside & alarm)
        first_inside = np.flatnonzero(inside)
        at_start = bool(alarm[first_inside[0]]) if first_inside.size else False
        out.append(dict(detected=bool(hits.size), at_start=at_start,
                        delay_min=float((grid[hits[0]] - e["start"]) / 60.0) if hits.size else None,
                        duration_min=(e["end"] - e["start"]) / 60.0))
    return out


def mask_intervals(grid: np.ndarray, intervals: list, pad_before: float = 0.0,
                   pad_after: float = 0.0) -> np.ndarray:
    m = np.zeros(grid.size, dtype=bool)
    for d in intervals:
        m |= (grid >= d["start"] - pad_before) & (grid <= d["end"] + pad_after)
    return m
