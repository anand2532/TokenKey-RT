# TokenKey RT

TokenKey RT is a compact USB-C desktop/laptop accessory built on the NXP i.MX RT1062 (Cortex-M7, up to 600 MHz; MIMXRT1062DVL6B, 10x10 mm BGA). It accelerates AI token-usage optimization — context reduction, request analysis and cost monitoring — working together with a Linux companion application on the host laptop.

## Repository layout

| Path | Contents |
|------|----------|
| `docs/` | Specifications, design decisions and project documentation |
| `hardware/schematic/` | KiCad schematic |
| `hardware/pcb/` | KiCad 4-layer PCB layout |
| `hardware/libraries/` | Project symbols, footprints and 3D models |
| `firmware/` | i.MX RT1062 firmware and USB protocol |
| `software/` | Laptop companion application |
| `fab/` | Manufacturing outputs (Gerbers, drill, BOM, pick-and-place, assembly drawings) |

## Documentation

- [Baseline specifications & requirements](docs/baseline-specs.md)
- [Design decisions](docs/decisions.md)

## Contributing

Every change follows the same flow:

1. Open an issue describing the change.
2. Create a branch named `issue-N-short` (e.g. `issue-1-scaffold`).
3. Commit with `Fixes #N` in the commit message.
4. Open a pull request into `main`.
5. Merge the PR, which closes the issue.

No direct pushes to `main`, and no force-pushes.
