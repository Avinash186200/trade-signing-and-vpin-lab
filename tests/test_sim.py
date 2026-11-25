import numpy as np
import pytest

from tsvlab.signing import prevailing_quotes
from tsvlab.sim import KIND_BURST, KIND_INFORMED, KIND_UNINFORMED, SimConfig, report_times, simulate


def test_same_seed_same_session(short_cfg, sess_informed):
    again = simulate(short_cfg, 11)
    for name in ("t", "side", "size", "kind", "price", "bid", "ask", "q_t", "q_bid", "q_ask"):
        assert np.array_equal(getattr(again, name), getattr(sess_informed, name))


def test_bad_mode():
    with pytest.raises(ValueError):
        simulate(SimConfig(mode="other"), 1)


def test_prices_inside_quotes_and_execution_rules(sess_informed):
    s = sess_informed
    assert s.price.dtype == np.int64
    assert np.all(s.bid < s.ask)
    assert np.all((s.price >= s.bid) & (s.price <= s.ask))
    spread = s.ask - s.bid
    assert set(np.unique(spread)) <= {1, 2, 3}
    at_quote = (s.price == s.bid) | (s.price == s.ask)
    # at the quote, a buyer pays the ask and a seller hits the bid
    assert np.all(s.price[at_quote & (s.side > 0)] == s.ask[at_quote & (s.side > 0)])
    assert np.all(s.price[at_quote & (s.side < 0)] == s.bid[at_quote & (s.side < 0)])
    # inside-the-spread trades only happen when the spread is wider than one tick
    assert np.all(spread[~at_quote] >= 2)
    assert (~at_quote).mean() > 0.05


def test_recorded_quote_is_the_prevailing_quote(sess_informed):
    s = sess_informed
    bid, ask = prevailing_quotes(s.t, s.q_t, s.q_bid, s.q_ask)
    assert np.array_equal(bid, s.bid) and np.array_equal(ask, s.ask)


def test_episodes_and_bursts_placed_as_configured(short_cfg, sess_informed):
    s = sess_informed
    for group in (s.episodes, s.bursts):
        for d in group:
            assert d["start"] >= short_cfg.warmup and d["end"] <= short_cfg.duration
        for a, b in zip(group, group[1:]):
            assert b["start"] >= a["end"] + short_cfg.min_gap
    assert len(s.episodes) == 2 and len(s.bursts) == 1


def test_informed_traders_trade_on_the_episode_side(sess_informed):
    s = sess_informed
    inf = s.kind == KIND_INFORMED
    assert inf.any()
    for e in s.episodes:
        m = inf & (s.t >= e["start"]) & (s.t < e["end"])
        assert m.sum() > 0 and np.all(s.side[m] == e["side"])
    # no informed trade outside any episode
    inside_any = np.zeros(s.n_trades, bool)
    for e in s.episodes:
        inside_any |= (s.t >= e["start"]) & (s.t < e["end"])
    assert not np.any(inf & ~inside_any)


def test_planted_share_matches_realised_share(sess_informed):
    s = sess_informed
    for e in s.episodes:
        m = (s.t >= e["start"]) & (s.t < e["end"])
        realised = np.mean(s.kind[m] == KIND_INFORMED)
        planted = np.mean(s.alpha_at(s.t[m]))
        assert abs(realised - planted) < 0.05
    quiet = s.alpha_at(np.array([1.0, 100.0]))
    assert np.all(quiet == 0.0)


def test_control_has_no_informed_flow_but_same_uninformed_arrivals(sess_informed, sess_control):
    c, s = sess_control, sess_informed
    assert not np.any(c.kind == KIND_INFORMED)
    assert c.episodes == [] and np.all(c.seg_alpha == 0.0)
    assert c.episode_windows == s.episodes  # placebo windows, nobody informed trades on them
    assert c.bursts == s.bursts
    u_s = s.t[s.kind == KIND_UNINFORMED]
    u_c = c.t[c.kind == KIND_UNINFORMED]
    assert np.array_equal(u_s, u_c)
    assert np.array_equal(s.t[s.kind == KIND_BURST], c.t[c.kind == KIND_BURST])


def test_informed_episode_moves_price_in_its_direction():
    moves = []
    for seed in range(1, 5):
        s = simulate(SimConfig(duration=7_200.0, warmup=900.0, n_episodes=(2, 2), n_bursts=(0, 0)), seed)
        for e in s.episodes:
            m0, m1 = s.mid_at(np.array([e["start"], e["end"]]))
            moves.append(e["side"] * (m1 - m0))
    assert np.mean(moves) > 5  # ticks, in the informed direction on average


def test_report_times():
    t = np.sort(np.random.default_rng(0).random(5_000) * 100)
    assert np.array_equal(report_times(t, 0.0, 1), t)
    r = report_times(t, 0.5, 1)
    assert np.all(np.diff(r) >= 0)          # feed order kept
    assert np.all(r >= t + 0.25 - 1e-12)    # never early, at least half the delay late
    assert 0.45 < np.mean(r - t) < 0.75
    assert np.array_equal(r, report_times(t, 0.5, 1))
