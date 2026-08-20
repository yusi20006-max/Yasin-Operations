# Yasin-Operations External-Agent Transport Boundary

**Issue:** #120 — P0.2 Canonical External-Agent Transport Boundary: JSONL vs MCP  
**Status:** Accepted  
**Repository:** `yusi20006-max/Yasin-Operations`  
**Cross-project source of truth:** `yusi20006-max/YASIN-DOCS`

## 1. Decision

Yasin-Operations will expose **local JSONL over stdin/stdout as its canonical component-scoped external transport for v0.1.x**.

A real MCP server is **not part of the current Yasin-Operations integration surface** and is not added as a dependency or runtime requirement by this issue.

MCP remains a future optional integration option. It may be introduced only through a separate architecture/integration decision when a concrete ecosystem consumer and contract require it.

## 2. Why JSONL is canonical now

The current repository already has a typed, bounded JSONL gateway with:

- explicit schema versioning;
- request identifiers and replay protection for the configured recent-ID window;
- request/parameter size limits;
- identifier validation;
- structured error responses;
- delegation into the existing `Executor` and `SafetyPolicy` boundary;
- no network listener by default;
- no mandatory Hermes dependency.

This provides the smallest transport surface consistent with the current repository responsibility: local operations, diagnostics and lifecycle control.

## 3. Why MCP is deferred

YASIN-DOCS ADR-0012 defines Hermes integration as **future and optional**, requires Yasin-Operations to remain independently deployable, and explicitly prohibits mandatory cross-repository dependencies. It does not require MCP.

The current Yasin-Operations repository contains no MCP server implementation and no MCP package dependency. Hermes has its own MCP functionality, but that fact does not make Yasin-Operations an MCP server.

Adding MCP now would therefore create an integration surface without a current source-level consumer requirement. That would be architecture-first coupling rather than evidence-backed integration.

## 4. Responsibility matrix

| Concern | JSONL gateway | MCP (future) |
|---|---|---|
| Current Yasin-Operations transport | **Canonical** | Not in current scope |
| Local stdin/stdout operation | **Yes** | Possible via stdio adapter |
| Network listener | **No** | Not allowed by default |
| Core dependency | None | None |
| Hermes dependency | None | None; adapter only |
| Executor/SafetyPolicy path | **Required** | **Required** |
| Schema ownership | Yasin-Operations gateway contract | Future MCP adapter contract |
| Versioning | `schema_version` | MCP protocol + adapter compatibility policy |
| Security boundary | Existing validation + Executor policy | Must reuse existing boundary |

## 5. Non-negotiable invariants

1. Transport code must never become an alternate execution path around `Executor`.
2. `SafetyPolicy` remains authoritative for authorization of mutating operations.
3. No transport may make Hermes, Yasin-AI, YasinPress or YasinRelay a required runtime dependency.
4. No network listener is enabled by default for the local operations gateway.
5. The JSONL protocol is not described as MCP.
6. Future MCP support must be an optional adapter/transport layer and must preserve Core independence.
7. Cross-repository integration status is promoted only after source-level evidence exists.

## 6. Compatibility policy

The JSONL gateway currently uses schema version `1`.

A request with an unsupported schema version is rejected without execution. Request IDs are validated and recent duplicates are rejected by default. Size and identifier limits are part of the transport boundary and must remain covered by tests.

Backward-incompatible changes to the JSONL envelope require a new schema version. Compatible additions should preserve existing required fields and error semantics.

MCP, if introduced later, will not redefine the Core operation model. It will map MCP tool calls to the same typed Operations contract and the same Executor/SafetyPolicy execution path.

## 7. Hermes integration statement

The Hermes adapter is a **transport-neutral adapter seam**, not proof of a live Hermes deployment or connection.

A future Hermes integration may consume the local JSONL transport or a future MCP adapter. Either way, the integration must remain optional and must terminate at the typed Operations contract before execution.

## 8. Acceptance evidence

This decision is considered complete when:

- this document records the canonical boundary;
- repository documentation no longer implies that JSONL is MCP;
- contract tests protect JSONL schema/error/size/replay behavior;
- tests prove the gateway delegates through the existing adapter/executor boundary;
- the package has no mandatory MCP dependency;
- CI validates the new tests.

## 9. Source of truth

The repository is authoritative for the current implementation. YASIN-DOCS remains authoritative for ecosystem architecture and governance. ADR-0012 is the governing boundary decision for the optional nature of Hermes and cross-repository integration.
