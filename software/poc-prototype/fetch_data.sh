#!/usr/bin/env sh
# Recreate data/ (not committed): 30 public SWE-agent trajectories + 10 SYNTHETIC sessions (seed 42).
# No API keys needed. Run from software/poc-prototype/ with the venv active.
set -e
mkdir -p data
python -m tokenkey_poc.sessions public 30 data/public_swe_agent_trajectories.jsonl   # HF nebius/SWE-agent-trajectories, streamed
python -m tokenkey_poc.sessions synthetic 10 data/SYNTHETIC_sessions.jsonl           # machine-generated, labelled SYNTHETIC
( cd tools/tamp && npm ci )                                                           # Tamp 0.8.21 for comparison arm E
