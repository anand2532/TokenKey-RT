# TokenKey RT — Baseline Specifications & Requirements

## 1. Project Objective
Develop a compact USB-connected hardware device using the NXP i.MX RT1062 MCU to support AI token-usage optimization, context reduction, request analysis, and cost monitoring through companion laptop software.

## 2. Hardware Requirements
- MCU: NXP i.MX RT1062, Cortex-M7, up to 600 MHz.
- PCB type: Custom bare-MCU design.
- Target PCB size: Approximately 50 × 40 mm; minimize dimensions without compromising electrical performance or manufacturability.
- PCB construction: 4-layer FR-4 PCB, using both top and bottom component sides where beneficial.
- Component placement: Place components on both sides of the PCB to maximize density, minimize routing length, and maintain serviceability.
- Host interface: USB 2.0 device via USB-C.
- Power input: USB 5 V with appropriate protection and regulation.
- Display: Compact I²C OLED, preferably 128 × 64.
- User controls: One rotary encoder with push switch and two additional buttons.
- Debug interface: JTAG/SWD-compatible debug access and optional UART console.
- Memory: Boot flash and any required external RAM selected according to the RT1062 reference design and application requirements.
- Enclosure: Compact desktop/laptop accessory with suitable display, button, connector, and mounting clearances.

## 3. PCB Stackup and Layout Requirements
- Use a 4-layer PCB with a manufacturer-approved stackup and impedance requirements.
- Proposed layer allocation:
  - L1 — Top: MCU and primary components, critical signals, and short high-speed routes.
  - L2 — Inner 1: Continuous ground plane with minimal interruptions.
  - L3 — Inner 2: Power distribution and suitable lower-speed signals.
  - L4 — Bottom: Secondary components, supporting circuitry, and additional signal routing.
- Populate both top and bottom sides where necessary to maintain the compact form factor.
- Place decoupling capacitors as close as practical to their associated MCU power pins.
- Place USB ESD protection close to the USB-C connector.
- Keep USB differential pairs short, properly coupled, and routed over a continuous ground reference.
- Avoid splitting the ground plane beneath critical high-speed signals.
- Use vias and layer transitions carefully; minimize unnecessary transitions on critical signals.
- Keep BGA escape routing, soldering, inspection, and assembly constraints in mind when placing bottom-side components.
- Maintain component-to-component, component-to-edge, enclosure, connector, and mounting-hole clearances.
- Prioritize electrical correctness, thermal performance, signal integrity, and manufacturability over achieving the smallest possible outline.
- Confirm that the proposed 50 × 40 mm dimensions are feasible after component placement and BGA fanout analysis; increase the size if required.

## 4. Firmware Requirements
- USB communication with the laptop companion application.
- Fast text parsing and bounded-buffer processing.
- Incremental hashing and duplicate-context detection.
- Changed-file and code-block identification.
- Context ranking and token-budget management.
- Token-count estimation and processing statistics.
- Economy, Balanced, and Quality operating modes.
- Real-time display of device status and optimization results.
- Robust error handling, watchdog support, and firmware recovery.

## 5. Laptop Software Requirements
- Companion application for Linux initially, with Windows support as a future target.
- Integration with selected AI APIs and coding tools.
- Provider-specific token counting and actual usage/cost tracking.
- Context optimization, model-routing policies, and optional prompt caching support.
- Preview and approval of modified prompts before submission.
- Privacy controls and local-first processing.
- Before/after measurement of token usage, API cost, latency, and answer quality.

## 6. Electrical and Component Design Requirements
- Follow the official NXP reference design for the exact RT1062 variant and package.
- Verify all MCU pin assignments, power rails, clocking, reset, boot configuration, flash interface, and USB connections.
- Include suitable USB ESD protection, USB-C CC configuration, input protection, and power regulation.
- Select all components using verified datasheets, electrical ratings, footprints, and availability.
- Provide accessible test points and programming/debug connections.
- Ensure the bottom-side components do not obstruct connectors, enclosure mounting, or required thermal paths.
- Complete KiCad ERC and DRC before manufacturing.
- Verify footprints against manufacturer mechanical drawings and the PCB manufacturer's design rules.

## 7. Performance and Validation Goals
- Measure MCU processing latency for representative text and code-context workloads.
- Measure throughput, RAM usage, and maximum supported buffer size.
- Compare actual input-token counts and API costs before and after optimization.
- Verify that optimization does not remove required context or significantly degrade answer quality.
- Validate USB stability, power consumption, reset recovery, and continuous operation.
- Establish measurable performance targets after benchmarking the first prototype.

## 8. Design Constraints
- The MCU accelerates context processing; it does not independently run a full cloud-scale LLM.
- Token savings must come from verified software optimizations, not MCU clock speed alone.
- Exact MCU package, pin assignments, regulator topology, flash, external memory, and component values remain subject to engineering verification.
- The 50 × 40 mm board size is a target, not a confirmed routing constraint.
- Both-side component placement and a 4-layer stackup must not compromise ground continuity, signal integrity, thermal performance, assembly, or debugging.
- No fabrication release until the schematic, layout, ERC/DRC, and electrical design review are complete.

## 9. Required Deliverables
1. Complete KiCad schematic.
2. Routed 4-layer PCB layout using both sides where beneficial.
3. Manufacturing outputs: Gerbers, drill files, BOM, pick-and-place files, and assembly drawings.
4. Verified BOM with manufacturer part numbers.
5. Pin mapping and interface documentation.
6. Firmware source code and USB protocol.
7. Laptop companion application.
8. Test plan and measured optimization results.
9. Fabrication, assembly, and bring-up documentation.
