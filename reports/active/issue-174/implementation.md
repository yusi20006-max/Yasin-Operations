# Implementation

A final software-side acceptance regression was added to YasinHub on branch `feat/final-ecosystem-e2e-174`:

`tests/test_final_ecosystem_e2e_acceptance.py`

It covers:
- canonical YasinRelay Termux launcher contract;
- Hub spawn boundary (`shell=False` and process identity verification);
- real child-process START → STOP → START → RESTART with PID replacement;
- PWA contract requiring authoritative `success===true`, backend PID rendering, lifecycle pending guard, and authoritative result formatting.

No production lifecycle authority was added. No Agent, AI, MCP, Relay, credential, or device implementation was changed.
