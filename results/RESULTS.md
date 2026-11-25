# Results

Synthetic data from `tsvlab.sim`. Rebuild with `make bench`. Means over seeds; ± is one standard error across seeds (8 per mode and split). Trade reporting delay 0.5 s unless a table says otherwise.

## Data (mean per session)

| split | mode | trades | volume | quotes | mean spread (ticks) | at the quote | inside, not at mid | at mid | informed trades | burst trades | high-vol time | episodes | bursts |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dev | informed | 59,223 | 13,158,275 | 52,978 | 1.76 | 0.863 | 0.052 | 0.085 | 0.102 | 0.030 | 0.325 | 4.25 | 3.25 |
| dev | control | 52,358 | 11,623,762 | 49,540 | 1.73 | 0.867 | 0.050 | 0.083 | 0.000 | 0.034 | 0.272 | 0.00 | 3.38 |
| holdout | informed | 58,669 | 13,038,025 | 52,775 | 1.77 | 0.860 | 0.054 | 0.086 | 0.083 | 0.029 | 0.372 | 4.00 | 3.00 |
| holdout | control | 52,797 | 11,749,388 | 49,969 | 1.75 | 0.865 | 0.051 | 0.084 | 0.000 | 0.031 | 0.307 | 0.00 | 2.75 |

## Trade-level accuracy by reporting delay (held-out, informed)

| delay (s) | tick rule | quote rule | Lee-Ready | EMO | quote rule unclassified |
|---|---|---|---|---|---|
| 0.0 | 0.826 ± 0.002 | 0.941 ± 0.001 | 0.940 ± 0.001 | 0.932 ± 0.001 | 0.086 ± 0.001 |
| 0.1 | 0.826 ± 0.002 | 0.886 ± 0.002 | 0.897 ± 0.002 | 0.894 ± 0.002 | 0.102 ± 0.001 |
| 0.25 | 0.826 ± 0.002 | 0.839 ± 0.002 | 0.860 ± 0.002 | 0.860 ± 0.002 | 0.114 ± 0.001 |
| 0.5 | 0.826 ± 0.002 | 0.800 ± 0.002 | 0.827 ± 0.002 | 0.832 ± 0.002 | 0.119 ± 0.000 |
| 1.0 | 0.826 ± 0.002 | 0.756 ± 0.003 | 0.785 ± 0.003 | 0.799 ± 0.002 | 0.115 ± 0.000 |
| 2.0 | 0.826 ± 0.002 | 0.706 ± 0.004 | 0.735 ± 0.004 | 0.767 ± 0.002 | 0.102 ± 0.001 |

## Trade-level accuracy by reporting delay (held-out, control)

| delay (s) | tick rule | quote rule | Lee-Ready | EMO | quote rule unclassified |
|---|---|---|---|---|---|
| 0.0 | 0.830 ± 0.002 | 0.943 ± 0.001 | 0.942 ± 0.001 | 0.935 ± 0.002 | 0.084 ± 0.001 |
| 0.1 | 0.830 ± 0.002 | 0.890 ± 0.002 | 0.902 ± 0.002 | 0.898 ± 0.002 | 0.100 ± 0.001 |
| 0.25 | 0.830 ± 0.002 | 0.843 ± 0.002 | 0.864 ± 0.002 | 0.864 ± 0.002 | 0.112 ± 0.001 |
| 0.5 | 0.830 ± 0.002 | 0.806 ± 0.002 | 0.832 ± 0.002 | 0.837 ± 0.002 | 0.118 ± 0.001 |
| 1.0 | 0.830 ± 0.002 | 0.764 ± 0.003 | 0.794 ± 0.004 | 0.806 ± 0.003 | 0.116 ± 0.001 |
| 2.0 | 0.830 ± 0.002 | 0.715 ± 0.004 | 0.745 ± 0.004 | 0.773 ± 0.002 | 0.104 ± 0.001 |

## Trade-level accuracy by condition (held-out, informed, delay 0.0 s)

| condition | share of trades | tick rule | quote rule | Lee-Ready | EMO |
|---|---|---|---|---|---|
| all trades | 1.000 | 0.826 ± 0.002 | 0.941 ± 0.001 | 0.940 ± 0.001 | 0.932 ± 0.001 |
| at the quote | 0.860 | 0.877 ± 0.001 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| inside the spread, not at the mid | 0.054 | 0.560 ± 0.005 | 0.700 ± 0.003 | 0.700 ± 0.003 | 0.560 ± 0.005 |
| at the midpoint | 0.086 | 0.486 ± 0.002 | 0.500 ± 0.000 | 0.486 ± 0.002 | 0.486 ± 0.002 |
| low-volatility regime | 0.564 | 0.844 ± 0.001 | 0.951 ± 0.000 | 0.951 ± 0.000 | 0.946 ± 0.000 |
| high-volatility regime | 0.436 | 0.802 ± 0.001 | 0.927 ± 0.001 | 0.925 ± 0.001 | 0.914 ± 0.001 |

