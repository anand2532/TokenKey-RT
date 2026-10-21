# Offline update 2026-10-19 (no paid API calls)

Gate status: G1 not passed (hinges on real timestamped logs); G2 not passed/untested (offline proxies only);
G3 not decidable at equal quality (proxies favour S-protect); G4 not testable without interviews; G5 passed (p95 2.19-3.04 ms).

Offline proxies (PROXIES, NOT TRUE QUALITY): see `offline_quality.md` / `offline_quality.json`
(`python -m tokenkey_poc.offline_quality --out results`). Public data, Sonnet 4.6, 5-min TTL, modelled breaks:
S-protect Economy 99.9 % next-turn reference recall, 100 % newest-error recall, +18.1 % net; G dedup-only 100 % / 100 % / +17.0 %;
llmtrim (markers) 100 % / 100 % / -43.2 %; Tamp 41.5 % / 20.6 % / +11.5 %; firmware-as-written Economy 78.9 % / 29.5 % / -4.2 %.
Caveat: in offline_quality.md the "no breaks" column for S-* rows bills sessions reduced under the break timeline without breaks,
so it is not comparable to the no-break figures below (+2.4 / 0.0 / +1.6 %); use those. Tamp recall may be understated
(format rewriting defeats substring matching). G4 desk research is in docs/poc/2026-10-19-prototype-results.md.

# TokenKey RT software-only PoC: results (updated 2026-10-19)

## Current status (PM decisions, round 2)

**G1: not passed. It hinges on real timestamped logs.**
**G5: passed** (proxy-added p95 ≤ 3.04 ms).
**G2, G3, G4: not yet testable.**

The PM made two decisions in this round:
1. **New default:** the newest tool output is exempt from cross-message dedup (variant **S-protect**).
2. **Middle variant (S-collapse):** inside the newest output only, runs of more than 3 identical consecutive lines are collapsed to first line + "[repeated N×]" + last line. The first traceback/error block is never touched.

Confirmed interpretations: assistant messages are exempt from ratios, and the ratio budget is counted on older tool output before dedup.

Headline (Sonnet 4.6, net cost vs the caching-on baseline B; positive = cheaper). Both new variants keep ≥ 90 % of the newest output in 100 % of requests:

| Setting | Economy (pub / syn / weighted) | Balanced | Quality |
|---|---|---|---|
| 5-min TTL, modelled breaks | +18.1 / +24.1 / **+20.3 %** | +13.3 / +16.4 / **+14.4 %** | +8.8 / +8.4 / **+8.7 %** |
| 1-hour TTL, modelled breaks | +5.0 / +4.7 / **+4.9 %** | +4.3 / +3.2 / **+3.9 %** | +3.3 / +1.3 / **+2.6 %** |
| No breaks | +2.4 / +0.0 / **+1.6 %** | same | same |

**S-collapse gives the same numbers as S-protect to one decimal place.** The collapse rule fired on 1 of 679 public tool outputs (saving 67 characters) and on 0 of 300 synthetic ones. The synthetic generator produces no consecutive repeated lines, so the synthetic data cannot test this rule at all. The duplicated content in newest outputs is repeated *across* messages, not in consecutive runs.

**Reading:** once the newest output is protected, savings come almost entirely from keep-ratio cuts of older tool output at cache cold starts. They therefore scale with how often the cache goes cold.
- With no breaks: +1.6 %.
- At a 1-hour TTL: below 5 %.
- At a 5-min TTL with the modelled 5 %/turn break rate: only Economy, cost-weighted, reaches 20 % (+20.3 %). Public data alone gives +18.1 %.

Whether real usage has enough cold starts is unknown. That is why G1 hinges on real timestamped logs.

### Round-2 method

- **Code:** `tokenkey_poc/session_reducer.py` (`newest_policy` = `protect` / `collapse` / `dedup`; `collapse_repeats()`), `tokenkey_poc/replay_v3.py` (runner). Results are in `results/v3_results.{md,json}`. 13 unit tests pass, including one for the collapse rule.
- **Collapse interpretation:** N in "[repeated N×]" is the total number of lines in the run. Only consecutive runs of ≥ 4 identical non-blank lines are collapsed. "First traceback/error block" = the first LOG segment found by the firmware scanner in the newest output.
- **Everything else is unchanged from round 1:**
  - Modelled gaps, because neither dataset has timestamps: agent step lognormal (median 20 s, σ 0.8); human break with 5 %/turn probability, log-uniform 2-120 minutes.
  - Same gaps for baseline and variant.
  - 1-hour cache writes billed at 2x base.
  - tiktoken o200k as a stand-in tokenizer; outputs identical across variants; message-level cache prefix.

