
### 5m TTL, modelled breaks (default)

| Mode | Data | Net cost vs B (Sonnet 4.6) | Net cost vs B (Opus 4.7) | Input tokens vs B | B $ / S $ (Sonnet 4.6) | Cold starts | Task kept ≥90 % | Newest tool output kept ≥90 % | Newest kept (mean) | Algo p95 ms | Full-reduction p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| economy | public | 28.0 % | 21.8 % | −34.1 % | 6.13 / 4.41 | 27 | 100.0 % | 41.5 % | 63.9 % | 0.42 | 3.15 |
| economy | synthetic (SYNTHETIC) | 36.9 % | 36.9 % | −35.4 % | 3.43 / 2.16 | 16 | 100.0 % | 82.6 % | 82.7 % | 1.02 | 4.04 |
| economy | **cost-weighted (public + synthetic)** | **31.2 %** | **26.6 %** | | | | | | | | |
| balanced | public | 23.2 % | 17.7 % | −27.6 % | 6.13 / 4.71 | 27 | 100.0 % | 41.5 % | 63.9 % | 0.43 | 2.99 |
| balanced | synthetic (SYNTHETIC) | 29.2 % | 29.2 % | −27.9 % | 3.43 / 2.43 | 16 | 100.0 % | 82.6 % | 82.7 % | 0.70 | 3.47 |
| balanced | **cost-weighted (public + synthetic)** | **25.3 %** | **21.4 %** | | | | | | | | |
| quality | public | 18.7 % | 14.3 % | −21.8 % | 6.13 / 4.99 | 27 | 100.0 % | 41.5 % | 63.9 % | 0.38 | 3.00 |
| quality | synthetic (SYNTHETIC) | 21.2 % | 21.2 % | −19.3 % | 3.43 / 2.70 | 16 | 100.0 % | 82.6 % | 82.7 % | 0.86 | 3.22 |
| quality | **cost-weighted (public + synthetic)** | **19.6 %** | **16.5 %** | | | | | | | | |

### 1h TTL, modelled breaks (sensitivity)

| Mode | Data | Net cost vs B (Sonnet 4.6) | Net cost vs B (Opus 4.7) | Input tokens vs B | B $ / S $ (Sonnet 4.6) | Cold starts | Task kept ≥90 % | Newest tool output kept ≥90 % | Newest kept (mean) | Algo p95 ms | Full-reduction p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| economy | public | 20.5 % | 16.9 % | −21.6 % | 6.43 / 5.12 | 3 | 100.0 % | 41.5 % | 63.9 % | 0.32 | 0.57 |
| economy | synthetic (SYNTHETIC) | 24.4 % | 24.4 % | −19.3 % | 3.35 / 2.54 | 2 | 100.0 % | 82.6 % | 82.7 % | 0.33 | 1.01 |
| economy | **cost-weighted (public + synthetic)** | **21.8 %** | **19.2 %** | | | | | | | | |
| balanced | public | 19.8 % | 16.4 % | −21.0 % | 6.43 / 5.16 | 3 | 100.0 % | 41.5 % | 63.9 % | 0.32 | 0.49 |
| balanced | synthetic (SYNTHETIC) | 22.8 % | 22.8 % | −17.8 % | 3.35 / 2.59 | 2 | 100.0 % | 82.6 % | 82.7 % | 0.33 | 0.98 |
| balanced | **cost-weighted (public + synthetic)** | **20.8 %** | **18.3 %** | | | | | | | | |
| quality | public | 18.7 % | 15.5 % | −20.1 % | 6.43 / 5.23 | 3 | 100.0 % | 41.5 % | 63.9 % | 0.30 | 0.58 |
| quality | synthetic (SYNTHETIC) | 20.9 % | 20.9 % | −16.0 % | 3.35 / 2.65 | 2 | 100.0 % | 82.6 % | 82.7 % | 0.33 | 1.09 |
| quality | **cost-weighted (public + synthetic)** | **19.5 %** | **17.1 %** | | | | | | | | |

### 5m TTL, always warm / no breaks (reference)

