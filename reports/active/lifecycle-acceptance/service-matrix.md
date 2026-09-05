# Lifecycle Acceptance — Service Matrix

| Service | Eligible | Start | Stop | Restart | PID verified | Final |
|---|---|---|---|---|---|---|
| yasinfeed | BLOCKED | FAIL (exit 1, child exit 2, no PID) | n/a (never RUNNING) | n/a | n/a | BLOCKED |
| eitaa_news_v2 | NOT_ELIGIBLE | n/a | n/a | n/a | n/a | NOT_ELIGIBLE |
| yasinrelay | ELIGIBLE | PASS (already RUNNING 4211) | PASS (4211 dead) | PASS (4211→17901) | YES | PASS |
| yasin-agent | ELIGIBLE | PASS (new 18087) | PASS (18087 dead) | PASS (18087→20523) | YES | PASS |
| yasin-ai | ELIGIBLE | PASS w/ caveat (new 27148 alive+stable; registered pattern stale) | FAIL (Hub refused; 27148 survives) | BLOCKED (not attempted; STOP preconditions unmet) | PARTIAL (owned-PID alive; pattern mismatch) | FAIL |
| yasin-coder | NOT_ELIGIBLE | n/a | n/a | n/a | n/a | NOT_ELIGIBLE |
| yasinpress | NOT_ELIGIBLE | n/a | n/a | n/a | n/a | NOT_ELIGIBLE |
| backup_manager | NOT_ELIGIBLE | n/a | n/a | n/a | n/a | NOT_ELIGIBLE |

Totals: 8 services — 2 PASS, 1 FAIL, 1 BLOCKED, 4 NOT_ELIGIBLE. Final verdict: **PARTIAL**.
