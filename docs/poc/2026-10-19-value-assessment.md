# TokenKey RT: Value Assessment (draft)

- **Date:** 2026-10-19
- **Status:** Draft for review. Not committed to the repo; intended for `docs/poc/` once the owner has set up `docs/poc/README.md`.
- **Inputs read:** `docs/baseline-specs.md` (sections 1, 5, 7, 8 in particular), `docs/decisions.md`, `firmware/docs/firmware_architecture.md`, `firmware/docs/usb_protocol.md`.

## Summary

**Recommendation: NO-GO on hardware spend (PCB fab, assembly, enclosure) for now. GO on a 2-4 week software-only PoC** (see `2026-10-19-poc-experiment-plan.md`). Re-decide on hardware only if the PoC clears the gates in section 7 of this document.

Why:

1. **The problem is real and measurable.** Anthropic gives an average of about $13 per developer per active day and $150-250 per developer per month for Claude Code in enterprise deployments [S1]. Research shows longer inputs make LLMs less reliable even on simple tasks [S2]. A focused ~300-token prompt beat the full ~113k-token prompt in every model family tested [S2].
2. **The value comes from software, and software substitutes are already free.** Spec section 8 itself says "Token savings must come from verified software optimizations, not MCU clock speed alone." Provider prompt caching bills repeated input at 0.1x of the base input price on most Anthropic and current OpenAI models [S3][S4]. Claude Code already caches and auto-compacts by default [S1]. Open-source local proxies already claim 30-50%+ token savings for Claude Code, Cursor and Aider [S10][S11]. Spend tracking already exists in LiteLLM, Langfuse (both self-hostable for free) and Helicone (free tier) [S7][S8][S9].
3. **No evidence yet that the hardware adds value.** We found no cited source showing that developers want, or would pay for, a dedicated USB device for token optimization. The host laptop CPU can run the same algorithm (assumption A3). The hardware-only benefits we can see (physical approve button, always-on spend display, mode knob) are untested hypotheses.
4. **The current firmware design may raise costs in caching-heavy workflows.** It reorders and drops segments by mode budget (25/50/85%). If that changes the cached prompt prefix, it can turn cheap 0.1x cache reads into 1.25x cache writes [S3]. See section 4.

## 1. What the spec asks for (repo check)

| Spec item | Status in repo | Relevance |
|---|---|---|
| §1 Objective: USB device for token optimization, context reduction, request analysis, cost monitoring | Present | Defines the value claim tested here |
| §5 Laptop software: provider-specific token counting, actual usage/cost tracking, caching support, prompt preview/approval, local-first privacy, before/after measurement of tokens, cost, latency, quality | Present. `software/` holds only a README, so no companion app exists yet | All the measurable value sits on the host side |
| §7 Performance and validation goals | **Present** (6 bullets). Bullet 6 says numeric targets are set "after benchmarking the first prototype", so **§7 has no numeric success thresholds today** | The PoC plan proposes thresholds (labelled as proposals) |
| §8 Constraints: MCU accelerates processing but runs no LLM; savings must come from software, not clock speed | Present | Directly supports a software-first PoC |
| Firmware architecture v0.1: xxHash dedup, diff/code/log/prose classifier, integer ranking, mode budgets 25/50/85%, token estimate = bytes/4 | Present (draft) | The PoC can reproduce this algorithm on the host exactly |
| Firmware open question 7: "Is the Linux companion app existing or new?" | Open | Confirms the app does not exist yet |

**Gaps found in the repo:** no numeric §7 targets; no companion app code; no target-user definition, pricing, BOM cost target or competitor analysis anywhere in the docs; and the token estimator choice (bytes/4 vs tokenizer table) is still open (firmware open question 6).

## 2. Target users

