# TokenKey RT: Software-only Prototype Results

- **Date:** 2026-10-19
- **Status:** Committed in PR #35. Offline G2-G4 update added 2026-10-19 (no paid API calls). Companion to `docs/poc/2026-10-19-value-assessment.md` and `docs/poc/2026-10-19-poc-experiment-plan.md`.
- **Prototype:** `software/poc-prototype/` (Python; full tables in `software/poc-prototype/results/REPORT.md`, offline proxies in `software/poc-prototype/results/offline_quality.md`).

## Summary

- **G1 (≥ 20 % lower net API cost than the caching-on baseline): NOT PASSED. It hinges on real timestamped logs.**
  - Under the current PM defaults (newest tool output exempt from dedup), only Economy mode clears 20 %, and only at a 5-minute cache TTL with a *modelled* break rate: +20.3 % cost-weighted, +18.1 % on public real agent data.
  - Balanced is +14.4 % and Quality +8.7 %.
  - With a 1-hour TTL, savings fall below 5 %. With no breaks (always warm), they fall to +1.6 %.
- **G5 (added latency p95 ≤ 50 ms): PASSED.** Proxy-added p95 is 2.19-3.04 ms.
- **G2 (quality): not passed / not testable offline.** Offline *proxies* (not true quality): S-protect keeps 99.9-100 % of the files/identifiers the agent used in its next turn and 100 % of error lines in the newest tool output, on public and synthetic data. True task success needs live model runs.
- **G3 (vs free proxies): not decidable at equal quality; offline proxies favour TokenKey S-protect.** llmtrim keeps the proxies at 100 % but raises cost (−43 % public, −6.5 % synthetic). Tamp saves +11.5 % on public data but keeps only 41.5 % of next-turn references (possibly understated, see below). S-protect Economy: +18.1 % with 99.9 % reference recall.
- **G4 (users/hardware): not testable without interviews.** Desk research finds demand for token-usage *visibility* (ccusage ≈19.1k GitHub stars, DIY e-ink Claude usage meters) and paid hardware for AI-coding *control* ($29-$99.99 keypads), but no public evidence of willingness to pay for token-*reduction* hardware.
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

## Offline G2/G3 proxies (no model calls; PROXIES, NOT TRUE QUALITY)

Method (`software/poc-prototype/tokenkey_poc/offline_quality.py`): for each replayed request, take the file paths and code identifiers that the *recorded* next assistant turn mentions and that appear in the original context, and check (substring) whether they survive in the reduced context. Same for error lines (tracebacks, `...Error:`, `FAILED`) in the newest tool output and in the whole context. Public: 684 requests with ≥ 1 reference (3,225 references), 325 with newest-output errors. Synthetic: 140 (280) and 180. Cost: Sonnet 4.6, 5-min TTL, modelled breaks, vs caching-on baseline B.

| Variant | Public: ref recall / all-refs-kept requests / newest-error recall / net cost | SYNTHETIC: same |
|---|---|---|
| S-protect Economy (= S-collapse) | 99.9 / 99.6 / 100.0 % / **+18.1 %** | 100 / 100 / 100 % / +24.1 % |
| S-protect Balanced | 99.9 / 99.7 / 100.0 % / +13.3 % | 100 / 100 / 100 % / +16.4 % |
| S-protect Quality | 100 / 100 / 100 % / +8.8 % | 100 / 100 / 100 % / +8.4 % |
| S-dedup Economy (round 1) | 99.9 / 99.4 / 98.6 % / +28.0 % | 100 / 100 / 85.1 % / +36.9 % |
| G dedup-only | 100 / 100 / 100 % / +17.0 % | 100 / 100 / 100 % / +18.3 % |
| C tail-only Economy | 71.7 / 62.3 / 28.1 % / +59.0 % | 80.7 / 80.7 / 2.1 % / +85.3 % |
| D firmware as written, Economy | 78.9 / 70.9 / 29.5 % / −4.2 % | 100 / 100 / 67.8 % / +3.0 % |
| D firmware as written, Quality | 97.0 / 93.4 / 91.5 % / −104.9 % | 100 / 100 / 100 % / −84.3 % |
| llmtrim agent (cache markers) | 100 / 100 / 100 % / −43.2 % | 100 / 100 / 100 % / −6.5 % |
| llmtrim agent (no markers) | 97.6 / 95.0 / 83.2 % / −41.2 % | 100 / 100 / 100 % / −6.6 % |
| Tamp 0.8.21 default | 41.5 / 32.4 / 20.6 % / +11.5 % | 96.4 / 96.4 / 55.1 % / −12.1 % |

