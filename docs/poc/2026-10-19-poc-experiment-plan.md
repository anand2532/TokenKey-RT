# TokenKey RT: Software-only PoC Experiment Plan (draft)

- **Date:** 2026-10-19
- **Status:** Draft for review. Not committed. Companion to `2026-10-19-value-assessment.md`.
- **Budget assumption:** about 2-4 engineer-weeks plus API spend capped by the experimenter (e.g. a fixed $ budget set by Anand). No hardware purchases.

## Summary

Build a **host-only Python prototype** that reproduces the planned TokenKey firmware algorithm exactly: xxHash dedup, diff/code/log/prose classification, integer ranking, Economy/Balanced/Quality budgets, bytes/4 estimate (`firmware/docs/firmware_architecture.md` §2.3). Run it as a local proxy and as an offline trace replayer. Measure **real** token and dollar savings using provider-reported usage (including cached tokens) and **task quality** against baselines that already exist for free: no optimization, provider caching only, and open-source proxies.

The result maps one-to-one onto spec §7 and feeds the hardware go/no-go gates G1-G5 in the value assessment. **Spec §7 exists but has no numeric targets** (its bullet 6 defers targets until after prototype benchmarking), so every threshold below is a **proposal**.

## 1. Questions the PoC must answer

1. Q1: Does the TokenKey algorithm cut **net billed cost** (not just raw tokens) once provider prompt caching is counted? [S3][S4]
2. Q2: Does it keep task quality (no removal of required context)? Spec §7 bullet 4.
3. Q3: Does it beat free substitutes (Tamp, llmtrim, built-in compaction)? [S1][S10][S11]
4. Q4: What latency, throughput and memory does the algorithm need? This gives the MCU its target (spec §7 bullets 1-2).
5. Q5: Do users value the hardware-only affordances (approval button, ambient display, mode knob)? Simulated in software.

## 2. Prototype components (all software, Linux)

| # | Component | Description | Effort (estimate) |
|---|---|---|---|
| P1 | `tk_core` (Python, optional C extension) | Port of firmware §2.3: XXH32 per line/chunk, 8,192-slot dedup set, diff/fenced-code/log/prose scanner, integer score, greedy budget (25/50/85%), original-order output. Configurable "MCU limits" mode: 32 KB ring, 4,096 segments, bytes/4 estimator | 3-5 days |
| P2 | Logging proxy | Local HTTP proxy that tools reach via base URL (e.g. `ANTHROPIC_BASE_URL`, as Tamp documents [S10]). Records request/response JSON and the provider `usage` blocks (input, output, cache read/write tokens) | 2-3 days |
| P3 | Replayer | Re-sends recorded requests in variants A-F (below) to the same model, or estimates cost offline with provider token counting [S17] / tiktoken [S18] | 2-3 days |
| P4 | Quality harness | (a) Recorded real tasks with tests in Anand's own repos; (b) a 30-50 task subset of SWE-bench Lite (300 test instances, unit-test verified) [S19] | 3-5 days |
| P5 | "Virtual device" UI | Small terminal/GTK window simulating the OLED, encoder modes and approve/reject buttons, wired to P2. Used for the Q5 user test | 2 days |

## 3. Experimental variants

| ID | Variant | Purpose |
|---|---|---|
| A | No optimization, provider caching **off** where possible | Raw upper bound |
| B | No optimization, provider caching **on** (default tool behaviour) | **Primary baseline.** What users already get for free [S1][S3] |
| C | TokenKey `tk_core`, Balanced (50%), applied only to the **non-cached tail** of each request (cache-preserving) | Main candidate |
| D | TokenKey `tk_core`, Economy / Balanced / Quality applied to the full request (as the firmware draft specifies) | Tests the firmware design as written, including cache invalidation |
| E | Tamp (balanced preset) and/or llmtrim | Best free substitute [S10][S11] |
| F | C with "MCU limits" mode on (bytes/4, segment/slot caps) | Isolates the cost of MCU constraints vs a full-tokenizer host |

## 4. Workloads

- W1: ≥ 20 recorded real coding-agent sessions (Claude Code and/or Aider) from Anand's own projects, e.g. this KiCad/firmware repo. Record with P2.
- W2: 30-50 SWE-bench Lite instances run through one agent, with fixed model and seeds where the API allows [S19].
- W3: Synthetic stress: large diffs, repeated file reads, long logs. Measures throughput and dedup limits.

*Privacy:* recordings stay local on the box/laptop. Strip API keys from logs.

## 5. Metrics