## Trade-level accuracy by condition (held-out, informed, delay 0.5 s)

| condition | share of trades | tick rule | quote rule | Lee-Ready | EMO |
|---|---|---|---|---|---|
| all trades | 1.000 | 0.826 ± 0.002 | 0.800 ± 0.002 | 0.827 ± 0.002 | 0.832 ± 0.002 |
| at the quote | 0.860 | 0.877 ± 0.001 | 0.850 ± 0.002 | 0.881 ± 0.002 | 0.887 ± 0.001 |
| inside the spread, not at the mid | 0.054 | 0.560 ± 0.005 | 0.576 ± 0.002 | 0.584 ± 0.003 | 0.564 ± 0.004 |
| at the midpoint | 0.086 | 0.486 ± 0.002 | 0.443 ± 0.002 | 0.441 ± 0.002 | 0.454 ± 0.003 |
| low-volatility regime | 0.564 | 0.844 ± 0.001 | 0.822 ± 0.001 | 0.850 ± 0.001 | 0.852 ± 0.001 |
| high-volatility regime | 0.436 | 0.802 ± 0.001 | 0.772 ± 0.001 | 0.797 ± 0.001 | 0.805 ± 0.001 |

## Trade-level accuracy by condition (held-out, control, delay 0.0 s)

| condition | share of trades | tick rule | quote rule | Lee-Ready | EMO |
|---|---|---|---|---|---|
| all trades | 1.000 | 0.830 ± 0.002 | 0.943 ± 0.001 | 0.942 ± 0.001 | 0.935 ± 0.002 |
| at the quote | 0.865 | 0.879 ± 0.001 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| inside the spread, not at the mid | 0.051 | 0.562 ± 0.004 | 0.701 ± 0.004 | 0.701 ± 0.004 | 0.562 ± 0.004 |
| at the midpoint | 0.084 | 0.497 ± 0.003 | 0.500 ± 0.000 | 0.497 ± 0.003 | 0.497 ± 0.003 |
| low-volatility regime | 0.640 | 0.847 ± 0.001 | 0.951 ± 0.000 | 0.951 ± 0.000 | 0.947 ± 0.000 |
| high-volatility regime | 0.360 | 0.801 ± 0.002 | 0.928 ± 0.001 | 0.927 ± 0.001 | 0.916 ± 0.001 |

## Trade-level accuracy by condition (held-out, control, delay 0.5 s)

| condition | share of trades | tick rule | quote rule | Lee-Ready | EMO |
|---|---|---|---|---|---|
| all trades | 1.000 | 0.830 ± 0.002 | 0.806 ± 0.002 | 0.832 ± 0.002 | 0.837 ± 0.002 |
| at the quote | 0.865 | 0.879 ± 0.001 | 0.855 ± 0.001 | 0.885 ± 0.001 | 0.890 ± 0.001 |
| inside the spread, not at the mid | 0.051 | 0.562 ± 0.004 | 0.579 ± 0.002 | 0.588 ± 0.003 | 0.561 ± 0.003 |
| at the midpoint | 0.084 | 0.497 ± 0.003 | 0.438 ± 0.002 | 0.437 ± 0.003 | 0.452 ± 0.002 |
| low-volatility regime | 0.640 | 0.847 ± 0.001 | 0.824 ± 0.001 | 0.852 ± 0.001 | 0.854 ± 0.001 |
| high-volatility regime | 0.360 | 0.801 ± 0.002 | 0.774 ± 0.001 | 0.798 ± 0.001 | 0.806 ± 0.002 |

## Volume accuracy on volume bars (held-out, informed)

| shares per bar | bars scored per session | tick rule | quote rule | Lee-Ready | EMO | BVC | naive 50/50 |
|---|---|---|---|---|---|---|---|
| 2,000 | 6469 | 0.862 ± 0.001 | 0.863 ± 0.002 | 0.872 ± 0.002 | 0.878 ± 0.001 | 0.732 ± 0.001 | 0.825 ± 0.002 |
| 10,000 | 1253 | 0.915 ± 0.001 | 0.926 ± 0.001 | 0.927 ± 0.001 | 0.929 ± 0.001 | 0.753 ± 0.001 | 0.899 ± 0.003 |
| 50,000 | 210 | 0.941 ± 0.002 | 0.959 ± 0.002 | 0.959 ± 0.002 | 0.956 ± 0.002 | 0.765 ± 0.003 | 0.924 ± 0.004 |

