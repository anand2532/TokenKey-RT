#!/usr/bin/env python3
"""Host end-to-end test: the device C code (libtksim.so = proto.c + jobs.c + engine.c + xxh32.c)
driven through tools/tkhost.py over the frame protocol, on the TokenKey PoC golden corpus.

  1. every variant (D Economy, S-protect Economy/Balanced/Quality, G dedup-only) byte-matches
     the PoC expected outputs (sha256 digests in corpus/expected_digests.json; and the full
     expected files when TK_POC_CORPUS points at the handoff corpus/ directory);
  2. the recall proxies (handoff SPEC.md 4, offline_quality.py) equal corpus/expected_metrics.json;
  3. acceptance: S-protect newest-error recall 100 %, next-turn reference recall >= 99.9 % for
     S-protect at the default (no ratio) and Quality, and the documented subset value for
     S-protect Economy/Balanced (99.37 %, one known miss, corpus README);
  4. tkhost CLI smoke tests on the simulator (hello, ping, info, mode, policy, run, stats, safe mode).

usage: test_corpus.py LIBTKSIM
"""
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import tkhost  # noqa: E402

# ---- recall proxies, verbatim regexes from the PoC (offline_quality.py; SPEC 4) -------------
PATH_RE = re.compile(r"(?:[\w.-]+/)+[\w.-]+|\b[\w-]+\.(?:py|pyi|js|ts|tsx|c|h|cc|cpp|hpp|java|go|rs|rb|json|ya?ml|toml|md|txt|cfg|ini|sh)\b")
IDENT_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*\b")
TICK_RE = re.compile(r"`([^`\n]{3,80})`")
ERR_RE = re.compile(r"(Traceback \(most recent call last\)|\b\w*(Error|Exception)\b[:(]|\bFAILED\b|syntax error|\berror:)", re.I)
STRIP = ".,:;()'\""


def _code_ident(t):
    return len(t) >= 4 and ("_" in t or "." in t or re.search(r"[a-z][A-Z]", t) is not None)


def next_turn_refs(reply):
    refs = set(m.group(0) for m in PATH_RE.finditer(reply))
    refs |= {t for t in IDENT_RE.findall(reply) if _code_ident(t)}
    refs |= {t.strip() for t in TICK_RE.findall(reply) if " " not in t.strip()}
    return {r.strip(STRIP) for r in refs if len(r.strip(STRIP)) >= 4}


def error_lines(text):
    return {l.strip() for l in text.splitlines() if ERR_RE.search(l) and len(l.strip()) >= 6}


def score(rows):
    rr_hit = rr_tot = rr_full = en_hit = en_tot = en_full = ea_hit = ea_tot = n_ref = n_en = 0
    for r, o, s in rows:
        orig, red = "\n".join(r), "\n".join(s)
        refs = {x for x in next_turn_refs(o) if x in orig}
        if refs:
            h = sum(x in red for x in refs); rr_hit += h; rr_tot += len(refs); n_ref += 1; rr_full += h == len(refs)
        en = error_lines(r[-1])
        if en:
            h = sum(x in red for x in en); en_hit += h; en_tot += len(en); n_en += 1; en_full += h == len(en)
        ea = error_lines(orig)
        ea_hit += sum(x in red for x in ea); ea_tot += len(ea)
    pct = lambda a, b: round(100 * a / b, 4) if b else None
    return {"ref_recall": pct(rr_hit, rr_tot), "ref_full_pct": pct(rr_full, n_ref), "requests_with_refs": n_ref,
            "err_recall_newest": pct(en_hit, en_tot), "err_full_newest_pct": pct(en_full, n_en),
            "requests_with_new_err": n_en, "err_recall_all": pct(ea_hit, ea_tot), "ref_items": rr_tot}


fails = 0


def check(cond, msg):
    global fails
    print(("ok   " if cond else "FAIL ") + msg)
    fails += 0 if cond else 1


