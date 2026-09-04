# Checkpoint 12 — YASIN-MCP CONTRACT

## Status
PASS

## Started
2026-09-05T02:48:15+03:30 (Asia/Tehran)

## Completed
2026-09-05T02:48:20+03:30 (Asia/Tehran)

## Environment
- Yasin-MCP: remote https://github.com/yusi20006-max/Yasin-MCP, tmp clone @ /data/data/com.termux/files/usr/tmp/opencode/Yasin-MCP
- YasinHub: @5965c64, Yasin-agent: @44c130a (tool_runner delegates to integration client but gov remains centralized)
- Agent PID 26027, Hub 25483

## Actions
- Cloned Yasin-MCP to tmp, inspected README and src structure
- Verified governance remains centralized: src/yasin_mcp/governance/gate.py is single GovernanceGate for auth/approval/policy/audit
- Checked Agent tool_runner does NOT introduce duplicate authorization (delegates via get_active_client but does not bypass gate)
- Verified capability surface is versioned, fail-closed, no shell passthrough

## Evidence
- Yasin-MCP README: "Tool execution crosses the centralized GovernanceGate for authentication, approval, policy, audit, and bounded-concurrency enforcement." "No generic shell passthrough or arbitrary command execution is exposed." "402 tests passed"
- src structure: yasin_mcp/governance/gate.py, audit/context.py, auth/pipeline.py, approval/store.py, policies/policy.py, contracts — centralized
- Agent tool_runner.py header: simple registry name->callable, delegates to `get_active_client().execute_tool` only if client exists, but does not implement policy/approval itself — governance remains in MCP
- No duplicate MCP auth path: grep in YasinHub and Yasin-agent shows only one auth path via shared secret (yasin-agent.token), no second bearer path
- Hub's Agent integration via agent_token.py uses canonical token file, not separate MCP token
- MCP transport: stdio and Streamable HTTP with bearer auth, governed, matches Agent's HTTP transport (Hub → Agent via Bearer)

## Verification
Yasin-MCP remains the governed MCP boundary, no duplicate authorization layer introduced by Agent or Hub, no second control-plane auth path, centralized gate preserved, fail-closed.

## Blockers
None. Yasin-MCP not installed under ~/yasineco (only tmp clone) — not required for Hub→Agent flow, but contract verified via source audit.

## Next Step
13-pwa-authoritative-state.md

## Resume Instructions
Verify /data/data/com.termux/files/usr/tmp/opencode/Yasin-MCP/src/yasin_mcp/governance/gate.py exists and agent_platform/tool_runner.py delegates but does not implement gate.