## Volume accuracy on volume bars (held-out, control)

| shares per bar | bars scored per session | tick rule | quote rule | Lee-Ready | EMO | BVC | naive 50/50 |
|---|---|---|---|---|---|---|---|
| 2,000 | 5824 | 0.866 ± 0.002 | 0.869 ± 0.002 | 0.878 ± 0.002 | 0.883 ± 0.001 | 0.736 ± 0.001 | 0.834 ± 0.001 |
| 10,000 | 1124 | 0.924 ± 0.001 | 0.932 ± 0.001 | 0.934 ± 0.001 | 0.936 ± 0.001 | 0.758 ± 0.002 | 0.918 ± 0.002 |
| 50,000 | 184 | 0.959 ± 0.002 | 0.966 ± 0.001 | 0.966 ± 0.001 | 0.966 ± 0.002 | 0.763 ± 0.005 | 0.954 ± 0.003 |

## BVC and how much price moves come from order flow (held-out informed seeds)

Efficient-price noise scaled by the factor below (1.0 is the base simulator). 10,000-share bars; OFI correlation is the 5-minute imbalance against the true-sign version.

| noise scale | bar accuracy: tick | Lee-Ready | BVC | naive 50/50 | OFI corr: tick | Lee-Ready | BVC |
|---|---|---|---|---|---|---|---|
| 0.0 | 0.928 ± 0.001 | 0.943 ± 0.001 | 0.767 ± 0.001 | 0.899 ± 0.003 | 0.890 ± 0.014 | 0.960 ± 0.006 | 0.612 ± 0.040 |
| 0.25 | 0.925 ± 0.001 | 0.941 ± 0.001 | 0.764 ± 0.001 | 0.899 ± 0.003 | 0.871 ± 0.012 | 0.956 ± 0.005 | 0.509 ± 0.044 |
| 0.5 | 0.923 ± 0.001 | 0.937 ± 0.001 | 0.759 ± 0.001 | 0.899 ± 0.003 | 0.856 ± 0.010 | 0.953 ± 0.004 | 0.373 ± 0.052 |
| 1.0 | 0.915 ± 0.001 | 0.927 ± 0.001 | 0.753 ± 0.001 | 0.899 ± 0.003 | 0.794 ± 0.014 | 0.927 ± 0.009 | 0.225 ± 0.055 |

## VPIN settings chosen on development seeds

Bucket volume = development mean session volume (12,391,019 shares) / buckets per session, rounded to 100 shares. Criterion: mean correlation of VPIN with the planted informed share on a 1-minute grid. Threshold: 90% quantile of VPIN on the development control seeds (1-minute grid).

| signing | buckets per session | shares per bucket | window (buckets) | dev correlation | alarm threshold |
|---|---|---|---|---|---|
| true signs | 400 | 31,000 | 5 | 0.702 | 0.166 |
| tick rule | 100 | 123,900 | 2 | 0.490 | 0.082 |
| quote rule | 400 | 31,000 | 10 | 0.575 | 0.124 |
| Lee-Ready | 200 | 62,000 | 2 | 0.584 | 0.123 |
| EMO | 100 | 123,900 | 2 | 0.561 | 0.096 |
| BVC | 50 | 247,800 | 2 | 0.209 | 0.694 |

Development correlation grid (rows: buckets per session; columns: window):

true signs:

| buckets \ window | 1 | 2 | 5 | 10 | 25 | 50 |
|---|---|---|---|---|---|---|
| 50 | 0.566 | 0.474 | 0.165 | 0.096 | n/a | n/a |
| 100 | 0.657 | 0.634 | 0.489 | 0.227 | 0.071 | n/a |
| 200 | 0.678 | 0.692 | 0.646 | 0.524 | 0.175 | 0.090 |
| 400 | 0.629 | 0.687 | 0.702 | 0.663 | 0.480 | 0.194 |
| 800 | 0.514 | 0.605 | 0.679 | 0.697 | 0.641 | 0.493 |
| 1600 | 0.358 | 0.475 | 0.592 | 0.652 | 0.675 | 0.628 |

tick rule:

