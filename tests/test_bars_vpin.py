import numpy as np
import pytest

from tsvlab.bars import bucket_sums, make_buckets, make_time_bars, time_bar_sums
from tsvlab.vpin import alarm_runs, detect_episodes, lagged_corr, mask_intervals, on_grid, vpin


def _brute_bucket_sums(size, share, V):
    """Walk trades share by share, filling buckets of V shares."""
    out, cur, filled = [], 0.0, 0
    for q, f in zip(size, share):
        for _ in range(q):
            cur += f
            filled += 1
            if filled == V:
                out.append(cur)
                cur, filled = 0.0, 0
    return np.array(out)


def test_bucket_sums_split_trades_exactly():
    rng = np.random.default_rng(1)
    size = rng.integers(1, 40, 300)
    share = rng.choice([0.0, 0.5, 1.0], 300)
    t = np.arange(300.0)
    b = make_buckets(size, t, np.arange(300), 37)
    got = bucket_sums(size, share, b)
    want = _brute_bucket_sums(size, share, 37)
    assert got.shape == want.shape
    assert np.allclose(got, want, atol=1e-9)
    assert np.allclose(bucket_sums(size, np.ones(300), b), 37.0)
    # the closing trade is the one that completes each bucket
    cum = np.cumsum(size)
    for k, i in enumerate(b.close_idx):
        assert cum[i] >= 37 * (k + 1) and (i == 0 or cum[i - 1] < 37 * (k + 1))


def test_time_bars():
    t = np.array([0.5, 1.2, 1.8, 4.1])
    size = np.array([10, 20, 30, 40])
    price = np.array([100, 101, 102, 99])
    bars = make_time_bars(t, size, price, 1.0, 5.0)
    assert bars.volume.tolist() == [10, 50, 0, 0, 40]
    assert bars.last_price.tolist() == [100, 102, 102, 102, 99]
    assert time_bar_sums(t, size, np.array([1, 0, 1, 0.5]), bars).tolist() == [10, 30, 0, 0, 20]


def test_vpin_brute_force_and_limits():
    rng = np.random.default_rng(2)
    buy = rng.uniform(0, 100, 50)
    v = vpin(buy, 100.0, 5)
    assert np.all(np.isnan(v[:4]))
    for i in range(4, 50):
        assert v[i] == pytest.approx(np.mean(np.abs(2 * buy[i - 4:i + 1] - 100) / 100))
    assert np.allclose(vpin(np.full(10, 100.0), 100.0, 3)[2:], 1.0)
    assert np.allclose(vpin(np.full(10, 50.0), 100.0, 3)[2:], 0.0)
    assert np.all(np.isnan(vpin(np.ones(2), 100.0, 3)))


def test_vpin_point_in_time():
    buy = np.random.default_rng(4).uniform(0, 100, 80)
    v = vpin(buy, 100.0, 10)
    buy2 = buy.copy()
    buy2[50:] = 100.0
    assert np.array_equal(vpin(buy2, 100.0, 10)[:50], v[:50], equal_nan=True)


def test_on_grid_steps_and_skips_nan():
    vals = np.array([np.nan, 1.0, 2.0, 3.0])
    times = np.array([0.5, 1.5, 2.5, 3.5])
    g = on_grid(vals, times, np.array([1.0, 2.0, 2.5, 10.0]))
    assert np.isnan(g[0]) and g[1:].tolist() == [1.0, 2.0, 3.0]


def test_lagged_corr_finds_the_lag():
    a = np.random.default_rng(6).standard_normal(500)
    v = np.empty(500)
    v[7:] = a[:-7]
    v[:7] = 0.0
    lags = np.arange(-10, 11)
    c = lagged_corr(v, a, lags)
    assert lags[np.argmax(c)] == 7   # v responds 7 steps after a
    assert c[np.argmax(c)] > 0.99


def test_alarm_helpers():
    a = np.array([True, True, False, True, False, False, True])
    assert alarm_runs(a) == 3
    assert alarm_runs(np.array([], bool)) == 0
    grid = np.arange(0, 600, 60.0)
    alarm = np.zeros(grid.size, bool)
    alarm[5] = True
    eps = [dict(start=150.0, end=400.0), dict(start=420.0, end=500.0)]
    d = detect_episodes(alarm, grid, eps)
    assert d[0]["detected"] and d[0]["delay_min"] == pytest.approx((300 - 150) / 60)
    assert not d[1]["detected"] and d[1]["delay_min"] is None
    m = mask_intervals(grid, eps, pad_after=60.0)
    assert m.tolist() == [False] * 3 + [True] * 7
