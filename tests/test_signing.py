import numpy as np
import pytest

from tsvlab.signing import (bvc_buy_fraction, buy_fraction, emo, lee_ready, prevailing_quotes,
                            quote_rule, sign_trades, tick_rule, trailing_std)
from tsvlab.sim import report_times


def test_tick_rule_hand_case():
    p = np.array([100, 101, 101, 100, 100, 100, 102, 102])
    assert tick_rule(p).tolist() == [0, 1, 1, -1, -1, -1, 1, 1]
    assert tick_rule(np.array([5, 5, 5])).tolist() == [0, 0, 0]
    assert tick_rule(np.array([5])).tolist() == [0]


def test_quote_rule_lee_ready_emo_hand_case():
    # bid/ask in ticks; spreads of 1, 2 and 3 ticks
    price = np.array([101, 100, 101, 102, 101, 102, 104])
    bid = np.array([100, 100, 100, 100, 100, 100, 100])
    ask = np.array([101, 101, 102, 102, 103, 103, 103])
    assert quote_rule(price, bid, ask).tolist() == [1, -1, 0, 1, -1, 1, 1]
    # trade 3 is at the mid: Lee-Ready falls back to the tick rule (101 after 100: up-tick)
    assert lee_ready(price, bid, ask).tolist() == [1, -1, 1, 1, -1, 1, 1]
    # EMO: at ask buy, at bid sell, otherwise tick rule (trade 5: 101 < 102, down-tick;
    # trade 6: 102 > 101 up-tick; trade 7 above the ask: up-tick)
    assert emo(price, bid, ask).tolist() == [1, -1, 1, 1, -1, 1, 1]
    with pytest.raises(ValueError):
        sign_trades("other", price, bid, ask)


def test_prevailing_quote_is_last_at_or_before():
    q_t = np.array([0.0, 1.0, 2.0])
    bid, ask = prevailing_quotes(np.array([0.5, 1.0, 1.99, 5.0]), q_t, np.array([10, 11, 12]),
                                 np.array([11, 12, 13]))
    assert bid.tolist() == [10, 11, 11, 12] and ask.tolist() == [11, 12, 12, 13]
    with pytest.raises(ValueError):
        prevailing_quotes(np.array([-1.0]), q_t, np.array([10, 11, 12]), np.array([11, 12, 13]))


def test_quote_rules_exact_at_the_quote_without_delay(sess_informed):
    s = sess_informed
    bid, ask = prevailing_quotes(report_times(s.t, 0.0, s.seed), s.q_t, s.q_bid, s.q_ask)
    at_quote = (s.price == s.bid) | (s.price == s.ask)
    for m in ("quote", "lee_ready", "emo"):
        sg = sign_trades(m, s.price, bid, ask)
        assert np.array_equal(sg[at_quote], s.side[at_quote]), m


def test_reporting_delay_hurts_quote_rules_not_tick_rule(sess_informed):
    s = sess_informed
    acc = {}
    for d in (0.0, 1.0):
        bid, ask = prevailing_quotes(report_times(s.t, d, s.seed), s.q_t, s.q_bid, s.q_ask)
        acc[d] = {m: np.mean(sign_trades(m, s.price, bid, ask) == s.side) for m in ("tick", "lee_ready")}
    assert acc[1.0]["tick"] == acc[0.0]["tick"]
    assert acc[1.0]["lee_ready"] < acc[0.0]["lee_ready"] - 0.05


def test_buy_fraction():
    assert buy_fraction(np.array([1, -1, 0])).tolist() == [1.0, 0.0, 0.5]


def test_trailing_std_matches_brute_force_and_excludes_current():
    x = np.random.default_rng(3).standard_normal(200)
    x[17] = np.nan
    got = trailing_std(x, lookback=20, min_periods=5)
    for i in range(200):
        w = x[max(0, i - 20):i]
        w = w[~np.isnan(w)]
        if w.size < 5:
            assert np.isnan(got[i])
        else:
            assert got[i] == pytest.approx(np.std(w, ddof=1), rel=1e-9, abs=1e-12)


def test_bvc_point_in_time_and_direction():
    p = np.cumsum(np.random.default_rng(5).integers(-2, 3, 300)).astype(float) + 1000
    f = bvc_buy_fraction(p, lookback=30)
    # changing later prices never changes earlier buy fractions
    p2 = p.copy()
    p2[200:] += 50
    assert np.array_equal(bvc_buy_fraction(p2, lookback=30)[:200], f[:200])
    dp = np.diff(p)
    ok = np.arange(1, 300) >= 15
    assert np.all(f[1:][ok & (dp > 0)] > 0.5) and np.all(f[1:][ok & (dp < 0)] < 0.5)
    assert np.all(f[1:][ok & (dp == 0)] == 0.5)
    assert np.all(f[:11] == 0.5)  # warm-up