| buckets \ window | 1 | 2 | 5 | 10 | 25 | 50 |
|---|---|---|---|---|---|---|
| 50 | 0.433 | 0.383 | 0.143 | 0.081 | n/a | n/a |
| 100 | 0.448 | 0.490 | 0.415 | 0.210 | 0.081 | n/a |
| 200 | 0.331 | 0.405 | 0.446 | 0.391 | 0.165 | 0.089 |
| 400 | 0.248 | 0.309 | 0.409 | 0.440 | 0.369 | 0.183 |
| 800 | 0.144 | 0.204 | 0.298 | 0.374 | 0.418 | 0.348 |
| 1600 | 0.088 | 0.116 | 0.183 | 0.239 | 0.310 | 0.308 |

quote rule:

| buckets \ window | 1 | 2 | 5 | 10 | 25 | 50 |
|---|---|---|---|---|---|---|
| 50 | 0.500 | 0.424 | 0.117 | 0.068 | n/a | n/a |
| 100 | 0.565 | 0.564 | 0.441 | 0.193 | 0.031 | n/a |
| 200 | 0.525 | 0.574 | 0.566 | 0.467 | 0.143 | 0.066 |
| 400 | 0.406 | 0.500 | 0.572 | 0.575 | 0.421 | 0.180 |
| 800 | 0.286 | 0.373 | 0.489 | 0.557 | 0.560 | 0.428 |
| 1600 | 0.150 | 0.225 | 0.345 | 0.445 | 0.527 | 0.533 |

Lee-Ready:

| buckets \ window | 1 | 2 | 5 | 10 | 25 | 50 |
|---|---|---|---|---|---|---|
| 50 | 0.506 | 0.421 | 0.105 | 0.058 | n/a | n/a |
| 100 | 0.574 | 0.575 | 0.446 | 0.196 | 0.040 | n/a |
| 200 | 0.529 | 0.584 | 0.578 | 0.472 | 0.139 | 0.077 |
| 400 | 0.410 | 0.503 | 0.583 | 0.583 | 0.430 | 0.180 |
| 800 | 0.272 | 0.363 | 0.483 | 0.558 | 0.560 | 0.441 |
| 1600 | 0.142 | 0.235 | 0.340 | 0.443 | 0.526 | 0.519 |

EMO:

| buckets \ window | 1 | 2 | 5 | 10 | 25 | 50 |
|---|---|---|---|---|---|---|
| 50 | 0.499 | 0.416 | 0.114 | 0.075 | n/a | n/a |
| 100 | 0.555 | 0.561 | 0.436 | 0.195 | 0.044 | n/a |
| 200 | 0.499 | 0.558 | 0.560 | 0.458 | 0.140 | 0.076 |
| 400 | 0.380 | 0.474 | 0.560 | 0.559 | 0.419 | 0.178 |
| 800 | 0.247 | 0.322 | 0.448 | 0.527 | 0.535 | 0.438 |
| 1600 | 0.147 | 0.214 | 0.311 | 0.404 | 0.494 | 0.493 |

BVC:

| buckets \ window | 1 | 2 | 5 | 10 | 25 | 50 |
|---|---|---|---|---|---|---|
| 50 | 0.204 | 0.209 | 0.067 | -0.156 | n/a | n/a |
| 100 | 0.164 | 0.189 | 0.173 | 0.075 | -0.134 | n/a |
| 200 | 0.081 | 0.109 | 0.130 | 0.124 | 0.092 | -0.095 |
| 400 | 0.011 | 0.025 | 0.027 | 0.029 | 0.050 | 0.051 |
| 800 | 0.019 | 0.007 | 0.006 | -0.005 | -0.029 | -0.082 |
| 1600 | -0.044 | -0.024 | -0.011 | -0.005 | -0.005 | 0.008 |

## VPIN on held-out seeds (run once)

| signing | corr with planted share | peak lag (min) | corr at peak | corr with the share 10 min later | corr with the share 10 min earlier | episodes detected | median delay (min) | placebo windows flagged (control) | alarm share in episodes | alarm share, informed mode away from episodes | alarm share, control | control: in bursts | control: no burst |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| true signs | 0.679 ± 0.056 | 3 | 0.731 | 0.262 | 0.433 | 32/32 | 2.2 | 10/29 | 76.9% | 9.6% | 9.8% | 31.8% | 0.9% |
| tick rule | 0.420 ± 0.062 | 5 | 0.527 | 0.100 | 0.430 | 29/32 | 4.4 | 9/29 | 49.1% | 7.7% | 8.8% | 21.7% | 3.6% |
| quote rule | 0.567 ± 0.057 | 5 | 0.671 | 0.158 | 0.566 | 31/32 | 4.3 | 10/29 | 65.2% | 8.0% | 10.5% | 28.7% | 2.1% |
| Lee-Ready | 0.560 ± 0.050 | 3 | 0.634 | 0.211 | 0.403 | 32/32 | 3.5 | 17/29 | 60.4% | 8.9% | 9.5% | 23.0% | 3.7% |
| EMO | 0.577 ± 0.043 | 5 | 0.699 | 0.131 | 0.571 | 31/32 | 4.5 | 9/29 | 66.0% | 8.7% | 9.4% | 26.7% | 1.7% |
| BVC | 0.115 ± 0.054 | -8 | 0.131 | 0.126 | 0.017 | 11/32 | 0.7 | 10/29 | 10.5% | 8.5% | 14.3% | 13.0% | 13.8% |

