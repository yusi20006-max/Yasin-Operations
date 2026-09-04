# Implementation

## hub_contract.py
- CONTRACT_VERSION = "1.0"
- HEADER_CONTRACT = "X-Yasin-Contract-Version"
- EXECUTION_STATES / TERMINAL_STATES
- Paths: health, ready, executions, events, fleets
- Explicit ownership boundary documentation (Hub vs Agent vs MCP vs AI vs Core)
- No PID/service manager

## app.py (single surface)
- `_runtime_ready()` probes list_executions / list / _executions
- health: ready from probe, contract_version, HEADER_CONTRACT
- ready: status ready|not_ready, HTTP 503 when not ready
- All prior execution/fleet/event endpoints unchanged
- run_server + main preserved

## hub_client.py
- Authorization Bearer + HEADER_REQUEST_ID + HEADER_CONTRACT
- Bounded retries on 5xx/transport

## Tests
- contract version/states
- no duplicate control plane tokens in server package
- health/ready contract headers
- auth fail-closed
- truthful execution lifecycle status
- durable store restart recovery
- AI capability boundary (no OPENAI_API_KEY / sk-)
- HubAgentClient contract header
