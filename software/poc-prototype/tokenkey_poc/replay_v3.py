"""PM decisions 2026-10-19 (second round): newest tool output exempt from cross-message dedup (new default,
'S-protect') and a middle variant 'S-collapse' (exempt from dedup + collapse >3 identical consecutive lines inside
the newest output, first traceback/error block untouched). Same timing/billing model as replay_v2.

Usage: python -m tokenkey_poc.replay_v3 --out results   -> results/v3_results.{json,md}
"""
from __future__ import annotations

import argparse
import json
import os
import time

from .replay import pctl
from .replay_v2 import DATASETS, MODES, evaluate, load, proxy_latency

VARIANTS = [("S-protect (new default: newest output exempt from dedup)", "protect"),
            ("S-collapse (middle: exempt from dedup + collapse >3 repeated lines in newest output)", "collapse"),
            ("S-dedup (previous run, for reference: newest output deduped)", "dedup")]
SETTINGS = [("5-min TTL, modelled breaks", 300.0, True),
            ("1-hour TTL, modelled breaks", 3600.0, True),
            ("No breaks (always warm, 5-min TTL)", 300.0, False)]
M = "claude-sonnet-4-6"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default="results"); a = ap.parse_args()
    data = {n: load(p) for n, p, _ in DATASETS}
    res = []
    for vname, pol in VARIANTS:
        for sname, ttl, breaks in SETTINGS:
            for mode in MODES:
                e = {d: evaluate(data[d], ttl, breaks, mode, newest_policy=pol) for d in data}
                row = {"variant": vname, "policy": pol, "setting": sname, "mode": mode}
                for d in e:
                    row[f"{d}_net_pct"] = 100 * (1 - e[d]["usd"][M]["S"] / e[d]["usd"][M]["B"])
                    row[f"{d}_net_pct_opus47"] = 100 * (1 - e[d]["usd"]["claude-opus-4-7"]["S"] / e[d]["usd"]["claude-opus-4-7"]["B"])
                    row[f"{d}_newest90"] = e[d]["newest_kept_pct"]
                    row[f"{d}_newest_mean"] = e[d]["newest_mean_kept_pct"]
                    row[f"{d}_task90"] = e[d]["task_kept_pct"]
                    row[f"{d}_algo_p95"] = pctl(e[d]["lat"], 95)
                    row[f"{d}_full_p95"] = pctl(e[d]["lat_full"], 95)
                    row[f"{d}_cold"] = e[d]["cold_starts"]
                    row[f"{d}_B_usd"], row[f"{d}_S_usd"] = e[d]["usd"][M]["B"], e[d]["usd"][M]["S"]
                row["weighted_net_pct"] = 100 * (1 - sum(e[d]["usd"][M]["S"] for d in e) / sum(e[d]["usd"][M]["B"] for d in e))
                row["weighted_net_pct_opus47"] = 100 * (1 - sum(e[d]["usd"]["claude-opus-4-7"]["S"] for d in e) /
                                                        sum(e[d]["usd"]["claude-opus-4-7"]["B"] for d in e))
                res.append(row)
                print(pol, sname, mode, round(row["public_net_pct"], 1), round(row["synthetic_net_pct"], 1),
                      round(row["weighted_net_pct"], 1), "newest90", round(row["public_newest90"], 1), round(row["synthetic_newest90"], 1), flush=True)
    lat = {}
    for _, pol in VARIANTS[:2]:
        for mode in MODES:
            pub, syn = proxy_latency(data["public"], mode, newest_policy=pol), proxy_latency(data["synthetic"], mode, newest_policy=pol)
            lat[f"{pol}/{mode}"] = {"public_p95": pctl(pub, 95), "synthetic_p95": pctl(syn, 95)}
    os.makedirs(a.out, exist_ok=True)
    json.dump({"generated": time.strftime("%Y-%m-%d %H:%M %Z"), "rows": res, "proxy_added_ms": lat},
              open(os.path.join(a.out, "v3_results.json"), "w"), indent=1)
    f1 = lambda x: f"{x:+.1f} %"
    with open(os.path.join(a.out, "v3_results.md"), "w") as f:
        for vname, pol in VARIANTS:
            f.write(f"\n### {vname}\n\nNet cost vs caching-on baseline B, Sonnet 4.6 (positive = cheaper); Opus 4.7 cost-weighted in brackets. "
                    "Newest ≥90 % = share of requests keeping at least 90 % of the newest tool output's tokens.\n\n"
                    "| Setting | Mode | Public real | SYNTHETIC | Cost-weighted | Newest ≥90 % public | Newest ≥90 % synthetic | Task ≥90 % (pub/syn) | Algo p95 ms (pub/syn) |\n"
                    "|---|---|---|---|---|---|---|---|---|\n")
            for r in [x for x in res if x["policy"] == pol]:
                f.write(f"| {r['setting']} | {r['mode']} | {f1(r['public_net_pct'])} | {f1(r['synthetic_net_pct'])} | "
                        f"**{f1(r['weighted_net_pct'])}** ({f1(r['weighted_net_pct_opus47'])}) | {r['public_newest90']:.1f} % | "
                        f"{r['synthetic_newest90']:.1f} % | {r['public_task90']:.0f} / {r['synthetic_task90']:.0f} % | "
                        f"{r['public_algo_p95']:.2f} / {r['synthetic_algo_p95']:.2f} |\n")
        f.write("\n### Added latency through the TokenKey proxy (5-min TTL, virtual clock), p95 ms\n\n| Variant/mode | Public | Synthetic |\n|---|---|---|\n")
        for k, v in lat.items():
            f.write(f"| {k} | {v['public_p95']:.2f} | {v['synthetic_p95']:.2f} |\n")
    print(open(os.path.join(a.out, "v3_results.md")).read())


if __name__ == "__main__":
    main()
