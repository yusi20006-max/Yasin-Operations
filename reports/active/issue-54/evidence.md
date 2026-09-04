# Evidence

## Local tests (2026-09-04)
```
tests/test_phase5_hub_agent_integration.py — 8 passed
full suite tests/ — 248 passed, 1 warning (Starlette TestClient deprecation)
```

## Files on branch tip `9529018`
- `agent_platform/hub_contract.py` (contract v1.0)
- `agent_platform/server/app.py` (21165 bytes, 526 lines, real newlines, syntax OK)
- `agent_platform/server/hub_client.py` (contract header)
- `tests/test_phase5_hub_agent_integration.py`

## Endpoints present in app.py
GET /v1/health, /v1/ready, /v1/metrics, /v1/executions, /v1/executions/{id},
/v1/executions/{id}/events, /v1/events, /v1/fleets, /v1/fleets/{task_id}
POST /v1/executions, pause/resume/cancel, /v1/fleets/{task_id}/cancel

## Remote verification
- `app.py` len=21165, newlines=526, no literal `\\n`, no `app_canonical`
- syntax compile OK after pull
