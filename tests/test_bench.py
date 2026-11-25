import json
import math
from pathlib import Path

import pytest

from tsvlab.bench import RESULT_FILES, SEEDS, load, render, run
from tsvlab.sim import SimConfig

ROOT = Path(__file__).resolve().parents[1]
SMALL = SimConfig(duration=7_200.0, warmup=900.0, n_episodes=(2, 2), n_bursts=(1, 1))
SMALL_SEEDS = {"dev": {"informed": (1, 2), "control": (101, 102)},
               "holdout": {"informed": (1001,), "control": (2001,)}}


def test_seed_sets_are_disjoint():
    all_seeds = [s for sp in SEEDS.values() for v in sp.values() for s in v]
    assert len(all_seeds) == len(set(all_seeds))
    assert all(len(v) >= 8 for sp in SEEDS.values() for v in sp.values())


def test_small_bench_end_to_end(tmp_path):
    res = run(tmp_path, base=SMALL, seeds=SMALL_SEEDS, log=lambda *_: None)
    for k in RESULT_FILES:
        assert (tmp_path / f"{k}.json").exists()
    assert (tmp_path / "RESULTS.md").read_text(encoding="utf-8").startswith("# Results")
    v = res["vpin"]
    for m, sel in v["selected"].items():
        assert f"{sel['buckets_per_session']}x{sel['window']}" in v["grid_combos"]
        assert m in v["holdout"]
    # the selected setting is the best development cell, nothing else
    for m, sel in v["selected"].items():
        best = max(c["mean"] for c in v["grid"][m].values() if c["mean"] is not None)
        assert sel["dev_corr"] == pytest.approx(best)


def test_dev_only_writes_no_holdout(tmp_path):
    res = run(tmp_path, base=SMALL, seeds=SMALL_SEEDS, log=lambda *_: None, dev_only=True)
    assert "holdout" not in res["vpin"] and "accuracy" not in res
    assert not (tmp_path / "RESULTS.md").exists()


def test_results_written_with_lf_only():
    for k in RESULT_FILES + ("RESULTS",):
        name = f"{k}.md" if k == "RESULTS" else f"{k}.json"
        assert b"\r\n" not in (ROOT / "results" / name).read_bytes()


def _diff(a, b, path="$"):
    """Differences between two JSON trees; floats match to 1e-6 relative or 1e-5 absolute
    (the JSON is rounded to 6 decimals), ints and strings exactly."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(a.keys() | b.keys()):
            if k not in a or k not in b:
                out.append(f"{path}.{k}: missing")
            else:
                out += _diff(a[k], b[k], f"{path}.{k}")
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{path}: length {len(a)} != {len(b)}"]
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in _diff(x, y, f"{path}[{i}]")]
    if isinstance(a, float) or isinstance(b, float):
        ok = isinstance(a, (int, float)) and isinstance(b, (int, float)) and \
            math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-5)
        return [] if ok else [f"{path}: {a} != {b}"]
    return [] if a == b else [f"{path}: {a!r} != {b!r}"]


@pytest.fixture(scope="module")
def full_run(tmp_path_factory):
    out = tmp_path_factory.mktemp("full")
    run(out, log=lambda *_: None)
    return out


@pytest.mark.parametrize("name", RESULT_FILES)
def test_committed_results_reproduce(full_run, name):
    fresh = json.loads((full_run / f"{name}.json").read_text(encoding="utf-8"))
    committed = json.loads((ROOT / "results" / f"{name}.json").read_text(encoding="utf-8"))
    diffs = _diff(fresh, committed)
    assert not diffs, "\n".join(diffs[:20])


def test_committed_report_matches_json():
    """RESULTS.md is exactly the render of the committed JSON (deterministic, no rerun)."""
    assert render(load(ROOT / "results")) == (ROOT / "results" / "RESULTS.md").read_text(encoding="utf-8")
