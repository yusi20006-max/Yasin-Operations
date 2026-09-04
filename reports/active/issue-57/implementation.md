# Implementation

1. `agent_platform/server/app.py` — create_execution holds idem_lock across check+create+cache when Idempotency-Key present
2. `agent_platform/persistence.py` — list_ids unlinks `*.json.tmp`
3. `tests/test_phase6_production_hardening.py` — 11 regressions
4. CHANGELOG 1.1.1
