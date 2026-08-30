# Yasin-Operations Architecture Reconciliation

**Issue:** #119 — P0.1 Repository & YASIN-DOCS Architecture Reconciliation  
**Repository:** `yusi20006-max/Yasin-Operations`  
**Cross-project source of truth:** `yusi20006-max/YASIN-DOCS`  
**Audit basis:** repository source tree, package contracts, runtime/adapter boundaries, README, release/acceptance documentation, and YASIN-DOCS architecture/ADR/registry documents.

## 1. Executive finding

Yasin-Operations is implemented as an independently deployable Operations component with a platform-agnostic Core, optional runtime adapters, explicit safety policy, structured audit support, optional ecosystem adapters, and an optional local JSONL gateway.

The implementation is broadly consistent with YASIN-DOCS ADR-0012: Yasin-Operations does not require Hermes, Yasin-AI, YasinPress, or YasinRelay; the ecosystem adapters are optional; and Hermes is represented as an adapter boundary rather than a package dependency.

The main documentation discrepancy found during this reconciliation is **release/architecture status**: the repository README describes v0.1.0 as "release-ready", while YASIN-DOCS still classifies Yasin-Operations as **newly registered / provisional**. These statements are not necessarily contradictory at the implementation level, but they describe different readiness dimensions and must not be presented as if they were the same architectural status.

This audit therefore establishes the following distinction:

- **Implementation status:** substantial v0.1.0 functionality is implemented and tested in the repository.
- **Integration status:** Hermes and cross-repository relationships remain optional unless source-level evidence proves otherwise.
- **Architecture registry status:** Yasin-Operations remains **Provisional** in YASIN-DOCS until the cross-project audit is promoted there.
- **Production readiness:** repository-local release readiness is not equivalent to ecosystem-wide production certification.

No runtime behavior is changed by this document.

## 2. Canonical ownership boundaries

| Capability | Canonical owner | Yasin-Operations position | Status |
|---|---|---|---|
| Core AI capabilities | Yasin-AI | Does not own; may consume future public contracts through an adapter | Verified boundary |
| Publishing/news processing | YasinPress | Does not own | Verified boundary |
| Feed/relay transport | YasinRelay | Does not own | Verified boundary |
| Ecosystem management/status | YasinHub | Operations provides operational diagnostics/lifecycle tooling; does not replace Hub management ownership | Boundary requires continued coordination |
| Unified ecosystem CLI | YasinCLI | Operations exposes its own local operational CLI; it is not the ecosystem-wide CLI | Verified boundary |
| Agent runtime | Yasin-Agent | Operations is not the agent runtime | Verified boundary |
| Operations/diagnostics/service lifecycle | Yasin-Operations | Primary responsibility | Verified implementation |
| Hermes operator interface | Hermes | Optional/future client of Operations | Adapter exists; live integration is not claimed |
| Cross-project architecture | YASIN-DOCS | Repository is implementation authority; YASIN-DOCS is ecosystem architecture authority | Verified governance rule |

## 3. Implementation-to-documentation matrix

| Area | Repository evidence | YASIN-DOCS expectation | Reconciliation |
|---|---|---|---|
| Standalone Core | `yasin_operations/core/`, `Executor`, typed operation/result contracts | ADR-0012 requires independent deployment/testability | **Implemented / aligned** |
| Safety boundary | `SafetyClass`, `SafetyPolicy`, `Executor` | Operations must remain bounded and independently controlled | **Implemented / aligned** |
| Runtime | `runtime/`, Termux/runit adapter, diagnostics and lifecycle tools | Operations owns operational/runtime inspection | **Implemented / aligned** |
| Ecosystem adapters | `adapters/ecosystem/` | Future integrations must be optional and evidence-backed | **Implemented as optional adapters / aligned** |
| Hermes adapter | `adapters/hermes/` | Hermes is optional; integration must use an adapter | **Adapter implemented; live Hermes integration not claimed** |
| JSONL gateway | `gateway.py`, `gateway_cli.py` | Transport/integration boundary may be introduced without creating mandatory dependency | **Implemented as local optional transport** |
| MCP | Optional stdio MCP bridge (`yasin_operations.mcp_server`) behind the `[mcp]` extra | ADR-0012 does not require MCP; optional integration only | **Optional adapter implemented; not a core dependency** |
| Yasin-AI dependency | No direct package dependency | Yasin-AI remains canonical AI platform | **Aligned** |
| YasinPress dependency | No direct package dependency | YasinPress owns publishing/news domain | **Aligned** |
| YasinRelay dependency | No direct package dependency | YasinRelay owns relay/feed transport | **Aligned** |
| YasinHub relationship | No mandatory dependency | Hub remains management/status owner | **No mandatory dependency; boundary needs explicit operational coordination** |
| YasinCLI relationship | Local CLI exists | YasinCLI is ecosystem control surface | **Local CLI is component-scoped, not a replacement** |
| Registry status | Repository has v0.1.0 implementation/release evidence | Registry says `newly-registered`, `architecture_status: provisional` | **Different readiness dimensions; must remain explicitly separated** |

## 4. Current public contracts

### Core

