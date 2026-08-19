# Yasin-Operations operator runbook

## Operating model

Yasin-Operations is optional. Existing Yasin services must not require it to start, run, or stop. The Core owns typed operations and safety policy; adapters provide platform/service boundaries.

## First verification

1. Run the complete test suite with `python -m pytest -q`.
2. Run `python -m yasin_operations.cli doctor` on the target host.
3. Run `python -m yasin_operations.cli status` and confirm only intentionally registered services appear.
4. Run `python -m yasin_operations.cli health`.
5. Validate a mutation with `--dry-run` before using `--confirm`.

## Safety rules

- Read-only operations do not require confirmation.
- Mutating operations require explicit confirmation by default.
- Protected targets remain denied unless explicitly allowlisted in policy.
- Dry-run never invokes the target tool.
- All adapter-driven mutations pass through `Executor` and `SafetyPolicy`.
- Audit records contain operation, target, actor/source, correlation ID, result, and timing.

## Failure isolation

If Operations is unavailable, adapters return structured `unavailable_dependency` responses. Existing services are not managed by a shared Operations process and therefore remain independently restartable by their own supervisor.

If a target service fails, the Operations adapter reports the failure; it does not rewrite the target service definition or its configured interval.

## Recovery matrix

| Scenario | Expected behavior |
| --- | --- |
| Operations stopped | Existing services continue independently |
| Operations restarted | Adapter/runtime state is rebuilt from configuration |
| Target service stopped | Status/health reports stopped or unhealthy |
| Target service unavailable | Adapter returns structured unavailable response |
| Adapter failure | Core remains importable and other adapters remain usable |
| Mutation without confirmation | Denied and audited |
| Dry-run mutation | Plan returned; target untouched |
| Runit unavailable | Termux diagnostics report the missing supervisor; no mutation is attempted |

## Termux always-on service

The optional service definition is under `deploy/termux/runit/yasin-operations/`. It runs the persistent Operations daemon under `runit`. The file must be executable after installation.

The service is intentionally independent of existing Hermes, Yasin-AI, YasinPress, and YasinRelay service definitions.
