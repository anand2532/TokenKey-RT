#!/usr/bin/env python3
"""Summarise ERC/DRC JSON: pass/fail, counts by type, unconnected count. Exit 1 if any error."""
import json, sys, pathlib, collections
r = pathlib.Path(sys.argv[1]); bad = 0
def load(n):
    try: return json.load((r / n).open())
    except Exception as e: print(f"- [ ] {n}: not produced ({e})"); return None
def tally(items):
    c = collections.Counter((v.get("severity"), v.get("type")) for v in items); return c
erc = load("erc.json")
if erc is not None:
    c = tally(v for s in erc.get("sheets", []) for v in s.get("violations", []))
    e = sum(n for (s, _), n in c.items() if s == "error")
    print(f"- [{'x' if e == 0 else ' '}] ERC: {e} errors, {sum(c.values()) - e} warnings")
    for (s, t), n in sorted(c.items()): print(f"  - {s} {t}: {n}")
    bad |= e > 0
drc = load("drc.json")
if drc is not None:
    c = tally(drc.get("violations", [])); u = len(drc.get("unconnected_items", [])); par = len(drc.get("schematic_parity", []))
    e = sum(n for (s, _), n in c.items() if s == "error")
    print(f"- [{'x' if e == 0 and u == 0 and par == 0 else ' '}] DRC: {e} errors, {sum(c.values()) - e} warnings, {u} unconnected, {par} parity")
    for (s, t), n in sorted(c.items()): print(f"  - {s} {t}: {n}")
    bad |= (e > 0 or u > 0 or par > 0)
miss = r / "missing-lcsc.md"
if miss.exists(): print("- " + miss.read_text().splitlines()[0].lstrip("# "))
sys.exit(1 if bad else 0)
