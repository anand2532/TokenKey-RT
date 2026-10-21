"""Sensitivity: net cost vs B for variant S (5m TTL) as the modelled human-break probability per turn varies."""
from . import timing
from .replay_v2 import DATASETS, evaluate, load

if __name__ == "__main__":
    data = {n: load(p) for n, p, _ in DATASETS}
    print("| Break prob./turn | Mode | Public | Synthetic (SYNTHETIC) | Cost-weighted | Public cold starts |\n|---|---|---|---|---|---|")
    for bp in (0.0, 0.02, 0.05, 0.10):
        timing.BREAK_P = bp
        for mode in ("economy", "balanced", "quality"):
            e = {d: evaluate(data[d], 300.0, True, mode) for d in data}
            m = "claude-sonnet-4-6"
            pct = {d: 100 * (1 - e[d]["usd"][m]["S"] / e[d]["usd"][m]["B"]) for d in e}
            w = 100 * (1 - sum(e[d]["usd"][m]["S"] for d in e) / sum(e[d]["usd"][m]["B"] for d in e))
            print(f"| {bp:.2f} | {mode} | {pct['public']:.1f} % | {pct['synthetic']:.1f} % | {w:.1f} % | {e['public']['cold_starts']} |")
