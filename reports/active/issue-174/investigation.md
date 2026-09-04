# Investigation — Issue #174

## Final software baseline
- YasinRelay canonical Termux launcher: merged `d977541`.
- Hub↔Relay lifecycle E2E: PR #169 / merge `57c52df`.
- Phase 3 device contract preparation: PR #171 / merge `7904a22`.
- PWA↔Control Plane truthful integration: PR #173 / merge `bb99859`.
- Yasin-Agent Phase 5: PR #55 / merge `248f2fd`.
- Yasin-Agent Phase 6 hardening: PR #58 / merge `f348134`.
- Final software-side acceptance regression: PR #175 / merge `21e306058dc88bd82fff1f4e178c206106c5d077`.

## Acceptance result
The merged final regression checks:
1. canonical Relay launcher command and `yasinrelay.cli` process identity;
2. Hub spawn safety (`shell=False`) and process identity verification;
3. real child-process START → STOP → START → RESTART with PID replacement and cleanup;
4. PWA rendering of backend PID and rejection of optimistic lifecycle state unless `success===true`.

PR CI run #206 completed successfully on Python 3.9–3.14-dev.

## Remaining boundary
Physical Android/Termux ARM64 acceptance and credentialed source/fetch/publish were not executed. They require the real target device plus operator-provided runtime configuration. They remain explicitly deferred rather than simulated.
