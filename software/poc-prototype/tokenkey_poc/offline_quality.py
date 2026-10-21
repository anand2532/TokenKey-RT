"""OFFLINE QUALITY PROXIES (G2) and substitute comparison (G3). These are PROXIES, NOT TRUE QUALITY.

No model is run. For each replayed request we ask whether the information the agent actually used in its NEXT
turn (the recorded assistant reply) is still present in the context that would be sent after reduction:

  ref_recall      file paths and code identifiers mentioned in the next assistant turn that appear somewhere in the
                  original request context: share still present (substring) in the reduced context.
  err_recall_new  distinct error lines (Traceback/...Error:/Exception/FAILED/syntax error...) in the NEWEST tool
                  output: share still present in the reduced context.
  err_recall_all  same for error lines anywhere in the original context.
Per variant: micro-averaged recall, and the share of requests with 100 % ref recall / 100 % newest-error recall.
Limits: a reference surviving does not mean the model would act the same; a reference missing does not
prove failure (the agent may re-read). Next-turn references come from the ORIGINAL run, so they are biased toward
what the unreduced context showed.

Usage: python -m tokenkey_poc.offline_quality --out results
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time

from . import variants
from .replay import tamp_run
from .replay_v2 import load
from .session_reducer import run_session
from .timing import bill_session_timed, request_times, usd

PATH_RE = re.compile(r"(?:[\w.-]+/)+[\w.-]+|\b[\w-]+\.(?:py|pyi|js|ts|tsx|c|h|cc|cpp|hpp|java|go|rs|rb|json|ya?ml|toml|md|txt|cfg|ini|sh)\b")
IDENT_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*\b")
TICK_RE = re.compile(r"`([^`\n]{3,80})`")
ERR_RE = re.compile(r"(Traceback \(most recent call last\)|\b\w*(Error|Exception)\b[:(]|\bFAILED\b|syntax error|\berror:)", re.I)
STRIP = ".,:;()'\""


def _is_code_ident(t: str) -> bool:
    return len(t) >= 4 and ("_" in t or "." in t or re.search(r"[a-z][A-Z]", t) is not None)


def next_turn_refs(reply: str) -> set[str]:
    refs = set(m.group(0) for m in PATH_RE.finditer(reply))
    refs |= {t for t in IDENT_RE.findall(reply) if _is_code_ident(t)}
    refs |= {t.strip() for t in TICK_RE.findall(reply) if " " not in t.strip()}
    return {r.strip(STRIP) for r in refs if len(r.strip(STRIP)) >= 4}


def error_lines(text: str) -> set[str]:
    return {l.strip() for l in text.splitlines() if ERR_RE.search(l) and len(l.strip()) >= 6}


def score(reqs, outs, sent):
    rr_hit = rr_tot = rr_full = en_hit = en_tot = en_full = ea_hit = ea_tot = n_ref = n_en = 0
    for r, o, s in zip(reqs, outs, sent):
        orig, red = "\n".join(r), "\n".join(s)
        refs = {x for x in next_turn_refs(o) if x in orig}
        if refs:
            h = sum(x in red for x in refs); rr_hit += h; rr_tot += len(refs); n_ref += 1; rr_full += h == len(refs)
        en = error_lines(r[-1])
        if en:
            h = sum(x in red for x in en); en_hit += h; en_tot += len(en); n_en += 1; en_full += h == len(en)
        ea = error_lines(orig)
        ea_hit += sum(x in red for x in ea); ea_tot += len(ea)
    pct = lambda a, b: 100 * a / b if b else None
    return {"ref_recall": pct(rr_hit, rr_tot), "ref_full_pct": pct(rr_full, n_ref), "requests_with_refs": n_ref,
            "err_recall_newest": pct(en_hit, en_tot), "err_full_newest_pct": pct(en_full, n_en), "requests_with_new_err": n_en,
            "err_recall_all": pct(ea_hit, ea_tot), "ref_items": rr_tot}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default="results"); a = ap.parse_args()
    M = "claude-sonnet-4-6"
    rows = []
    for dname, path in (("public", "data/public_swe_agent_trajectories.jsonl"), ("synthetic", "data/SYNTHETIC_sessions.jsonl")):
        data = load(path)
        V = {"B caching-on baseline (no reduction)": lambda r, sid: r}
        for mode in ("economy", "balanced", "quality"):
            for pol in ("protect", "collapse", "dedup"):
                V[f"S-{pol} {mode}"] = (lambda r, sid, m=mode, p=pol:
                                         run_session(r, request_times(sid, len(r), True), m, 300.0, newest_policy=p)[0])
            V[f"C tail-only {mode}"] = lambda r, sid, m=mode: variants.run_tail_only(r, m)[0]
            V[f"D firmware full-request {mode}"] = lambda r, sid, m=mode: variants.run_full_request(r, m)[0]
        V["G dedup-only"] = lambda r, sid: variants.run_dedup_only_tail(r)[0]
        V["E llmtrim agent (cache markers)"] = lambda r, sid: variants.run_llmtrim(r, "agent", True)[0]
        V["E llmtrim agent (no markers)"] = lambda r, sid: variants.run_llmtrim(r, "agent", False)[0]
        tamp_sent, _ = tamp_run([r for _, r, _ in data], "tools/tamp")
        tmap = {sid: s for (sid, _, _), s in zip(data, tamp_sent)}
        V["E Tamp balanced (default)"] = lambda r, sid: tmap[sid]
        for name, fn in V.items():
            allr, allo, alls = [], [], []
            cost = {"B5": 0.0, "S5": 0.0, "Bw": 0.0, "Sw": 0.0}
            for sid, reqs, outs in data:
                sent = fn(reqs, sid)
                allr += reqs; allo += outs; alls += sent
                for tag, breaks in (("5", True), ("w", False)):
                    t = request_times(sid, len(reqs), breaks)
                    cost["B" + tag] += usd(bill_session_timed(reqs, outs, t, M, 300.0)[0], M, 300.0)
                    cost["S" + tag] += usd(bill_session_timed(sent, outs, t, M, 300.0)[0], M, 300.0)
            sc = score(allr, allo, alls)
            row = {"dataset": dname, "variant": name, **sc,
                   "net_5m_breaks_pct": 100 * (1 - cost["S5"] / cost["B5"]), "net_no_breaks_pct": 100 * (1 - cost["Sw"] / cost["Bw"])}
            rows.append(row)
            print(dname, name, {k: (round(v, 1) if isinstance(v, float) else v) for k, v in row.items()
                                if k in ("ref_recall", "ref_full_pct", "err_recall_newest", "err_recall_all",
                                         "net_5m_breaks_pct", "net_no_breaks_pct")}, flush=True)
    json.dump({"generated": time.strftime("%Y-%m-%d %H:%M %Z"), "rows": rows},
              open(os.path.join(a.out, "offline_quality.json"), "w"), indent=1)
    f1 = lambda x: "n/a" if x is None else f"{x:.1f}"
    with open(os.path.join(a.out, "offline_quality.md"), "w") as f:
        f.write("OFFLINE PROXIES, NOT TRUE QUALITY. Net cost: Sonnet 4.6, 5-min TTL, vs caching-on baseline B "
                "(positive = cheaper); S variants use the modelled gaps, the others are timing-independent reducers billed "
                "with the same gaps.\n")
        for d in ("public", "synthetic"):
            f.write(f"\n### {d}{' (SYNTHETIC)' if d == 'synthetic' else ' (public real SWE-agent trajectories)'}\n\n"
                    "| Variant | Next-turn ref recall % | Requests with all refs kept % | Newest-output error-line recall % | "
                    "Requests with all newest errors kept % | All-context error-line recall % | Net cost, modelled breaks | Net cost, no breaks |\n"
                    "|---|---|---|---|---|---|---|---|\n")
            for r in [x for x in rows if x["dataset"] == d]:
                f.write(f"| {r['variant']} | {f1(r['ref_recall'])} | {f1(r['ref_full_pct'])} | {f1(r['err_recall_newest'])} | "
                        f"{f1(r['err_full_newest_pct'])} | {f1(r['err_recall_all'])} | {r['net_5m_breaks_pct']:+.1f} % | "
                        f"{r['net_no_breaks_pct']:+.1f} % |\n")
            rr = [x for x in rows if x["dataset"] == d][0]
            f.write(f"\nRequests with ≥1 next-turn reference found in context: {rr['requests_with_refs']} ({rr['ref_items']} references); "
                    f"requests whose newest output has error lines: {rr['requests_with_new_err']}.\n")


if __name__ == "__main__":
    main()
