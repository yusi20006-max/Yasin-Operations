# Issue #163 — Investigation

## Files inspected (YasinHub @ main 5addef7)

- `yasinhub/service_manager.py` — `start_service` saves PID, sleeps **0.3s**, checks
  `proc.poll()` once. Any child dying after 0.3s (e.g. YasinRelay failing config
  validation after ~1s of imports) is reported successful with a stale PID file.
  `stop_service` kills saved PID (verified via `stop_pid_safely` TERM→KILL+verify) but
  falls back to killing **every** `pgrep -f` match (blanket kill, including potentially
  its own PID). `restart_service` = stop + sleep 0.2 + start with no PID-difference or
  liveness assertions.
- `yasinhub/process_checker.py` — `pgrep -f` discovery only; Termux-compatible. No identity.
- `yasinhub/pid_store.py` — `is_pid_alive` via `waitpid(WNOHANG)` + `kill(pid,0)`; sound.
- `yasinhub/status_store.py` / `report.py` — `calculate_health_state` freshness window
  (SUCCESS ≤ 24h else STALE) is the authoritative semantic; no test contradicts it on main.
- `yasinhub/registry.py` — relay entry still `python3 -m yasinrelay.cli run` /
  pattern `yasinrelay.cli`. No `yasinrelay-termux` launcher exists in YasinRelay repo
  (checked: no such file, no `[project.scripts]` entry). Registry command change would
  require a YasinRelay-side launcher → separate cross-repo issue, out of scope.
- `yasinhub/api/server.py::handle_control` — returns `{"success": start_service(...)}`
  directly, so the manager-level false success propagates to the HTTP API verbatim.
- `yasinhub/adapters/http_transport.py::from_env` — even with an explicitly injected env
  dict, resolves the real `~/.yasinhub/yasin-agent.token` file and overrides the dict's
  token. Breaks hermeticity; production callers pass `env=None` (real process env).

## Mock-coupling constraints (must not break)

- `test_start_service_does_not_use_shell` patches `service_manager.time` wholesale and uses
  a MagicMock Popen with fake `pid=1234` + `poll()=None`. Therefore the verification loop
  must use attempt-count + `time.sleep` only (no `time.time()` arithmetic) and must NOT call
  `is_pid_alive()` on the fresh child in the success path.
- `test_stop_service_by_pid` asserts `os.kill(4567, SIGTERM)` via the pattern fallback —
  pattern fallback must keep working (self-PID exclusion is compatible: 4567 ≠ getpid).
- `test_start_service_success` (MagicMock `poll()=None`) must still return True.
