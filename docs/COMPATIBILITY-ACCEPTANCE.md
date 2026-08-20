# Compatibility & Acceptance Matrix

This document defines how Yasin-Operations establishes reproducible compatibility evidence.

## Supported Python baseline

The package declares `requires-python = ">=3.11"`. The hosted CI matrix explicitly verifies Python 3.11, 3.12, 3.13, and 3.14.

## Hosted CI evidence

For each supported Python version, CI performs:

1. Editable installation with development test dependencies.
2. `pip check` dependency consistency verification.
3. Source compilation.
4. Complete pytest suite.
5. Production acceptance harness without live service dependencies.
6. Wheel and source-distribution build.
7. Clean virtual-environment installation from the built wheel.
8. Clean virtual-environment installation from the source distribution.
9. Installed console-entrypoint and module-entrypoint version/help checks.
10. Installed JSONL gateway entrypoint smoke verification.
11. Production acceptance and release-readiness verification from the clean wheel environment.

Hosted CI intentionally does **not** claim live Termux/runit health. The production acceptance harness reports live checks as skipped unless `--live` is explicitly supplied on a host that provides the required `sv` environment.

## Live-host evidence

A valid Termux/runit host may run:

```text
python scripts/production_acceptance.py --live --json
```

This is operational evidence for that host only. It must not be represented as a hosted CI result.

## Clean-environment rule

Acceptance commands that validate installed artifacts execute from `/tmp` rather than the repository working directory. This prevents accidental imports from the checkout and verifies that package metadata, console scripts, module entrypoints, runtime package boundaries, and the gateway are actually installed.

## Failure policy

A matrix failure blocks the release-completion work. Compatibility is not established by a single successful developer environment, and a green unit-test suite alone is insufficient evidence for package/install compatibility.
