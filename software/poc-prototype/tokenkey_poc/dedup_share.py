"""Diagnostic: share of newly-arriving message bytes that are exact duplicates (same XXH32 segment) of
content seen earlier in the same session. This is the lossless part of the firmware algorithm (dedup),
an upper bound for savings without dropping unique content."""
import sys

from . import sessions
from . import tk_core as tk

for path in sys.argv[1:]:
    tot = dup = 0
    for s in sessions.load(path):
        reqs, _ = sessions.requests_of(s)
        d = tk.DupSet(); n = 0
        for r in reqs:
            off = 0
            for mi, m in enumerate(r[n:]):
                for seg in tk.scan_message(m, mi, off):
                    tot += seg.length
                    if d.check_insert(__import__("xxhash").xxh32_intdigest(seg.data), 0) and seg.data.strip():
                        dup += seg.length
            n = len(r)
    print(f"{path}: duplicate share of new content = {100 * dup / tot:.1f}% of {tot} bytes")
