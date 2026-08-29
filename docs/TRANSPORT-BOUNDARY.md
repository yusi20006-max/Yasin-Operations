# Yasin-Operations External-Agent Transport Boundary

**Issue:** #120 — P0.2 Canonical External-Agent Transport Boundary: JSONL vs MCP  
**Status:** Accepted (updated for optional MCP bridge)  
**Repository:** `yusi20006-max/Yasin-Operations`  
**Cross-project source of truth:** `yusi20006-max/YASIN-DOCS`

## 1. Decision

Yasin-Operations exposes **local JSONL over stdin/stdout as its canonical component-scoped external transport for v0.1.x**.

An optional **stdio MCP bridge** (`yasin_operations.mcp_server`) is also provided for Hermes and other MCP clients. MCP is an optional extra (`[project.optional-dependencies] mcp`) and is never a core runtime dependency.

JSONL remains the primary local transport; MCP is an additional optional surface that maps tool calls onto the same typed Operations + Executor + SafetyPolicy path.

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

## 3. Optional MCP bridge

YASIN-DOCS keeps Hermes integration optional and prohibits mandatory
cross-repository dependencies. The optional MCP bridge satisfies the
Hermes monitoring use-case without making MCP or Hermes a core dependency.

The MCP bridge:

- uses stdio transport only (no network listener by default);
- maps tools to the existing typed Operations contract;
- routes all execution through Executor + SafetyPolicy;
- remains fully optional at install and runtime time.

## 4. Responsibility matrix

| Concern | JSONL gateway | Optional MCP bridge |
|---|---|---|
| Current Yasin-Operations transport | **Canonical** | Optional extra |
| Local stdin/stdout operation | **Yes** | **Yes** (stdio) |
| Network listener | **No** | **No** by default |
| Core dependency | None | None |
| Hermes dependency | None | None; client only |
| Executor/SafetyPolicy path | **Required** | **Required** |
| Schema ownership | Yasin-Operations gateway contract | MCP tools map to Operations |
| Versioning | `schema_version` | MCP protocol + tool contract |
| Security boundary | Existing validation + Executor policy | Same boundary |

## 5. Non-negotiable invariants

1. Transport code must never become an alternate execution path around `Executor`.
2. `SafetyPolicy` remains authoritative for authorization of mutating operations.
3. No transport may make Hermes, Yasin-AI, YasinPress or YasinRelay a required runtime dependency.
4. No network listener is enabled by default for the local operations gateway.
5. The JSONL protocol is not described as MCP.
6. MCP support is an optional adapter/transport layer and preserves Core independence.
7. Cross-repository integration status is promoted only after source-level evidence exists.

## 6. Compatibility policy

The JSONL gateway currently uses schema version `1`.

A request with an unsupported schema version is rejected without execution. Request IDs are validated and recent duplicates are rejected by default. Size and identifier limits are part of the transport boundary and must remain covered by tests.

Backward-incompatible changes to the JSONL envelope require a new schema version. Compatible additions should preserve existing required fields and error semantics.

MCP maps tool calls to the same typed Operations contract and the same Executor/SafetyPolicy execution path.

## 7. Hermes integration statement

The Hermes adapter is a **transport-neutral adapter seam**, not proof of a live Hermes deployment or connection.

Hermes may consume the local JSONL transport or the optional MCP bridge. Either way, the integration must remain optional and must terminate at the typed Operations contract before execution.

## 8. Acceptance evidence

See CI, production acceptance harness, and live Termux evidence recorded under the P4 Monitoring Completion Program (#152–#157).
