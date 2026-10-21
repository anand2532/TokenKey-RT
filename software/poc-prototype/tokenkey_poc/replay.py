"""Replay sessions through all variants; compute tokens, net cost vs caching-on baseline (G1),
added latency (G5), substitute comparison (G3) and required-context proxy diagnostics.

Usage: python -m tokenkey_poc.replay data/X.jsonl [data/Y.jsonl ...] --out results/
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import time

from . import costmodel as cm
from . import proxy, sessions, variants
from .anthropic_body import from_body, to_body
from .prices import PRICES

MODELS = ["claude-sonnet-4-6", "claude-opus-4-7"]


def pctl(xs, q):
    if not xs:
        return None
    xs = sorted(xs)
    k = max(0, min(len(xs) - 1, int(round(q / 100 * (len(xs) - 1)))))
    return xs[k]


def tamp_run(all_reqs, tamp_dir):
    """Send every request through a real Tamp proxy to a local mock; return forwarded bodies + added latency."""
    mt, md = proxy.Mock(), proxy.Mock()
    t = proxy.Tamp(mt.port, tamp_dir)
    sent_all, added = [], []
    try:
        for reqs in all_reqs:
            start = len(mt.captured)
            for r in reqs:
                b = to_body(r)
                lt = proxy.post(t.port, b)
                ld = proxy.post(md.port, b)
                added.append(lt - ld)
            sent_all.append([from_body(c) for c in mt.captured[start:]])
    finally:
        t.close(); mt.close(); md.close()
    return sent_all, added


def tokenkey_proxy_latency(all_reqs, variant, mode="balanced", max_req=400):
    md = proxy.Mock(); mp = proxy.Mock()
    px = proxy.TokenKeyProxy(mp.port, variant=variant, mode=mode)
    added, n = [], 0
    try:
        for si, reqs in enumerate(all_reqs):
            for r in reqs:
                b = to_body(r)
                lp = proxy.post(px.port, b, {"x-tk-session": f"s{si}"})
                ld = proxy.post(md.port, b)
                added.append(lp - ld); n += 1
                if n >= max_req:
                    return added
    finally:
        px.close(); md.close(); mp.close()
    return added


def run_dataset(path, tamp_dir, max_turns=None):
    S = sessions.load(path)
    all_reqs, all_outs = [], []
    for s in S:
        r, o = sessions.requests_of(s, max_turns)
        if r:
            all_reqs.append(r); all_outs.append(o)
    V = {}

    def record(name, fn, caching=True):
        bills = {m: cm.Bill() for m in MODELS}
        lat, extra, diag_r, diag_s = [], {}, [], []
        t0 = time.time()
        for reqs, outs in zip(all_reqs, all_outs):
            sent, l, x = fn(reqs)
            for m in MODELS:
                bills[m].add(cm.bill_session(sent, outs, m, caching))
            lat += l
            for k, v in x.items():
                extra[k] = extra.get(k, 0) + v
            diag_r += reqs; diag_s += sent
        V[name] = {"bills": bills, "lat": lat, "extra": extra, "diag": variants.diagnostics(diag_r, diag_s),
                   "wall_s": round(time.time() - t0, 1)}
        print(f"  {name}: done in {V[name]['wall_s']}s", flush=True)

    record("A_no_cache_raw", variants.run_raw, caching=False)
    record("B_cache_raw (baseline)", variants.run_raw)
    for mode in ("economy", "balanced", "quality"):
        record(f"D_firmware_full_request_{mode}", lambda r, m=mode: variants.run_full_request(r, m))
    for mode in ("economy", "balanced", "quality"):
        record(f"C_firmware_tail_only_{mode}", lambda r, m=mode: variants.run_tail_only(r, m))
    record("F_host_unconstrained_tail_only_balanced",
           lambda r: variants.run_tail_only(r, "balanced", enforce_caps=False,
                                            token_counter=lambda b: cm.ntok(b.decode("utf-8", "surrogatepass"))))
    record("G_ext_dedup_only_tail (not a firmware mode)", variants.run_dedup_only_tail)
    record("E_llmtrim_agent_with_cache_markers", lambda r: variants.run_llmtrim(r, "agent", True))
    record("E_llmtrim_agent_no_cache_markers", lambda r: variants.run_llmtrim(r, "agent", False))
    tamp_sent, tamp_added = tamp_run(all_reqs, tamp_dir)
    it = iter(tamp_sent)
    record("E_tamp_balanced_default", lambda r: (next(it), [], {}))
    V["E_tamp_balanced_default"]["proxy_added_ms"] = tamp_added
    print("  proxy latency benches...", flush=True)
    V["C_firmware_tail_only_balanced"]["proxy_added_ms"] = tokenkey_proxy_latency(all_reqs, "C")
    V["D_firmware_full_request_balanced"]["proxy_added_ms"] = tokenkey_proxy_latency(all_reqs, "D")
    n_req = sum(len(r) for r in all_reqs)
    return {"dataset": path, "sessions": len(all_reqs), "requests": n_req, "variants": V,
            "synthetic": all(s.get("synthetic") for s in S)}


def summarize(res):
    base = res["variants"]["B_cache_raw (baseline)"]["bills"]
    rows = []
    for name, v in res["variants"].items():
        b = v["bills"]["claude-sonnet-4-6"]
        row = {
            "variant": name,
            "input_tokens_billed": b.input_total,
            "uncached_in": b.base_in, "cache_read": b.cache_read, "cache_write": b.cache_write, "output": b.out,
            "usd_sonnet46": round(b.usd("claude-sonnet-4-6"), 4),
            "net_cost_vs_B_pct_sonnet46": round(100 * (1 - b.usd("claude-sonnet-4-6") / base["claude-sonnet-4-6"].usd("claude-sonnet-4-6")), 1),
            "net_cost_vs_B_pct_opus47": round(100 * (1 - v["bills"]["claude-opus-4-7"].usd("claude-opus-4-7") / base["claude-opus-4-7"].usd("claude-opus-4-7")), 1),
            "input_tokens_vs_B_pct": round(100 * (1 - b.input_total / base["claude-sonnet-4-6"].input_total), 1),
            "algo_ms_p50": round(pctl(v["lat"], 50), 2) if v["lat"] else None,
            "algo_ms_p95": round(pctl(v["lat"], 95), 2) if v["lat"] else None,
            "proxy_added_ms_p95": round(pctl(v["proxy_added_ms"], 95), 2) if v.get("proxy_added_ms") else None,
            "proxy_added_ms_p50": round(pctl(v["proxy_added_ms"], 50), 2) if v.get("proxy_added_ms") else None,
            "newest_msg_kept_pct": round(v["diag"]["newest_msg_kept_pct"], 1),
            "task_kept_pct": round(v["diag"]["task_kept_pct"], 1),
            **{k: v2 for k, v2 in v["extra"].items()},
        }
        rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("datasets", nargs="+")
    ap.add_argument("--out", default="results")
    ap.add_argument("--tamp-dir", default="tools/tamp")
    ap.add_argument("--max-turns", type=int, default=None)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    allres = []
    for d in a.datasets:
        print("dataset", d, flush=True)
        res = run_dataset(d, a.tamp_dir, a.max_turns)
        rows = summarize(res)
        allres.append({"dataset": d, "synthetic": res["synthetic"], "sessions": res["sessions"],
                       "requests": res["requests"], "rows": rows})
    with open(os.path.join(a.out, "results.json"), "w") as f:
        json.dump({"generated": time.strftime("%Y-%m-%d %H:%M %Z"), "prices": PRICES, "results": allres}, f, indent=1)
    cols = ["variant", "net_cost_vs_B_pct_sonnet46", "net_cost_vs_B_pct_opus47", "input_tokens_vs_B_pct", "usd_sonnet46",
            "cache_read", "cache_write", "uncached_in", "output", "newest_msg_kept_pct", "task_kept_pct",
            "algo_ms_p95", "proxy_added_ms_p50", "proxy_added_ms_p95", "overflow", "set_full"]
    with open(os.path.join(a.out, "results.md"), "w") as f:
        for r in allres:
            tag = "SYNTHETIC DATA" if r["synthetic"] else "PUBLIC REAL AGENT TRAJECTORIES"
            f.write(f"\n## {r['dataset']} ({tag}): {r['sessions']} sessions, {r['requests']} requests\n\n")
            f.write("| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n")
            for row in r["rows"]:
                f.write("| " + " | ".join("" if row.get(c) is None else str(row.get(c)) for c in cols) + " |\n")
    print(open(os.path.join(a.out, "results.md")).read())


if __name__ == "__main__":
    main()
