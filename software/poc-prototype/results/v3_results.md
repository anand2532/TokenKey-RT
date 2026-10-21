
### S-protect (new default: newest output exempt from dedup)

Net cost vs caching-on baseline B, Sonnet 4.6 (positive = cheaper); Opus 4.7 cost-weighted in brackets. Newest ≥90 % = share of requests keeping at least 90 % of the newest tool output's tokens.

| Setting | Mode | Public real | SYNTHETIC | Cost-weighted | Newest ≥90 % public | Newest ≥90 % synthetic | Task ≥90 % (pub/syn) | Algo p95 ms (pub/syn) |
|---|---|---|---|---|---|---|---|---|
| 5-min TTL, modelled breaks | economy | +18.1 % | +24.1 % | **+20.3 %** (+17.1 %) | 100.0 % | 100.0 % | 100 / 100 % | 0.42 / 1.02 |
| 5-min TTL, modelled breaks | balanced | +13.3 % | +16.4 % | **+14.4 %** (+12.0 %) | 100.0 % | 100.0 % | 100 / 100 % | 0.37 / 0.78 |
| 5-min TTL, modelled breaks | quality | +8.8 % | +8.4 % | **+8.7 %** (+7.1 %) | 100.0 % | 100.0 % | 100 / 100 % | 0.37 / 0.69 |
| 1-hour TTL, modelled breaks | economy | +5.0 % | +4.7 % | **+4.9 %** (+4.4 %) | 100.0 % | 100.0 % | 100 / 100 % | 0.30 / 0.34 |
| 1-hour TTL, modelled breaks | balanced | +4.3 % | +3.2 % | **+3.9 %** (+3.5 %) | 100.0 % | 100.0 % | 100 / 100 % | 0.31 / 0.33 |
| 1-hour TTL, modelled breaks | quality | +3.3 % | +1.3 % | **+2.6 %** (+2.3 %) | 100.0 % | 100.0 % | 100 / 100 % | 0.36 / 0.37 |
| No breaks (always warm, 5-min TTL) | economy | +2.4 % | +0.0 % | **+1.6 %** (+1.4 %) | 100.0 % | 100.0 % | 100 / 100 % | 0.32 / 0.33 |
| No breaks (always warm, 5-min TTL) | balanced | +2.4 % | +0.0 % | **+1.6 %** (+1.4 %) | 100.0 % | 100.0 % | 100 / 100 % | 0.30 / 0.34 |
| No breaks (always warm, 5-min TTL) | quality | +2.4 % | +0.0 % | **+1.6 %** (+1.4 %) | 100.0 % | 100.0 % | 100 / 100 % | 0.29 / 0.38 |

### S-collapse (middle: exempt from dedup + collapse >3 repeated lines in newest output)

Net cost vs caching-on baseline B, Sonnet 4.6 (positive = cheaper); Opus 4.7 cost-weighted in brackets. Newest ≥90 % = share of requests keeping at least 90 % of the newest tool output's tokens.

| Setting | Mode | Public real | SYNTHETIC | Cost-weighted | Newest ≥90 % public | Newest ≥90 % synthetic | Task ≥90 % (pub/syn) | Algo p95 ms (pub/syn) |
|---|---|---|---|---|---|---|---|---|
| 5-min TTL, modelled breaks | economy | +18.1 % | +24.1 % | **+20.3 %** (+17.1 %) | 100.0 % | 100.0 % | 100 / 100 % | 0.57 / 0.74 |
| 5-min TTL, modelled breaks | balanced | +13.3 % | +16.4 % | **+14.4 %** (+12.0 %) | 100.0 % | 100.0 % | 100 / 100 % | 0.50 / 0.83 |
| 5-min TTL, modelled breaks | quality | +8.8 % | +8.4 % | **+8.7 %** (+7.1 %) | 100.0 % | 100.0 % | 100 / 100 % | 0.57 / 0.85 |
| 1-hour TTL, modelled breaks | economy | +5.0 % | +4.7 % | **+4.9 %** (+4.4 %) | 100.0 % | 100.0 % | 100 / 100 % | 0.42 / 0.65 |
| 1-hour TTL, modelled breaks | balanced | +4.3 % | +3.2 % | **+3.9 %** (+3.5 %) | 100.0 % | 100.0 % | 100 / 100 % | 0.42 / 0.65 |
| 1-hour TTL, modelled breaks | quality | +3.3 % | +1.3 % | **+2.6 %** (+2.3 %) | 100.0 % | 100.0 % | 100 / 100 % | 0.42 / 0.61 |
| No breaks (always warm, 5-min TTL) | economy | +2.4 % | +0.0 % | **+1.6 %** (+1.4 %) | 100.0 % | 100.0 % | 100 / 100 % | 0.39 / 0.64 |
| No breaks (always warm, 5-min TTL) | balanced | +2.4 % | +0.0 % | **+1.6 %** (+1.4 %) | 100.0 % | 100.0 % | 100 / 100 % | 0.41 / 0.62 |
| No breaks (always warm, 5-min TTL) | quality | +2.4 % | +0.0 % | **+1.6 %** (+1.4 %) | 100.0 % | 100.0 % | 100 / 100 % | 0.39 / 0.60 |

