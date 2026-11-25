import numpy as np
import pytest

from tsvlab import analysis as A
from tsvlab.sim import Session


def test_trade_accuracy_counts_unclassified_as_half():
    truth = np.array([1, 1, -1, -1])
    r = A.trade_accuracy(np.array([1, 0, 1, -1]), truth)
    assert r["accuracy"] == pytest.approx((2 + 0.5) / 4) and r["unclassified"] == 0.25
    assert A.trade_accuracy(truth, truth, np.zeros(4, bool))["n"] == 0


def test_volume_accuracy():
    vol = np.array([100.0, 100.0])
    true_buy = np.array([70.0, 40.0])
    assert A.volume_accuracy(true_buy, true_buy, vol) == 1.0
    # half/half guess: min(50,70)+min(50,30) + min(50,40)+min(50,60) = 80 + 90
    assert A.volume_accuracy(np.array([50.0, 50.0]), true_buy, vol) == pytest.approx(170 / 200)


def test_truth_is_perfect_and_naive_baseline_is_reported(sess_informed):
    ob = A.observe(sess_informed, 0.5)
    res = A.bar_accuracy(sess_informed, ob, 10_000, skip=0)
    assert 0.5 < res["naive"] < 1.0
    for m in ("tick", "quote", "lee_ready", "emo", "bvc"):
        assert 0.5 < res[m] <= 1.0


def test_condition_masks_partition_trades(sess_informed):
    ob = A.observe(sess_informed, 0.0)
    c = A.trade_conditions(sess_informed, ob)
    assert np.all(c["at_quote"] ^ c["inside_not_mid"] ^ c["at_mid"])
    assert np.all(c["low_vol"] ^ c["high_vol"])


def _truncate(s: Session, t_cut: float) -> Session:
    keep = s.t <= t_cut
    qk = s.q_t <= t_cut
    return Session(cfg=s.cfg, seed=s.seed, t=s.t[keep], side=s.side[keep], size=s.size[keep],
                   kind=s.kind[keep], price=s.price[keep], bid=s.bid[keep], ask=s.ask[keep],
                   regime=s.regime[keep], q_t=s.q_t[qk], q_bid=s.q_bid[qk], q_ask=s.q_ask[qk],
                   seg_start=s.seg_start, seg_alpha=s.seg_alpha, seg_regime=s.seg_regime,
                   episodes=s.episodes, bursts=s.bursts, episode_windows=s.episode_windows)


def test_vpin_is_point_in_time(sess_informed):
    """Deleting every trade after a cut leaves every VPIN value (all methods) before it unchanged."""
    s = sess_informed
    cut = 0.6 * s.cfg.duration
    full = A.vpin_series(s, A.observe(s, 0.5), 20_000, (1, 5))
    part_s = _truncate(s, cut)
    part = A.vpin_series(part_s, A.observe(part_s, 0.5), 20_000, (1, 5))
    k = part["n_buckets"] - 1  # the last bucket of the cut session may close differently
    assert k > 50
    for key, v in part.items():
        if isinstance(key, tuple):
            assert np.array_equal(v[:k], full[key][:k], equal_nan=True), key


def test_vpin_true_signs_rise_in_episodes(sess_informed):
    s = sess_informed
    ser = A.vpin_series(s, A.observe(s, 0.5), 20_000, (5,))
    grid, v, a = A.grid_view(s, ser, "truth", 5)
    ok = np.isfinite(v)
    assert v[ok & (a > 0)].mean() > v[ok & (a == 0)].mean() + 0.05
    assert A.vpin_alpha_corr(s, ser, "truth", 5) > 0.3


def test_ofi_truth_matches_itself_and_features_are_trailing(sess_informed):
    s = sess_informed
    f = A.ofi_features(s, A.observe(s, 0.5))
    m = A.ofi_metrics(f)
    assert m["truth"]["corr_with_true"] == pytest.approx(1.0)
    assert m["truth"]["mean_abs_error"] == 0.0
    assert m["lee_ready"]["corr_with_true"] > m["bvc"]["corr_with_true"]
    # truncation: OFI rows before the cut do not change
    cut = 0.6 * s.cfg.duration
    part_s = _truncate(s, cut)
    g = A.ofi_features(part_s, A.observe(part_s, 0.5))
    rows = int(cut // A.OFI_BAR) - A.OFI_SKIP - 1
    for meth in f["ofi"]:
        assert np.array_equal(g["ofi"][meth][:rows], f["ofi"][meth][:rows], equal_nan=True), meth


def test_alarm_stats_shape(sess_control):
    s = sess_control
    ser = A.vpin_series(s, A.observe(s, 0.5), 20_000, (5,))
    grid, v, _ = A.grid_view(s, ser, "truth", 5)
    st = A.alarm_stats(s, grid, v, threshold=np.nanquantile(v, 0.9))
    assert st["episodes"] == []  # control: no informed episodes
    assert 0.0 <= st["alarm_share"] <= 0.2


def test_session_stats(sess_informed):
    st = A.session_stats(sess_informed)
    assert st["trades"] == sess_informed.n_trades
    assert abs(st["at_quote_share"] + st["inside_not_mid_share"] + st["at_mid_share"] - 1) < 1e-12
    assert 0 < st["high_vol_time_share"] < 1
