"""P2 recording proxy for REAL sessions (needs Anand's API key; untested against the live API here).

Run:   python -m tokenkey_poc.record_proxy --upstream https://api.anthropic.com --log data/real_log.jsonl --port 8787
Then:  ANTHROPIC_BASE_URL=http://127.0.0.1:8787 claude      (Claude Code, API-key billing)

It forwards every request unchanged (no reduction), streams the response back, and appends one JSON line per
request: {"ts", "path", "request": <body>, "response_text": <assistant text>, "usage": <provider usage incl. cache
fields>}. API keys/headers are NOT logged. Convert the log with sessions.from_proxy_log() and replay it.
"""
from __future__ import annotations

import argparse
import http.client
import json
import ssl
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_lock = threading.Lock()


def make_handler(upstream: str, log_path: str):
    u = urllib.parse.urlparse(upstream)

    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        def log_message(self, *a): pass

        def do_POST(self):
            n = int(self.headers.get("content-length", 0))
            raw = self.rfile.read(n)
            hdrs = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "content-length", "accept-encoding")}
            Conn = http.client.HTTPSConnection if u.scheme == "https" else http.client.HTTPConnection
            kw = {"context": ssl.create_default_context()} if u.scheme == "https" else {}
            c = Conn(u.hostname, u.port or (443 if u.scheme == "https" else 80), timeout=600, **kw)
            c.request("POST", self.path, raw, hdrs)
            r = c.getresponse()
            self.send_response(r.status)
            for k, v in r.getheaders():
                if k.lower() not in ("transfer-encoding", "content-length", "connection", "content-encoding"):
                    self.send_header(k, v)
            self.send_header("transfer-encoding", "chunked")
            self.end_headers()
            buf = bytearray()
            while True:
                chunk = r.read1(65536) if hasattr(r, "read1") else r.read(65536)
                if not chunk:
                    break
                buf += chunk
                self.wfile.write(b"%x\r\n%s\r\n" % (len(chunk), chunk)); self.wfile.flush()
            self.wfile.write(b"0\r\n\r\n")
            c.close()
            text, usage = parse_response(bytes(buf))
            try:
                req = json.loads(raw)
            except Exception:
                req = None
            with _lock, open(log_path, "a") as f:
                f.write(json.dumps({"ts": time.time(), "path": self.path, "status": r.status, "request": req,
                                    "response_text": text, "usage": usage}) + "\n")
    return H


def parse_response(b: bytes):
    """Handle both JSON and SSE (stream=true) Messages API responses."""
    s = b.decode("utf-8", "replace")
    try:
        j = json.loads(s)
        return "".join(x.get("text", "") for x in j.get("content", []) if isinstance(x, dict)), j.get("usage")
    except Exception:
        pass
    text, usage = [], {}
    for line in s.splitlines():
        if not line.startswith("data:"):
            continue
        try:
            ev = json.loads(line[5:].strip())
        except Exception:
            continue
        t = ev.get("type")
        if t == "message_start":
            usage.update(ev["message"].get("usage", {}))
        elif t == "content_block_delta" and ev["delta"].get("type") == "text_delta":
            text.append(ev["delta"]["text"])
        elif t == "message_delta":
            usage.update(ev.get("usage", {}))
    return "".join(text), usage


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--upstream", default="https://api.anthropic.com")
    ap.add_argument("--log", required=True)
    ap.add_argument("--port", type=int, default=8787)
    a = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(a.upstream, a.log))
    print(f"recording proxy on http://127.0.0.1:{a.port} -> {a.upstream}, log {a.log}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
