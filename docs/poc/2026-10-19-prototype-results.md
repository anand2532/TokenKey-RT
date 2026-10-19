# TokenKey RT: Software-only Prototype Results (draft)

- **Date:** 2026-10-19
- **Status:** Draft for `docs/poc/`. Not committed. Companion to `2026-10-19-value-assessment.md` and `2026-10-19-poc-experiment-plan.md`.
- **Prototype:** `/tmp/tk_poc/prototype/` (Python; full tables in `results/REPORT.md`).

## Summary

- **G1 (≥ 20 % lower net API cost than the caching-on baseline): NOT PASSED. It hinges on real timestamped logs.**
  - Under the current PM defaults (newest tool output exempt from dedup), only Economy mode clears 20 %, and only at a 5-minute cache TTL with a *modelled* break rate: +20.3 % cost-weighted, +18.1 % on public real agent data.
  - Balanced is +14.4 % and Quality +8.7 %.
  - With a 1-hour TTL, savings fall below 5 %. With no breaks (always warm), they fall to +1.6 %.
- **G5 (added latency p95 ≤ 50 ms): PASSED.** Proxy-added p95 is 2.19-3.04 ms.
- **G2 (quality), G3 (vs free proxies at equal quality) and G4 (users): not yet testable.** They need an API key with a spend cap, real runs, and interviews.
- **The firmware context engine as written in firmware_architecture.md v0.1** (reduce the whole request each turn) *raises* net cost by 22-158 %, because it defeats provider prompt caching [S1][S2].
- **The main lesson:** once prompt caching is on, a reducer can only touch content when it first arrives, which is when the model needs it most. So safe savings are small unless the cache often goes cold.

## What was built

- **Algorithm:** a host-side port of the firmware context engine (firmware_architecture.md §2.3): XXH32 dedup set (8,192 slots, 75 % load cap), diff/code/log/prose scanner, integer ranking, Economy/Balanced/Quality keep ratios (25/50/85 %), bytes/4 estimate, 4,096-segment cap. 13 unit tests.
- **Variants:**
  - Firmware as written (D).
  - Cache-preserving tail-only (C).
  - Dedup-only (G).
  - PM defaults S-dedup (round 1), S-protect (current default) and S-collapse (middle variant).
- **Free proxies:** Tamp 0.8.21 [S5] and llmtrim 0.13.7 [S6], run locally.
- **Cost model:** published Anthropic prices and caching multipliers [S1][S2]: Sonnet 4.6 at $3 input / $3.75 5-minute cache write / $6 1-hour write / $0.30 cache read / $15 output per MTok; Opus 4.7 at $5 / $6.25 / $10 / $0.50 / $25.
- **Latency:** measured through a local proxy against a local mock upstream. No real provider calls were made.

## Data

- **Public real agent trajectories:** 30 sessions, 709 requests, from `nebius/SWE-agent-trajectories` [S3] (SWE-agent with open Llama models).
- **SYNTHETIC sessions:** 10 sessions, 310 requests, machine-generated (seed 42). They are labelled synthetic everywhere and are not evidence about real users.

## Results

### Current PM defaults (round 2): net cost vs caching-on baseline, Sonnet 4.6, positive = cheaper

| Variant | Setting | Economy (pub / syn / weighted) | Balanced | Quality | Newest output kept ≥ 90 % |
|---|---|---|---|---|---|
| S-protect (default) | 5-min TTL, modelled breaks | +18.1 / +24.1 / +20.3 % | +13.3 / +16.4 / +14.4 % | +8.8 / +8.4 / +8.7 % | 100 % of requests (pub and syn) |
| S-protect | 1-hour TTL, modelled breaks | +5.0 / +4.7 / +4.9 % | +4.3 / +3.2 / +3.9 % | +3.3 / +1.3 / +2.6 % | 100 % |
| S-protect | No breaks | +2.4 / +0.0 / +1.6 % (all modes) | same | same | 100 % |
| S-collapse (middle) | all three settings | identical to S-protect to one decimal | | | 100 % |

- **S-collapse:** the rule fired on 1 of 679 public tool outputs (saving 67 characters) and on 0 of 300 synthetic ones. Repeated content in agent outputs here is repeated across messages, not in consecutive runs.
- **For comparison, round 1** (newest output deduped; superseded): +31.2 / +25.3 / +19.6 % cost-weighted at the 5-min TTL. But only 41.5 % of public requests kept ≥ 90 % of the newest output. Dedup removed repeated error messages and tracebacks the agent needs.