### Round-2 full results

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

### Gate status (current)

| Gate | Status |
|---|---|
| G1 ≥ 20 % net vs caching-on baseline | **Not passed: hinges on real timestamped logs.** Under the new default, only Economy at a 5-min TTL with modelled breaks clears 20 % on the cost-weighted figure (+20.3 %; public +18.1 %). Every other mode/setting is below 20 % |
| G2 quality | Not yet testable (needs an API key, a spend cap and real runs) |
| G3 vs free proxies at equal quality | Not yet testable |
| G4 users | Not yet testable (needs interviews) |
| G5 host p95 ≤ 50 ms | **Passed.** Proxy-added p95 2.19-3.04 ms; algorithm p95 ≤ 1.02 ms |

---


**Superseded (round 1 of PM defaults, newest output deduped). Kept for reference; see the current status above.**

The PM defaults:
- A job is only the new messages; the cached prefix is never rewritten.
- The system prompt, the task statement and the newest tool output are exempt from keep ratios.
- A session is one conversation while the cache is warm: 5-minute TTL by default, 1 hour as a sensitivity check. A full-request reduction is allowed once at each cold start.
- Exact-duplicate removal is on in every mode.

Headline (Sonnet 4.6, 5-minute TTL, modelled breaks):

| Mode | Public real trajectories | SYNTHETIC | Cost-weighted |
|---|---|---|---|
| Economy | +28.0 % | +36.9 % | +31.2 % |
| Balanced | +23.2 % | +29.2 % | +25.3 % |
| Quality | +18.7 % | +21.2 % | +19.6 % |

G1 (≥ 20 %) is **reached on paper for Economy and Balanced and missed for Quality**, under a *modelled* break pattern. Neither dataset has timestamps. Three things qualify this:
- With no breaks (automated runs), every mode falls to +17.0 % (public), short of 20 %.
- At a 1-hour TTL, only Economy and Balanced on the cost-weighted figure stay above 20 % (+21.8 % / +20.8 %); public alone is +20.5 % / +19.8 %.
- Duplicate removal takes out 30.4 % of the newest tool output's bytes. That includes repeated "syntax error" and traceback messages the agent needs to see. If the newest output is not deduped, only Economy clears 20 %, on the cost-weighted figure only (+20.3 %).

G5 passes: added proxy latency p95 is ≤ 3.10 ms.

## PM-defaults re-run (variant S): method

- **Code:** `tokenkey_poc/session_reducer.py` (variant S), `tokenkey_poc/timing.py` (TTL-aware billing and gap model), `tokenkey_poc/replay_v2.py` (runner), `tokenkey_poc/break_sweep.py`. `tk_core.run_job` gained the optional `exempt` / `drop_dups` arguments; the original firmware path is unchanged (12 unit tests pass), and earlier variants are unaffected.
- **Interpretations I had to make:**
  1. Assistant messages are not "tool output", so they are not ratio-reduced (dedup only). With rules 1 and 2 together, a warm turn's new messages are [assistant reply, newest tool output], both exempt from ratios. **On warm turns the modes are therefore identical (dedup only); keep ratios act only at cold starts**, on older tool output.
  2. Rule 4 is applied inside exempt messages too, including the newest tool output (rule 2 exempts from ratios only). A sensitivity row shows the alternative.
  3. The ratio budget is the mode percentage × the older-tool-output tokens counted before dedup.