Reading and caveats:
- Against the G2 recall bar (≥ 98 %), S-protect at every mode, S-dedup and G pass *the proxy*; C and D fail it. This is not G2: surviving text does not prove the model acts the same, and missing text does not prove failure (the agent can re-read).
- References come from the original (unreduced) run, which biases toward what that context showed.
- Substring matching is lenient for dedup variants (an earlier identical copy counts as present) and harsh for Tamp, which rewrites formats (e.g. minifies), so Tamp's recall may be understated.
- The Tamp public cost here (+11.5 %) differs from the first-run −0.3 % because the replay now sends agent-style `tool_result` blocks, which Tamp compresses; first-run figure is superseded.
- **G dedup-only** reaches +17 % public / +18.3 % synthetic with full proxy recall; it should be a G2 arm.
- A local open-model judge was not used: no local LLM runtime is installed and an 8-core CPU run over ~1,000 long contexts was not practical. Deterministic checks were used instead.

## G4 desk research (not testable without interviews)

Public evidence, not user research:
- **Demand for token-usage visibility (software, free):** ccusage, a local CLI reporting coding-agent token use and cost, has ≈19.1k GitHub stars and ≈880 forks [S10].
- **Paid market for LLM cost/observability tools:** Helicone reports 16,000 organizations and 14.2 T tokens processed before its acquisition by Mintlify (2026-03-03) [S11]; ClickHouse acquired Langfuse (2026-01-16), citing 20k+ stars and 26M+ monthly SDK installs [S12]; 63 % of State of FinOps 2025 respondents manage AI spend, up from 31 % [S13].
- **Hardware interest (DIY, unpaid):** several open-source desk displays show Claude Code usage limits on e-ink/AMOLED ESP32 boards (Clawdometer, claude-usage-epaper, TokenGenie), and one adds hardware tool-approval buttons (m5-paper-buddy) [S14].
- **Paid hardware for AI coding (control, not cost):** VibeKeys Pro $29 (accept/reject/"Usage" keys) [S15]; AhaKey X1 $79.90 [S16]; Logitech MX Keypad $99.99 (reported via search, not verified on the vendor page) [S17].
- **Gap:** none of this shows willingness to pay for *token-reduction* hardware; the DIY meters track subscription rate limits rather than API spend. G4 (≥ 10 users preferring a hardware affordance plus purchase intent) needs interviews.

## Gate status

| Gate (approved threshold) | Status |
|---|---|
| G1 ≥ 20 % net cost reduction vs caching-on baseline | **Not passed: hinges on real timestamped logs** |
| G2 quality drop ≤ 2 pp, required-context recall ≥ 98 % | **Not passed (untested): needs live model runs.** Offline proxy: S-protect 99.9-100 % next-turn reference recall, 100 % newest-error recall. Design: 50 SWE-bench Lite tasks [S4] + own repos, 3 runs per arm |
| G3 ≥ best free proxy at equal quality | **Not passed (untested at equal quality).** Proxy comparison favours S-protect: +18.1 % at 99.9 % recall vs Tamp +11.5 % at 41.5 % and llmtrim −43.2 % at 100 % (public) |
| G4 ≥ 10 users prefer a hardware affordance + purchase intent | **Not testable without interviews.** Desk research: demand for usage visibility and $29-$99.99 AI-coding keypads exists; no evidence for token-reduction hardware |
| G5 host p95 ≤ 50 ms | **Passed** (2.19-3.04 ms proxy-added p95) |

