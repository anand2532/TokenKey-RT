"""Re-run of G1/G5 with the TokenKey PM defaults (variant S), TTL-aware billing.

Usage: python -m tokenkey_poc.replay_v2 --out results
Writes results/v2_results.json and results/v2_results.md.
"""
from __future__ import annotations

import argparse
import json
import os
import time

from . import proxy, sessions
from .anthropic_body import to_body
from .costmodel import Bill, ntok
from .replay import pctl
from .session_reducer import run_session
from .timing import bill_session_timed, request_times, usd

DATASETS = [("public", "data/public_swe_agent_trajectories.jsonl", False),
            ("synthetic", "data/SYNTHETIC_sessions.jsonl", True)]
SETTINGS = [("5m TTL, modelled breaks (default)", 300.0, True, True),
            ("1h TTL, modelled breaks (sensitivity)", 3600.0, True, True),
            ("5m TTL, always warm / no breaks (reference)", 300.0, False, True),
            ("5m TTL, modelled breaks, newest tool output NOT deduped (sensitivity; deviates from PM rule 4)", 300.0, True, False)]
MODES = ("economy", "balanced", "quality")
MODELS = ("claude-sonnet-4-6", "claude-opus-4-7")


def load(path):
    out = []
    for s in sessions.load(path):
        r, o = sessions.requests_of(s)
        if r:
            out.append((s["id"], r, o))
    return out


def kept(orig, sent):
    a = ntok(orig)
    return 1.0 if a == 0 else min(1.0, ntok(sent) / a)


def evaluate(data, ttl, breaks, mode, dedup_newest=True, newest_policy=None):
    res = {m: {"B": Bill(), "S": Bill()} for m in MODELS}
    lat, lat_full, cold = [], [], 0
    task_ok = newest_ok = n = 0
    newest_frac = 0.0
    st_tot = {"full_reductions": 0, "warm_jobs": 0, "overflow": 0}
    for sid, reqs, outs in data:
        times = request_times(sid, len(reqs), breaks)
        if mode is None:
            sent = reqs
        else:
            sent, l, lf, st = run_session(reqs, times, mode, ttl, dedup_newest, newest_policy)
            lat += l; lat_full += lf
            for k in st_tot:
                st_tot[k] += st[k]
        for m in MODELS:
            bB, c = bill_session_timed(reqs, outs, times, m, ttl)
            bS, _ = bill_session_timed(sent, outs, times, m, ttl)
            res[m]["B"].add(bB); res[m]["S"].add(bS)
        cold += c
        for r, s in zip(reqs, sent):
            n += 1
            task_ok += kept(r[1], s[1]) >= 0.9 if len(r) > 1 else 1
            f = kept(r[-1], s[-1]); newest_frac += f; newest_ok += f >= 0.9
    return {"usd": {m: {"B": usd(res[m]["B"], m, ttl), "S": usd(res[m]["S"], m, ttl)} for m in MODELS},
            "tokens": {"B_input": res[MODELS[0]]["B"].input_total, "S_input": res[MODELS[0]]["S"].input_total},
            "lat": lat, "lat_full": lat_full, "cold_starts": cold, "requests": n, "stats": st_tot,
            "task_kept_pct": 100 * task_ok / n, "newest_kept_pct": 100 * newest_ok / n,
            "newest_mean_kept_pct": 100 * newest_frac / n}


