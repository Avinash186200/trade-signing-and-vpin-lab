# Walkthrough

From one simulated session to the full benchmark. Every output below is real output from the commands shown (Python 3.11, versions in `constraints.txt`). Seed 1 is a development seed, so nothing here touches the held-out seeds.

## 1. Install and test

```bash
python -m venv .venv && source .venv/bin/activate
pip install -c constraints.txt -e ".[dev]"
pytest -q
```

The test suite includes a full rerun of the benchmark compared against the committed `results/*.json`, so a green run means the numbers in the README rebuild on your machine.

## 2. Look at one session

```bash
tsvlab simulate --mode informed --seed 1 --out data
```

```
60108 trades, 53566 quotes, 5 informed episodes, 4 uninformed bursts -> data
```

`data/trades_informed_1.csv` has one row per trade:

```
t_true,t_reported,price_ticks,size,true_side,trader_kind,bid_at_trade,ask_at_trade,vol_regime,tick,quote,lee_ready,emo
0.247330,0.677169,5000,300,1,0,4999,5001,0,0,-1,-1,-1
0.806349,1.364622,5000,200,-1,0,5000,5002,0,0,-1,-1,-1
0.970309,1.542700,5000,200,-1,0,4999,5002,0,0,-1,-1,-1
```

- `true_side` is the truth (+1 buyer, -1 seller); `trader_kind` is 0 uninformed, 1 informed, 2 burst.
- `bid_at_trade` and `ask_at_trade` are the quote the trade really executed against. The signing columns (`tick`, `quote`, `lee_ready`, `emo`) only saw `t_reported`, which is late (0.5 s on average by default, `--delay` to change it).
- The very first row already shows the problem the lab is about. A buyer traded at 5000, inside a 4999/5001 spread, right at the mid. The report arrived 0.43 s later, by which time the quote had moved; matched to the newer quote, the price looked low, and the quote rule, Lee-Ready and EMO all called it a sell. The tick rule has no previous price yet and leaves it unclassified (0).

`data/quotes_informed_1.csv` has every quote update (`t,bid_ticks,ask_ticks`), stamped correctly.

## 3. Sign a session at different delays

```python
from tsvlab.sim import SimConfig, simulate
from tsvlab import analysis as A

s = simulate(SimConfig(), seed=1)
for d in (0.0, 0.5, 2.0):
    ob = A.observe(s, delay=d)
    print(d, {m: round(A.trade_accuracy(ob.signs[m], s.side)["accuracy"], 3) for m in ob.signs})
```

```
0.0 {'tick': 0.835, 'quote': 0.944, 'lee_ready': 0.943, 'emo': 0.937}
0.5 {'tick': 0.835, 'quote': 0.809, 'lee_ready': 0.837, 'emo': 0.84}
2.0 {'tick': 0.835, 'quote': 0.721, 'lee_ready': 0.752, 'emo': 0.779}
```

Same trades every time; only the report timestamps move. The tick rule does not change because it never looks at quotes.

## 4. VPIN against the planted informed share

```python
ob = A.observe(s, delay=0.5)
ser = A.vpin_series(s, ob, bucket_volume=62_000, windows=(2,))
print({m: round(A.vpin_alpha_corr(s, ser, m, 2), 3) for m in A.VPIN_METHODS})
```

```
{'truth': 0.688, 'tick': 0.378, 'quote': 0.567, 'lee_ready': 0.56, 'emo': 0.542, 'bvc': 0.023}
```

`vpin_series` builds 62,000-share buckets (splitting trades at the boundaries), computes each method's buy volume per bucket, and VPIN over a 2-bucket window. `vpin_alpha_corr` samples VPIN and the planted share on a 1-minute grid and correlates them. This is one session at one setting; the benchmark chooses each method's setting on 8 development sessions and reports 8 held-out ones.

## 5. The full benchmark

```bash
make bench     # same as: python -m tsvlab.cli bench --out results
```

It simulates 32 sessions, then:

1. **Development seeds:** builds the bucket-volume grid from their mean volume, scores every (bucket size, window) cell for each signing method, keeps the best, and sets each method's alarm threshold at the 90th percentile of its VPIN on the development control sessions. `python -m tsvlab.cli bench --dev-only --out somewhere` stops here and never touches the held-out seeds.
2. **Held-out seeds:** applies those settings once and writes VPIN correlations, lead/lag curves, detection against placebo windows, false alarms, the accuracy tables and the imbalance features.

Outputs: `results/data.json`, `accuracy.json`, `vpin.json`, `ofi.json`, and `RESULTS.md` rendered from them (`tsvlab report` re-renders without re-running).

## 6. Reading the results

- **Accuracy tables:** compare each rule at 0 s with the same rule at 0.5 s. The size of that drop is what a desk should check on its own feed: how far apart are trade and quote timestamps, really?
- **Bar accuracy:** always read against the naive 50/50 column.
- **VPIN table:** read "episodes detected" against "placebo windows flagged", and the alarm share in the control against the burst split. A VPIN that fires on bursts as often as on episodes is a one-sided-volume meter, which is what it is here.
- **Imbalance features:** the first column (correlation with the true-sign feature) is the cost of signing error; the forward-return column is too noisy at 8 seeds to rank methods.

## 7. Changing the simulator

`SimConfig` holds every parameter (see `sim.py`). For example, a market where the dealer re-quotes slowly:

```python
from dataclasses import replace
cfg = replace(SimConfig(), react_prob=0.2, react_lag_mean=1.0)
```

If you change anything that feeds the committed results, rerun `make bench` and commit the new JSON; the tests fail otherwise. If you change a choice that was made on development seeds, follow the rule in CONTRIBUTING.md and draw fresh held-out seeds.
