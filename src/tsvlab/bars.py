"""Volume buckets and clock-time bars.

A volume bucket closes every ``bucket_volume`` shares. A trade that crosses a
bucket boundary is split: the part that fills the bucket goes in it, the rest
starts the next one. Any per-trade quantity that is a share of the trade's volume
(buy share, informed share) is split the same way, by linear interpolation of its
running total against running volume. That is exact, because within one trade the
running total grows linearly with volume.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Buckets:
    volume: float            # shares per bucket
    close_idx: np.ndarray    # index of the trade that closes each bucket
    close_t: np.ndarray      # reported time of that trade
    close_price: np.ndarray  # its price (ticks)

    @property
    def n(self) -> int:
        return int(self.close_idx.size)


def make_buckets(size: np.ndarray, t: np.ndarray, price: np.ndarray, bucket_volume: float) -> Buckets:
    cumv = np.cumsum(size, dtype=np.int64)
    n_b = int(cumv[-1] // bucket_volume) if cumv.size else 0
    edges = bucket_volume * np.arange(1, n_b + 1)
    idx = np.searchsorted(cumv, edges, side="left")
    return Buckets(volume=float(bucket_volume), close_idx=idx, close_t=np.asarray(t)[idx],
                   close_price=np.asarray(price)[idx])


def bucket_sums(size: np.ndarray, share: np.ndarray, b: Buckets) -> np.ndarray:
    """Per-bucket total of ``size * share``, splitting trades at bucket boundaries."""
    size = np.asarray(size, dtype=float)
    cumv = np.concatenate([[0.0], np.cumsum(size)])
    cumx = np.concatenate([[0.0], np.cumsum(size * np.asarray(share, dtype=float))])
    edges = b.volume * np.arange(0, b.n + 1)
    at = np.interp(edges, cumv, cumx)
    return np.diff(at)


@dataclass
class TimeBars:
    seconds: float
    n: int
    volume: np.ndarray       # shares per bar
    last_price: np.ndarray   # last trade price in the bar, carried forward when empty (ticks)
    end_t: np.ndarray        # bar end times


def make_time_bars(t: np.ndarray, size: np.ndarray, price: np.ndarray, seconds: float,
                   duration: float) -> TimeBars:
    n = int(np.ceil(duration / seconds))
    bar = np.minimum((np.asarray(t) // seconds).astype(np.int64), n - 1)
    vol = np.bincount(bar, weights=size, minlength=n)
    last = np.full(n, np.nan)
    # trades are in feed order (bar numbers never decrease): take each bar's last trade
    is_last = np.ones(bar.size, dtype=bool)
    is_last[:-1] = bar[1:] != bar[:-1]
    last[bar[is_last]] = np.asarray(price)[is_last]
    # carry the last price forward through empty bars (the first price fills any leading gap)
    valid = ~np.isnan(last)
    idx = np.where(valid, np.arange(n), 0)
    np.maximum.accumulate(idx, out=idx)
    first = np.argmax(valid)
    last = np.where(np.arange(n) < first, last[first], last[idx])
    return TimeBars(seconds=seconds, n=n, volume=vol, last_price=last,
                    end_t=seconds * np.arange(1, n + 1))


def time_bar_sums(t: np.ndarray, size: np.ndarray, share: np.ndarray, bars: TimeBars) -> np.ndarray:
    bar = np.minimum((np.asarray(t) // bars.seconds).astype(np.int64), bars.n - 1)
    return np.bincount(bar, weights=np.asarray(size, dtype=float) * share, minlength=bars.n)
