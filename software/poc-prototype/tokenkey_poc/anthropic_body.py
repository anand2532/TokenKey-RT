"""Convert between message-text lists and Anthropic Messages API request bodies.

Agent-style encoding (what Claude Code sends): messages[0] is the user task (text block); every assistant turn
is a text block + a tool_use block; every following user turn is a tool_result block carrying the observation.
This matters for Tamp/llmtrim, which compress tool_result content only.
"""
from __future__ import annotations

import json


def to_body(msgs: list[str], model: str = "claude-sonnet-4-6", max_tokens: int = 1024) -> dict:
    system, rest = msgs[0], msgs[1:]
    messages = []
    for i, t in enumerate(rest):
        t = t if t else "."
        if i == 0:
            messages.append({"role": "user", "content": [{"type": "text", "text": t}]})
        elif i % 2 == 1:
            messages.append({"role": "assistant", "content": [
                {"type": "text", "text": t},
                {"type": "tool_use", "id": f"toolu_{i:04d}", "name": "bash", "input": {"command": "run"}}]})
        else:
            messages.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": f"toolu_{i - 1:04d}", "content": [{"type": "text", "text": t}]}]})
    if messages and messages[-1]["role"] == "assistant":   # dangling tool_use would be invalid; drop it
        messages[-1]["content"] = messages[-1]["content"][:1]
    if messages:
        messages[-1]["content"][-1]["cache_control"] = {"type": "ephemeral"}
    return {"model": model, "max_tokens": max_tokens,
            "system": [{"type": "text", "text": system or ".", "cache_control": {"type": "ephemeral"}}],
            "messages": messages}


def _text(content) -> str:
    if isinstance(content, str):
        return content
    parts = []
    for b in content:
        if not isinstance(b, dict):
            parts.append(str(b))
        elif b.get("type") == "text":
            parts.append(b.get("text", ""))
        elif b.get("type") == "tool_result":
            parts.append(_text(b.get("content", "")))
    return "".join(parts)


def from_body(body: dict | str) -> list[str]:
    if isinstance(body, (str, bytes)):
        body = json.loads(body)
    return [_text(body.get("system", ""))] + [_text(m["content"]) for m in body["messages"]]


def set_texts(body: dict, texts: list[str]) -> dict:
    """Write reduced texts back into an agent-style body (used by the TokenKey proxy)."""
    body["system"] = [{"type": "text", "text": texts[0]}]
    for m, t in zip(body["messages"], texts[1:]):
        for b in m["content"]:
            if b.get("type") == "text":
                b["text"] = t; break
            if b.get("type") == "tool_result":
                b["content"] = [{"type": "text", "text": t}]; break
    return body
