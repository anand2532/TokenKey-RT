#!/usr/bin/env bash
# TokenKey RT fab-package pipeline (kicad-cli 9.x). Generates files only; never orders or quotes.
# Usage: fab/scripts/make_fab.sh [--strict]   (default dry-run: gates report but don't stop)
set -uo pipefail
STRICT=0; [ "${1:-}" = "--strict" ] && STRICT=1
ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
HW="$ROOT/hardware/schematic"; PCB="$HW/TokenKey-RT.kicad_pcb"; SCH="$HW/TokenKey-RT.kicad_sch"
SHA="$(git -C "$ROOT" rev-parse --short HEAD)"; DIRTY=""; git -C "$ROOT" diff --quiet HEAD -- hardware || DIRTY="-dirty"
OUT="$ROOT/fab/out/$SHA$DIRTY"; rm -rf "$OUT"
G="$OUT/gerbers"; P="$OUT/pcba"; D="$OUT/docs"; R="$OUT/reports"; mkdir -p "$G" "$P" "$D" "$R"
KV="$(kicad-cli version)"; SUMMARY="$R/summary.md"
echo "# Fab dry run $SHA$DIRTY ($(TZ=Asia/Kolkata date '+%F %T IST'), kicad-cli $KV)" > "$SUMMARY"
FAIL=0
step(){ local n="$1"; shift; if "$@" >"$R/$n.log" 2>&1; then echo "- [x] $n" >>"$SUMMARY"; else echo "- [ ] $n FAILED (see reports/$n.log)" >>"$SUMMARY"; FAIL=1; fi; }

step gerbers kicad-cli pcb export gerbers "$PCB" -o "$G/" --no-x2 --use-drill-file-origin --subtract-soldermask \
  --layers F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,Edge.Cuts
step drill kicad-cli pcb export drill "$PCB" -o "$G/" --format excellon --excellon-units mm --excellon-separate-th \
  --drill-origin plot --generate-map --map-format gerberx2
step pos_top kicad-cli pcb export pos "$PCB" -o "$R/pos-top.csv" --side front --format csv --units mm --use-drill-file-origin --exclude-dnp
step pos_bottom kicad-cli pcb export pos "$PCB" -o "$R/pos-bottom.csv" --side back --format csv --units mm --use-drill-file-origin --exclude-dnp
step bom_raw kicad-cli sch export bom "$SCH" -o "$R/bom-raw.csv" --exclude-dnp \
  --fields 'Value,Reference,Footprint,LCSC' --labels 'Comment,Designator,Footprint,LCSC Part #' --group-by 'Value,Footprint,LCSC' --ref-range-delimiter ''
step ipcd356 kicad-cli pcb export ipcd356 "$PCB" -o "$OUT/TokenKey-RT.ipc356"
step assy_top kicad-cli pcb export pdf "$PCB" -o "$D/assembly-top.pdf" --mode-single --layers F.Fab,Edge.Cuts --ibt --sp --cdnp
step assy_bottom kicad-cli pcb export pdf "$PCB" -o "$D/assembly-bottom.pdf" --mode-single --mirror --layers B.Fab,Edge.Cuts --ibt --sp --cdnp
step jlc_convert python3 "$ROOT/fab/scripts/jlc_convert.py" "$R" "$P"
cp "$ROOT/fab/README.md" "$ROOT/fab/stackup.md" "$OUT/" 2>/dev/null

# Gates (always reported; only --strict makes them fatal)
kicad-cli sch erc "$SCH" -o "$R/erc.json" --format json --severity-all >"$R/erc.log" 2>&1
kicad-cli pcb drc "$PCB" -o "$R/drc.json" --format json --severity-all --schematic-parity >"$R/drc.log" 2>&1
python3 "$ROOT/fab/scripts/gate_summary.py" "$R" >>"$SUMMARY"; GATE=$?

python3 -c "import shutil,sys; shutil.make_archive(sys.argv[1], 'zip', sys.argv[2])" "$OUT/TokenKey-RT_gerbers_drill_$SHA" "$G" && echo "- [x] gerber+drill zip" >>"$SUMMARY"
echo; cat "$SUMMARY"; echo "Output: $OUT"
[ $STRICT = 1 ] && { [ $FAIL = 0 ] && [ $GATE = 0 ] || exit 1; }
exit 0
