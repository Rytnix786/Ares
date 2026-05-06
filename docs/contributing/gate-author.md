# Gate Author Guide

Gate authors can publish custom decision policy without editing `ares/gate/rules_engine.py`.

1. Implement the `GatePlugin` contract from `ares.gate.plugins`.
2. Return `GateDecision` with stable verdict/reason/deltas.
3. Register via `[project.entry-points."ares.gate_plugins"]`.
4. Add plugin failure/isolation tests.
5. Treat plugins as trusted code and use production allowlists.

See `docs/gate-plugin-guide.md`.