### S-dedup (previous run, for reference: newest output deduped)

Net cost vs caching-on baseline B, Sonnet 4.6 (positive = cheaper); Opus 4.7 cost-weighted in brackets. Newest ≥90 % = share of requests keeping at least 90 % of the newest tool output's tokens.

| Setting | Mode | Public real | SYNTHETIC | Cost-weighted | Newest ≥90 % public | Newest ≥90 % synthetic | Task ≥90 % (pub/syn) | Algo p95 ms (pub/syn) |
|---|---|---|---|---|---|---|---|---|
| 5-min TTL, modelled breaks | economy | +28.0 % | +36.9 % | **+31.2 %** (+26.6 %) | 41.5 % | 82.6 % | 100 / 100 % | 0.37 / 0.70 |
| 5-min TTL, modelled breaks | balanced | +23.2 % | +29.2 % | **+25.3 %** (+21.4 %) | 41.5 % | 82.6 % | 100 / 100 % | 0.37 / 0.76 |
| 5-min TTL, modelled breaks | quality | +18.7 % | +21.2 % | **+19.6 %** (+16.5 %) | 41.5 % | 82.6 % | 100 / 100 % | 0.42 / 0.72 |
| 1-hour TTL, modelled breaks | economy | +20.5 % | +24.4 % | **+21.8 %** (+19.2 %) | 41.5 % | 82.6 % | 100 / 100 % | 0.30 / 0.33 |
| 1-hour TTL, modelled breaks | balanced | +19.8 % | +22.8 % | **+20.8 %** (+18.3 %) | 41.5 % | 82.6 % | 100 / 100 % | 0.31 / 0.33 |
| 1-hour TTL, modelled breaks | quality | +18.7 % | +20.9 % | **+19.5 %** (+17.1 %) | 41.5 % | 82.6 % | 100 / 100 % | 0.32 / 0.40 |
| No breaks (always warm, 5-min TTL) | economy | +17.0 % | +19.7 % | **+17.9 %** (+15.2 %) | 41.5 % | 82.6 % | 100 / 100 % | 0.28 / 0.31 |
| No breaks (always warm, 5-min TTL) | balanced | +17.0 % | +19.7 % | **+17.9 %** (+15.2 %) | 41.5 % | 82.6 % | 100 / 100 % | 0.28 / 0.32 |
| No breaks (always warm, 5-min TTL) | quality | +17.0 % | +19.7 % | **+17.9 %** (+15.2 %) | 41.5 % | 82.6 % | 100 / 100 % | 0.26 / 0.30 |

### Added latency through the TokenKey proxy (5-min TTL, virtual clock), p95 ms

| Variant/mode | Public | Synthetic |
|---|---|---|
| protect/economy | 2.38 | 2.53 |
| protect/balanced | 2.34 | 2.41 |
| protect/quality | 2.19 | 2.62 |
| collapse/economy | 2.28 | 2.80 |
| collapse/balanced | 2.34 | 3.04 |
| collapse/quality | 2.75 | 2.75 |
