# Methodology

The rules behind every number in the README, what was decided where, and the papers the methods come from.

## Seeds

| mode | development seeds (all choices) | held-out seeds (scored once) |
|---|---|---|
| informed | 1-8 | 1001-1008 |
| control | 101-108 | 2001-2008 |

Each seed is one independent session of 6.5 hours (23,400 s). No seed appears twice (a test checks this).

## The simulator

All prices are integer ticks, so "the price equals the ask" is an exact comparison.

**Arrivals.** The session is cut into segments where every rate is constant (regime switches, episode and burst boundaries). In each segment, four Poisson streams:

| stream | rate | side |
|---|---|---|
| uninformed buyers | eps = 1.0 /s (x1.3 in high volatility) | buy |
| uninformed sellers | eps | sell |
| informed traders (informed mode, during an episode) | mu = alpha / (1 - alpha) x 2 eps | the episode's side |
| burst traders (during a burst) | share / (1 - share) x 2 eps | the burst's side |

This is the arrival structure of the PIN model (Easley, Kiefer, O'Hara and Paperman 1996): uninformed traders on both sides, informed traders on one side when there is information. Each session has 3 to 5 episodes of 15 to 35 minutes with alpha drawn from 15% to 40%, and 2 to 4 bursts of 5 to 20 minutes with a share of 15% to 35%. Neither starts in the first 30 minutes, and episodes (or bursts) are at least 10 minutes apart. Bursts and episodes may overlap. Trade size = 100 x Geometric(0.45) shares for every trader.

**Planted informed share** at time t = informed rate / total rate in the segment containing t. This is what VPIN is judged against.

**Efficient price.** A random walk in ticks with volatility 0.4 (low regime) or 1.0 (high regime) ticks per square-root second; regimes alternate with exponential durations, mean 40 and 20 minutes. During an informed episode the efficient price also drifts linearly by 15 to 40 ticks in the informed direction. Bursts do not move it.

**Dealer quotes.** Quotes are centred on V + L, where L is a temporary flow pressure: each trade adds 0.12 ticks in its direction, and L decays with a 40 s half-life. The spread is 1, 2 or 3 ticks (probabilities 0.55 / 0.30 / 0.15 in low volatility, 0.30 / 0.40 / 0.30 in high). Quotes update at Poisson times (1 per second) and, with probability 0.5, after each trade with a lag of 20 ms plus an exponential with mean 150 ms. This is the mechanism that makes a late trade report dangerous: the quote a late report is matched to has often already moved in the direction of that trade, in the spirit of a dealer updating on order flow (Glosten and Milgrom 1985).

**Execution.** A trade executes against the quote in force just before it. If the spread is 2 or 3 ticks, with probability 0.25 it prints inside: at the mid for a 2-tick spread; for a 3-tick spread on one of the two inside ticks, on the initiator's half with probability 0.7. Otherwise a buyer pays the ask and a seller hits the bid.

**Control mode.** With the same seed, the control places the same regimes, episode windows, bursts and uninformed arrival times as the informed mode (a test checks the arrival times are identical); the informed traders and their price drift are left out, and later random draws differ because the trade count differs. The episode windows are kept as placebo windows. The benchmark uses different seeds for the two modes, so each control session places its own windows exactly as an informed session would (29 windows over the held-out control seeds, against 32 episodes in the held-out informed seeds) and nobody informed trades in them.

**Reporting delay.** Trade reports are stamped `d x U(0.5, 1.5)` seconds late, then a running maximum keeps the feed in its original order. Quotes are stamped correctly. The delay re-stamps the same session, so every delay in the accuracy table sees exactly the same trades. The default delay for everything except the delay table is 0.5 s.

## Signing rules

Every rule sees only what a desk sees: trade prices in feed order, reported trade times, and quotes. A trade is matched to the last quote stamped at or before its reported time.

| rule | buy if | sell if | otherwise | reference |
|---|---|---|---|---|
| tick | price above the last different price | below | unclassified (only the first trade of the session) | Lee and Ready 1991 discuss it as the fallback |
| quote | price above the quote midpoint | below | unclassified (at the mid) | |
| Lee-Ready | quote rule | quote rule | tick rule at the mid | Lee and Ready 1991 |
| EMO | price equals the ask | equals the bid | tick rule | Ellis, Michaely and O'Hara 2000 |
| BVC | bar buy share = Φ(ΔP / σ) | | | Easley, López de Prado and O'Hara 2012, 2016 |

Lee and Ready also suggested matching a trade with an earlier quote (5 seconds before its reported time, for the reporting delays of their data). A desk that knows its typical delay could do the same; that variant is not implemented or tested here, so the delay table shows the uncorrected cost of a delay, not the best a desk could do.

For BVC, ΔP is the change in the last trade price from the previous bar and σ the standard deviation of the previous 50 bar changes (60 for the 1-minute imbalance bars; at least 10 needed; before that the buy share is 0.5). It is applied to the volume buckets themselves for VPIN, to volume bars for the bar-accuracy table, and to 1-minute bars for the imbalance features. Easley, López de Prado and O'Hara apply BVC to 1-minute time bars that are then aggregated into volume buckets, and later work uses a Student-t CDF; Chakrabarty, Pascual and Shkilko (2015) compare BVC with the tick rule and Lee-Ready on real data and find the comparison depends on the bar size and the market.

## Accuracy

- **Trade level:** share of trades where the rule's sign equals the true side, with an unclassified trade counting as half right (its expected value under a coin flip). The quote rule's unclassified share is reported separately.
- **Condition masks** use the true prevailing quote: at the quote (price equals bid or ask), at the mid, inside the spread off the mid; and the true volatility regime at the trade.
- **Bar level:** for each bar, min(estimated buy volume, true buy volume) + min(estimated sell volume, true sell volume), summed over bars and divided by total volume (the measure used by Chakrabarty, Pascual and Shkilko 2015). The first 50 bars of each session are left out (BVC warm-up). Because errors net out inside a bar, this measure is always reported next to a naive 50/50 split, which needs no signing at all.

## VPIN

VPIN at bucket τ = (1/n) Σ over buckets τ-n+1..τ of |B - S| / V, where V is the bucket volume (Easley, López de Prado and O'Hara 2012). Buckets close every V shares; a trade crossing a boundary is split, and its buy share (1, 0, or 0.5 if unclassified) is split with it, by interpolating running buy volume against running volume. A test compares this against a share-by-share brute force.

To compare VPIN with the planted share on equal footing for every setting, both are sampled on a 1-minute clock grid: VPIN at minute t is the value of the last bucket closed (by reported time) at or before t.

### What was chosen on development seeds

| choice | rule | where in the results |
|---|---|---|
| bucket volume grid | development mean session volume / {50, 100, 200, 400, 800, 1600}, rounded to 100 shares | `vpin.json` -> `bucket_volume` |
| window grid | {1, 2, 5, 10, 25, 50} buckets, only where the window is at most a quarter of a session's buckets | `vpin.json` -> `grid_combos` |
| setting per signing method | the grid cell with the highest mean correlation with the planted share over development informed seeds | `vpin.json` -> `selected`, `grid` |
| alarm threshold per method | 90th percentile of that method's VPIN on the 1-minute grid, pooled over development control seeds | `vpin.json` -> `thresholds` |

Each method gets its own best setting, so the held-out comparison is between each method at its best, not at one shared setting.

### What is measured on held-out seeds

| measure | definition | field in `vpin.json` -> `holdout.<method>` |
|---|---|---|
| correlation with planted share | Pearson on the 1-minute grid, per session, mean and standard error across 8 sessions | `corr_alpha` |
| lead/lag | corr(VPIN at t, share at t - k) for k from -30 to +30 minutes, averaged over sessions; k > 0 means VPIN follows | `lead_lag` |
| detection | an episode is detected if any alarm minute falls inside it; delay = first alarm minute - start, so an episode already in alarm at its start counts with a delay under one minute (`already_alarm_at_start`: 4 to 7 of 32 per method, 6 of BVC's 11 detections) | `episodes` |
| placebo | the same rule on the control sessions' placebo windows | `placebo_episodes` |
| alarm share | share of valid minutes in alarm: inside episodes; in informed mode away from episodes (episode + 30 min excluded); in the control overall, during bursts (+ 30 min) and outside them | `informed_alarm_share_*`, `control_alarm_share*` |
| false alarm spells | alarm onsets away from informed episodes, per session | `*_false_spells_per_session` |
| event profile | mean VPIN at fixed offsets from each episode start | `event_profile` |

## Order-flow imbalance features

1-minute bars by reported trade time, for every method including the truth, so the only difference between columns is the signing. Feature = (B - S) / (B + S) over the trailing 5 bars. Forward return = change in the quote midpoint over the next 5 minutes, using quotes only (stamped correctly). The first 30 bars are dropped (BVC warm-up). This is a trade-flow imbalance; the book-event OFI of Cont, Kukanov and Stoikov (2014) is in the companion repo.

## Leakage controls

| risk | control | where it is tested |
|---|---|---|
| a rule using information a desk does not have | rules get trade prices, reported times and quotes only; true sides, trader types and the efficient price are used for scoring only | `signing.py` signatures |
| BVC's σ using the bar it classifies | σ from the previous 50 bars only (60 for the 1-minute imbalance bars) | `test_trailing_std_matches_brute_force_and_excludes_current`, `test_bvc_point_in_time_and_direction` |
| VPIN or features reading the future | deleting every trade and quote after a cut leaves all earlier VPIN values and features unchanged | `test_vpin_is_point_in_time`, `test_ofi_truth_matches_itself_and_features_are_trailing` |
| settings fitted on test data | bucket size, window and threshold come from development seeds only | `bench.vpin_section`; `test_small_bench_end_to_end` checks the selected cell is the best development cell |
| the threshold tuned to the held-out control | threshold from development control seeds; the held-out control's alarm share (8.8% to 10.5% for trade-level rules, 14.3% for BVC) is an out-of-sample check of the nominal 10% | `vpin.json` -> `holdout.<method>.control_alarm_share` |
| chance detection read as skill | placebo windows in the control | `placebo_episodes` |

## History of the choices (honest account)

Everything below happened on development seeds, before the held-out seeds were run.

1. The simulator's parameters (rates, volatility, spreads, impact, reaction lag, inside-print probabilities) were set by looking at development sessions only, to give realistic-looking spreads, a mix of at-quote and inside prints, and informed episodes that move the price.
2. The first VPIN selection criterion was correlation with the planted share at bucket close, over windows {5, 10, 25, 50, 100} and buckets {100, ..., 1600}. Two problems showed up on development seeds: some cells had almost no valid VPIN values (a window as long as the session), and every method's best cell sat on the smallest window. I then (a) restricted windows to at most a quarter of a session, (b) added windows of 1 and 2 and 50 buckets per session, and (c) switched to correlation on a common 1-minute grid, so that settings with fewer, larger buckets are compared on the same points rather than on their own bucket times. After that the best cells for all trade-level methods are inside the grid.
3. Looking at the alarm results on development seeds, I added the placebo windows, because "episode detected" without a chance rate is not interpretable.
4. The held-out seeds were then run once (`make bench`). After that run, only the renderer and the docs changed: column labels, the order of rows in `RESULTS.md`, a placebo column that the first render left out, and, after an independent review, more label and wording fixes. No number in the JSON changed, and the full rerun in the tests reproduces it.

For the quote rule, Lee-Ready and EMO the best two development cells are within 0.0006 of each other, so the pick between them is effectively a tie; read their held-out results as "a setting near the top of the grid", not "the best setting".

BVC's development choice is on the edge of the grid (50 buckets a session, the largest buckets). Its development correlation is below 0.21 everywhere in the grid, so I did not widen it.

## References

- Andersen, T. G., and Bondarenko, O. (2014). VPIN and the flash crash. *Journal of Financial Markets*, 17, 1-46.
- Chakrabarty, B., Pascual, R., and Shkilko, A. (2015). Evaluating trade classification algorithms: Bulk volume classification versus the tick rule and the Lee-Ready algorithm. *Journal of Financial Markets*, 25, 52-79.
- Cont, R., Kukanov, A., and Stoikov, S. (2014). The price impact of order book events. *Journal of Financial Econometrics*, 12(1), 47-88.
- Easley, D., Kiefer, N. M., O'Hara, M., and Paperman, J. B. (1996). Liquidity, information, and infrequently traded stocks. *Journal of Finance*, 51(4), 1405-1436.
- Easley, D., López de Prado, M. M., and O'Hara, M. (2012). Flow toxicity and liquidity in a high-frequency world. *Review of Financial Studies*, 25(5), 1457-1493.
- Easley, D., López de Prado, M., and O'Hara, M. (2016). Discerning information from trade data. *Journal of Financial Economics*, 120(2), 269-285.
- Ellis, K., Michaely, R., and O'Hara, M. (2000). The accuracy of trade classification rules: Evidence from Nasdaq. *Journal of Financial and Quantitative Analysis*, 35(4), 529-551.
- Glosten, L. R., and Milgrom, P. R. (1985). Bid, ask and transaction prices in a specialist market with heterogeneously informed traders. *Journal of Financial Economics*, 14(1), 71-100.
- Lee, C. M. C., and Ready, M. J. (1991). Inferring trade direction from intraday data. *Journal of Finance*, 46(2), 733-746.

Andersen and Bondarenko (2014) question VPIN's reported early warning before the May 2010 flash crash, finding that its behaviour is driven largely by trading volume and by the bulk classification step rather than by information. The lag, burst and BVC results here point the same way, in a setting where the truth is known.
