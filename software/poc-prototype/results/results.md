
## data/SYNTHETIC_sessions.jsonl (SYNTHETIC DATA): 10 sessions, 310 requests

| variant | net_cost_vs_B_pct_sonnet46 | net_cost_vs_B_pct_opus47 | input_tokens_vs_B_pct | usd_sonnet46 | cache_read | cache_write | uncached_in | output | newest_msg_kept_pct | task_kept_pct | algo_ms_p95 | proxy_added_ms_p50 | proxy_added_ms_p95 | overflow | set_full |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A_no_cache_raw | -507.2 | -507.2 | 0.0 | 15.4978 | 0 | 0 | 5153945 | 2399 | 100.0 | 100.0 |  |  |  | 0 |  |
| B_cache_raw (baseline) | 0.0 | 0.0 | 0.0 | 2.5521 | 4872792 | 281153 | 0 | 2399 | 100.0 | 100.0 |  |  |  | 0 |  |
| D_firmware_full_request_economy | -26.1 | -64.9 | 74.8 | 3.2194 | 484081 | 801077 | 11369 | 2399 | 71.3 | 100.0 | 3.14 |  |  | 0 |  |
| D_firmware_full_request_balanced | -139.4 | -158.4 | 49.4 | 6.109 | 1073855 | 1533554 | 0 | 2399 | 81.9 | 100.0 | 3.09 | 3.22 | 5.29 | 0 |  |
| D_firmware_full_request_quality | -129.6 | -134.6 | 16.4 | 5.8603 | 2992644 | 1313741 | 0 | 2399 | 87.7 | 100.0 | 3.06 |  |  | 0 |  |
| C_firmware_tail_only_economy | 82.4 | 49.1 | 91.8 | 0.4497 | 320061 | 19845 | 81083 | 2399 | 3.2 | 100.0 | 0.31 |  |  | 0 | 0 |
| C_firmware_tail_only_balanced | 75.3 | 23.2 | 76.0 | 0.6302 | 1172444 | 64673 | 0 | 2399 | 3.2 | 100.0 | 0.33 | 1.24 | 1.87 | 0 | 0 |
| C_firmware_tail_only_quality | 53.9 | 33.8 | 53.0 | 1.1768 | 2300475 | 120190 | 0 | 2399 | 7.4 | 100.0 | 0.31 |  |  | 0 | 0 |
| F_host_unconstrained_tail_only_balanced | 75.1 | 23.0 | 75.7 | 0.6366 | 1184784 | 65369 | 0 | 2399 | 3.2 | 100.0 | 0.77 |  |  | 0 | 0 |
| G_ext_dedup_only_tail (not a firmware mode) | 19.7 | 19.7 | 15.6 | 2.0498 | 4142516 | 205610 | 0 | 2399 | 82.6 | 100.0 | 0.32 |  |  | 0 |  |
| E_llmtrim_agent_with_cache_markers | -10.0 | -10.0 | -0.5 | 2.8068 | 4824702 | 352897 | 0 | 2399 | 100.0 | 100.0 | 4.26 |  |  | 0 |  |
| E_llmtrim_agent_no_cache_markers | -10.2 | -10.2 | -0.3 | 2.8135 | 4816265 | 355366 | 0 | 2399 | 99.7 | 100.0 | 9.97 |  |  | 0 |  |
| E_tamp_balanced_default | -20.2 | -20.2 | 1.1 | 3.0667 | 4660956 | 435323 | 0 | 2399 | 23.2 | 100.0 |  | 86.87 | 2458.86 |  |  |

## data/public_swe_agent_trajectories.jsonl (PUBLIC REAL AGENT TRAJECTORIES): 30 sessions, 709 requests

| variant | net_cost_vs_B_pct_sonnet46 | net_cost_vs_B_pct_opus47 | input_tokens_vs_B_pct | usd_sonnet46 | cache_read | cache_write | uncached_in | output | newest_msg_kept_pct | task_kept_pct | algo_ms_p95 | proxy_added_ms_p50 | proxy_added_ms_p95 | overflow | set_full |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A_no_cache_raw | -353.3 | -261.7 | 0.0 | 23.3449 | 0 | 0 | 7354598 | 85410 | 100.0 | 100.0 |  |  |  | 0 |  |
| B_cache_raw (baseline) | 0.0 | 0.0 | 0.0 | 5.1503 | 6872626 | 481972 | 0 | 85410 | 100.0 | 100.0 |  |  |  | 0 |  |
| D_firmware_full_request_economy | -22.4 | -3.4 | 75.4 | 6.3016 | 488278 | 1205017 | 118371 | 85410 | 16.6 | 5.8 | 3.95 |  |  | 0 |  |
| D_firmware_full_request_balanced | -72.9 | -65.2 | 50.8 | 8.9047 | 1716034 | 1870980 | 30840 | 85410 | 30.7 | 52.9 | 3.92 | 2.49 | 6.39 | 0 |  |
| D_firmware_full_request_quality | -132.6 | -117.1 | 15.3 | 11.9805 | 3669433 | 2559615 | 0 | 85410 | 64.9 | 94.5 | 3.97 |  |  | 0 |  |
| C_firmware_tail_only_economy | 53.9 | 27.9 | 83.3 | 2.3754 | 980429 | 79876 | 166857 | 85410 | 5.2 | 0.0 | 0.29 |  |  | 0 | 0 |
| C_firmware_tail_only_balanced | 41.7 | 17.7 | 57.4 | 3.0052 | 2897718 | 201762 | 32712 | 85410 | 17.1 | 0.0 | 0.28 | 1.22 | 1.91 | 0 | 0 |
| C_firmware_tail_only_quality | 29.2 | 14.3 | 38.9 | 3.6459 | 4201736 | 294451 | 0 | 85410 | 28.5 | 87.3 | 0.29 |  |  | 0 | 0 |
| F_host_unconstrained_tail_only_balanced | 41.2 | 17.8 | 57.2 | 3.0264 | 2905239 | 204485 | 35612 | 85410 | 10.4 | 0.0 | 0.53 |  |  | 0 | 0 |
| G_ext_dedup_only_tail (not a firmware mode) | 17.0 | 13.4 | 19.7 | 4.2744 | 5550885 | 354134 | 0 | 85410 | 41.5 | 100.0 | 0.26 |  |  | 0 |  |
| E_llmtrim_agent_with_cache_markers | -52.6 | -38.9 | -0.7 | 7.8591 | 6142762 | 1262696 | 0 | 85410 | 100.0 | 100.0 | 5.34 |  |  | 0 |  |
| E_llmtrim_agent_no_cache_markers | -52.7 | -50.7 | 12.8 | 7.8626 | 5065915 | 1349789 | 0 | 85410 | 76.7 | 99.2 | 21.57 |  |  | 0 |  |
| E_tamp_balanced_default | -0.3 | -0.2 | 0.0 | 5.1654 | 6865693 | 486555 | 0 | 85410 | 97.3 | 100.0 |  | 44.59 | 48.81 |  |  |