| Segment | Evidence | Who pays per token? | Fit |
|---|---|---|---|
| Professional developers using AI coding tools daily | 84% of Stack Overflow 2025 respondents use or plan to use AI tools. 50.6% of professional developers use them daily [S5] | Mixed. Many are on flat subscriptions | Large pool, but see the next row |
| Subscription users (Claude Pro/Max/Team, Copilot, Cursor plans) | Claude Code docs: for Pro/Max subscribers "the session cost figure isn't relevant for billing purposes"; usage counts against plan limits [S1] | Vendor (flat fee) | **Weak.** Savings show up as fewer limit hits, not dollars |
| API-key / pay-per-token users (indie devs, startups, enterprise Console/Bedrock/Vertex accounts) | Claude Code bills per token on the Console and on cloud providers [S1] | User or employer | **Best fit** for cost savings |
| Individual developers paying out of pocket | Findy (Japan, 605 engineers, June 2025): 47.1% pay personally for AI tools, averaging ¥5,776/month [S6] | Individual | Small budgets. A hardware price must be justified against roughly $40/month of spend (currency conversion is approximate) |
| Platform/FinOps teams managing org AI spend | Claude Code docs point teams to OpenTelemetry, LLM gateways and LiteLLM for per-user spend [S1] | Employer | Wants fleet-wide gateways, **not per-desk devices** |

**Assumption A1:** the beachhead is pay-per-token developers on Linux (spec §5 is Linux-first). Their size is **unknown**; we found no cited figure.

## 3. Size of the problem

- **Token spend:** about $13 per developer per active day on average, $150-250 per developer per month, and below $30 per active day for 90% of users (Anthropic, enterprise Claude Code) [S1]. Business Insider reports Anthropic more than doubled these public estimates in April 2026 [S12].
- **Where the money goes (worked example, not representative):** the Claude Code docs show a sample session with 1.2k input, 5.3k output, 940.0k cache-read and 50.0k cache-write tokens on Sonnet 4.6, totalling $0.55 [S1]. At the cited Sonnet 4.6 prices ($3 input, $15 output, $0.30 cache read, $3.75 5-minute cache write per MTok [S3]), that splits into roughly 51% cache reads, 34% cache writes, 14% output and under 1% uncached input. *Our calculation from one sample session.* It suggests that in agentic tools **most input is already billed at the cache rate**, so the extra saving from cutting input is smaller than raw token counts imply.
- **Context bloat hurts quality as well as cost:** Chroma tested 18 models. Performance "consistently degrades with increasing input length". Focused ~300-token prompts beat full ~113k-token prompts across all model families [S2]. This is the strongest argument for context reduction, and it holds whatever the price.
- **Anthropic's own cost guidance** recommends `/clear`, custom `/compact`, hooks that pre-filter logs and test output, and smaller models [S1]. Those are free behavioural fixes that compete with TokenKey.

## 4. Competitors and substitutes

| Category | Examples (cited) | What they already do | Gap TokenKey could fill |
|---|---|---|---|
| Provider prompt caching | Anthropic: reads at 0.1x base input, 5-minute writes at 1.25x, 1-hour writes at 2x [S3]. OpenAI: automatic for prompts of 1,024+ tokens; current models charge 0.1x for reads and 1.25x for writes [S4] | Up to ~90% off repeated input, with zero effort | None directly. **Risk:** prefix-changing compression defeats it |
| Built-in agent context management | Claude Code: automatic caching, auto-compaction, `/clear`, `/compact`, hooks, skills, `/context`, `/usage` with cache hit stats [S1]. Aider repo map: tree-sitter ranking within a token budget (`--map-tokens`) [S13] | Context selection and visibility inside the tool | Cross-tool, vendor-neutral view |
| Context-compression proxies / libraries | Tamp (MIT local proxy; claims 52.6% token savings for Claude Code, Codex CLI, Cursor, Aider) [S10]. llmtrim (local proxy; claims -31% input / -74% output; repo shows 0 stars) [S11]. LLMLingua (up to 20x compression with a 1.5-point drop on GSM8K) [S14]. LongCodeZip (up to 5.6x code-context compression without degradation, per the authors) [S15] | The same job as TokenKey's core, free, on the host | **These vendor claims are unverified.** The PoC should benchmark them |
| Gateways / observability | LiteLLM (open source: per-key/user/team spend tracking and budgets) [S7]. Langfuse (MIT, free to self-host, token and cost tracking) [S8]. Helicone (free 10k requests/month; Pro $79/month; caching, cost tracking) [S9] | Cost monitoring, budgets, caching | A glanceable, physical, local display |
| Hardware | None found in our searches (absence of results ≠ absence of products) | n/a | Possibly a novel niche, or no demand at all |

