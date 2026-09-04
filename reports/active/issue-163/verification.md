# Issue #163 — Verification

## Regression tests (new)

`python3 -m pytest tests/test_control_plane_startup.py -q` → **7 passed** (real processes).

## Targeted suites

`test_control_plane_startup + test_service_management_ops + test_yasinhub +
test_service_manager_security + test_supervised_status_reconcile + test_http_transport`
→ **48 passed** (incl. previously failing `test_config_from_env_present`).

## Full suite

`python3 -m pytest tests/ -q` → **456 passed, 0 failed** (~37s).
Baseline was 1 failed / 448 passed. No test modified or weakened.

## Lint / type-check / static analysis

- No ruff/mypy/flake8/bandit/pylint configuration in repo; CI (`.github/workflows/ci.yml`)
  runs `pytest -q` only on ubuntu × Python 3.9–3.13 → recorded as **NOT CONFIGURED**
  (not claimed as PASS). `git diff --check` → clean. `compileall` import check → OK.
- Security grep over changed files (`shell=True|eval(|exec(|pickle|yaml.load`) → clean.
  `shlex.split` + `shell=False` preserved; no new subprocess surface.

## Repro re-run (post-fix)

Same synthetic relay-like service (`sleep 1.2; exit 1`) via `start_service`:
→ returns **False**, PID file removed, FAILED status with exit code. False-success gone.

## Real Termux verification (live Hub HTTP API, port 18099, isolated config)

Script: `~/.yasin-reports/issue-163/live_verify.py` → **13/13 passed**:
health-live OK · start-success (real PID 19075, alive) · status/services reflect live ·
stop-success · stop-pid-gone · stop-pidfile-removed · start-again-new-PID (19092) ·
restart-success (PID 19130) · restart-old-dead · restart-new-alive-PID-differs ·
final-stop. No leftover PID/status/log files. Clean session (isolated config dir,
no TTY dependence, no stale files).

Note: one live probe of the real YasinRelay was started during investigation and
immediately killed via timeout after it began real fetch/publish activity; synthetic
probes used thereafter. No fake SOURCE_CHANNELS injected anywhere.

## Remaining for completion

Commit → push → PR → CI → merge → branch cleanup → final report → index update.
