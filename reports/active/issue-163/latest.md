# Issue #163 — Current Status (handoff)

## CURRENT ISSUE

YasinHub START false-success workstream (child exits shortly after Popen → Hub said success).

## REPOSITORY

yusi20006-max/YasinHub

## BRANCH

Work is MERGED; branch `fix/control-plane-startup-verification` deleted (local + remote).
Main is at merge commit `2b30970`.

## CURRENT PHASE

COMPLETED — final report at `reports/completed/issue-163/final-report.md`.

## OBJECTIVE

(achieved) Bounded START verification, identity-aware STOP, verified RESTART, hermetic from_env.

## LAST SUCCESSFUL STEP

PR #167 merged 2026-09-04T14:38:23Z; CI 6/6 green; post-merge main 37/37 targeted green;
live device verification 13/13; branches cleaned; final report pushed (this update).

## CURRENT STATE

All evidence in `reports/completed/issue-163/final-report.md` and this directory's
`status/investigation/evidence/implementation/verification.md`.

## EVIDENCE

Pre-fix repro `start_service=True pid_file=11959 alive_after_wait=False`; post-fix `False`
+ PID removed + FAILED; full suite 485/485 ×2; live HTTP 13/13; CI run 33884611788 green.

## FAILURES

None remaining in this workstream.

## ROOT CAUSE

0.3s single poll; no ownership check; unverified restart; non-hermetic from_env; three
latent test-isolation defects (all fixed with evidence, none weakened).

## CHANGES MADE

Commit `81589b4` (6 files, +321/−23), merged as `2b30970`. Original `~/yasineco/YasinHub`
checkout untouched (pre-existing dashboard merge conflict left alone).

## TEST STATUS

485/485 full suite (merged main). No tests deleted/skipped/weakened.

## LINT STATUS

NOT CONFIGURED (CI runs pytest only).

## TYPE CHECK STATUS

NOT CONFIGURED.

## SECURITY STATUS

Grep-clean; no new exec surface; no secrets in reports.

## CI STATUS

PASS 6/6 (3.9–3.13, 3.14-dev).

## PR STATUS

#167 MERGED.

## BLOCKER

None.

## NEXT ACTION

None for this workstream. Remaining cross-repo item: YasinRelay-side `yasinrelay-termux`
launcher (separate Issue/branch/PR in YasinRelay if owned there). Broader #163 checklist
continues separately.

## LAST UPDATED

2026-09-04 (UTC) — by autonomous agent.
