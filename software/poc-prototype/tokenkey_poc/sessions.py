"""Session loading / generation.

Session JSONL schema (one session per line):
  {"id", "source", "synthetic": bool, "system": str, "turns": [{"role": "user"|"assistant", "text": str}], "meta": {...}}
Replay: for every assistant turn k, the request is [system] + turns[:k] and the recorded reply is turns[k]
(full-history resend, as Claude Code does; SWE-agent itself trims old observations, so this is an upper bound for that agent).
"""
from __future__ import annotations

import json
import os
import random
import sys


def load(path: str) -> list[dict]:
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def requests_of(session: dict, max_turns: int | None = None):
    reqs, outs = [], []
    turns = session["turns"]
    for k, t in enumerate(turns):
        if t["role"] == "assistant" and k > 0:
            reqs.append([session["system"]] + [x["text"] for x in turns[:k]])
            outs.append(t["text"])
            if max_turns and len(reqs) >= max_turns:
                break
    return reqs, outs


# ------------------------------------------------------------------ public data
def fetch_public(n: int, out_path: str, min_msgs: int = 12, max_msgs: int = 120, seed: int = 0):
    """Stream real, public SWE-agent trajectories (nebius/SWE-agent-trajectories on Hugging Face)."""
    from datasets import load_dataset
    ds = load_dataset("nebius/SWE-agent-trajectories", split="train", streaming=True)
    ds = ds.shuffle(seed=seed, buffer_size=2000)
    kept = 0
    with open(out_path, "w") as f:
        for r in ds:
            tr = r["trajectory"]
            if not (min_msgs <= len(tr) <= max_msgs):
                continue
            system = tr[0]["system_prompt"] if tr[0]["role"] == "system" else ""
            turns = []
            for m in tr[1:]:
                role = "assistant" if m["role"] == "ai" else "user"
                text = m["text"] if m["text"] not in (None, "None") else ""
                if turns and turns[-1]["role"] == role:
                    turns[-1]["text"] += "\n" + text
                else:
                    turns.append({"role": role, "text": text})
            f.write(json.dumps({"id": r["instance_id"] + "|" + r["model_name"], "source": "hf:nebius/SWE-agent-trajectories",
                                "synthetic": False, "system": system or "", "turns": turns,
                                "meta": {"model_name": r["model_name"], "resolved": bool(r["target"]),
                                         "exit_status": r["exit_status"], "generated_patch": r["generated_patch"]}}) + "\n")
            kept += 1
            if kept >= n:
                break
    return kept


# ------------------------------------------------------------------ synthetic data
_WORDS = ("config parser buffer token budget context session request handler cache index stream frame payload "
          "router policy encoder display button driver flash memory segment ranking score module client server "
          "update retry timeout logger metric value result error state queue worker").split()


def _ident(rng):
    return "_".join(rng.sample(_WORDS, 2))


def _py_file(rng, name, n_funcs):
    out = [f'"""{name}: synthetic module."""', "import os", "import json", ""]
    for _ in range(n_funcs):
        fn = _ident(rng)
        args = ", ".join(rng.sample(_WORDS, rng.randint(1, 3)))
        out.append(f"def {fn}({args}):")
        out.append(f'    """Handle {rng.choice(_WORDS)} for {rng.choice(_WORDS)}."""')
        for _ in range(rng.randint(3, 12)):
            out.append(f"    {_ident(rng)} = {rng.choice(_WORDS)}.{_ident(rng)}({rng.randint(0, 999)})")
        out.append(f"    return {rng.choice(_WORDS)}")
        out.append("")
    return "\n".join(out)


def _numbered(text):
    return "\n".join(f"{i + 1:6d}\t{l}" for i, l in enumerate(text.splitlines()))


def _traceback(rng, fname):
    lines = ["============================= test session starts ==============================",
             f"collected {rng.randint(20, 200)} items", ""]
    for _ in range(rng.randint(5, 30)):
        lines.append(f"tests/test_{rng.choice(_WORDS)}.py::test_{_ident(rng)} PASSED")
    lines += ["", "Traceback (most recent call last):"]
    for _ in range(rng.randint(3, 8)):
        lines.append(f'  File "{fname}", line {rng.randint(1, 400)}, in {_ident(rng)}')
        lines.append(f"    {_ident(rng)}({rng.choice(_WORDS)})")
    lines.append(f"KeyError: '{rng.choice(_WORDS)}'")
    lines.append(f"FAILED tests/test_{rng.choice(_WORDS)}.py::test_{_ident(rng)} - KeyError")
    return "\n".join(lines)


def _diff(rng, fname, src):
    ls = src.splitlines()
    k = rng.randint(4, max(5, len(ls) - 6))
    old = ls[k:k + 3]
    new = [l.replace("return", "return  # fixed") if "return" in l else l + "  # tk" for l in old]
    body = [f"diff --git a/{fname} b/{fname}", "index 1a2b3c4..5d6e7f8 100644", f"--- a/{fname}", f"+++ b/{fname}",
            f"@@ -{k + 1},3 +{k + 1},3 @@"] + [f"-{l}" for l in old] + [f"+{l}" for l in new]
    return "\n".join(body)