## 5. Why hardware instead of software only?

**Cited facts:** spec §8 says savings must come from software. Every substitute above runs on the host or in the cloud at little or no cost.

**Possible hardware value (all hypotheses, unvalidated):**

- H1 *Physical consent:* a button/encoder approval step for modified prompts (spec §5 asks for "preview and approval"). It can't be faked by a runaway agent loop, provided the host app enforces it.
- H2 *Ambient awareness:* the OLED shows live spend and savings without switching windows.
- H3 *Tangible mode control:* an Eco/Balanced/Quality knob.
- H4 *Novelty / gift / desk-gadget appeal* for enthusiasts.

**Arguments against (analysis):**

- A3 (assumption): a laptop x86/ARM CPU runs xxHash, classification and ranking faster than a 600 MHz Cortex-M7, with no USB round trip. So the "accelerator" framing in spec §1 is unlikely to hold. The firmware also caps a job at 4,096 segments and 8,192 dedup slots, and estimates tokens as bytes/4 instead of using a provider tokenizer.
- Privacy is not improved: prompt text still passes through the host, which also holds the API keys and the TLS session.
- A device adds BOM, certification, support and a second update channel. **Reference point only:** a Teensy 4.1 dev board on the same RT1062 MCU retails at $31.50 [S16]. That is not our BOM cost, which is still unknown.

## 6. Willingness to pay

- Findy (Japan, June 2025, 605 engineers): 47.1% pay personally for AI tools, averaging ¥5,776/month [S6].
- **No source found** on willingness to pay for a token-optimization *device* or *tool* specifically. We have not invented a price point.
- Substitutes cost $0 (Tamp, llmtrim, LiteLLM, self-hosted Langfuse) [S7][S8][S10][S11]. A device has to beat free on something other than savings, i.e. H1-H4.
- **Assumption A4 (to test):** a pay-per-token user spending $150-250/month [S1] who gets X% net savings saves $1.5X-2.5X per month. The device payback needs X to be verified on real traces *net of caching effects*.

## 7. Risks (ranked)

1. **Substitution / no hardware moat (high):** free software and built-in features already cover dedup, compression, caching and cost tracking [S1][S3][S7]-[S11]. Model vendors keep improving context management, and the Claude Code cost docs changed several times in 2026 [S1][S12].
2. **Net savings may be small or negative once caching is counted (high):** most agent input is billed at 0.1x cache rates [S1][S3]. Dropping or reordering segments can invalidate cached prefixes (1.25x-2x writes) [S3]. Gross token reduction ≠ cost reduction.
3. **Quality loss (high):** greedy keep-ratio budgets (Economy keeps 25% of input) can drop required context. Compression papers report task-dependent drops (e.g. LLMLingua BBH −13.2 EM at 7x) [S14]. Spec §7 bullet 4 requires showing this doesn't happen.
4. **Market fit / buyer mismatch (medium-high):** subscription users don't see per-token dollars [S1]. Org buyers prefer gateways [S1]. No WTP data for a device.
5. **Integration fragility (medium):** each tool must be pointed at a local proxy (base-URL or HTTPS_PROXY + CA) [S10][S11]. Tool and API changes break this.
6. **Technical (medium):** bytes/4 estimates vs real tokenizers [S17][S18]. MCU buffer limits vs 100k+-token contexts. USB adds latency.