- **Timing (assumption):** neither the public SWE-agent trajectories nor the synthetic sessions carry timestamps, so gaps are modelled deterministically per session id:
  - Agent step: lognormal, median 20 s, σ 0.8.
  - Human break: added with probability 5 % per turn, log-uniform between 2 and 120 minutes.
  - The cache is cold when the gap since the previous request exceeds the TTL.
  - The baseline B uses exactly the same gaps and TTL. At a 1-hour TTL, cache writes bill at 2x base ($6.00/MTok Sonnet 4.6, $10.00 Opus 4.7, https://platform.claude.com/docs/en/about-claude/pricing).
  - The "always warm" row and the break sweep show how much the result depends on this assumption.
- **Unchanged from before:** tiktoken o200k proxy tokenizer; outputs identical across variants; message-level cache prefix; local mock upstream.

## PM-defaults re-run: full results

Positive = cheaper than the caching-on baseline B. "Cost-weighted" pools the dollar costs of both datasets, so it mixes real and SYNTHETIC sessions.

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

### Sensitivity to the modelled break rate (5-minute TTL, Sonnet 4.6)

| Break prob./turn | Mode | Public | Synthetic (SYNTHETIC) | Cost-weighted | Public cold starts |
|---|---|---|---|---|---|
| 0.00 | economy | 17.0 % | 19.7 % | 17.9 % | 0 |
| 0.00 | balanced | 17.0 % | 19.7 % | 17.9 % | 0 |
| 0.00 | quality | 17.0 % | 19.7 % | 17.9 % | 0 |
| 0.02 | economy | 23.2 % | 28.2 % | 24.9 % | 10 |
| 0.02 | balanced | 20.5 % | 24.2 % | 21.8 % | 10 |
| 0.02 | quality | 18.1 % | 20.2 % | 18.8 % | 10 |
| 0.05 | economy | 28.0 % | 36.9 % | 31.2 % | 27 |
| 0.05 | balanced | 23.2 % | 29.2 % | 25.3 % | 27 |
| 0.05 | quality | 18.7 % | 21.2 % | 19.6 % | 27 |
| 0.10 | economy | 31.2 % | 39.8 % | 34.4 % | 49 |
| 0.10 | balanced | 25.0 % | 30.1 % | 26.9 % | 49 |
| 0.10 | quality | 19.2 % | 20.0 % | 19.5 % | 49 |

### What drives the numbers

- **Warm turns:** savings come only from exact-duplicate removal. That gives 17.0 % (public) and 19.7 % (synthetic), the "always warm" row.
- **Cold starts:** each one lets the keep ratio cut older tool output once. Later turns append to that shortened history, so the saving persists for the rest of the session. More breaks mean more savings, as the sweep shows (+17.0 % at 0 breaks to +31.2 % Economy at 10 %/turn, public).
- **Newest-output retention:** dedup removed 30.4 % of the newest tool output's bytes on public data. Most of that is repeated status lines ("(Open file: …)"), but it also includes repeated "Your proposed edit has introduced new syntax error(s)…" (64 times) and "Traceback (most recent call last):" (19 times). So the agent might not see that its latest action failed again. That is a quality risk G2 must test.
- **Older tool output is not covered by the retention checks:** at a cold start, Economy keeps only 25 % of it. Its quality impact is likewise unmeasured.

## G1/G5 status after the round-1 re-run (superseded: G1 is now recorded as not passed)

| Gate | Status |
|---|---|
| G1 ≥ 20 % net vs caching-on baseline | **Reached on paper for Economy (+31.2 % cost-weighted; +28.0 % public) and Balanced (+25.3 %; +23.2 %) at 5-minute TTL with modelled breaks. Not reached for Quality (+19.6 %; +18.7 %).** Not reached by any mode on public data when always warm (+17.0 %) or at a 1-hour TTL (public +20.5 % / +19.8 % / +18.7 %; cost-weighted Economy +21.8 %, Balanced +20.8 %). Not a pass yet: it depends on an unvalidated break model, a proxy tokenizer, and quality (G2) |
| G5 host p95 ≤ 50 ms | **PASS.** Proxy-added p95 is 2.07-3.10 ms across modes and datasets. Algorithm p95 is ≤ 0.99 ms; full-reduction turns ≤ 5.03 ms |
| G2, G3, G4 | Unchanged: not yet testable |

---

# Earlier results (first PoC run, unchanged below)


**Summary.** I ran a host-side Python port of the firmware context engine (firmware_architecture.md §2.3) over two datasets:
- **PUBLIC REAL agent trajectories:** 30 SWE-agent sessions, 709 requests, from `nebius/SWE-agent-trajectories` on Hugging Face.
- **SYNTHETIC sessions:** 10 sessions, 310 requests, machine-generated.

Each run was billed against a caching-on baseline (B) at published Anthropic prices.

Findings:
- **The firmware as written** (reduce the whole request each turn) cuts input tokens by 15-75 %, yet *raises* net cost by 22-158 %, because it breaks prompt caching.
- **A cache-preserving variant** (reduce only new messages) meets the ≥ 20 % cost bar, but only by discarding most of each new tool output. Its quality is untested and the required-context proxy looks very poor.
- **The lossless dedup part alone** saves 17.0 % (public) and 19.7 % (synthetic), just under the 20 % bar.
- **Latency is fine:** added p95 ≤ 6.4 ms through a local proxy.
- **The free proxies (Tamp 0.8.21, llmtrim 0.13.7)** gave no net input-cost saving in this replay. Their output-shaping features can't be measured offline.

**Gate status (approved thresholds):**
- G1: fails as designed (firmware as written); not established for any quality-safe variant.
- G2: not yet testable.
- G3: not yet testable.
- G4: not yet testable.
- G5: passes on the host.

## What was measured, and how

- **Algorithm:** `tokenkey_poc/tk_core.py`. Spec items are implemented as written: XXH32, 8192-slot dupset with a 75 % load cap and set_full counting, 4096-segment CTX_OVERFLOW, diff/fenced-code/log/prose classes with weight order diff > code > log > prose, integer score = type + recency + refcount − dup penalty, keep ratio 25/50/85 %, bytes/4 estimate, greedy by score/size, original order kept. 10 unit tests pass. The doc leaves ten parameters open, so I chose values; they are listed in `tk_core.UNSPECIFIED_CHOICES` and in the README.
- **Cost:** `tokenkey_poc/costmodel.py` and `prices.py`.
  - Prices: Sonnet 4.6 $3 input / $3.75 5-min cache write / $0.30 cache read / $15 output per MTok; Opus 4.7 $5 / $6.25 / $0.50 / $25. Minimum cacheable length 1,024 tokens (Sonnet) and 4,096 (Opus). Sources: https://platform.claude.com/docs/en/about-claude/pricing, https://platform.claude.com/docs/en/build-with-claude/prompt-caching, https://platform.claude.com/cookbook/misc-prompt-caching
  - Cache model: message-level common prefix with the previous request is read at 0.1x; the rest is written at 1.25x; all turns are assumed to fall within the TTL.
  - Tokens: tiktoken `o200k_base` as a **proxy** for Claude's tokenizer.
  - Outputs: assumed identical across variants (recorded assistant text).
- **Positive % = cheaper than B.** All numbers below are for Sonnet 4.6 unless marked.

### Public real agent trajectories (30 sessions, 709 requests)

| Variant | Input tokens vs B | **Net cost vs B** | Opus 4.7 | Newest msg kept ≥ 90 % | Task kept ≥ 90 % |
|---|---|---|---|---|---|
| A no caching | 0 % | −353.3 % | −261.7 % | 100 % | 100 % |
| **B caching on (baseline)**, $5.15 | 0 | 0 | 0 | 100 % | 100 % |
| D firmware full-request, Economy | −75.4 % | **−22.4 %** | −3.4 % | 16.6 % | 5.8 % |
| D firmware full-request, Balanced | −50.8 % | **−72.9 %** | −65.2 % | 30.7 % | 52.9 % |
| D firmware full-request, Quality | −15.3 % | **−132.6 %** | −117.1 % | 64.9 % | 94.5 % |
| C cache-preserving, Economy | −83.3 % | +53.9 % | +27.9 % | 5.2 % | 0.0 % |
| C cache-preserving, Balanced | −57.4 % | +41.7 % | +17.7 % | 17.1 % | 0.0 % |
| C cache-preserving, Quality | −38.9 % | +29.2 % | +14.3 % | 28.5 % | 87.3 % |
| F = C-Balanced without MCU caps, real tokenizer | −57.2 % | +41.2 % | +17.8 % | 10.4 % | 0.0 % |
| G dedup-only, cache-preserving (extension) | −19.7 % | **+17.0 %** | +13.4 % | 41.5 % | 100 % |
| E llmtrim `agent`, with cache markers | +0.7 % | −52.6 % | −38.9 % | 100 % | 100 % |
| E llmtrim `agent`, no cache markers | −12.8 % | −52.7 % | −50.7 % | 76.7 % | 99.2 % |
| E Tamp balanced (default stages) | 0.0 % | −0.3 % | −0.2 % | 97.3 % | 100 % |

### SYNTHETIC sessions (10 sessions, 310 requests); machine-generated filler, do not treat as evidence about real users

| Variant | Input tokens vs B | Net cost vs B | Opus 4.7 |
|---|---|---|---|
| D Economy / Balanced / Quality | −74.8 / −49.4 / −16.4 % | −26.1 / −139.4 / −129.6 % | −64.9 / −158.4 / −134.6 % |
| C Economy / Balanced / Quality | −91.8 / −76.0 / −53.0 % | +82.4 / +75.3 / +53.9 % | +49.1 / +23.2 / +33.8 % |
| G dedup-only | −15.6 % | +19.7 % | +19.7 % |
| E llmtrim (markers / no markers) | +0.5 / +0.3 % | −10.0 / −10.2 % | −10.0 / −10.2 % |
| E Tamp | −1.1 % | −20.2 % | −20.2 % |

### Latency (G5)

| Measure | Public | Synthetic |
|---|---|---|
| Algorithm only, p95 per request: D full request / C tail-only (Python) | 3.92 / 0.28 ms | 3.09 / 0.33 ms |
| Added by TokenKey proxy, p50 / p95: D-Balanced | 2.49 / **6.39 ms** | 3.22 / 5.29 ms |
| Added by TokenKey proxy, p50 / p95: C-Balanced | 1.22 / **1.91 ms** | 1.24 / 1.87 ms |
| Added by Tamp proxy, p50 / p95 | 44.59 / 48.81 ms | 86.87 / 2458.86 ms (long tail on large synthetic tool results) |

Added latency is measured as (client → proxy → local mock) minus (client → mock) on the same machine, one request at a time. No real network or provider latency is included.

### Other measurements

- MCU constraints: **0 CTX_OVERFLOW and 0 dupset set_full events** on both datasets. F vs C differ by ≤ 0.5 pp, so bytes/4 and the caps are not what limits results here.
- bytes/4 vs o200k token counts: aggregate ratio 1.001 (public) and 1.069 (synthetic). Per message, p5/p50/p95 = 0.80/1.03/1.23 (public).
- Exact-duplicate share of newly arriving content (segment-level XXH32): 27.2 % of bytes (public), 27.3 % (synthetic).
- llmtrim 0.13.7 sometimes adds or removes the system-prompt line "Reply in the user's language." between turns (12 of 190 turn pairs in 10 public sessions). Each toggle invalidates the whole cached prefix, which explains its net cost increase here.
- Tamp in its default cache-safe mode compresses only the newest tool result. On the next turn the agent re-sends the original text, so the cached (compressed) prefix no longer matches. On the synthetic data this produced −20 % net cost.

## Interpretation

1. **Caching dominates.** In B, cache reads are 93 % of billed input tokens on public data (6.87M read vs 0.48M written). A reducer that rewrites history turns 0.1x reads into 1.25x writes. That is why the firmware's "reduce the whole job" design loses money even at 50-75 % fewer tokens.
2. **Under prefix caching, content can only be reduced once, when it first arrives.** At that moment it is the newest and usually most needed context. C's savings come from cutting 50-75 % of each new tool output. That is very likely to hurt quality (newest message kept ≥ 90 % in only 5-29 % of requests), and G2 has to test it.
3. **Lossless dedup is the only quality-plausible saving found**, at 13-20 %, just under the G1 bar of 20 %. It runs fine on a laptop (p95 0.26 ms), so it doesn't need hardware.
4. **Caveats:**
   - The public data is SWE-agent with open Llama models, not Claude Code or Cursor. SWE-agent normally trims history itself; I replayed full history.
   - Tokens are counted with a proxy tokenizer.
   - Outputs are fixed, so any output-token savings from llmtrim/Tamp output shaping are **not** credited. This makes the comparison unfavourable to them.

## Gate status

| Gate (approved threshold) | Status | Evidence |
|---|---|---|
| G1 net cost ≥ 20 % below caching-on baseline | **FAIL for the firmware design as written** (D: −22 % to −158 %, i.e. more expensive). **Not established** for any quality-safe variant: C meets the number but fails the required-context proxy; G reaches 17.0 % / 19.7 % | Tables above. Final verdict needs real pay-per-token logs and real billed usage |
| G2 quality drop ≤ 2 pp, recall ≥ 98 % | **Not yet testable** (needs an API key, a spend cap, and real runs). The proxy diagnostic suggests C-Balanced/Economy would fail | `docs/G2_quality_experiment_design.md` |
| G3 TokenKey ≥ best free proxy at equal quality | **Not yet testable** (equal quality unknown; output effects of Tamp/llmtrim unmeasured). Input-cost only: TokenKey C/G beat Tamp and llmtrim in this replay | Tables above |
| G4 ≥ 10 users prefer a hardware affordance and state purchase intent | **Not yet testable** (needs interviews; no data collected) | `docs/G4_user_study_design.md` |
| G5 host p95 ≤ 50 ms per request | **PASS** (host): p95 added 6.39 ms (D) / 1.91 ms (C) via the local proxy; algorithm only ≤ 3.97 ms | Latency table. Tamp's p95 was 48.81 ms on public data and 2458.86 ms on synthetic |
