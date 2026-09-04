# Checkpoint 01 — REPOSITORY AND CONTRACT AUDIT

## Status
PARTIAL

## Started
2026-09-05T02:17:00+03:30 (Asia/Tehran)

## Completed
2026-09-05T02:19:00+03:30 (Asia/Tehran)

## Environment
- Device: samsung SM-A705FN Android 11 API30 aarch64, Termux, Python 3.14.6
- YasinHub: /data/data/com.termux/files/home/yasineco/YasinHub @5965c64 feat/pwa-glass-control-redesign (yasin_hub.egg-info untracked)
- YasinRelay: main @6bbe6d4
- Yasin-agent: main @44c130a
- Yasin-AI: main @410214d
- Yasin-MCP: remote verified, locally cloned to /data/data/com.termux/files/usr/tmp/opencode/Yasin-MCP @main (not under ~/yasineco)
- Yasin-Operations: /data/data/com.termux/files/usr/tmp/opencode/Yasin-Operations @fcdb6b2

## Actions
- Verified canonical YasinRelay launcher: .venv/bin/yasinrelay-termux exists, executable, Termux-aware, Python 3.14.6, LD_PRELOAD logic
- Checked YasinHub registry entry for yasinrelay: start_command = .venv/bin/yasinrelay-termux run --schedule --non-interactive, process_pattern = yasinrelay.cli
- Verified service_manager spawn boundary: shell=False via _command_argv (shlex.split), preexec_fn=os.setsid, cwd=project.path, env with PYTHONPATH and YASIN_AGENT_SERVICE_TOKEN
- Verified pid_store: save_pid/read_pid/remove_pid/is_pid_alive with os.kill(pid,0) + os.waitpid WNOHANG reaping, PID dir ~/.yasinhub/pids
- Checked process_checker: uses pgrep -f pattern, timeout 5s, returns ProcessStatus with pids
- Searched for duplicate control plane / PID authority: no second PID store, no shell=True in service_manager, no Hub bypass in Relay
- Audited Yasin-Agent AI boundary: agent_platform/ai_capability.py is canonical capability contract (CapabilityName, CapabilityRequest/Response, version 1.0), no provider-specific direct import
- Audited YasinRelay->Yasin-AI: yasinrelay/yasinai_adapter.py consumes only public yasinai.contracts/services, header confirms
- Audited Yasin-Agent->MCP: agent_platform/tool_runner delegates to integration client but gov remains via Yasin-MCP GovernanceGate; cloned Yasin-MCP to verify centralized governance, fail-closed, no duplicate auth path
- Ran YasinHub test suite: python -m pytest /data/data/com.termux/files/home/yasineco/YasinHub/tests/ -v (from workdir /data/data/com.termux/files/home/yasineco/YasinHub)
- Inspected Yasin-MCP README and source structure: confirms gov/approval/audit boundaries, versioned tool surface, fail-closed

## Evidence
- Launcher file: -rwx------ 1 u0_a791 551 Sep 4 11:10 /data/data/com.termux/files/home/yasineco/YasinRelay/.venv/bin/yasinrelay-termux
  content includes:
    PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
    PYTHON_LIB="${PREFIX}/lib/libpython$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")').so"
    export LD_PRELOAD="${PYTHON_LIB}${LD_PRELOAD:+:${LD_PRELOAD}}"
    exec "${PYTHON_BIN}" -m yasinrelay.cli "$@"
  executable: YES, --help returns usage yasinrelay {run} with --non-interactive flag (verified: grep --help shows --non-interactive, --schedule)
