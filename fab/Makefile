# TokenKey RT fab package. `make` = dry run incl. panel (gates reported, not fatal); `make release` = strict.
KIKIT_VERSION := 1.8.1
VENV ?= /workspace/.venv-kikit
KIKIT ?= $(VENV)/bin/kikit
export KIKIT
.PHONY: all dry-run release panel kikit clean
all dry-run: kikit
	@bash scripts/make_fab.sh
release: kikit
	@bash scripts/make_fab.sh --strict
panel: kikit
	@bash scripts/make_fab.sh   # panel is part of every run; outputs in out/<sha>/panel
kikit:
	@test -x $(KIKIT) || { python3 -m venv --system-site-packages $(VENV) && $(VENV)/bin/pip install -q kikit==$(KIKIT_VERSION); }
clean:
	rm -rf out
