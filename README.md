# Yasin-Operations

Modular Operations Agent foundation for the Yasin ecosystem.

## Independence

This repository is standalone. It does not require, import, or call
out to Yasin-AI, YasinPress, YasinRelay, Hermes, any other Yasin
repository, any external AI provider, or any running service outside
this repository. A clean clone can install, import, and run its full
test suite with none of those available.

Future integrations (Hermes, Yasin-AI, YasinPress, YasinRelay) are
implemented as optional adapters that depend on this Core -- the Core
never depends on them.

## Package layout

```
yasin_operations/
    core/
        operations/   Typed operation and lifecycle contracts
        execution/    Policy-enforced executor and tool dispatch
        results/      OperationResult, OperationError, ErrorCategory
    runtime/
        local/        Portable local process/service backends
        termux/       Optional Termux/runit adapter and diagnostics
        tools.py      Runtime Tool adapters and registration
        health.py     Structured health results
        diagnostics.py Runtime diagnostics
    tools/
        contracts/    Tool protocol, descriptors, capabilities
        registry/     ToolRegistry
    config/           OperationsConfig, load_config()
    logging/          AuditRecord, AuditRecorder, in-memory recorder
    safety/           SafetyClass and deny-by-default SafetyPolicy
    adapters/         Reserved for ecosystem integration adapters
```

## Safety boundary

Every `Operation` carries an explicit `SafetyClass`
(`READ_ONLY` or `MUTATING`). `SafetyPolicy` enforces the boundary
before a tool can execute:

- read-only operations are permitted without confirmation;
- mutating operations require explicit confirmation by default;
- protected targets are denied unless explicitly allowlisted;
- dry-run produces a deterministic plan and never calls a tool;
- retry limits and execution timeout policy are explicit;
- denied, successful, failed, and dry-run outcomes can be audited with
  actor, source, correlation ID, timestamp, target, and duration.

The executor never exposes unrestricted shell execution and never
bypasses the policy layer.

## Termux adapter

The Termux integration is optional and isolated under
`yasin_operations/runtime/termux/`. It detects the Termux/runit
environment, observes registered services, performs lifecycle actions
using fixed argument vectors, and reports startup/always-on diagnostics.
It does not modify external Yasin service definitions and is not
required for the existing services to operate.

## Status

Issues #1 through #3 are implemented on `main`. Issue #4 is the
current safety/permissions/audit implementation. Issues #5 through #7
remain planned work.

## Development

```bash
pip install -e ".[dev]"
python -m pytest -q
```

A GitHub Actions test matrix validates the suite on supported Python
versions.
