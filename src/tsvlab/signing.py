"""Trade-signing rules.

Trade-level rules return an int8 array: +1 buyer-initiated, -1 seller-initiated,
0 unclassified. They see only what a desk sees: trade prices in feed order, the
reported trade times, and correctly stamped quotes.

* Tick rule: up-tick buy, down-tick sell; a zero tick takes the last non-zero tick.
* Quote (midpoint) rule: above the prevailing mid buy, below sell, at the mid unclassified.
* Lee-Ready (Lee and Ready 1991): the quote rule, with the tick rule for trades at the mid.
* EMO (Ellis, Michaely and O'Hara 2000): at the ask buy, at the bid sell, anything
  else (inside or outside the quotes) by the tick rule.

Bulk volume classification (Easley, Lopez de Prado and O'Hara 2012) works on bars,
not trades; see :func:`bvc_buy_fraction`.

All rules match a trade to the last quote stamped at or before the trade's
reported time. Lee and Ready's original paper also suggested comparing with the
quote in force five seconds before the reported trade time, to undo reporting
delays of that era; that variant is not used here.
"""

from __future__ import annotations

import numpy as np
from scipy.special import ndtr

TRADE_METHODS = ("tick", "quote", "lee_ready", "emo")
METHODS = TRADE_METHODS + ("bvc",)
LABELS = {"truth": "true signs", "tick": "tick rule", "quote": "quote rule",
          "lee_ready": "Lee-Ready", "emo": "EMO", "bvc": "BVC"}


def tick_rule(price: np.ndarray) -> np.ndarray:
    p = np.asarray(price)
    s = np.zeros(p.size, dtype=np.int8)
    if p.size < 2:
        return s
    s[1:] = np.sign(np.diff(p)).astype(np.int8)
    # zero ticks inherit the last non-zero tick (forward fill)
    idx = np.where(s != 0, np.arange(s.size), 0)
    np.maximum.accumulate(idx, out=idx)
    return s[idx]


def prevailing_quotes(t_reported: np.ndarray, q_t: np.ndarray, q_bid: np.ndarray,
                      q_ask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Bid and ask of the last quote stamped at or before each reported trade time."""
    idx = np.searchsorted(q_t, t_reported, side="right") - 1
    if np.any(idx < 0):
        raise ValueError("a trade is reported before the first quote")
    return q_bid[idx], q_ask[idx]


def quote_rule(price: np.ndarray, bid: np.ndarray, ask: np.ndarray) -> np.ndarray:
    # 2p vs bid + ask keeps the comparison in exact integers
    return np.sign(2 * np.asarray(price) - (np.asarray(bid) + np.asarray(ask))).astype(np.int8)


def lee_ready(price: np.ndarray, bid: np.ndarray, ask: np.ndarray) -> np.ndarray:
    q = quote_rule(price, bid, ask)
    return np.where(q != 0, q, tick_rule(price)).astype(np.int8)


def emo(price: np.ndarray, bid: np.ndarray, ask: np.ndarray) -> np.ndarray:
    p = np.asarray(price)
    out = tick_rule(p).copy()
    out[p == bid] = -1
    out[p == ask] = 1
    return out


def sign_trades(method: str, price: np.ndarray, bid: np.ndarray, ask: np.ndarray) -> np.ndarray:
    if method == "tick":
        return tick_rule(price)
    if method == "quote":
        return quote_rule(price, bid, ask)
    if method == "lee_ready":
        return lee_ready(price, bid, ask)
    if method == "emo":
        return emo(price, bid, ask)
    raise ValueError(f"unknown trade-level method {method!r}")


def buy_fraction(signs: np.ndarray) -> np.ndarray:
    """Share of each trade's volume counted as buying: 1, 0, or 0.5 if unclassified."""
    return (np.asarray(signs, dtype=float) + 1.0) / 2.0


def trailing_std(x: np.ndarray, lookback: int, min_periods: int = 10) -> np.ndarray:
    """Standard deviation of the previous ``lookback`` values, excluding the current one.

    NaN values in ``x`` are skipped. The result at i uses x[i - lookback .. i - 1] only,
    so it never sees the bar it is applied to. NaN where fewer than ``min_periods``
    values are available.
    """
    x = np.asarray(x, dtype=float)
    ok = ~np.isnan(x)
    v = np.where(ok, x, 0.0)
    c0 = np.concatenate([[0.0], np.cumsum(ok)])
    c1 = np.concatenate([[0.0], np.cumsum(v)])
    c2 = np.concatenate([[0.0], np.cumsum(v * v)])
    i = np.arange(x.size)
    lo = np.maximum(i - lookback, 0)
    n = c0[i] - c0[lo]
    s1 = c1[i] - c1[lo]
    s2 = c2[i] - c2[lo]
    with np.errstate(invalid="ignore", divide="ignore"):
        var = (s2 - s1 * s1 / n) / (n - 1)
    out = np.sqrt(np.maximum(var, 0.0))
    out[n < max(min_periods, 2)] = np.nan
    return out


def bvc_buy_fraction(close_price: np.ndarray, lookback: int = 50, min_periods: int = 10) -> np.ndarray:
    """Bulk volume classification: buy share of each bar = Phi(dP / sigma).

    dP is the change in the bar's last trade price from the previous bar, and sigma
    the standard deviation of the previous ``lookback`` bar changes (point in time).
    Bars without a usable sigma (warm-up, or no price variation yet) get 0.5.
    """
    p = np.asarray(close_price, dtype=float)
    dp = np.full(p.size, np.nan)
    dp[1:] = np.diff(p)
    sd = trailing_std(dp, lookback, min_periods)
    with np.errstate(invalid="ignore", divide="ignore"):
        z = dp / sd
    frac = ndtr(z)
    bad = ~np.isfinite(z)
    frac[bad] = 0.5
    return frac
