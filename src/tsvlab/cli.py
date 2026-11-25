"""Command line: tsvlab simulate | bench | report."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from . import bench
from .signing import TRADE_METHODS, prevailing_quotes, sign_trades
from .sim import SimConfig, report_times, simulate


def _simulate(args) -> None:
    cfg = SimConfig(mode=args.mode, duration=args.duration)
    s = simulate(cfg, args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    t_rep = report_times(s.t, args.delay, s.seed)
    bid, ask = prevailing_quotes(t_rep, s.q_t, s.q_bid, s.q_ask)
    signs = {m: sign_trades(m, s.price, bid, ask) for m in TRADE_METHODS}
    tag = f"{args.mode}_{args.seed}"
    with open(out / f"trades_{tag}.csv", "w", newline="\n", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["t_true", "t_reported", "price_ticks", "size", "true_side", "trader_kind",
                    "bid_at_trade", "ask_at_trade", "vol_regime", *TRADE_METHODS])
        for i in range(s.n_trades):
            w.writerow([f"{s.t[i]:.6f}", f"{t_rep[i]:.6f}", s.price[i], s.size[i], s.side[i], s.kind[i],
                        s.bid[i], s.ask[i], s.regime[i], *(signs[m][i] for m in TRADE_METHODS)])
    with open(out / f"quotes_{tag}.csv", "w", newline="\n", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["t", "bid_ticks", "ask_ticks"])
        for i in range(s.q_t.size):
            w.writerow([f"{s.q_t[i]:.6f}", s.q_bid[i], s.q_ask[i]])
    print(f"{s.n_trades} trades, {s.q_t.size} quotes, {len(s.episodes)} informed episodes, "
          f"{len(s.bursts)} uninformed bursts -> {out}")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="tsvlab", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    ps = sub.add_parser("simulate", help="write one session's trades and quotes to CSV")
    ps.add_argument("--mode", choices=("informed", "control"), default="informed")
    ps.add_argument("--seed", type=int, default=1)
    ps.add_argument("--delay", type=float, default=bench.DEFAULT_DELAY, help="trade reporting delay (s)")
    ps.add_argument("--duration", type=float, default=SimConfig.duration, help="session length (s)")
    ps.add_argument("--out", default="data")
    pb = sub.add_parser("bench", help="full run; writes results/*.json and RESULTS.md")
    pb.add_argument("--out", default="results")
    pb.add_argument("--dev-only", action="store_true",
                    help="development seeds only (VPIN selection and thresholds); no held-out run")
    pr = sub.add_parser("report", help="re-render RESULTS.md from the JSON")
    pr.add_argument("--out", default="results")
    args = p.parse_args(argv)
    if args.cmd == "simulate":
        _simulate(args)
    elif args.cmd == "bench":
        bench.run(args.out, dev_only=args.dev_only)
    else:
        bench.write_report(args.out)


if __name__ == "__main__":
    main()
