PY ?= python3
all:
	$(PY) build.py
check:
	$(PY) build.py --check-only
variant-trim:
	TK_SHAFT_TRIM=2.5 TK_KNOB_H=14 TK_DKEY_MARGIN=0.5 $(PY) build.py --check-only
.PHONY: all check variant-trim