False alarm spells per session (alarm onsets away from informed episodes):

| signing | informed mode | control |
|---|---|---|
| true signs | 2.25 ± 0.37 | 4.38 ± 0.46 |
| tick rule | 2.50 ± 0.53 | 4.38 ± 0.71 |
| quote rule | 2.50 ± 0.80 | 6.12 ± 0.67 |
| Lee-Ready | 4.50 ± 1.00 | 9.00 ± 0.80 |
| EMO | 1.88 ± 0.35 | 3.62 ± 0.32 |
| BVC | 1.38 ± 0.42 | 3.50 ± 0.42 |

Mean VPIN around the start of held-out informed episodes (minutes from start):

| signing | threshold | -30 | -15 | -5 | +0 | +5 | +10 | +15 | +20 | +30 | +45 | +60 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| true signs | 0.166 | 0.146 | 0.107 | 0.103 | 0.114 | 0.267 | 0.280 | 0.257 | 0.232 | 0.148 | 0.116 | 0.143 |
| tick rule | 0.082 | 0.064 | 0.056 | 0.049 | 0.043 | 0.075 | 0.097 | 0.088 | 0.084 | 0.071 | 0.050 | 0.053 |
| quote rule | 0.124 | 0.114 | 0.096 | 0.092 | 0.097 | 0.131 | 0.161 | 0.166 | 0.157 | 0.131 | 0.092 | 0.109 |
| Lee-Ready | 0.123 | 0.100 | 0.068 | 0.074 | 0.081 | 0.164 | 0.160 | 0.162 | 0.134 | 0.093 | 0.073 | 0.093 |
| EMO | 0.096 | 0.083 | 0.052 | 0.044 | 0.051 | 0.090 | 0.144 | 0.146 | 0.137 | 0.092 | 0.055 | 0.072 |
| BVC | 0.694 | 0.360 | 0.336 | 0.388 | 0.410 | 0.453 | 0.417 | 0.394 | 0.324 | 0.335 | 0.394 | 0.421 |

## Order-flow imbalance features (held-out, informed)

Trailing 5-minute imbalance (B - S) / (B + S) on 1-minute bars; forward return = quote-midpoint change over the next 5 minutes.

| signing | corr with true-sign OFI | mean abs error | corr with forward return |
|---|---|---|---|
| true signs | 1.000 ± 0.000 | 0.000 ± 0.000 | 0.069 ± 0.042 |
| tick rule | 0.794 ± 0.014 | 0.085 ± 0.004 | 0.058 ± 0.037 |
| quote rule | 0.926 ± 0.008 | 0.059 ± 0.003 | 0.053 ± 0.042 |
| Lee-Ready | 0.927 ± 0.009 | 0.057 ± 0.003 | 0.061 ± 0.041 |
| EMO | 0.920 ± 0.008 | 0.063 ± 0.003 | 0.066 ± 0.038 |
| BVC | 0.225 ± 0.055 | 0.211 ± 0.006 | 0.055 ± 0.035 |

## Order-flow imbalance features (held-out, control)

Trailing 5-minute imbalance (B - S) / (B + S) on 1-minute bars; forward return = quote-midpoint change over the next 5 minutes.

| signing | corr with true-sign OFI | mean abs error | corr with forward return |
|---|---|---|---|
| true signs | 1.000 ± 0.000 | 0.000 ± 0.000 | -0.106 ± 0.050 |
| tick rule | 0.605 ± 0.035 | 0.053 ± 0.003 | -0.057 ± 0.063 |
| quote rule | 0.823 ± 0.029 | 0.039 ± 0.002 | -0.060 ± 0.038 |
| Lee-Ready | 0.808 ± 0.033 | 0.040 ± 0.002 | -0.061 ± 0.039 |
| EMO | 0.789 ± 0.029 | 0.043 ± 0.002 | -0.056 ± 0.046 |
| BVC | 0.022 ± 0.043 | 0.203 ± 0.004 | -0.047 ± 0.020 |
