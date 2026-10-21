OFFLINE PROXIES, NOT TRUE QUALITY. Net cost: Sonnet 4.6, 5-min TTL, vs caching-on baseline B (positive = cheaper); S variants use the modelled gaps, the others are timing-independent reducers billed with the same gaps.

### public (public real SWE-agent trajectories)

| Variant | Next-turn ref recall % | Requests with all refs kept % | Newest-output error-line recall % | Requests with all newest errors kept % | All-context error-line recall % | Net cost, modelled breaks | Net cost, no breaks |
|---|---|---|---|---|---|---|---|
| B caching-on baseline (no reduction) | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | +0.0 % | +0.0 % |
| S-protect economy | 99.9 | 99.6 | 100.0 | 100.0 | 85.6 | +18.1 % | +7.4 % |
| S-collapse economy | 99.9 | 99.6 | 100.0 | 100.0 | 85.6 | +18.1 % | +7.4 % |
| S-dedup economy | 99.9 | 99.4 | 98.6 | 98.2 | 84.9 | +28.0 % | +19.6 % |
| C tail-only economy | 71.7 | 62.3 | 28.1 | 18.5 | 19.6 | +59.0 % | +53.9 % |
| D firmware full-request economy | 78.9 | 70.9 | 29.5 | 28.6 | 30.8 | -4.2 % | -22.4 % |
| S-protect balanced | 99.9 | 99.7 | 100.0 | 100.0 | 92.7 | +13.3 % | +1.5 % |
| S-collapse balanced | 99.9 | 99.7 | 100.0 | 100.0 | 92.7 | +13.3 % | +1.5 % |
| S-dedup balanced | 99.9 | 99.7 | 100.0 | 100.0 | 92.7 | +23.2 % | +14.2 % |
| C tail-only balanced | 90.4 | 79.7 | 58.7 | 46.2 | 50.6 | +44.2 % | +41.7 % |
| D firmware full-request balanced | 90.2 | 82.7 | 58.8 | 56.3 | 59.5 | -50.2 % | -72.9 % |
| S-protect quality | 100.0 | 100.0 | 100.0 | 100.0 | 99.5 | +8.8 % | -2.0 % |
| S-collapse quality | 100.0 | 100.0 | 100.0 | 100.0 | 99.5 | +8.8 % | -2.0 % |
| S-dedup quality | 100.0 | 100.0 | 100.0 | 100.0 | 99.5 | +18.7 % | +13.0 % |
| C tail-only quality | 93.2 | 86.1 | 70.6 | 58.8 | 60.3 | +31.1 % | +29.2 % |
| D firmware full-request quality | 97.0 | 93.4 | 91.5 | 88.3 | 92.1 | -104.9 % | -132.6 % |
| G dedup-only | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | +17.0 % | +17.0 % |
| E llmtrim agent (cache markers) | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | -43.2 % | -52.6 % |
| E llmtrim agent (no markers) | 97.6 | 95.0 | 83.2 | 77.8 | 82.7 | -41.2 % | -52.7 % |
| E Tamp balanced (default) | 41.5 | 32.4 | 20.6 | 22.2 | 28.7 | +11.5 % | +9.9 % |

Requests with ≥1 next-turn reference found in context: 684 (3225 references); requests whose newest output has error lines: 325.

### synthetic (SYNTHETIC)

| Variant | Next-turn ref recall % | Requests with all refs kept % | Newest-output error-line recall % | Requests with all newest errors kept % | All-context error-line recall % | Net cost, modelled breaks | Net cost, no breaks |
|---|---|---|---|---|---|---|---|
| B caching-on baseline (no reduction) | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | +0.0 % | +0.0 % |
| S-protect economy | 100.0 | 100.0 | 100.0 | 100.0 | 79.8 | +24.1 % | +10.3 % |
| S-collapse economy | 100.0 | 100.0 | 100.0 | 100.0 | 79.8 | +24.1 % | +10.3 % |
| S-dedup economy | 100.0 | 100.0 | 85.1 | 88.3 | 71.6 | +36.9 % | +27.5 % |
| C tail-only economy | 80.7 | 80.7 | 2.1 | 1.1 | 2.6 | +85.3 % | +82.4 % |
| D firmware full-request economy | 100.0 | 100.0 | 67.8 | 67.2 | 55.1 | +3.0 % | -26.1 % |
| S-protect balanced | 100.0 | 100.0 | 100.0 | 100.0 | 89.3 | +16.4 % | +0.3 % |
| S-collapse balanced | 100.0 | 100.0 | 100.0 | 100.0 | 89.3 | +16.4 % | +0.3 % |
| S-dedup balanced | 100.0 | 100.0 | 93.5 | 93.9 | 85.6 | +29.2 % | +17.5 % |
| C tail-only balanced | 85.7 | 85.7 | 36.9 | 23.9 | 34.2 | +75.2 % | +75.3 % |
| D firmware full-request balanced | 100.0 | 100.0 | 95.1 | 96.1 | 92.1 | -85.6 % | -139.4 % |
| S-protect quality | 100.0 | 100.0 | 100.0 | 100.0 | 96.4 | +8.4 % | -5.8 % |
| S-collapse quality | 100.0 | 100.0 | 100.0 | 100.0 | 96.4 | +8.4 % | -5.8 % |
| S-dedup quality | 100.0 | 100.0 | 98.5 | 98.3 | 95.5 | +21.2 % | +13.5 % |
| C tail-only quality | 90.7 | 90.7 | 61.1 | 47.8 | 60.7 | +53.1 % | +53.9 % |
| D firmware full-request quality | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | -84.3 % | -129.6 % |
| G dedup-only | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | +18.3 % | +19.7 % |
| E llmtrim agent (cache markers) | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | -6.5 % | -10.0 % |
| E llmtrim agent (no markers) | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | -6.6 % | -10.2 % |
| E Tamp balanced (default) | 96.4 | 96.4 | 55.1 | 40.0 | 96.0 | -12.1 % | -18.5 % |

Requests with ≥1 next-turn reference found in context: 140 (280 references); requests whose newest output has error lines: 180.
