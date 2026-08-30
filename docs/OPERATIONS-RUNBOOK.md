# Yasin-Operations runbook

Operational notes for the standalone Operations component. This document does
not replace YASIN-DOCS architecture authority.

## Local commands

```sh
python -m yasin_operations doctor
python -m yasin_operations status
python -m yasin_operations health
python -m yasin_operations monitor
python -m yasin_operations restart <service> --dry-run
python -m yasin_operations restart <service> --confirm
yasin-operations --version
```

Use `--json` for machine-readable output.

## Production acceptance

Hosted/offline acceptance:

```sh
python scripts/production_acceptance.py
python scripts/production_acceptance.py --json
```

Live service inspection is opt-in and remains read-only:

```sh
python scripts/production_acceptance.py --live
python scripts/production_acceptance.py --live --json
```

See `docs/TERMUX-LIVE-ACCEPTANCE.md` for PASS/FAIL/SKIP/BLOCKED classification,
optional-service handling, and Termux operator commands.

A runit result beginning with `run:` is interpreted as actual `running`. A result beginning with `down:` is actual `stopped`, even when the text says `normally up`. `fail:` and `timeout:` are actual `failed`. Desired state is not substituted for actual state. Therefore a service configured as desired `running` but reported by runit as `down: ... normally up` is a genuine runtime failure for a live acceptance run, not a harness success.

Use `--json` for machine-readable harness output.

## Release readiness

Before a release candidate, run:

```sh
python scripts/release_readiness.py --json
```

This is a safe, non-destructive gate. It verifies that the authoritative package version is present, tracked repository files contain no forbidden credential/key/cache artifacts, the source tree has no imports of external Yasin packages, and the canonical acceptance harness succeeds.

The package can be verified independently with:

```sh
python -m pip install build
python -m build --wheel --sdist
python -m pip install dist/*.whl
python -m yasin_operations --version
yasin-operations --version
```

The two version commands must report the same package version. The source distribution must also install successfully in a clean environment.

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
| Target service failed | Status/health reports failed; other services remain observable |
| Optional service directory absent | Live acceptance SKIP; not a product FAIL |
| Service root / sv missing | Live acceptance BLOCKED (environment) |
