# Lifecycle Acceptance — Status

- Date (UTC): 2026-09-05 (execution window approx 18:24–18:45 UTC)
- Device/runtime: Android 11 aarch64, Termux, Python 3.14.6
- Ecosystem root: `YASIN_ECOSYSTEM_ROOT="$HOME/YasinEco"`
- Control plane: YasinHub `~/YasinEco/YasinHub` @ `21e3060` (clean tree)
- Reports repo: Yasin-Operations `~/YasinEco/Yasin-Operations` @ `deeaae9` pre-task (clean tree)
- Previous lifecycle-acceptance report: NOT FOUND (no `reports/active/lifecycle-acceptance/`, nothing in git log)
- Authority: YasinHub ONLY. No direct Relay launch, no manual kill/start, no PWA changes, no real publish.

## Counts

- Registry services: 8
- ELIGIBLE (lifecycle attempted): 3 — yasinrelay, yasin-agent, yasin-ai
- Full PASS (START+STOP+RESTART): 2 — yasinrelay, yasin-agent
- FAIL: 1 — yasin-ai (STOP refused by ownership protection; process survives)
- BLOCKED: 1 — yasinfeed (stale `start_command`, entry file missing)
- NOT_ELIGIBLE: 4 — eitaa_news_v2, yasin-coder, yasinpress, backup_manager

## Final verdict

**PARTIAL** — 2 full PASS, 1 FAIL (yasin-ai STOP), 1 BLOCKED (yasinfeed), 4 NOT_ELIGIBLE.
See `service-matrix.md` and `final-report.md`.
