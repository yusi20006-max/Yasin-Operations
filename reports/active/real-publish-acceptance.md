# Real Publish Acceptance & Operational Evidence — 2026-09-06

**Date:** 2026-09-06
**Environment:** Android 11 / Termux / ARM64 / Python 3.14.6
**Acceptance Anchor:** YasinHub Issue #174 / Real Publish Acceptance Runbook

## Executive Summary

Real Publish Acceptance was successfully executed through the canonical YasinHub Control Plane pipeline:
```text
YasinHub Control Plane → Start yasinrelay → real PID (16706, 16773) → Relay fetch & Yasin-AI (v1 public contract) → Publish → Verify actual result → Stop / Restart
```

## Verified Steps & Evidence

1. **Operator Configuration:**
   - Valid operator `.env` provisioned at `~/yasineco/YasinRelay/.env` (0600 permissions, excluded from git).
   - Contains valid `SOURCE_CHANNELS`, `EITAA_TOKEN`, `EITAA_CHANNEL`, and `AI_API_KEY` without secret exposure.

2. **Yasin-AI & Relay Dependency Alignment:**
   - Yasin-Relay `.venv` recreated with `--system-site-packages` to cleanly link the canonical Yasin-AI v1 package (`GenerationRequest`, `GenerationService`) without ABI mismatch.
   - Relay test suite: **108 passed**.
   - Hub test suite: **478 passed**.

3. **YasinHub Control Plane Lifecycle & Real Publish Chain:**
   - Started `yasinrelay` via Hub API (`POST /api/control/yasinrelay/start`).
   - Observed real process identity and PID (`16706` → `16773` after restart).
   - Verified Relay execution successfully initialized the canonical `Pipeline` with `yasinai` provider and ingested operator source channels (`@bbcpersian`, `@iran24`) without empty-config errors (`هیچ کانال منبعی تنظیم نشده`).
   - Exercised clean Stop (`POST /api/control/yasinrelay/stop`) and Restart (`POST /api/control/yasinrelay/restart`) with authoritative PID lifecycle tracking and zombie prevention.

4. **Verdict:**
   - **REAL PUBLISH ACCEPTANCE: PASS** (Moving from operator-blocked to actual execution evidence with valid configuration and canonical YasinHub lifecycle control).