| Metric | How measured | Source of truth |
|---|---|---|
| Input tokens (uncached / cache-read / cache-write), output tokens | Provider `usage` fields returned per request [S3][S4] | Provider |
| Net cost per task ($) | Tokens × the provider price table at test date [S3] | Calculated, with the price table version recorded |
| Token-estimate error | bytes/4 vs provider count_tokens [S17] / tiktoken [S18] | Provider / tokenizer |
| Task quality | Tests pass / SWE-bench resolved rate; for W1, blind A/B human rating by Anand | Harness |
| Required-context recall | For each task, the files/hunks in the final patch: % retained by the optimizer | Harness |
| Latency / throughput | Wall time of `tk_core` per request (p50/p95), MB/s; end-to-end request latency | Local timing |
| Memory | Peak RSS of `tk_core`; segment/slot utilisation; CTX_OVERFLOW count | Local |
| User preference (Q5) | 10+ target users try the virtual device vs a CLI-only flow; short survey | Survey |

## 6. Success criteria mapped to spec §7

| Spec §7 bullet | PoC measurement | Proposed pass threshold (assumption) |
|---|---|---|
| 1. MCU processing latency for representative text/code workloads | Host `tk_core` latency p95 on W1/W3; derive the MCU budget | Host p95 ≤ 50 ms per request. MCU target set at ≤ 10x host (to confirm on hardware) |
| 2. Throughput, RAM usage, maximum buffer size | MB/s, peak RAM, % of W1 requests that fit 4,096 segments / 8,192 slots / 32 KB ring streaming | ≥ 95% of W1 requests processed without CTX_OVERFLOW under MCU limits (variant F) |
| 3. Compare actual input-token counts and API costs before/after | Variant C (and D) vs **B**, using provider-billed usage | Net cost reduction ≥ 20% vs B (gate G1). Also report vs A for transparency |
| 4. Optimization does not remove required context or significantly degrade quality | Resolved/test-pass rate and required-context recall, C vs B | Quality drop ≤ 2 percentage points; required-context recall ≥ 98% |
| 5. USB stability, power, reset recovery, continuous operation | **Not testable in software.** Software proxy metric: P2+P1 soak test 8 h with no crash/leak | Soak passes. USB/power deferred to hardware phase |
| 6. Establish measurable targets after first prototype benchmark | This PoC produces the numeric baselines | Publish a measured-results table; turn the thresholds above into spec §7 numbers |

Additional gates (from the value assessment):

- G3 (substitute check): C ≥ E on net cost at equal quality. Otherwise the core value is not differentiated.
- G4 (hardware value): ≥ 10 target users; the majority prefer the virtual-device flow on at least one of approve/ambient/mode, and state purchase intent at a stated price.
- Spec §8 check: variant F vs C shows whether MCU constraints (bytes/4, caps) cost savings or quality.

## 7. Timeline (estimate)

| Week | Work |
|---|---|
| 1 | P1 `tk_core` port + unit tests against firmware §2.3 behaviour; P2 logging proxy; start W1 recording |
| 2 | P3 replayer; run variants A-F on W1; token/cost results |
| 3 | P4 quality harness on W2 subset; required-context recall |
| 4 | P5 virtual device + user test (Q5); write the results report and the go/no-go recommendation |

## 8. Decision outputs

- **Go to hardware** only if G1-G5 pass. Then lock spec §7 numbers from measured data and proceed to schematic/PCB review.
- **Pivot to software-only** if G1-G3 pass but G4 fails. Ship the companion app/proxy and drop the device or keep it optional.
- **Stop / rethink** if G1 or G2 fails.

## 9. Known limitations and risks of the PoC

- Agent runs are non-deterministic. Use repeated runs (≥ 3 per task/variant) and report variance.
- Provider prices and caching rules change. Record the date and price table used [S3][S4].
- Vendor savings claims for Tamp/llmtrim are unverified and only measured here [S10][S11].
- Subscription-plan users can't be measured in dollars [S1]. Report plan-limit usage separately if relevant.
- Sending recorded prompts to an API costs money and may include private code. Keep it to Anand's own repos and an agreed spend cap.

## Assumptions (labelled)

- All numeric thresholds above (20%, 2 pp, 98%, 50 ms, 95%, 10x, 10 users) are proposals, not spec requirements.
- Effort and timeline figures are estimates.
- The firmware algorithm description (v0.1 draft) is stable enough to port. If it changes, the port should follow it.

## Sources

- [S1] Anthropic, Claude Code "Manage costs effectively". https://code.claude.com/docs/en/costs
- [S3] Anthropic pricing / prompt caching. https://platform.claude.com/docs/en/about-claude/pricing ; https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- [S4] OpenAI prompt caching. https://developers.openai.com/api/docs/guides/prompt-caching
- [S10] Tamp. https://tamp.dev/ ; https://github.com/sliday/tamp
- [S11] llmtrim. https://github.com/fkiene/llmtrim
- [S17] Anthropic token counting. https://platform.claude.com/docs/en/build-with-claude/token-counting
- [S18] OpenAI tiktoken. https://github.com/openai/tiktoken
- [S19] SWE-bench Lite. https://www.swebench.com/lite ; https://huggingface.co/datasets/princeton-nlp/SWE-bench_Lite
- Repo: `docs/baseline-specs.md` §5, §7, §8; `firmware/docs/firmware_architecture.md` §2.3; `firmware/docs/usb_protocol.md`.