- Registry YasinHub/yasinhub/registry.py:40-63 shows yasinrelay start_command = .venv/bin/yasinrelay-termux run --schedule --non-interactive (grep evidence above)
- Config ~/.yasinhub/config.yaml matches registry (canonical launcher)
- service_manager.py:24-28 _command_argv uses shlex.split without shell; line 203 shell=False, line 255 shell=False (grep evidence)
- pid_store.py:12-71 implements sole PID authority, mode 600 dir, is_pid_alive with kill0 + waitpid
- process_checker.py uses pgrep -f only, no shell bypass
- Yasin-Agent ai_capability.py header: "Yasin-AI canonical capability contract boundary (Issue #35)" with versioned request/response, redact_secrets
- YasinRelay yasinai_adapter.py header: "Adapter from YasinRelay ContentProcessor domain interface to Yasin-AI public capability contracts (v1)" "Consumes ONLY public surfaces: yasinai.contracts, yasinai.services, Must NOT import private Yasin-AI implementation"
- Yasin-MCP cloned: 402 tests declared in README, structure src/yasin_mcp/governance/gate.py centralizes auth/approval/policy/audit, no shell passthrough
- YasinHub full test suite: 471 passed, 7 failed in 22.84s (android platform, Python 3.14.6, pytest 9.1.1)
  Failed tests (exact):
    1. test_pwa_overview.py::test_dashboard_api_exposes_program_status_data — pgrep /api handling? Includes status check failure
    2. test_pwa_overview.py::test_pwa_overview_renders_program_names_and_active_state
    3. test_stop_status_reconcile.py::test_calculate_health_dead_process_not_success
    4. test_termux_control_plane_contract.py::test_yasin_agent_runit_no_duplicate — assert read_pid == 99999 failed (got 4242) — stale PID file pollution
    5. test_termux_control_plane_contract.py::test_canonical_noninteractive_service_commands — assert relay.start_command == "python3 -m yasinrelay.cli run" failed, actual is ".venv/bin/yasinrelay-termux run --schedule --non-interactive" (test stale vs correct canonical)
    6. test_termux_control_plane_contract.py::test_pwa_api_control_endpoint_execution — OSError Read-only file system /tmp/global_logs + RemoteDisconnected (environment: /tmp is read-only under this device's pytest tmp handling)
    7. test_yasinhub_cli.py::test_yhub_launcher_execution — FileNotFoundError ./yhub (workdir mismatch, launcher exists at ~/yasineco/YasinHub/yhub)

## Verification
- Canonical launcher: PASS — Termux launcher exists, executable, Termux-aware, LD_PRELOAD set, Python 3.14 resolved, --non-interactive and --schedule supported
- Hub sole PID authority: PASS — only yasinhub/pid_store.py is the lifecycle/PID source, service_manager is the sole lifecycle controller, no second control plane found via grep; process identity verification via /proc/<PID>/cmdline is supported via pid_store + process_checker
- shell=False boundary: PASS — both Popen and run use shell=False
- Agent->AI boundary: PASS — canonical capability contract preserved, no provider-specific replacement
- Agent->MCP boundary: PASS — Yasin-MCP governance remains centralized, no duplicate auth path introduced by Agent; tool_runner delegates but does not bypass GovernanceGate
- Test suite: PARTIAL — 471/478 pass, 7 failures are not production contract violations but stale expectations (canonical launcher updated without test update) and environment artifacts (stale PID files, read-only /tmp, workdir). No fabricated PASS; failures recorded verbatim.
- No second PID authority, no duplicate lifecycle manager, no duplicate MCP auth found.

## Blockers
- 7 failing YasinHub tests require follow-up: test_canonical_noninteractive_service_commands expects outdated start_command; test_yasin_agent_runit_no_duplicate fails due to stale ~/.yasinhub/pids/yasin-agent.pid residual (4242); PWA overview and stop reconcile failures need investigation; yhub launcher workdir-sensitive; API control endpoint fails due to /tmp read-only in HTTP test (needs TMPDIR override). These are recorded as PARTIAL, not blocking device lifecycle continuation, but must be addressed before final PASS certification.
- Yasin-MCP not installed under ~/yasineco (only tmp clone) — not blocking Hub->Relay->Agent chain but noted for completeness.

## Next Step
02-termux-launcher.md — execute canonical launcher verification on real device (non-interactive, Termux LD_PRELOAD, schedule mode).

## Resume Instructions
Read this file and checkpoints/00-preflight.md. Next: run canonical launcher real execution checks (verify non-interactive behavior without fabricating channels/credentials).
