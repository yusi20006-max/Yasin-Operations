# Yasin-Operations

Modular Operations Agent foundation for the Yasin ecosystem.

## Independence

This repository is standalone. It does not require, import, or call
out to Yasin-AI, YasinPress, YasinRelay, Hermes, any other Yasin
repository, any external AI provider, or any running service outside
this repository. A clean clone can install, import, and run its full
test suite with none of those available.

Future integrations (Hermes, Yasin-AI, YasinPress, YasinRelay) will
be implemented as adapters that depend on this Core -- the Core will
never depend on them. See `yasin_operations/adapters/` (currently
empty; adapters are out of scope for Issue #1).

## Package layout

```
yasin_operations/
    core/
        operations/   Operation, OperationTarget, OperationMetadata,
                       OperationState, OperationStatus lifecycle
        execution/     Executor: dispatches Operations to registered Tools
        results/       OperationResult, OperationError, ErrorCategory
    tools/
        contracts/     Tool protocol, ToolDescriptor, ToolCapability
        registry/      ToolRegistry
    config/            OperationsConfig, load_config()
    logging/           AuditRecord, AuditRecorder protocol,
                        InMemoryAuditRecorder
    safety/            SafetyClass (READ_ONLY / MUTATING)
    adapters/          empty in this issue; future integration adapters
```

## Safety boundary

Every `Operation` carries an explicit `SafetyClass`
(`READ_ONLY` or `MUTATING`). This issue does not implement shell
execution, arbitrary command execution, or any destructive
capability -- it only establishes the classification a future
permission-enforcement layer (Issue #4) will use.

## Status

Issue #1 (Core Architecture -- Operations Agent Foundation) only.
No Hermes/Yasin-AI/YasinPress/YasinRelay integration exists yet.

## Development

```bash
pip install -e ".[dev]"
pytest
```