def gen_synthetic(n_sessions: int, out_path: str, turns: int = 30, seed: int = 42):
    """SYNTHETIC coding-agent sessions: big static system prompt, file reads (with re-reads),
    test logs, diffs, grep output, occasional user follow-ups. Text is machine-generated filler."""
    rng = random.Random(seed)
    with open(out_path, "w") as f:
        for s in range(n_sessions):
            system = "\n".join(f"Rule {i}: When working on {_ident(rng)}, always {rng.choice(_WORDS)} the "
                               f"{rng.choice(_WORDS)} before {rng.choice(_WORDS)}." for i in range(250))
            system += "\n\n# Tools\n" + "\n".join(
                f'{{"name": "{_ident(rng)}", "description": "Tool to {rng.choice(_WORDS)} a {rng.choice(_WORDS)}"}}'
                for _ in range(40))
            files = {f"src/{_ident(rng)}.py": None for _ in range(rng.randint(4, 8))}
            for fn in files:
                files[fn] = _py_file(rng, fn, rng.randint(6, 20))
            tl = [{"role": "user", "text": f"Fix the failing test related to {_ident(rng)} in this repo. "
                                           f"The {rng.choice(_WORDS)} breaks when {rng.choice(_WORDS)} is empty."}]
            for _ in range(turns):
                fn = rng.choice(list(files))
                act = rng.choices(["read", "test", "diff", "grep", "user"], [0.4, 0.2, 0.15, 0.15, 0.1])[0]
                if act == "read":
                    a, obs = f"Let me read `{fn}`.", (_numbered(files[fn]) if rng.random() < 0.5
                                                       else f"```python\n{files[fn]}\n```")
                elif act == "test":
                    a, obs = "Running the test suite.", _traceback(rng, fn)
                elif act == "diff":
                    a, obs = f"I'll edit `{fn}` and show the diff.", _diff(rng, fn, files[fn])
                elif act == "grep":
                    a = f"Searching for {rng.choice(_WORDS)}."
                    obs = "\n".join(f"{rng.choice(list(files))}:{rng.randint(1, 300)}: {_ident(rng)} = {rng.choice(_WORDS)}"
                                    for _ in range(rng.randint(5, 40)))
                else:
                    a, obs = "Waiting for your input.", f"Please also check {_ident(rng)} handling in {fn}."
                tl.append({"role": "assistant", "text": a})
                tl.append({"role": "user", "text": obs})
            tl.append({"role": "assistant", "text": "Done. Summary of changes: ..."})
            f.write(json.dumps({"id": f"synthetic-{s:03d}", "source": "SYNTHETIC (tokenkey_poc.sessions.gen_synthetic, seed=%d)" % seed,
                                "synthetic": True, "system": system, "turns": tl, "meta": {}}) + "\n")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "public":
        k = fetch_public(int(sys.argv[2]), sys.argv[3])
        print("kept", k, flush=True)
        os._exit(0)   # avoid datasets/pyarrow shutdown crash
    elif cmd == "synthetic":
        gen_synthetic(int(sys.argv[2]), sys.argv[3])
        print("ok")


# ------------------------------------------------------------------ real logs
def from_proxy_log(log_path: str) -> list[dict]:
    """Group a record_proxy log into replayable sessions: a request continues the current session when the
    previous request's messages are a prefix of it. Returns sessions with explicit 'requests'/'outputs'/'usage'."""
    from .anthropic_body import from_body
    out, cur = [], None
    for line in open(log_path):
        e = json.loads(line)
        if not e.get("request") or "messages" not in e["request"]:
            continue
        msgs = from_body(e["request"])
        if cur and msgs[:len(cur["requests"][-1])] == cur["requests"][-1] and msgs[0] == cur["requests"][-1][0]:
            pass
        else:
            cur = {"id": f"real-{len(out):03d}", "source": log_path, "synthetic": False, "requests": [], "outputs": [], "usage": []}
            out.append(cur)
        cur["requests"].append(msgs); cur["outputs"].append(e.get("response_text") or ""); cur["usage"].append(e.get("usage"))
    return out


def from_claude_code_transcript(path: str) -> dict:
    """BEST-EFFORT importer for a Claude Code local transcript (~/.claude/projects/<proj>/<session>.jsonl).
    Untested against real files in this PoC; the transcript format is not a documented API. It rebuilds the
    linear user/assistant text history (tool_use inputs dropped, tool_result text kept)."""
    from .anthropic_body import _text
    turns = []
    for line in open(path):
        try:
            e = json.loads(line)
        except Exception:
            continue
        m = e.get("message")
        if e.get("type") not in ("user", "assistant") or not isinstance(m, dict):
            continue
        role = "assistant" if m.get("role") == "assistant" else "user"
        text = _text(m.get("content", ""))
        if turns and turns[-1]["role"] == role:
            turns[-1]["text"] += "\n" + text
        else:
            turns.append({"role": role, "text": text})
    if turns and turns[0]["role"] == "assistant":
        turns.insert(0, {"role": "user", "text": ""})
    return {"id": path, "source": "claude-code-transcript", "synthetic": False, "system": "", "turns": turns, "meta": {}}
