# Evaluation: BTCUSD (1d)

**Period:** 2024-09-08 -> 2026-09-08
**Capital:** $100,000  |  **Risk/Trade:** 1.0%

## Ranking theo Sharpe

| # | Strategy | Sharpe | Sortino | Max DD % | Win Rate | Profit Factor | Avg R | Trades |
|---|----------|-------:|--------:|---------:|---------:|--------------:|------:|-------:|
| 1 | `02-breakout-plus-volume` | 0.89 | 0.40 | 4.1 | 58.3% | 2.72 | 0.75 | 12 |
| 2 | `10-donchian-channel-breakout` | 0.48 | 0.20 | 3.6 | 52.9% | 1.57 | 0.27 | 17 |
| 3 | `07-vwap-pullback` | 0.40 | 0.21 | 2.0 | 38.5% | 1.47 | 0.19 | 26 |
| 4 | `03-breakout-retest` | 0.00 | 0.00 | 0.0 | 0.0% | 0.00 | 0.00 | 0 |
| 5 | `09-opening-range-breakout` | 0.00 | 0.00 | 0.0 | 0.0% | 0.00 | 0.00 | 0 |
| 6 | `06-bollinger-squeeze-breakout` | -0.01 | -0.00 | 2.0 | 50.0% | 1.67 | 0.35 | 4 |
| 7 | `04-ema20-pullback` | -0.02 | -0.01 | 6.7 | 33.3% | 1.09 | 0.06 | 15 |
| 8 | `08-macd-ema200-trend-filter` | -0.02 | -0.01 | 2.0 | 28.6% | 0.87 | -0.07 | 7 |
| 9 | `01-ema-20-50-crossover` | -0.31 | -0.06 | 3.4 | 33.3% | 0.77 | -0.12 | 6 |
| 10 | `05-rsi-bollinger-mean-reversion` | -0.79 | -0.15 | 3.6 | 16.7% | 0.30 | -0.58 | 6 |

## Top 3 chi tiết

### `02-breakout-plus-volume`

- Params: `{'lookback': 20, 'vol_mult': 1.5, 'rr': 2.0}`
- Total return: **8.91%**
- Sharpe: 0.892
- Max drawdown: 4.06%
- Win rate: 58.3%
- Profit factor: 2.72
- Avg R-multiple: 0.75
- Trades: 12 (7W / 5L)

### `10-donchian-channel-breakout`

- Params: `{'lookback': 20, 'atr_n': 14, 'atr_sl': 2.0, 'atr_tp': 3.0}`
- Total return: **4.10%**
- Sharpe: 0.484
- Max drawdown: 3.60%
- Win rate: 52.9%
- Profit factor: 1.57
- Avg R-multiple: 0.27
- Trades: 17 (9W / 8L)

### `07-vwap-pullback`

- Params: `{'vwap_n': 20, 'swing': 5, 'rr': 1.5}`
- Total return: **3.65%**
- Sharpe: 0.396
- Max drawdown: 2.02%
- Win rate: 38.5%
- Profit factor: 1.47
- Avg R-multiple: 0.19
- Trades: 26 (10W / 16L)
