# Evidence Register

| Evidence | Source | State |
|---|---|---|
| Canonical Relay launcher contract | YasinHub `tests/test_yasinrelay_control_plane_e2e.py` | Present in main |
| Real START/STOP/RESTART lifecycle regression | Same test file | Present; execution pending current PR CI |
| Early-exit startup failure regression | Same test file + `test_control_plane_startup.py` | Present in main |
| PWA authoritative PID/status contract | Phase 4 merged code | Present in main |
| Agent Phase 6 hardening | Yasin-Agent PR #58 / merge `f348134...` | Merged |
| Physical Android/Termux | No attached device evidence in this execution | NOT EXECUTED |
| Credentialed publish | No operator credentials supplied | BLOCKED — OPERATOR CONFIGURATION REQUIRED |

No fabricated PID, device, credential, publish, or runtime result is recorded.
