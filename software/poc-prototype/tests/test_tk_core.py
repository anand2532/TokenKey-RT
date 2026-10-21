import pytest
from tokenkey_poc import tk_core as tk


def test_scanner_types():
    txt = ("Intro paragraph\nmore prose\n\n```python\nx=1\n```\n"
           "diff --git a/src/a.py b/src/a.py\nindex 1..2 100644\n--- a/src/a.py\n+++ b/src/a.py\n@@ -1 +1 @@\n-a\n+b\n"
           "Traceback (most recent call last):\n  File \"x.py\", line 3, in f\n    g()\nKeyError: 'k'\n")
    segs = tk.scan_message(txt, 0, 0)
    kinds = [s.type for s in segs]
    assert kinds == [tk.PROSE, tk.CODE, tk.DIFF, tk.LOG]
    assert segs[2].file_id == "src/a.py"
    assert b"".join(s.data for s in segs).decode() == txt          # lossless segmentation
    assert all(segs[i].offset + segs[i].length == segs[i + 1].offset for i in range(len(segs) - 1))


@pytest.mark.parametrize("mode,pct", tk.MODE_KEEP_PCT.items())
def test_budget_respected_and_order_kept(mode, pct):
    msgs = ["\n\n".join(f"paragraph {i} " + "word " * (i % 7 + 3) for i in range(200))]
    out, st = tk.run_job(msgs, mode)
    assert st.tok_in == st.bytes_in // 4
    assert st.tok_out <= st.tok_in * pct // 100
    # kept text is a subsequence of the original in original order
    pos = 0
    for para in out[0].split("\n\n"):
        if para.strip():
            j = msgs[0].find(para.strip(), pos)
            assert j >= pos
            pos = j


def test_duplicates_dropped_first():
    block = "```\n" + "same code line\n" * 20 + "```\n"
    msgs = [block, "unique prose here\n\n", block]
    out, st = tk.run_job(msgs, "quality")
    assert st.dup_hits == 1
    assert out[2] == ""          # the later duplicate is dropped, the original kept
    assert out[0] == block


def test_type_weight_order():
    w = tk.TYPE_WEIGHT
    assert w[tk.DIFF] > w[tk.CODE] > w[tk.LOG] > w[tk.PROSE]


def test_ctx_overflow():
    msgs = ["\n".join(f"line {i}\n" for i in range(tk.MAX_SEGMENTS + 10))]
    with pytest.raises(tk.CtxOverflow):
        tk.run_job(msgs, "quality")


def test_dupset_load_cap_and_set_full():
    d = tk.DupSet()
    for h in range(d.cap):
        assert d.check_insert(h * 7919 + 1, h) is False
    assert d.count == 8192 * 75 // 100
    assert d.check_insert(999_999_999, 0) is False and d.set_full == 1   # full: not deduped, counted


def test_explicit_token_budget_overrides_mode():
    msgs = ["\n\n".join("p%d %s" % (i, "x" * 40) for i in range(100))]
    _, st = tk.run_job(msgs, "quality", token_budget=100)
    assert st.tok_out <= 100


def test_greedy_density_prefers_small_segments():
    # [SPEC] greedy by score/size: a small prose paragraph outranks a large code block per byte,
    # so under a tight budget the code block can be dropped even though its type weight is higher.
    block = "```\n" + "same code line\n" * 20 + "```\n"
    out, _ = tk.run_job([block, "unique prose here\n\n"], "balanced")
    assert out[0] == "" and out[1] != ""


def test_exempt_messages_kept_and_ratio_only_on_rest():
    big = "\n\n".join(f"older output line {i} " + "z" * 30 for i in range(100))
    msgs = ["system prompt\n", "the task\n", big, "newest output\n"]
    out, st = tk.run_job(msgs, "economy", exempt=[True, True, False, True], drop_dups=True)
    assert out[0] == msgs[0] and out[1] == msgs[1] and out[3] == msgs[3]
    assert 0 < len(out[2]) <= len(big) * 30 // 100


def test_drop_dups_applies_to_exempt_messages_too():
    block = "```\n" + "same code line\n" * 20 + "```\n"
    out, _ = tk.run_job(["sys\n", block, block], "quality", exempt=[True, True, True], drop_dups=True)
    assert out[1] == block and out[2] == ""


def test_collapse_repeats_keeps_first_last_and_first_traceback():
    from tokenkey_poc.session_reducer import collapse_repeats
    tb = "Traceback (most recent call last):\n" + '  File "x.py", line 1, in f\n' * 5 + "KeyError: 'k'\n"
    txt = "start\n" + "warning: deprecated\n" * 6 + "\n" + tb + "end\n" + "x\n" * 3
    out = collapse_repeats(txt)
    assert "warning: deprecated\n[repeated 6×]\nwarning: deprecated\n" in out
    assert tb in out                      # first traceback block untouched even though it has a run of 5
    assert out.endswith("x\nx\nx\n")      # run of 3 is not collapsed