`Operation` is an immutable operation description. `OperationTarget`, `OperationMetadata`, and `OperationState` keep execution data separate from lifecycle state. The Core does not directly execute arbitrary shell commands.

### Executor

The execution path is:

`Operation -> ToolRegistry -> capability/safety validation -> SafetyPolicy -> registered Tool -> OperationResult -> AuditRecorder`

The Executor does not make external repositories mandatory.

### Safety

`SafetyClass.READ_ONLY` and `SafetyClass.MUTATING` are explicit. Mutating operations require confirmation by default, with protected-target handling and dry-run support in `SafetyPolicy`.

### Adapters

Adapters translate external interfaces into Core contracts. They must not become alternate execution paths that bypass `Executor` or `SafetyPolicy`.

### Gateway

The JSONL gateway is local and transport-neutral. It is not a network listener and does not import/control Hermes. It translates validated requests into the Hermes-facing typed contract and then delegates to the existing Executor boundary.

### CLI

The installed `yasin-operations` entrypoint and module CLI route to the same implementation. `gateway` is an optional subcommand and therefore does not turn the gateway into a mandatory runtime component.

## 5. Trust and dependency boundary

The authoritative dependency rule is:

```text
External client / optional adapter
              |
              v
      typed Operations contract
              |
              v
          Executor
          /      \
 SafetyPolicy   ToolRegistry
                 |
                 v
          registered tools
                 |
                 v
       local/runtime backends
```

No external project is allowed to become a hidden execution dependency merely because an adapter exists.

The current repository evidence supports these rules:

1. Yasin-Operations can import and operate without Hermes.
2. Yasin-Operations can import and operate without Yasin-AI.
3. Yasin-Operations can import and operate without YasinPress or YasinRelay.
4. Ecosystem adapters are integration boundaries, not ownership transfers.
5. The JSONL gateway does not create a network service or mandatory external dependency.
6. Future Hermes integration must remain adapter-based.
7. Future Yasin-AI integration must use Yasin-AI's public versioned contracts rather than importing internal implementation details.

## 6. Claims requiring careful wording

### 6.1 "Release-ready"

The repository may claim **repository-local v0.1.0 release readiness** when its release checks pass. It must not imply that Yasin-Operations is already an ecosystem-wide certified integration.

YASIN-DOCS currently classifies the project as provisional. That is appropriate until the architecture registry is explicitly promoted using source-level evidence.

### 6.2 Hermes integration

The existence of `adapters/hermes/` means an adapter boundary exists. It does **not** prove that Hermes is configured, connected, or operationally integrated on a deployment.

### 6.3 MCP

An optional stdio MCP bridge (`yasin_operations.mcp_server`) is available behind the `[mcp]` optional dependency. Hermes has its own MCP facility; that does not make Yasin-Operations an MCP server by default, and the JSONL gateway is not described as MCP. MCP remains optional, never a core runtime dependency, and must not be inferred solely from JSONL tests.

### 6.4 Ecosystem adapters

The Yasin-AI/YasinPress/YasinRelay adapters are evidence of optional interface seams. They are not evidence that Yasin-Operations owns those domains or that cross-repository runtime dependencies are required.

## 7. Findings and follow-up mapping

| Finding | Severity | Follow-up |
|---|---|---|
| Optional MCP bridge exists behind the `[mcp]` extra; core remains independent | Informational; keep MCP optional | #120 / #154 |
| JSONL gateway is local-only and not an MCP transport | Informational | #120 |
| Mutation authorization must remain centralized in Executor/SafetyPolicy | High architectural invariant | #123 |
| Request replay/idempotency semantics need explicit production contract | High | #124 |
| Audit sink failure semantics need explicit integrity decision | High | #125 |
| Runtime lifecycle behavior requires live-host evidence | Medium/High | #126 |
| Retry/timeout/resource semantics require production contract | High | #127 |
| Optional ecosystem adapters need failure-isolation evidence | Medium | #128 |
| Gateway/adversarial testing must prove boundary behavior | High | #129 |
| Hosted CI and live Termux evidence must remain distinct | Medium | #130 |
| Release documentation must distinguish local readiness from ecosystem certification | Medium | #131 |
| Final independent audit must reconcile all changes before release closure | High | #132 |

## 8. Required YASIN-DOCS follow-up

The following facts should remain canonical in YASIN-DOCS:

- Yasin-Operations is an independent optional component.
- It does not own Yasin-AI, YasinPress, or YasinRelay domains.
- Hermes integration is optional and adapter-based.
- The JSONL gateway is local/optional and is not equivalent to an MCP server.
- Repository-local release readiness must not be confused with ecosystem-wide architecture verification.
- Registry promotion from `provisional` requires source-level evidence.

No cross-repository dependency should be added to the registry until the corresponding implementation is verified in source.

## 9. Audit conclusion

**P0.1 reconciliation conclusion: PASS with documented status distinction.**

The implementation boundary is consistent with ADR-0012. The principal discrepancy is terminology around release readiness versus ecosystem architecture status. That discrepancy is now explicitly recorded instead of silently treating the two claims as equivalent.

The next work should therefore focus on the concrete integration and production-contract gaps identified above rather than redesigning the standalone Core.
