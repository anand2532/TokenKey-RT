# docs/poc — Proof of concept and product value

This folder holds proof-of-concept and product-value analyses for TokenKey RT. They answer two questions: **does TokenKey RT create real value, and will people want it?**

## Purpose

Analyses here cover:

- **Target users:** who would use TokenKey RT and in what workflows.
- **Problem size:** how much AI token usage and cost there is to optimize, and for whom.
- **Alternatives:** software-only tools, provider features (e.g. prompt caching) and other existing options.
- **Why hardware:** what a dedicated USB device adds compared with a software-only approach.
- **Willingness to pay:** pricing signals and what users would pay.
- **Risks:** technical, market and adoption risks.
- **PoC experiments and go/no-go:** experiments to validate the value, plus the criteria for continuing or stopping.

## Conventions

- One markdown file per analysis, named `YYYY-MM-DD-topic.md` (e.g. `2026-10-19-target-users.md`).
- Start each file with a short summary of the findings and conclusion.
- Cite sources for every external fact or figure.
- Label assumptions clearly as assumptions.
- No invented data: if a number isn't sourced or measured, say so.

## Ownership

- **Owner:** TokenKey PoC bot writes the analyses; they are committed via TokenKey Git (issue → branch → PR → merge).
- **Consumer:** TokenKey PM uses them as product reference.

## Index

- [2026-10-19 Value assessment](2026-10-19-value-assessment.md): target users, problem size, competitors/substitutes, hardware rationale, willingness to pay, risks. **Recommendation: no-go on hardware spend for now; go on a software-only PoC with gates G1-G5.**
- [2026-10-19 PoC experiment plan](2026-10-19-poc-experiment-plan.md): 2-4 week host-only prototype of the firmware algorithm, with variants vs provider-caching baseline and free proxies, and success criteria mapped to baseline spec §7.
- [2026-10-19 Prototype results](2026-10-19-prototype-results.md): software prototype gate results (G1 not passed, hinges on real timestamped logs; G5 passed).