### Earlier findings (first run, public data, Sonnet 4.6)

- **Firmware as written:** −22.4 % (Economy), −72.9 % (Balanced), −132.6 % (Quality), i.e. more expensive, even with 15-75 % fewer input tokens.
- **Cache-preserving with fixed ratios on new content:** +29 to +54 %, but the newest output kept ≥ 90 % in only 5-29 % of requests.
- **Free proxies under the same input-cost model:**
  - Tamp: −0.3 %.
  - llmtrim: −52.6 %. It sometimes toggles one system-prompt line between turns, which invalidates the cache.
  - Output-shortening features of both were not measured.
- **MCU constraints:** no CTX_OVERFLOW or dedup-set-full events. bytes/4 averaged 1.001× the stand-in tokenizer count.

## Gate status

| Gate (approved threshold) | Status |
|---|---|
| G1 ≥ 20 % net cost reduction vs caching-on baseline | **Not passed: hinges on real timestamped logs** |
| G2 quality drop ≤ 2 pp, required-context recall ≥ 98 % | Not yet testable. Design: 50 SWE-bench Lite tasks [S4] + own repos, 3 runs per arm |
| G3 ≥ best free proxy at equal quality | Not yet testable |
| G4 ≥ 10 users prefer a hardware affordance + purchase intent | Not yet testable. Interview protocol drafted; no data collected |
| G5 host p95 ≤ 50 ms | **Passed** (2.19-3.04 ms proxy-added p95) |

## Assumptions (labelled)

- **A1 Timing:** neither dataset has timestamps, so gaps are modelled per session: agent step lognormal (median 20 s, σ 0.8); a human break with 5 % probability per turn, log-uniform 2-120 minutes. This drives G1. A break-rate sweep in REPORT.md shows the dependence (that sweep is for the round-1 variant).
- **A2 Tokenizer:** tiktoken `o200k_base` [S7] stands in for Claude's tokenizer, which is not public. Exact counts need the token-counting API [S8].
- **A3 Outputs:** model replies are assumed identical across variants. Real effects need live runs (G2).
- **A4 Caching:** message-level cache prefixes; the cache is warm while gaps ≤ TTL; reads 0.1x, 5-min writes 1.25x, 1-hour writes 2x base input [S1][S2]; minimum cacheable 1,024 tokens (Sonnet), 4,096 (Opus) [S9].
- **A5 Public data:** SWE-agent sessions replayed as full-history resends. They are not Claude Code or Cursor sessions.
- **A6 Firmware choices:** the firmware doc leaves ten parameters open (weights, recency, reference count, dedup penalty, greedy rule, session scope, and others). Values are listed in the prototype README.
- **A7 PM interpretations (confirmed):** assistant messages are exempt from ratios; the ratio budget is counted on older tool output before dedup. Collapse marker N = total lines in the run (prototype choice).

## Needed next

1. Real, timestamped pay-per-token session logs (recording proxy provided; no API keys are logged). This decides G1.
2. An API key, a spend cap and approval for the G2 pilot (5 tasks × 2 arms) before the full quality run.
3. Interview recruiting and a price to test for G4 (externally visible; needs approval).

## Sources

- [S1] Anthropic, Pricing. https://platform.claude.com/docs/en/about-claude/pricing (accessed 2026-10-19)
- [S2] Anthropic, Prompt caching. https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- [S3] Nebius, SWE-agent trajectories dataset. https://huggingface.co/datasets/nebius/SWE-agent-trajectories
- [S4] SWE-bench Lite. https://www.swebench.com/lite
- [S5] Tamp. https://tamp.dev/ ; https://github.com/sliday/tamp
- [S6] llmtrim. https://github.com/fkiene/llmtrim
- [S7] OpenAI tiktoken. https://github.com/openai/tiktoken
- [S8] Anthropic, Token counting. https://platform.claude.com/docs/en/build-with-claude/token-counting
- [S9] Anthropic Cookbook, Prompt caching. https://platform.claude.com/cookbook/misc-prompt-caching
- Repo: `docs/baseline-specs.md` §7-§8; `firmware/docs/firmware_architecture.md` §2.3.