## 8. Go/no-go gates for hardware (proposed, to confirm with Anand)

Fund the first PCB/fab only if **all** of these hold on the software PoC:

- G1 Net API cost (with provider caching on in the baseline) drops ≥ 20% on pay-per-token traces. *Proposed threshold, an assumption.*
- G2 Task quality is non-inferior: resolved-rate or test-pass drop ≤ 2 percentage points vs baseline. *Proposed.*
- G3 TokenKey's algorithm beats or matches the best free proxy (Tamp/llmtrim) on G1 at equal quality. Otherwise the value is not ours.
- G4 At least one hardware-specific benefit (H1-H3) is preferred by most of ≥ 10 target users in a quick usability test, plus a stated purchase intent at a defined price. *Proposed.*
- G5 Host-side processing latency ≤ 50 ms p95 per request. This becomes the bar the MCU must also meet, feeding spec §7 bullet 1. *Proposed.*

## Assumptions (labelled)

- A1: the beachhead is Linux pay-per-token developers. Size unknown.
- A2: the Claude Code sample session in [S1] illustrates the cost mix. It is one example, not a distribution.
- A3: a host CPU outperforms the RT1062 for this workload. Not measured; the PoC measures host latency.
- A4: savings → payback arithmetic is illustrative only. No measured X yet.
- All thresholds in section 8 are proposals, not requirements from the spec.

## Sources

- [S1] Anthropic, "Manage costs effectively", Claude Code Docs. https://code.claude.com/docs/en/costs (accessed 2026-10-19)
- [S2] Hong, Troynikov, Huber, "Context Rot: How Increasing Input Tokens Impacts LLM Performance", Chroma, July 2025. https://www.trychroma.com/research/context-rot
- [S3] Anthropic, Pricing and Prompt caching docs. https://platform.claude.com/docs/en/about-claude/pricing ; https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- [S4] OpenAI, Prompt caching guide. https://developers.openai.com/api/docs/guides/prompt-caching ; "Prompt Caching in the API" https://openai.com/index/api-prompt-caching/
- [S5] Stack Overflow Developer Survey 2025, AI section. https://survey.stackoverflow.co/2025/AI
- [S6] Findy Inc., IT/Web engineer generative AI survey, 2025-06-30. https://findy.co.jp/3038/
- [S7] LiteLLM docs: Spend Tracking, Budgets. https://docs.litellm.ai/docs/proxy/cost_tracking ; https://docs.litellm.ai/docs/proxy/users
- [S8] Langfuse, Self-hosted pricing and cost tracking. https://langfuse.com/pricing-self-host ; https://langfuse.com/docs/model-usage-and-cost
- [S9] Helicone pricing. https://www.helicone.ai/pricing
- [S10] Tamp. https://tamp.dev/ ; https://github.com/sliday/tamp (vendor claims)
- [S11] llmtrim. https://github.com/fkiene/llmtrim (vendor claims)
- [S12] Business Insider, "Anthropic Doubles Estimate for Claude Code Token Spend", April 2026. https://www.businessinsider.com/anthropic-claude-code-token-estimates-2026-4
- [S13] Aider, Repository map. https://aider.chat/docs/repomap.html
- [S14] Jiang et al., "LLMLingua", EMNLP 2023. https://aclanthology.org/2023.emnlp-main.825/ ; https://arxiv.org/abs/2310.05736
- [S15] "LongCodeZip: Compress Long Context for Code Language Models", ASE 2025. https://arxiv.org/abs/2510.00446
- [S16] SparkFun / PJRC, Teensy 4.1. https://www.sparkfun.com/teensy-4-1.html ; https://www.pjrc.com/store/teensy41.html
- [S17] Anthropic, Token counting. https://platform.claude.com/docs/en/build-with-claude/token-counting
- [S18] OpenAI, tiktoken. https://github.com/openai/tiktoken
