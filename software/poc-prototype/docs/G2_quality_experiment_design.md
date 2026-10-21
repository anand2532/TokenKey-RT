# G2 quality experiment design (NOT RUN: needs an API key and spend approval)

**Summary:** G2 asks whether reduction keeps task quality (approved threshold: resolved/test-pass drop ≤ 2 percentage points vs the caching-on baseline B; required-context recall ≥ 98 %). This can only be measured by running a real model on real tasks with and without reduction. Nothing below has been run. No quality numbers exist yet.

## Design

- **Tasks:** 50 instances from SWE-bench Lite (300 test instances, unit-test verified; https://www.swebench.com/lite), fixed list with seed 0, plus 10-20 tasks from Anand's own repos that have tests.
- **Agent:** one agent, model and settings fixed for every arm (e.g. Claude Code with `ANTHROPIC_BASE_URL` pointing at the TokenKey proxy, or mini-SWE-agent). Temperature fixed where the API allows it.
- **Arms:**
  - B: caching on, no reduction.
  - C-quality, C-balanced: firmware algorithm, cache-preserving.
  - G: dedup-only extension.
  - E: Tamp and llmtrim, default settings.
  - D-balanced: firmware as written. Optional, since replay already shows a cost increase.
- **Repeats:** 3 runs per task per arm. Pass@1 is the mean over runs, and every run is logged by `record_proxy` so G1 can be recomputed from **real billed usage**.
- **Primary metric:** resolved rate (SWE-bench harness, `python -m swebench.harness.run_evaluation`). Non-inferiority margin: 2 pp; test with a paired bootstrap over tasks, 95 % CI.
- **Secondary metrics:**
  - Required-context recall: the share of the files/hunks touched by the gold patch whose content stayed in the sent context.
  - Number of turns, output tokens, and real $ from `usage`.
- **Budget (estimate, an assumption):** cost per run is unknown until the pilot. Run a pilot first (5 tasks × 2 arms × 1 run), then extrapolate and ask Anand to approve a spend cap.
- **Pass rule:** an arm passes G2 if the upper CI bound of (B − arm) is ≤ 2 pp and recall is ≥ 98 %.
- **What replay already suggests (not G2):** under the required-context proxy, C-balanced keeps ≥ 90 % of the newest message in only 17 % of public-trajectory requests. Expect C-balanced and C-economy to fail. C-quality and G are the real candidates.


## Added arm (2026-10-21, per TokenKey PM)

- **Dedup-only (G):** exact-duplicate removal only, with no keep ratios. In the offline proxy it scored 100% next-turn reference recall and 100% newest-error recall at +17.0% net (public data). It runs alongside the baseline, S-protect (Economy, Balanced, Quality), Tamp and llmtrim.
