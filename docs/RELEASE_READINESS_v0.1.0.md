# Yasin-Operations v0.1.0 — Release Readiness

## Release scope

Yasin-Operations is an optional, standalone Operations Agent for the Yasin ecosystem. Core operation does not require Hermes, Yasin-AI, YasinPress, YasinRelay, another Yasin repository, or an external AI provider.

## Architecture completed

- Core operation contracts and execution foundation
- Runtime process/service/health/diagnostics layer
- Optional ecosystem adapters for Yasin-AI, YasinPress, YasinRelay, and Hermes
- Centralized authorization and default-deny policy enforcement
- Unified audit and observability
- Retry, cancellation, scheduling, and reliability controls
- Production CLI, configuration, packaging, and optional local daemon/gateway
- Termux/runit integration with authoritative runtime-state normalization
- Canonical production acceptance harness
- Release-readiness checks and CI acceptance gating

## Package

- Version: `0.1.0`
- Supported Python: `>=3.11` (CI matrix covers 3.11, 3.12, 3.13, and 3.14)
- Runtime dependencies: none
- CLI: `yasin-operations`
- Module entrypoint: `python -m yasin_operations`

## Canonical verification

```text
python -m pytest -q
python scripts/production_acceptance.py --json
python scripts/release_readiness.py --json
python scripts/production_acceptance.py --live --json
```

Hosted CI performs the non-live acceptance surface. Live runit checks are host/operator verification and are not represented as hosted-CI health claims.

## Live evidence

The final live Termux verification completed with **14 PASS / 0 FAIL / 0 SKIP**. The four supervised services observed by the acceptance harness were running at the successful verification point: Hermes, Yasin-AI, YasinPress, and YasinRelay.

This document intentionally contains no PIDs, private filesystem paths, credentials, tokens, or machine-specific configuration.

## Security boundary

- `SafetyClass.READ_ONLY` and `SafetyClass.MUTATING` remain explicit.
- Authorization is enforced before tool execution.
- Mutating operations require explicit authorization/confirmation.
- Retry logic never retries permission denial.
- Scheduler is not privileged and cannot bypass policy.
- No unrestricted shell execution or `shell=True`.
- No external Yasin package is a hard dependency.
- No network listener is required by the standalone runtime.
- Diagnostics and audit records do not dump secrets or the environment.

## Release conclusion

The repository is ready to be treated as the stable `Yasin-Operations v0.1.0` standalone Operations layer, subject to the repository's existing CI gates and the recorded live host verification above.
