# Investigation

Phase 5 baseline confirmed on main @ 248f2fd.

Real gaps for Phase 6 (not reimplementing completed work):
1. create_execution Idempotency-Key race under concurrent retries
2. Stale .json.tmp files after interrupted durable writes
3. Missing focused production-hardening regressions

Cross-repo: Hub lifecycle ownership unchanged; Agent-side only fixes.
