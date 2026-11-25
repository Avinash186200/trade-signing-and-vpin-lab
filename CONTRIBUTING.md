# Contributing

Thanks for taking a look. Changes are judged on whether they keep the repo offline, point-in-time and honest about its numbers.

## Ground rules

1. **Everything in CI runs offline and on CPU.** Tests and `make bench` need no network and no GPU.
2. **Numbers come from results.** Any number in a doc must be in a `results/*.json` file written by `make bench`. If you change code that affects results, rerun `make bench` and commit the new JSON and `RESULTS.md` with the change. CI fails if the committed JSON does not match a fresh run.
3. **Never tune on the held-out seeds.** Bucket sizes, windows, thresholds and simulator parameters are chosen on the development seeds (`make bench-dev` runs only those). If a change needs a new choice, make it on development seeds, then draw fresh held-out seeds and say so in `docs/methodology.md`.
4. **Signing rules see only what a desk sees.** Trade prices in feed order, reported times and quotes. True sides, trader types and the efficient price are for scoring only.
5. **Point in time only.** VPIN, BVC and features may use data up to the current bucket or bar. Keep the truncation tests (`test_vpin_is_point_in_time`, `test_ofi_truth_matches_itself_and_features_are_trailing`) passing.
6. **No timing assertions in tests.** Tests check correctness, never speed.
7. **Seeds stay fixed.** Every generator takes a seed.
8. **No secrets.** Nothing here needs credentials; `.env` is git-ignored and CI runs a secret scan.

## Set up

```bash
python -m venv .venv && source .venv/bin/activate
pip install -c constraints.txt -e ".[dev]"
pytest -q
```

## Adding a signing rule

1. Add it to `signing.py` and to `TRADE_METHODS` (trade level) or next to BVC (bar level), with a hand-worked test in `tests/test_signing.py`.
2. Rerun `make bench` and update the docs from the new JSON.
