# Evidence Register — Issue #174

| Evidence | Source | Result |
|---|---|---|
| Canonical Relay launcher | YasinHub `tests/test_final_ecosystem_e2e_acceptance.py` on `main` | VERIFIED |
| Hub sole lifecycle/PID boundary | Existing Hub lifecycle tests + final regression | VERIFIED in software test boundary |
| Real process START/STOP/START/RESTART | Final regression on PR #175 | PASS; PR CI green |
| PID replacement and cleanup | Final regression on PR #175 | PASS; asserts live/dead PIDs and PID-file cleanup |
| PWA authoritative state | Final regression + Phase 4 implementation | VERIFIED |
| Agent Phase 5/6 contracts | Existing merged baselines PR #55 / #58 | VERIFIED by prior merged acceptance |
| PR CI | YasinHub PR #175, run #206 | SUCCESS on Python 3.9–3.14-dev |
| Post-merge workflow on merge SHA | GitHub workflow lookup for `21e306058dc88bd82fff1f4e178c206106c5d077` | No run registered; CI is PR-triggered |
| Physical Android/Termux ARM64 | No real device execution available in this run | NOT EXECUTED / DEFERRED |
| Credentialed source/fetch/publish | No operator runtime configuration supplied | BLOCKED — OPERATOR CONFIGURATION REQUIRED |

No fabricated PID, device, credential, channel, publish, or runtime evidence is recorded.
