import csv

from tsvlab.cli import main


def test_simulate_writes_csv(tmp_path):
    main(["simulate", "--mode", "control", "--seed", "3", "--duration", "1800", "--out", str(tmp_path)])
    with open(tmp_path / "trades_control_3.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) > 1000
    assert {"t_true", "t_reported", "true_side", "lee_ready", "emo"} <= set(rows[0])
    assert all(r["trader_kind"] != "1" for r in rows)  # control: no informed traders
    with open(tmp_path / "quotes_control_3.csv", newline="", encoding="utf-8") as f:
        assert next(csv.reader(f)) == ["t", "bid_ticks", "ask_ticks"]
