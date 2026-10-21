PY ?= python3
all:
	$(PY) build.py
check:
	$(PY) build.py --check-only
.PHONY: all check
# FreeCAD port (#63): params.json -> FCStd + exports -> VALIDATION.md (needs freecadcmd on PATH)
freecad:
	cd ../freecad && $(PY) export_params.py && freecadcmd -c "exec(open('build_fc.py').read())" \
	  && freecadcmd -c "exec(open('validate_fc.py').read())" && python3 write_validation.py
.PHONY: freecad
# Print-ready STLs (#72): oriented, on z = 0
print:
	$(PY) print_export.py
.PHONY: print
