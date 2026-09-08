# Evaluation: XAUUSD (1d)

**Period:** 2024-09-09 -> 2026-09-08
**Capital:** $100,000  |  **Risk/Trade:** 1.0%

## Ranking theo Sharpe

| # | Strategy | Sharpe | Sortino | Max DD % | Win Rate | Profit Factor | Avg R | Trades |
|---|----------|-------:|--------:|---------:|---------:|--------------:|------:|-------:|
| 1 | `10-donchian-channel-breakout` | 1.11 | 0.66 | 2.1 | 59.1% | 2.12 | 0.48 | 22 |
| 2 | `01-ema-20-50-crossover` | 0.99 | 133.56 | 0.0 | 100.0% | 99.99 | 2.00 | 2 |
| 3 | `02-breakout-plus-volume` | 0.73 | 0.29 | 1.2 | 57.1% | 2.62 | 0.71 | 7 |
| 4 | `06-bollinger-squeeze-breakout` | 0.70 | 0.00 | 0.0 | 100.0% | 99.99 | 2.00 | 1 |
| 5 | `08-macd-ema200-trend-filter` | 0.62 | 0.23 | 2.6 | 50.0% | 2.29 | 0.58 | 6 |
| 6 | `04-ema20-pullback` | 0.60 | 0.28 | 2.3 | 45.5% | 1.97 | 0.45 | 11 |
| 7 | `07-vwap-pullback` | 0.33 | 0.15 | 3.4 | 46.2% | 1.52 | 0.24 | 13 |
| 8 | `03-breakout-retest` | 0.00 | 0.00 | 0.0 | 0.0% | 0.00 | 0.00 | 0 |
| 9 | `09-opening-range-breakout` | 0.00 | 0.00 | 0.0 | 0.0% | 0.00 | 0.00 | 0 |
| 10 | `05-rsi-bollinger-mean-reversion` | -1.25 | -0.18 | 3.1 | 0.0% | 0.00 | -1.00 | 3 |

## Top 3 chi tiết

### `10-donchian-channel-breakout`

- Params: `{'lookback': 20, 'atr_n': 14, 'atr_sl': 2.0, 'atr_tp': 3.0}`
- Total return: **9.93%**
- Sharpe: 1.113
- Max drawdown: 2.12%
- Win rate: 59.1%
- Profit factor: 2.12
- Avg R-multiple: 0.48
- Trades: 22 (13W / 9L)

### `01-ema-20-50-crossover`

- Params: `{'fast_len': 20, 'slow_len': 50, 'rr': 2.0, 'swing': 5}`
- Total return: **3.95%**
- Sharpe: 0.991
- Max drawdown: 0.02%
- Win rate: 100.0%
- Profit factor: 99.99
- Avg R-multiple: 2.00
- Trades: 2 (2W / 0L)

### `02-breakout-plus-volume`

- Params: `{'lookback': 20, 'vol_mult': 1.5, 'rr': 2.0}`
- Total return: **4.45%**
- Sharpe: 0.728
- Max drawdown: 1.23%
- Win rate: 57.1%
- Profit factor: 2.62
- Avg R-multiple: 0.71
- Trades: 7 (4W / 3L)
