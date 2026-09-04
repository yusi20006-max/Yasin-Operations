# Investigation

## Baseline
The current YasinHub `main` tip is `bb99859568d177074c777097e469018ed98bdbfd`, containing the Phase 4 truthful PWA ↔ Control Plane integration.

The Hub already contains real-process lifecycle regressions covering canonical Relay start, START/STOP/START/RESTART PID behavior, early startup failure, crash reconciliation, foreign-PID protection, Hub restart reconciliation, and `shell=False` spawning.

Yasin-Agent Phase 6 is already complete under canonical Issue #57 / PR #58, not duplicate Issue #56.

## Decision
Issue #56 in Yasin-Agent was closed as duplicate. Final acceptance is consolidated under YasinHub #174.

## Remaining verification
- CI execution for the new final acceptance test.
- Post-merge verification on the resulting Hub main commit.
- Physical Termux/Android ARM64 acceptance remains deferred until a real device is available.
- Credentialed source/fetch/publish remains operator-dependent and must not be simulated.
