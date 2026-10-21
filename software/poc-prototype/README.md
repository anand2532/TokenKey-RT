# TokenKey RT software-only PoC prototype

**Summary:** Python harness (now also variant S = TokenKey PM defaults: `session_reducer.py`, `timing.py`, `replay_v2.py`, `break_sweep.py`; results in `results/REPORT.md` top section) that ports the firmware context engine (`firmware/docs/firmware_architecture.md` v0.1 §2.3) to the host. It replays agent sessions through it and through free proxies (Tamp, llmtrim), and computes tokens, net $ against a caching-on baseline (G1) and added latency (G5). Results: `results/REPORT.md`. Designs for gates that need real users or an API key: `docs/`. **SYNTHETIC data is labelled everywhere it appears.** Built 2026-10-19; committed as `software/poc-prototype/`. Summary report: `docs/poc/2026-10-19-prototype-results.md`. Offline G2/G3 proxies: `tokenkey_poc/offline_quality.py` → `results/offline_quality.md`.

## Layout

| Path | What |
|---|---|
| `tokenkey_poc/tk_core.py` | Firmware algorithm port ([SPEC] items as written; [CHOICE] items listed in `UNSPECIFIED_CHOICES`) |
| `tokenkey_poc/costmodel.py`, `prices.py` | Tokenizer proxy (tiktoken o200k_base) and prompt-caching cost model with cited prices |
| `tokenkey_poc/variants.py` | A no-cache, B caching baseline, C cache-preserving tail-only, D full-request (firmware as written), F host without MCU caps, G dedup-only extension, E llmtrim |
| `tokenkey_poc/proxy.py` | Local mock upstream, TokenKey proxy (P2), Tamp runner, added-latency bench |
| `tokenkey_poc/record_proxy.py` | Recording pass-through proxy for REAL sessions (needs an API key; smoke-tested only against a local mock) |
| `tokenkey_poc/sessions.py` | Public data fetcher (HF `nebius/SWE-agent-trajectories`), SYNTHETIC generator, `from_proxy_log()`, best-effort `from_claude_code_transcript()` (untested on real files) |
| `tokenkey_poc/replay.py` | Runs all variants and writes `results/results.{json,md}` |
| `tokenkey_poc/dedup_share.py` | Lossless-duplicate share diagnostic |
| `tests/test_tk_core.py` | 13 unit tests for the firmware behaviours |
| `data/public_swe_agent_trajectories.jsonl` (fetched, not committed) | 30 public real trajectories (source: https://huggingface.co/datasets/nebius/SWE-agent-trajectories) |
| `data/SYNTHETIC_sessions.jsonl` (generated, not committed) | 10 SYNTHETIC sessions (seed 42) |
| `tokenkey_poc/offline_quality.py` | Offline G2/G3 proxies (next-turn reference and error-line survival); PROXIES, NOT TRUE QUALITY |
| `tools/tamp/` | `package.json` for `@sliday/tamp@0.8.21` (`npm ci`); llmtrim 0.13.7 via requirements.txt |

## Run

```sh
cd software/poc-prototype
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
./fetch_data.sh   # data/ and tools/tamp/node_modules are not committed
python -m pytest -q tests
python -m tokenkey_poc.replay data/SYNTHETIC_sessions.jsonl data/public_swe_agent_trajectories.jsonl --out results   # ~4.5 min
python -m tokenkey_poc.dedup_share data/*.jsonl
python -m tokenkey_poc.offline_quality --out results   # ~8.5 min; offline proxies, no model calls
```

Real sessions (Anand): start `python -m tokenkey_poc.record_proxy --log data/real_log.jsonl`, then run Claude Code with `ANTHROPIC_BASE_URL=http://127.0.0.1:8787` on API-key billing. Afterwards, convert the log with `sessions.from_proxy_log()`. Replay support for logs with real `usage` still needs a small adapter, roughly half a day of work.

## Ambiguities in firmware v0.1 that change results (decisions needed)

1. **What a "job" is on the host:** the whole API request every turn (D) or only new messages (C). D breaks prompt caching.
2. **Dupset scope:** "never evicted mid-session" with no definition of a session. I used job scope for D and session scope for C and G.
3. **Weights, recency, reference count and dup-penalty values:** only the weight order is specified.
4. **Greedy rule:** score/size density favours small prose over large code blocks (see the unit test). A first-fit skip-and-continue rule was assumed.
5. **The fixed keep ratio (25/50/85 %) also applies to the newest content:** no protection for the latest tool output or the user task.
6. **Host behaviour on CTX_OVERFLOW:** I assumed the original request is passed through unreduced.

## Assumptions (labelled)

- The o200k_base tokenizer stands in for Claude's tokenizer.
- Outputs are identical across variants.
- All turns fall within the cache TTL.
- Message-level cache prefixes are used.
- The public trajectories are replayed as full-history resends.
- Latency is measured on this box against a local mock, with no provider or network time.