def main():
    lib = os.path.abspath(sys.argv[1])
    tmp = tempfile.mkdtemp()
    with tarfile.open(os.path.join(HERE, "corpus", "inputs.tar.xz")) as t:
        t.extractall(tmp, filter="data") if hasattr(tarfile, "data_filter") else t.extractall(tmp)
    digests = json.load(open(os.path.join(HERE, "corpus", "expected_digests.json")))
    want = json.load(open(os.path.join(HERE, "corpus", "expected_metrics.json")))
    poc = os.environ.get("TK_POC_CORPUS")
    exp_dir = os.path.join(poc, "expected") if poc and os.path.isdir(os.path.join(poc, "expected")) else None

    def factory():
        tr = tkhost.SimTransport(lib)
        return tkhost.Client(tr), tr

    res, bad = tkhost.corpus_check(factory, os.path.join(tmp, "inputs"), exp_dir, digests)
    n = sum(len(v["sent"]) for v in res.values())
    check(n == len(digests) == 340, "corpus: %d variant-requests replayed (%d digests)" % (n, len(digests)))
    check(not bad, "byte-exact vs PoC expected outputs%s: %d mismatches %s" %
          (" (full files + digests)" if exp_dir else " (digests)", len(bad), bad[:5]))
    for v, r in res.items():
        got = score(r["sent"])
        same = all(abs((got[k] or 0) - (want[v][k] or 0)) < 1e-3 for k in want[v])
        check(same, "%s metrics == expected_metrics.json: ref %.2f %% / newest-err %.2f %% / all-err %.2f %%" %
              (v, got["ref_recall"], got["err_recall_newest"], got["err_recall_all"]))
        st = {k: sum(s[k] for kk, s in r.items() if kk.startswith("stats_")) for k in ("full", "warm", "overflow", "pass2")}
        print("     %s: %s" % (v, st))
        if v.startswith("S_protect"):
            check(got["err_recall_newest"] == 100.0, "%s newest-error recall 100 %%" % v)
        if v in ("S_protect_quality", "G_dedup_only"):
            check(got["ref_recall"] >= 99.9, "%s next-turn reference recall >= 99.9 %%" % v)
    # default preset S-protect (no ratio) on the corpus
    rows = []
    for sd in sorted(os.listdir(os.path.join(tmp, "inputs"))):
        c, tr = factory()
        red = tkhost.Reducer(c, "s-protect")
        for f in sorted(os.listdir(os.path.join(tmp, "inputs", sd))):
            j = json.load(open(os.path.join(tmp, "inputs", sd, f)))
            tr.now = j["t_s_modelled"]
            rows.append((j["messages"], j["next_assistant"], red.process(j["messages"], tr.now)))
    s = score(rows)
    check(s["err_recall_newest"] == 100.0 and s["ref_recall"] >= 99.9,
          "S-protect default (no ratio): newest-error recall %.1f %%, reference recall %.2f %%" % (s["err_recall_newest"], s["ref_recall"]))

    # ---- CLI smoke tests (separate processes, simulator) ------------------------------------
    tk = [sys.executable, os.path.join(HERE, "..", "tools", "tkhost.py"), "--sim-lib", lib, "--json"]
    run = lambda *a: json.loads(subprocess.run(tk + list(a), check=True, capture_output=True, text=True).stdout)
    h = run("hello")
    check(h["sessions"] and h["minor"] == 3 and h["proto"] == 1, "tkhost hello: %s" % h)
    check(run("ping", "abc")["ok"], "tkhost ping")
    check("build_id" in run("info"), "tkhost info")
    check(run("mode", "quality")["keep_pct"] == 85, "tkhost mode quality")
    check(run("policy")["preset"] == 3, "tkhost policy: default preset S-protect")
    p = run("policy", "--keep", "40", "--weight", "code=350")
    check(p["preset"] == 255 and p["keep_pct"] == 40 and p["weights"]["code"] == 350, "tkhost policy custom")
    f = os.path.join(tmp, "inputs", "synthetic-002", "req_010.json")
    o = os.path.join(tmp, "out.json")
    for var in ("s-protect", "economy", "dedup-only", "d-economy"):
        r = run("run", f, "--variant", var, "--out", o)
        check(r["bytes_out"] <= r["bytes_in"] and len(json.load(open(o))) == r["messages"], "tkhost run %s: %s" % (var, r))
    stf = os.path.join(tmp, "state.json")
    run("run", os.path.join(tmp, "inputs", "synthetic-002", "req_000.json"), "--state", stf)
    r = run("run", os.path.join(tmp, "inputs", "synthetic-002", "req_001.json"), "--state", stf)
    check(r["mismatch"] == 1 and r["full"] == 1, "tkhost run --state: fresh simulator -> SESSION_MISMATCH -> FULL fallback")
    check(run("stats")["bytes_in"] == 0, "tkhost stats (fresh simulator)")
    sm = subprocess.run(tk[:-1] + ["--safe-mode", "run", f], capture_output=True, text=True)
    check(sm.returncode != 0 and "SAFE_MODE" in sm.stderr, "safe mode: jobs refused with SAFE_MODE")
    hs = json.loads(subprocess.run(tk + ["--safe-mode", "hello"], capture_output=True, text=True).stdout)
    check(not hs["sessions"], "safe mode: HELLO caps without SESSIONS")
    print("test_corpus: %d failure(s)" % fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
