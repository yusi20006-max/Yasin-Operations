# Issue #163 — Current Status (handoff)

## CURRENT ISSUE

YasinHub START reports success for services that exit shortly after Popen
(YasinRelay with no channels: HTTP `success:true` + PID file, then NO RELAY PROCESS).

## REPOSITORY

yusi20006-max/YasinHub (worktree `~/yasineco/.worktrees/yasinhub-163`; original checkout
`~/yasineco/YasinHub` left untouched on conflicted dashboard branch — DO NOT TOUCH).

## BRANCH

`fix/control-plane-startup-verification` (base: main @ 5addef7).

## CURRENT PHASE

Reproduced with evidence → implementing fix.

## OBJECTIVE

Bounded deterministic START verification (fail fast on early exit, FAILED status + PID
cleanup), identity-aware STOP (never kill self / foreign PID), verified RESTART
(old-dead + new-alive + PID-differ), hermetic `from_env`.

## LAST SUCCESSFUL STEP

Bug reproduced: `start_service=True pid_file=11959 alive_after_wait=False`.

## CURRENT STATE

Reports written (`status.md`, `investigation.md`, `evidence.md`, this file).
Implementation not yet started.

## EVIDENCE

See `evidence.md` (E1–E4).

## FAILURES

- Baseline suite: 1 failed (`test_config_from_env_present`), 448 passed.
- Repro script confirms false-success START.

## ROOT CAUSE

Single 0.3s `proc.poll()` check in `start_service`; no startup verification window, no
process-identity check, blanket pattern kill in stop, unverified restart.

## CHANGES MADE

None yet (branch created, clean).

## TEST STATUS

Baseline: 1 failed / 448 passed. Regression test to be added:
`tests/test_control_plane_startup.py`.

## LINT STATUS

NOT CONFIGURED (no ruff/mypy/flake8 in repo — to be confirmed during verification).

## TYPE CHECK STATUS

Pending (likely NOT CONFIGURED).

## SECURITY STATUS

Pending (grep scan planned; no `shell=True` — `shlex.split` + `shell=False` already).

## CI STATUS

No PR yet.

## PR STATUS

No PR yet.

## BLOCKER

None. (Do NOT run live YasinRelay publishing again — a probe run started real
fetch/publish activity and was killed via timeout; use synthetic repro only.)

## NEXT ACTION

Implement `service_manager.py` changes + `from_env` fix + regression tests, then full
suite, Termux lifecycle verification, PR/CI/merge, final report.

## LAST UPDATED

2026-09-04 (UTC) — by autonomous agent.