## Assumptions (labelled)

- **A1 Timing:** neither dataset has timestamps, so gaps are modelled per session: agent step lognormal (median 20 s, σ 0.8); a human break with 5 % probability per turn, log-uniform 2-120 minutes. This drives G1. A break-rate sweep in REPORT.md shows the dependence (that sweep is for the round-1 variant).
- **A2 Tokenizer:** tiktoken `o200k_base` [S7] stands in for Claude's tokenizer, which is not public. Exact counts need the token-counting API [S8].
- **A3 Outputs:** model replies are assumed identical across variants. Real effects need live runs (G2).
- **A4 Caching:** message-level cache prefixes; the cache is warm while gaps ≤ TTL; reads 0.1x, 5-min writes 1.25x, 1-hour writes 2x base input [S1][S2]; minimum cacheable 1,024 tokens (Sonnet), 4,096 (Opus) [S9].
- **A5 Public data:** SWE-agent sessions replayed as full-history resends. They are not Claude Code or Cursor sessions.
- **A6 Firmware choices:** the firmware doc leaves ten parameters open (weights, recency, reference count, dedup penalty, greedy rule, session scope, and others). Values are listed in the prototype README.
- **A7 PM interpretations (confirmed):** assistant messages are exempt from ratios; the ratio budget is counted on older tool output before dedup. Collapse marker N = total lines in the run (prototype choice).

## Still needs real logs, API runs or interviews

1. **G1 – real timestamped logs:** pay-per-token Claude Code/Cursor sessions with timestamps (recording proxy `tokenkey_poc/record_proxy.py`; no API keys are logged). Break rate and gap distribution decide G1; everything above uses modelled timing (A1).
2. **G1 – exact token counts:** Anthropic token-counting API [S8] instead of the tiktoken stand-in (A2). Free endpoint, but needs a key.
3. **G2 – live quality runs (paid; blocked by the no-paid-API instruction):** SWE-bench Lite + own repos, arms B / S-protect / G dedup-only / Tamp / llmtrim, 3 runs each; pilot 5 tasks × 2 arms first.
4. **G2/G3 – real output effects:** outputs were assumed identical across variants (A3); output length and retries need live runs.
5. **G3 – equal-quality comparison:** needs G2 data for every arm.
6. **G4 – interviews:** ≥ 10 users, recruiting and price test (externally visible; needs approval).
7. **Claude Code / Cursor data:** public data is SWE-agent with open models (A5).

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
- [S10] ccusage. https://github.com/ccusage/ccusage (accessed 2026-10-19)
- [S11] Helicone, "Helicone is joining Mintlify", 2026-03-03. https://www.helicone.ai/blog/joining-mintlify ; https://www.mintlify.com/blog/mintlify-acquires-helicone
- [S12] ClickHouse, Series D and Langfuse acquisition, 2026-01-16. https://clickhouse.com/blog/clickhouse-raises-400-million-series-d-acquires-langfuse-launches-postgres
- [S13] FinOps Foundation, State of FinOps 2025. https://data.finops.org/2025-report/
- [S14] https://github.com/nsyll/clawdometer-eink ; https://github.com/Pharkie/claude-usage-epaper ; https://github.com/Jensen-JZ/token-genie ; https://github.com/op7418/m5-paper-buddy
- [S15] VibeKeys Pro. https://vibekeys.dev/vibekeys-pro.html
- [S16] AhaKey X1. https://finalkeystudio.com/products/finalkey-x-ahakey-x1-vibe-coding-macro-keyboard
- [S17] Logitech MX Keypad. https://www.logitech.com/en-us/shop/p/mx-keypad
- Repo: `docs/baseline-specs.md` §7-§8; `firmware/docs/firmware_architecture.md` §2.3.
