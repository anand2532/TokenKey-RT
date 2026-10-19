PY ?= python3
all:
	$(PY) build.py
check:
	$(PY) build.py --check-only
variant-a:
	TK_SHAFT=15 TK_KNOB_H=7 $(PY) build.py --check-only
.PHONY: all check variant-a