| Mode | Data | Net cost vs B (Sonnet 4.6) | Net cost vs B (Opus 4.7) | Input tokens vs B | B $ / S $ (Sonnet 4.6) | Cold starts | Task kept ≥90 % | Newest tool output kept ≥90 % | Newest kept (mean) | Algo p95 ms | Full-reduction p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| economy | public | 17.0 % | 13.4 % | −19.7 % | 5.15 / 4.27 | 0 | 100.0 % | 41.5 % | 63.9 % | 0.29 | 0.47 |
| economy | synthetic (SYNTHETIC) | 19.7 % | 19.7 % | −15.6 % | 2.55 / 2.05 | 0 | 100.0 % | 82.6 % | 82.7 % | 0.37 | 0.67 |
| economy | **cost-weighted (public + synthetic)** | **17.9 %** | **15.2 %** | | | | | | | | |
| balanced | public | 17.0 % | 13.4 % | −19.7 % | 5.15 / 4.27 | 0 | 100.0 % | 41.5 % | 63.9 % | 0.29 | 0.43 |
| balanced | synthetic (SYNTHETIC) | 19.7 % | 19.7 % | −15.6 % | 2.55 / 2.05 | 0 | 100.0 % | 82.6 % | 82.7 % | 0.35 | 0.68 |
| balanced | **cost-weighted (public + synthetic)** | **17.9 %** | **15.2 %** | | | | | | | | |
| quality | public | 17.0 % | 13.4 % | −19.7 % | 5.15 / 4.27 | 0 | 100.0 % | 41.5 % | 63.9 % | 0.29 | 0.46 |
| quality | synthetic (SYNTHETIC) | 19.7 % | 19.7 % | −15.6 % | 2.55 / 2.05 | 0 | 100.0 % | 82.6 % | 82.7 % | 0.34 | 0.97 |
| quality | **cost-weighted (public + synthetic)** | **17.9 %** | **15.2 %** | | | | | | | | |

### 5m TTL, modelled breaks, newest tool output NOT deduped (sensitivity; deviates from PM rule 4)

| Mode | Data | Net cost vs B (Sonnet 4.6) | Net cost vs B (Opus 4.7) | Input tokens vs B | B $ / S $ (Sonnet 4.6) | Cold starts | Task kept ≥90 % | Newest tool output kept ≥90 % | Newest kept (mean) | Algo p95 ms | Full-reduction p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| economy | public | 18.1 % | 13.8 % | −23.6 % | 6.13 / 5.02 | 27 | 100.0 % | 100.0 % | 100.0 % | 0.40 | 3.18 |
| economy | synthetic (SYNTHETIC) | 24.1 % | 24.1 % | −23.9 % | 3.43 / 2.60 | 16 | 100.0 % | 100.0 % | 100.0 % | 0.99 | 4.41 |
| economy | **cost-weighted (public + synthetic)** | **20.3 %** | **17.1 %** | | | | | | | | |
| balanced | public | 13.3 % | 9.9 % | −17.1 % | 6.13 / 5.31 | 27 | 100.0 % | 100.0 % | 100.0 % | 0.50 | 3.64 |
| balanced | synthetic (SYNTHETIC) | 16.4 % | 16.4 % | −16.4 % | 3.43 / 2.86 | 16 | 100.0 % | 100.0 % | 100.0 % | 0.81 | 5.03 |
| balanced | **cost-weighted (public + synthetic)** | **14.4 %** | **12.0 %** | | | | | | | | |
| quality | public | 8.8 % | 6.5 % | −11.4 % | 6.13 / 5.59 | 27 | 100.0 % | 100.0 % | 100.0 % | 0.50 | 3.61 |
| quality | synthetic (SYNTHETIC) | 8.4 % | 8.4 % | −7.8 % | 3.43 / 3.14 | 16 | 100.0 % | 100.0 % | 100.0 % | 0.80 | 3.43 |
| quality | **cost-weighted (public + synthetic)** | **8.7 %** | **7.1 %** | | | | | | | | |

### Added latency through the TokenKey proxy (variant S, 5m TTL, virtual clock), ms

| Mode | Public p50 | Public p95 | Synthetic p50 | Synthetic p95 |
|---|---|---|---|---|
| economy | 1.36 | 2.14 | 1.53 | 2.59 |
| balanced | 1.22 | 2.07 | 1.43 | 2.57 |
| quality | 1.35 | 2.26 | 1.51 | 2.71 |
