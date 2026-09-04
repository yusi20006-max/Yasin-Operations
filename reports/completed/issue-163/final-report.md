# Final Report — Issue #163 (lifecycle verification workstream)

## ISSUE

yusi20006-max/YasinHub#163 — compat: enforce Termux-first Android ARM64 Control Plane contract
(workstream: START/STOP/RESTART lifecycle verification; false-success START bug).

## STATUS

**COMPLETED** (engineering + verification + merge + cleanup done; Issue #163 itself remains
OPEN for its broader checklist — this workstream's defects are resolved and merged).

## REPOSITORY

yusi20006-max/YasinHub

## BRANCH

`fix/control-plane-startup-verification` (created from `main @ 5addef7`, rebased onto
`main @ 5965c64` mid-work; merged; local + remote branches deleted — verified).

## COMMIT

`81589b4` — `fix(#163): enforce control-plane START/STOP/RESTART verification contracts`

## PR

yusi20006-max/YasinHub#167 — **MERGED** 2026-09-04T14:38:23Z (merge commit `2b30970`).

## CI

**PASS** — all 6 matrix jobs (3.9, 3.10, 3.11, 3.12, 3.13, 3.14-dev), run
`33884611788`. One intermediate CI failure occurred (my new identity unit test assumed a
`python3 -m pytest` argv[0]; CI uses the `pytest` console script) — fixed by deriving
argv[0] from `/proc/self/cmdline`, re-pushed, all green. No test was weakened to get green.

## MERGED

YES (`2b30970`).

## BRANCH DELETED

YES (local `git branch -d` + remote `--delete` — both verified).

## TESTS

- Baseline (pre-rebase main): 1 failed / 448 passed.
- Rebased main (parallel work landed): 3 failed / 482 passed — all 3 proven pre-existing
  on pristine `origin/main` worktree (not regressions): time-bombed STALE date assert,
  device-PID-dependent runit test, order-dependent singleton pollution.
- Final (merged main): **485 passed, 0 failed** ×2 consecutive full runs (~60s each).
- New `tests/test_control_plane_startup.py`: 7 tests, real processes only — including the
  exact bug shape (child exits 1.2s after Popen → `False` + PID removed + FAILED status
  with exit code).
- Evidence-based test corrections (no weakening): obsolete relay-command assert →
  canonical Termux launcher (per newer commit 5965c64 + `test_termux_service_registry`);
  stale-success assert SUCCESS→STALE (implementation's 24h window is authoritative and
  matches the test's own "not success" intent); PID-dir isolation for the runit test;
  singleton restore for the config test.

## Evidence

- E1 repro (pre-fix): `start_service=True pid_file=11959 alive_after_wait=False` → BUG.
- E2 YasinRelay code path: `yasinrelay/cli.py:93` returns 1 after imports/config (>0.3s
  window); install script documents exit-1-without-channels as the honest contract.
- E3 post-fix repro: same shape → `False` + PID removed + FAILED+exit-code.
- E4 API propagation: `handle_control` returns `start_service()` verbatim → fixed at source.
- E5 live Termux HTTP verification (isolated config, port 18099): **13/13** — health,
  START real PID alive, status/services live, STOP PID-gone + file-removed, START new PID,
  RESTART old-dead/new-alive/PID-differs, final STOP; zero leftover state.

## Root Cause

Single 0.3s `proc.poll()` check; no verification window, no ownership check, unverified
restart, non-hermetic `from_env`, plus three latent test-isolation defects exposed by
rebasing onto current main.

## Implementation

`yasinhub/service_manager.py`: `_wait_for_stable_start` (2s grace, fail-fast, mock-safe
attempt loop), `verify_process_identity` (/proc cmdline: pattern OR spawn argv[0]),
identity-aware STOP (never self-kill; foreign PIDs refused), verified RESTART, self-PID
guard in `stop_pid_safely`; pattern matching kept for reconciliation/discovery per
existing tests + parallel main's `_mark_stopped` preserved through rebase.
`HttpTransportConfig.from_env`: explicit env dict authoritative (parallel main made the
identical fix independently — kept theirs). `CHANGELOG.md` entry. No new dependencies,
no API shape changes.

## Regression / Full Suite / Lint / Type-Check / Security

- Regression: 7/7 new (real processes). Full: 485/485 ×2. Lint/type-check/static-analysis:
  **NOT CONFIGURED** (repo CI runs pytest only) — `git diff --check` clean, import check OK.
- Security: grep clean over changed files; `shlex`+`shell=False` preserved; Bearer/token
  paths untouched; no secrets in reports (one live relay probe during investigation began
  real fetch/publish and was killed via timeout — synthetic probes used thereafter; no
  fake SOURCE_CHANNELS injected anywhere).

## Git Diff Review

Final: 6 files (`service_manager.py`, `http_transport.py`→identical to main's parallel fix,
`CHANGELOG.md`, new `test_control_plane_startup.py`, corrected `test_stop_status_reconcile.py`,
`test_termux_control_plane_contract.py`, `test_config_manager.py`), +321/−23. No unrelated
changes. `relay.db` (untracked runtime artifact) left untouched/uncommitted. Original
`~/yasineco/YasinHub` checkout (conflicted dashboard merge) never touched.

## CI / PR / Merge Commit / Branch Cleanup / Final Verification

See headers above. Post-merge main: 37/37 targeted tests green; merge commit `2b30970` verified.

## Runtime Verification

13/13 live HTTP lifecycle on-device (see E5) + cross-repo checks: Yasin-AI `LD_PRELOAD`
passes through `_service_env` unchanged; missing relay launcher fails honestly
(`False` + error, no PID); Yasin-agent untouched.

## Remaining Issues (NOT fixed here — separate scope)

1. No `yasinrelay-termux` launcher exists in YasinRelay → needs a YasinRelay-side
   Issue/branch/PR (per scope rule; Hub now surfaces the honest failure instead of masking).
2. Pattern-based stop fallback can still match unrelated processes (kept for reconciliation
   per existing tests; self-PID excluded) — future hardening candidate.
3. `app.state`-style unbounded caches / query-filter asymmetries — noted, untouched.
4. No lint/type-check tooling configured in YasinHub CI (pytest only).
5. Issue #163's broader checklist (docs matrix, bootstrap validation, smoke test) continues
  outside this workstream.
