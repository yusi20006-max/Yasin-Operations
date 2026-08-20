# Ecosystem Adapter Contract

## Purpose

The Yasin-AI, YasinPress, and YasinRelay adapters are integration boundaries, not implementations of those projects. They translate observations and typed Operations without importing provider internals.

## Contract version

The canonical ecosystem adapter contract is version `1`.

Every `ServiceSnapshot` and `AdapterResult` carries the contract version. Consumers must reject unknown contract versions rather than guessing field semantics.

## ServiceSnapshot

Required invariants:

- `service` is the adapter-owned canonical service identity.
- `available` is explicit.
- `state` is one of the shared transport-neutral states.
- `version`, when present, uses a bounded identifier format.
- capabilities are non-empty strings, unique, and deterministically sorted.
- diagnostics are non-authoritative observation data.
- error is optional structured human-readable context.

A probe returning another service identity is treated as an unavailable/failed boundary condition. It is never silently accepted.

## Capability namespace

Each adapter owns one operation prefix:

- `Yasin-AI` → `yasin_ai_*`
- `YasinPress` → `yasin_press_*`
- `YasinRelay` → `yasin_relay_*`

The common capability suffixes are `status`, `health`, `version`, and `capabilities`.

Capability discovery is deterministic and must not depend on provider SDK metadata.

## Failure isolation

Probe failures are converted to a structured snapshot. Timeout and connection failures are represented as unavailable; malformed or unexpected probe behavior is represented as a failed boundary. The failure of one adapter does not alter another adapter's state.

Executor failures are also normalized at the adapter boundary. Raw provider exceptions are never exposed as the adapter API.

## Execution authority

Adapter operations are always read-only in this layer. Any future mutating integration must still construct a typed Core `Operation` and pass through `Executor` and `SafetyPolicy`; adapters cannot authorize mutations themselves.

## Dependency boundary

Adapters must not:

- import implementation modules from Yasin-AI, YasinPress, or YasinRelay;
- embed provider SDK semantics in Core contracts;
- execute shell commands;
- perform privileged operations;
- bypass replay/idempotency protections;
- treat diagnostic metadata as authorization input.

## Extension rule

A new ecosystem service should implement the same `EcosystemServiceAdapter` contract, add only its service-specific identity/prefix, and provide contract tests for identity, capability namespace, version, unavailable behavior, timeout behavior, malformed probe behavior, and Executor failure isolation.
