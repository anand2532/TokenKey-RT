# TokenKey RT fab package. `make` = dry run (gates reported, not fatal); `make release` = strict.
.PHONY: all dry-run release clean
all dry-run:
	@bash scripts/make_fab.sh
release:
	@bash scripts/make_fab.sh --strict
clean:
	rm -rf out
