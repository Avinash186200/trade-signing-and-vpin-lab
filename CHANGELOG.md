# Changelog

All notable changes are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
uses [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-11-25

### Added

- Trades-and-quotes simulator with known ground truth: PIN-style uninformed and informed arrivals, planted informed episodes (share 15% to 40%, one-sided, with a permanent price drift), uninformed one-sided bursts with temporary impact only, volatility regimes, a dealer who re-quotes after trades, trades at the quote, inside the spread and at the mid, and a trade reporting delay that keeps the feed order. A control mode with the same seed keeps everything except the informed traders, and keeps the episode windows as placebo windows. CSV export of trades and quotes.
- Signing rules: tick, quote (midpoint), Lee-Ready, EMO, and bulk volume classification with a point-in-time sigma. Trade-level accuracy by reporting delay, print location and volatility regime; bar-level volume accuracy with a naive 50/50 baseline; a BVC sensitivity to efficient-price noise.
- VPIN on equal-volume buckets with exact trade splitting, for every signing method and for the true signs. Bucket size and window chosen per method on development seeds, alarm thresholds from development control seeds; held-out seeds scored once for correlation with the planted share, lead/lag, detection against placebo windows and false alarms.
- Trailing 5-minute trade-flow imbalance features per signing method, compared with the true-sign feature and with forward returns.
- Tests including point-in-time truncation checks and a full rerun against the committed results; `constraints.txt` with exact library versions; CI on ubuntu (Python 3.11) with a secret scan.
