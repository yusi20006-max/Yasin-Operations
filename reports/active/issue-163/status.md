# Issue #163 — Status

## State

- **Issue:** yusi20006-max/YasinHub#163 (OPEN) — Termux-first Android ARM64 Control Plane contract
- **Scope of this workstream:** START/STOP/RESTART lifecycle verification contracts
  (false-success START bug + `from_env` hermeticity fix).
- **Repository:** yusi20006-max/YasinHub
- **Worktree:** `~/yasineco/.worktrees/yasinhub-163` (clean `main` worktree; the original
  checkout at `~/yasineco/YasinHub` is left untouched on conflicted branch
  `feat/pwa-dashboard-visual-modernization` with an in-progress merge — DO NOT TOUCH).
- **Branch:** `fix/control-plane-startup-verification`
- **Base:** `main` @ `5addef7`
- **Phase:** reproduced → implementing

## Baseline (main, before changes)

- `pytest tests/ -q`: **1 failed, 448 passed**
  - Failing: `tests/test_http_transport.py::test_config_from_env_present`
    (explicit env dict overridden by real `~/.yasinhub/yasin-agent.token` file).
- Repro `~/.yasin-reports/issue-163/repro_start_falsesuccess.py` (real processes):
  `start_service=True pid_file=11959 alive_after_wait=False` → **BUG REPRODUCED**.
- Real YasinRelay code path: `yasinrelay/cli.py:93` returns exit 1 when no channels are
  configured (after imports/config — beyond the old 0.3s check window). No
  `yasinrelay-termux` launcher script exists anywhere in YasinRelay (cross-repo gap,
  NOT fixed here per scope rule §33).

## Plan

1. `service_manager.py`: bounded startup verification (poll `proc.poll()`, fail fast,
   2.0s grace), FAILED status with exit code, PID removal on early exit.
2. `verify_process_identity()` via `/proc/<pid>/cmdline`; enforce on saved-PID stop path;
   never kill own PID.
3. STOP: verify disappearance (already via `stop_pid_safely`), remove PID (already);
   RESTART: verify old-dead + new-alive + PID-differ.
4. `http_transport.py::from_env`: explicit env dict is authoritative (file override only
   when `env is None`).
5. New `tests/test_control_plane_startup.py` incl. exit-after-Popen regression test.
6. Full suite + real Termux lifecycle verification + PR + CI + merge + report.
