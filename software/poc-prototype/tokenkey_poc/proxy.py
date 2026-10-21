"""Local HTTP plumbing: mock Anthropic upstream, TokenKey proxy (P2), Tamp runner, added-latency bench.

Nothing here talks to a real provider: the upstream is a local mock that records the bodies it receives
and returns a fixed minimal Messages-API response. Added latency = (client->proxy->mock) - (client->mock).
"""
from __future__ import annotations

import http.client
import json
import os
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import tk_core as tk
from .anthropic_body import from_body, set_texts, to_body
from .variants import PLACEHOLDER

MOCK_RESPONSE = json.dumps({"id": "msg_mock", "type": "message", "role": "assistant", "model": "mock",
                            "content": [{"type": "text", "text": "ok"}], "stop_reason": "end_turn",
                            "usage": {"input_tokens": 1, "output_tokens": 1}}).encode()


def free_port() -> int:
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


class Mock:
    def __init__(self):
        self.captured: list[dict] = []
        outer = self

        class H(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"
            def log_message(self, *a): pass
            def do_POST(self):
                n = int(self.headers.get("content-length", 0))
                raw = self.rfile.read(n)
                enc = self.headers.get("content-encoding", "")
                try:
                    if enc == "zstd":
                        import subprocess as sp
                        raw = sp.run(["zstd", "-dc"], input=raw, capture_output=True).stdout
                    outer.captured.append(json.loads(raw))
                except Exception as e:   # record undecodable bodies for inspection
                    outer.captured.append({"_error": str(e), "_len": len(raw)})
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(MOCK_RESPONSE)))
                self.end_headers()
                self.wfile.write(MOCK_RESPONSE)

        self.port = free_port()
        self.srv = ThreadingHTTPServer(("127.0.0.1", self.port), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def close(self):
        self.srv.shutdown()


class TokenKeyProxy:
    """P2: local proxy applying the TokenKey job. variant 'D' = full request, 'C' = tail-only (cache-preserving,
    state keyed by the x-tk-session header)."""

    def __init__(self, upstream_port: int, variant: str = "C", mode: str = "balanced", ttl: float = 300.0,
                 newest_policy: str = "dedup"):
        self.state: dict[str, dict] = {}
        self.ttl = ttl
        self.newest_policy = newest_policy
        outer = self

        class H(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"
            def log_message(self, *a): pass
            def do_POST(self):
                n = int(self.headers.get("content-length", 0))
                body = json.loads(self.rfile.read(n))
                msgs = from_body(body)
                try:
                    if variant == "S":
                        from .session_reducer import SessionReducer
                        sid = self.headers.get("x-tk-session", "default")
                        red = outer.state.setdefault(sid, SessionReducer(mode, outer.ttl, newest_policy=outer.newest_policy))
                        out = red.process(msgs, float(self.headers.get("x-tk-time", time.time())))
                    elif variant == "D":
                        out, _ = tk.run_job(msgs, mode)
                    else:
                        sid = self.headers.get("x-tk-session", "default")
                        st = outer.state.setdefault(sid, {"dup": tk.DupSet(), "hist": [], "n": 0})
                        tail, _ = tk.run_job(msgs[st["n"]:], mode, dupset=st["dup"])
                        st["hist"] = st["hist"] + tail; st["n"] = len(msgs); out = st["hist"]
                    out = [x if x.strip() else PLACEHOLDER for x in out]
                    set_texts(body, out)
                except tk.CtxOverflow:
                    pass
                data = json.dumps(body).encode()
                c = http.client.HTTPConnection("127.0.0.1", upstream_port, timeout=60)
                c.request("POST", self.path, data, {"content-type": "application/json"})
                r = c.getresponse(); resp = r.read(); c.close()
                self.send_response(r.status)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)

        self.port = free_port()
        self.srv = ThreadingHTTPServer(("127.0.0.1", self.port), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def close(self):
        self.srv.shutdown()


def post(port: int, body: dict, headers: dict | None = None) -> float:
    data = json.dumps(body).encode()
    h = {"content-type": "application/json", "x-api-key": "sk-dummy-local-mock", "anthropic-version": "2023-06-01"}
    h.update(headers or {})
    t0 = time.perf_counter()
    c = http.client.HTTPConnection("localhost", port, timeout=120)
    c.request("POST", "/v1/messages", data, h)
    r = c.getresponse(); r.read(); c.close()
    return (time.perf_counter() - t0) * 1000


class Tamp:
    def __init__(self, upstream_port: int, tamp_dir: str, preset: str = "balanced", extra_env: dict | None = None):
        self.port = free_port()
        env = dict(os.environ, TAMP_UPSTREAM=f"http://127.0.0.1:{upstream_port}", TAMP_PORT=str(self.port),
                   TAMP_HOST="127.0.0.1", TAMP_COMPRESSION_PRESET=preset, HOME=os.path.join(tamp_dir, "home"))
        env.update(extra_env or {})
        os.makedirs(env["HOME"], exist_ok=True)
        self.log = open(os.path.join(tamp_dir, "tamp.log"), "w")
        self.p = subprocess.Popen(["node", os.path.join(tamp_dir, "node_modules/@sliday/tamp/bin/tamp.js"), "-y"],
                                  env=env, stdout=self.log, stderr=subprocess.STDOUT)
        for _ in range(300):
            try:
                socket.create_connection(("localhost", self.port), timeout=0.2).close(); return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError("tamp did not start; see tamp.log")

    def close(self):
        self.p.terminate(); self.p.wait(5); self.log.close()