def proxy_latency(data, mode, ttl=300.0, max_req=400, newest_policy="dedup"):
    md, mp = proxy.Mock(), proxy.Mock()
    px = proxy.TokenKeyProxy(mp.port, variant="S", mode=mode, ttl=ttl, newest_policy=newest_policy)
    added = []
    try:
        for sid, reqs, outs in data:
            for r, t in zip(reqs, request_times(sid, len(reqs), True)):
                b = to_body(r)
                lp = proxy.post(px.port, b, {"x-tk-session": sid, "x-tk-time": str(t)})
                ld = proxy.post(md.port, b)
                added.append(lp - ld)
                if len(added) >= max_req:
                    return added
    finally:
        px.close(); md.close(); mp.close()
    return added


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default="results"); a = ap.parse_args()
    data = {name: load(p) for name, p, _ in DATASETS}
    out = {"generated": time.strftime("%Y-%m-%d %H:%M %Z"), "settings": []}
    for sname, ttl, breaks, dn in SETTINGS:
        srow = {"setting": sname, "ttl_s": ttl, "breaks": breaks, "modes": {}}
        for mode in MODES:
            row = {}
            for dname, _, _ in DATASETS:
                e = evaluate(data[dname], ttl, breaks, mode, dn)
                row[dname] = {
                    "net_vs_B_pct_sonnet46": 100 * (1 - e["usd"]["claude-sonnet-4-6"]["S"] / e["usd"]["claude-sonnet-4-6"]["B"]),
                    "net_vs_B_pct_opus47": 100 * (1 - e["usd"]["claude-opus-4-7"]["S"] / e["usd"]["claude-opus-4-7"]["B"]),
                    "B_usd_sonnet46": e["usd"]["claude-sonnet-4-6"]["B"], "S_usd_sonnet46": e["usd"]["claude-sonnet-4-6"]["S"],
                    "B_usd_opus47": e["usd"]["claude-opus-4-7"]["B"], "S_usd_opus47": e["usd"]["claude-opus-4-7"]["S"],
                    "input_tokens_vs_B_pct": 100 * (1 - e["tokens"]["S_input"] / e["tokens"]["B_input"]),
                    "algo_p95_ms": pctl(e["lat"], 95), "algo_p50_ms": pctl(e["lat"], 50),
                    "full_reduction_p95_ms": pctl(e["lat_full"], 95), "cold_starts": e["cold_starts"],
                    "requests": e["requests"], "task_kept_pct": e["task_kept_pct"], "newest_kept_pct": e["newest_kept_pct"],
                    "newest_mean_kept_pct": e["newest_mean_kept_pct"], **e["stats"]}
            for m, tag in (("sonnet46", "sonnet46"), ("opus47", "opus47")):
                B = sum(row[d][f"B_usd_{m}"] for d in ("public", "synthetic")); S = sum(row[d][f"S_usd_{m}"] for d in ("public", "synthetic"))
                row.setdefault("cost_weighted", {})[f"net_vs_B_pct_{tag}"] = 100 * (1 - S / B)
            srow["modes"][mode] = row
            print(sname, mode, {d: round(row[d]["net_vs_B_pct_sonnet46"], 1) for d in ("public", "synthetic")},
                  "weighted", round(row["cost_weighted"]["net_vs_B_pct_sonnet46"], 1), flush=True)
        out["settings"].append(srow)
    pl = data["public"] + data["synthetic"]
    out["proxy_added_ms"] = {}
    for mode in MODES:
        pub = proxy_latency(data["public"], mode); syn = proxy_latency(data["synthetic"], mode)
        out["proxy_added_ms"][mode] = {"public_p50": pctl(pub, 50), "public_p95": pctl(pub, 95),
                                       "synthetic_p50": pctl(syn, 50), "synthetic_p95": pctl(syn, 95),
                                       "n": [len(pub), len(syn)]}
        print("proxy", mode, out["proxy_added_ms"][mode], flush=True)
    os.makedirs(a.out, exist_ok=True)
    json.dump(out, open(os.path.join(a.out, "v2_results.json"), "w"), indent=1)
    f2 = lambda x: "" if x is None else f"{x:.1f}"
    with open(os.path.join(a.out, "v2_results.md"), "w") as f:
        for s in out["settings"]:
            f.write(f"\n### {s['setting']}\n\n| Mode | Data | Net cost vs B (Sonnet 4.6) | Net cost vs B (Opus 4.7) | Input tokens vs B | "
                    f"B $ / S $ (Sonnet 4.6) | Cold starts | Task kept ≥90 % | Newest tool output kept ≥90 % | Newest kept (mean) | "
                    f"Algo p95 ms | Full-reduction p95 ms |\n|---|---|---|---|---|---|---|---|---|---|---|---|\n")
            for mode, row in s["modes"].items():
                for d in ("public", "synthetic"):
                    r = row[d]
                    f.write(f"| {mode} | {d}{' (SYNTHETIC)' if d == 'synthetic' else ''} | {f2(r['net_vs_B_pct_sonnet46'])} % | "
                            f"{f2(r['net_vs_B_pct_opus47'])} % | −{f2(r['input_tokens_vs_B_pct'])} % | "
                            f"{r['B_usd_sonnet46']:.2f} / {r['S_usd_sonnet46']:.2f} | {r['cold_starts']} | {f2(r['task_kept_pct'])} % | "
                            f"{f2(r['newest_kept_pct'])} % | {f2(r['newest_mean_kept_pct'])} % | {r['algo_p95_ms']:.2f} | "
                            f"{'' if r['full_reduction_p95_ms'] is None else f'{r["full_reduction_p95_ms"]:.2f}'} |\n")
                cw = row["cost_weighted"]
                f.write(f"| {mode} | **cost-weighted (public + synthetic)** | **{f2(cw['net_vs_B_pct_sonnet46'])} %** | "
                        f"**{f2(cw['net_vs_B_pct_opus47'])} %** | | | | | | | | |\n")
        f.write("\n### Added latency through the TokenKey proxy (variant S, 5m TTL, virtual clock), ms\n\n"
                "| Mode | Public p50 | Public p95 | Synthetic p50 | Synthetic p95 |\n|---|---|---|---|---|\n")
        for mode, v in out["proxy_added_ms"].items():
            f.write(f"| {mode} | {v['public_p50']:.2f} | {v['public_p95']:.2f} | {v['synthetic_p50']:.2f} | {v['synthetic_p95']:.2f} |\n")
    print(open(os.path.join(a.out, "v2_results.md")).read())


if __name__ == "__main__":
    main()
