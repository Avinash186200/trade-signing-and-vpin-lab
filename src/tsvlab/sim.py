"""Trades-and-quotes simulator with known ground truth.

One session is a continuous stretch of trading (default 6.5 hours of clock time).
Every trade carries its true initiator side and the kind of trader behind it, so
every signing rule and every flow-toxicity number can be scored against the truth.

Order flow (PIN-style arrival model, after Easley, Kiefer, O'Hara and Paperman):

* Uninformed buyers and sellers arrive as Poisson processes at rate ``eps`` each.
  The rate is higher in high-volatility regimes.
* **Informed episodes** (``mode="informed"`` only): during an episode, informed
  traders arrive at rate ``mu`` and all trade on one side. The episode sets the
  informed share ``alpha = mu / (mu + 2 eps)`` and moves the efficient price
  permanently in the informed direction.
* **Uninformed bursts** (both modes): a large uninformed parent order split into
  many child trades on one side. It pushes quotes temporarily but carries no
  information, so the price reverts. These are present in the control too, so the
  control asks: what does VPIN do on one-sided flow that is not informed?

Quotes: a dealer quotes bid and ask around ``V(t) + L(t)``, where ``V`` is the
efficient price (a random walk with regime volatility plus the informed drift) and
``L`` is a temporary order-flow pressure that each trade pushes in its direction
and that decays exponentially. Quotes update at exogenous Poisson times and,
with some probability, shortly after each trade (the dealer reacting to flow).
A trade executes against the quote in force just before it: at the ask (buy) or
bid (sell), or, when the spread is 2 or 3 ticks, sometimes inside the spread.

Prices are integer ticks throughout, so "price equals the ask" is an exact test.

``mode="control"`` with the same seed places the same regimes, episode windows,
bursts and uninformed arrival times as ``mode="informed"``, then leaves the
informed traders out (and with them the informed price drift). Later random
draws (trade sizes, quote times, price noise, execution) are not the same,
because the number of trades differs; the generator's rules are.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace

import numpy as np

MODES = ("informed", "control")
KIND_UNINFORMED, KIND_INFORMED, KIND_BURST = 0, 1, 2


@dataclass(frozen=True)
class SimConfig:
    mode: str = "informed"
    duration: float = 23_400.0          # seconds (6.5 hours)
    start_ticks: int = 5_000            # 50.00 with a 0.01 tick
    base_rate: float = 1.0              # uninformed arrivals per second, per side
    high_vol_rate_mult: float = 1.3     # uninformed arrivals scale up in high volatility
    sigma_low: float = 0.4              # efficient-price vol, ticks per sqrt(second)
    sigma_high: float = 1.0
    regime_mean_low: float = 2_400.0    # mean regime durations (seconds)
    regime_mean_high: float = 1_200.0
    n_episodes: tuple[int, int] = (3, 5)        # inclusive range per session
    episode_minutes: tuple[float, float] = (15.0, 35.0)
    episode_alpha: tuple[float, float] = (0.15, 0.40)
    episode_move_ticks: tuple[float, float] = (15.0, 40.0)
    n_bursts: tuple[int, int] = (2, 4)
    burst_minutes: tuple[float, float] = (5.0, 20.0)
    burst_share: tuple[float, float] = (0.15, 0.35)
    warmup: float = 1_800.0             # no episode or burst starts in the first 30 minutes
    min_gap: float = 600.0              # seconds between two episodes (or two bursts)
    exo_quote_rate: float = 1.0         # exogenous quote updates per second
    react_prob: float = 0.5             # chance the dealer re-quotes after a trade
    react_lag_min: float = 0.02         # seconds
    react_lag_mean: float = 0.15        # mean of the exponential part (seconds)
    impact_ticks: float = 0.12          # push on L per trade, ticks
    impact_halflife: float = 40.0       # seconds
    spread_probs_low: tuple[float, float, float] = (0.55, 0.30, 0.15)   # P(spread = 1, 2, 3 ticks)
    spread_probs_high: tuple[float, float, float] = (0.30, 0.40, 0.30)
    inside_prob: float = 0.25           # chance a trade executes inside a 2- or 3-tick spread
    inside_tilt: float = 0.70           # 3-tick spread: chance an inside trade is on the initiator's half
    size_lot: int = 100
    size_geom_p: float = 0.45           # trade size = lot * Geometric(p)

    def with_mode(self, mode: str) -> "SimConfig":
        return replace(self, mode=mode)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Session:
    cfg: SimConfig
    seed: int
    # trades, in true time order
    t: np.ndarray          # true execution time (s)
    side: np.ndarray       # true initiator: +1 buyer, -1 seller (int8)
    size: np.ndarray       # shares (int64)
    kind: np.ndarray       # 0 uninformed, 1 informed, 2 burst (int8)
    price: np.ndarray      # ticks (int64)
    bid: np.ndarray        # prevailing bid at execution (ticks)
    ask: np.ndarray        # prevailing ask at execution (ticks)
    regime: np.ndarray     # 0 low vol, 1 high vol (int8)
    # quotes, in time order (always stamped correctly)
    q_t: np.ndarray
    q_bid: np.ndarray
    q_ask: np.ndarray
    # truth about the planted structure
    seg_start: np.ndarray  # piecewise-constant segments of the arrival rates
    seg_alpha: np.ndarray  # planted informed share of arrivals in each segment
    seg_regime: np.ndarray
    episodes: list         # dicts: start, end, side, alpha, move_ticks
    bursts: list           # dicts: start, end, side, share
    episode_windows: list  # the placed episodes in either mode; in control nobody trades on them (placebo)

    @property
    def n_trades(self) -> int:
        return int(self.t.size)

    def alpha_at(self, times: np.ndarray) -> np.ndarray:
        """Planted informed share of trader arrivals at the given times."""
        idx = np.searchsorted(self.seg_start, np.asarray(times, dtype=float), side="right") - 1
        return self.seg_alpha[np.clip(idx, 0, None)]

    def regime_at(self, times: np.ndarray) -> np.ndarray:
        idx = np.searchsorted(self.seg_start, np.asarray(times, dtype=float), side="right") - 1
        return self.seg_regime[np.clip(idx, 0, None)]

    def mid_at(self, times: np.ndarray) -> np.ndarray:
        """Quote midpoint (ticks) in force at each time; quotes are stamped correctly."""
        idx = np.searchsorted(self.q_t, np.asarray(times, dtype=float), side="right") - 1
        idx = np.clip(idx, 0, None)
        return 0.5 * (self.q_bid[idx] + self.q_ask[idx])


def _regimes(cfg: SimConfig, rng: np.random.Generator) -> list[tuple[float, float, int]]:
    out, t, state = [], 0.0, 0
    while t < cfg.duration:
        mean = cfg.regime_mean_low if state == 0 else cfg.regime_mean_high
        d = float(rng.exponential(mean))
        out.append((t, min(t + d, cfg.duration), state))
        t += d
        state ^= 1
    return out


def _place(cfg: SimConfig, rng: np.random.Generator, n_range, minutes) -> list[tuple[float, float]]:
    """Non-overlapping intervals, at least ``min_gap`` apart, after the warm-up."""
    k = int(rng.integers(n_range[0], n_range[1] + 1))
    placed: list[tuple[float, float]] = []
    for _ in range(k):
        for _attempt in range(200):
            dur = float(rng.uniform(*minutes)) * 60.0
            lo, hi = cfg.warmup, cfg.duration - dur - cfg.min_gap
            if hi <= lo:  # session too short for this interval
                continue
            s = float(rng.uniform(lo, hi))
            e = s + dur
            if all(e + cfg.min_gap <= a or s >= b + cfg.min_gap for a, b in placed):
                placed.append((s, e))
                break
    return sorted(placed)


def simulate(cfg: SimConfig, seed: int) -> Session:
    if cfg.mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    rng = np.random.default_rng(seed)
    T = cfg.duration

    regimes = _regimes(cfg, rng)
    ep_iv = _place(cfg, rng, cfg.n_episodes, cfg.episode_minutes)
    episodes = [dict(start=s, end=e, side=int(rng.choice([-1, 1])),
                     alpha=float(rng.uniform(*cfg.episode_alpha)),
                     move_ticks=float(rng.uniform(*cfg.episode_move_ticks))) for s, e in ep_iv]
    bu_iv = _place(cfg, rng, cfg.n_bursts, cfg.burst_minutes)
    bursts = [dict(start=s, end=e, side=int(rng.choice([-1, 1])),
                   share=float(rng.uniform(*cfg.burst_share))) for s, e in bu_iv]
    informed_on = cfg.mode == "informed"

    # piecewise-constant segments of all arrival rates
    cuts = {0.0, T}
    for a, b, _ in regimes:
        cuts.update((a, min(b, T)))
    for d in episodes + bursts:
        cuts.update((d["start"], d["end"]))
    edges = np.array(sorted(c for c in cuts if 0.0 <= c <= T))

    ts, sides, kinds = [], [], []
    seg_start, seg_alpha, seg_regime = [], [], []
    for a, b in zip(edges[:-1], edges[1:]):
        if b <= a:
            continue
        mid = 0.5 * (a + b)
        reg = next(r for s, e, r in regimes if s <= mid < e)
        eps = cfg.base_rate * (cfg.high_vol_rate_mult if reg else 1.0)
        mu, mu_side, br, br_side = 0.0, 1, 0.0, 1
        for d in episodes:
            if d["start"] <= mid < d["end"]:
                mu = d["alpha"] / (1.0 - d["alpha"]) * 2.0 * eps
                mu_side = d["side"]
        for d in bursts:
            if d["start"] <= mid < d["end"]:
                br = d["share"] / (1.0 - d["share"]) * 2.0 * eps
                br_side = d["side"]
        streams = [(eps, 1, KIND_UNINFORMED), (eps, -1, KIND_UNINFORMED),
                   (mu, mu_side, KIND_INFORMED), (br, br_side, KIND_BURST)]
        for rate, sd, kd in streams:
            n = int(rng.poisson(rate * (b - a))) if rate > 0 else 0
            # the same draws happen in both modes; control drops informed arrivals after
            u = rng.random(n)
            if kd == KIND_INFORMED and not informed_on:
                continue
            ts.append(a + u * (b - a))
            sides.append(np.full(n, sd, dtype=np.int8))
            kinds.append(np.full(n, kd, dtype=np.int8))
        mu_eff = mu if informed_on else 0.0
        seg_start.append(a)
        seg_alpha.append(mu_eff / (2.0 * eps + mu_eff + br))
        seg_regime.append(reg)

    t = np.concatenate(ts)
    order = np.argsort(t, kind="stable")
    t = t[order]
    side = np.concatenate(sides)[order]
    kind = np.concatenate(kinds)[order]
    n = t.size
    size = cfg.size_lot * rng.geometric(cfg.size_geom_p, n).astype(np.int64)

    seg_start_a = np.array(seg_start)
    seg_regime_a = np.array(seg_regime, dtype=np.int8)

    def regime_of(x):
        return seg_regime_a[np.clip(np.searchsorted(seg_start_a, x, side="right") - 1, 0, None)]

    # quote events: one at t=0, exogenous Poisson updates, and reactions after trades
    n_exo = int(rng.poisson(cfg.exo_quote_rate * T))
    exo_t = np.sort(rng.random(n_exo) * T)
    react = rng.random(n) < cfg.react_prob
    react_t = t + cfg.react_lag_min + rng.exponential(cfg.react_lag_mean, n)
    react_t = react_t[react & (react_t < T)]
    qt = np.concatenate([[0.0], exo_t, react_t])
    qt.sort(kind="stable")
    nq = qt.size

    ev_t = np.concatenate([t, qt])
    ev_is_trade = np.concatenate([np.ones(n, bool), np.zeros(nq, bool)])
    ev_idx = np.concatenate([np.arange(n), np.arange(nq)])
    # quotes sort before trades at equal times (only possible at t=0)
    ev_order = np.lexsort((ev_is_trade, ev_t))
    ev_t, ev_is_trade, ev_idx = ev_t[ev_order], ev_is_trade[ev_order], ev_idx[ev_order]

    # efficient price at every event: regime-vol random walk + informed drift (ticks)
    dt = np.diff(ev_t, prepend=0.0)
    sig = np.where(regime_of(np.concatenate([[0.0], ev_t[:-1]])) == 1, cfg.sigma_high, cfg.sigma_low)
    z = rng.standard_normal(ev_t.size)
    V = cfg.start_ticks + np.cumsum(sig * np.sqrt(dt) * z)
    if informed_on:
        for d in episodes:
            frac = np.clip((ev_t - d["start"]) / (d["end"] - d["start"]), 0.0, 1.0)
            V = V + d["side"] * d["move_ticks"] * frac
    decay = np.exp(-np.log(2.0) * dt / cfg.impact_halflife)

    # spread for each quote event, by the regime at that time
    q_reg = regime_of(qt)
    u_sp = rng.random(nq)
    cl, ch = np.cumsum(cfg.spread_probs_low), np.cumsum(cfg.spread_probs_high)
    q_spread = np.where(q_reg == 1, 1 + (u_sp > ch[0]) + (u_sp > ch[1]),
                        1 + (u_sp > cl[0]) + (u_sp > cl[1])).astype(np.int64)

    q_bid = np.empty(nq, np.int64)
    tr_bid = np.empty(n, np.int64)
    tr_spread = np.empty(n, np.int64)
    L = 0.0
    bid = spread = 0
    k = cfg.impact_ticks
    # the only sequential step: quotes depend on the flow pressure L, which trades move
    for is_tr, j, dec, v in zip(ev_is_trade.tolist(), ev_idx.tolist(), decay.tolist(), V.tolist()):
        L *= dec
        if is_tr:
            tr_bid[j] = bid
            tr_spread[j] = spread
            L += k * side[j]
        else:
            spread = int(q_spread[j])
            bid = int(np.floor(v + L - 0.5 * spread + 0.5))
            q_bid[j] = bid
    q_ask = q_bid + q_spread
    tr_ask = tr_bid + tr_spread

    # execution price: at the quote, or inside a 2- or 3-tick spread
    u_in = rng.random(n)
    u_tilt = rng.random(n)
    inside = (tr_spread >= 2) & (u_in < cfg.inside_prob)
    price = np.where(side > 0, tr_ask, tr_bid).astype(np.int64)
    on_initiator_half = u_tilt < cfg.inside_tilt
    in3 = np.where((side > 0) == on_initiator_half, tr_bid + 2, tr_bid + 1)
    price = np.where(inside & (tr_spread == 2), tr_bid + 1, price)
    price = np.where(inside & (tr_spread == 3), in3, price)

    return Session(cfg=cfg, seed=seed, t=t, side=side, size=size, kind=kind, price=price,
                   bid=tr_bid, ask=tr_ask, regime=regime_of(t), q_t=qt, q_bid=q_bid,
                   q_ask=q_ask, seg_start=seg_start_a, seg_alpha=np.array(seg_alpha),
                   seg_regime=seg_regime_a, episodes=episodes if informed_on else [],
                   bursts=bursts, episode_windows=episodes)


def report_times(t: np.ndarray, delay: float, seed: int) -> np.ndarray:
    """Trade timestamps as a feed would report them: late by ``delay`` seconds on average.

    Each trade is stamped ``delay * U(0.5, 1.5)`` late; a running maximum keeps the
    trade feed in its original order. Quotes are stamped correctly, so only the
    alignment of trades to quotes changes. ``delay=0`` returns the true times.
    """
    t = np.asarray(t, dtype=float)
    if delay <= 0:
        return t.copy()
    u = np.random.default_rng([int(seed), 7]).uniform(0.5, 1.5, t.size)
    return np.maximum.accumulate(t + delay * u)
