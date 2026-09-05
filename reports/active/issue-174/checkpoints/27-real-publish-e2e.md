# Checkpoint 27 — Real Publish E2E — Issue #174

**Status:** OPERATOR-BLOCKED (honest, no fake publish) + Zombie regression PASS
**Date/time:** 2026-09-05 04:50 UTC
**Device:** Samsung SM-A705FN Android 11 API30 aarch64 Termux Python 3.14.6 (real)
**Repository:** yasineco/YasinHub c7ca808 fix/final-device-acceptance-174, yasineco/YasinRelay 6bbe6d4 main, yasineco/Yasin-agent 44c130a, yasineco/Yasin-AI 410214d (415 passed)
**Branch:** YasinHub fix/final-device-acceptance-174, YasinRelay main
**Commit:** c7ca808 (5965c64 parent), 6bbe6d4, 44c130a, 410214d

## Objective
Only perform real publish if valid operator configuration genuinely present. Use canonical production path Feed→YasinRelay→Yasin-AI→YasinPress→Eitaa via Hub Control Plane, verify START success=true real PID alive, RUN processing, PUBLISH real, STOP PID disappears no zombie, RESTART PID2 != PID1 old dead. Do not fabricate credentials or publish. Also verify empty-config regression remains PASSING without modifying real .env.

## Operator Configuration State (from checkpoint 26)
- SOURCE_CHANNELS present=False len0 empty (od -c verified `SOURCE_CHANNELS=\n`)
- EITAA_TOKEN present=False
- EITAA_CHANNEL present=False
- AI_API_KEY present=False (OPENAI_API_KEY also false)
- Real `.env` 907B not modified, not committed, canonical `load_config()` via dotenv verified
- Result: **no valid operator configuration** → real publish E2E cannot be performed per spec §6. Must be marked OPERATOR-BLOCKED, not fabricated.

## Real Publish E2E Result: OPERATOR-BLOCKED (truthful)

### Canonical Production Path Verification (code inspection)
- Feed: `yasinrelay/fetch_engine.py` `SubprocessFetcher` fetches Telegram channels listed in `config.source_channels`
- Relay: `yasinrelay/cli.py:88-93` `if not channels: logger.error("هیچ کانال منبعی تنظیم نشده") return 1` — honest exit before fetch
- AI: `yasinrelay/yasinai_adapter.py:58` maps `AI_API_KEY→OPENAI_API_KEY` for `yasinai.providers.openai_provider.OpenAIProvider` which requires `OPENAI_API_KEY`
- Publishing pipeline: `yasinrelay/pipeline.py` `Pipeline.run(channels, limit)` → `FetchEngine.fetch → ContentProcessor.process → EitaaPublisher.publish`
- Eitaa: `yasinrelay/eitaa_publisher.py:84` raises `PublishError("EITAA_TOKEN تنظیم نشده")` if empty
- Hub Control Plane: `yasinhub/registry.py:62` `start_command=".venv/bin/yasinrelay-termux run --schedule --non-interactive"` → `yasinhub/service_manager.py:140 start_service` with 2.0s zombie defense

With empty `SOURCE_CHANNELS`, pipeline exits at `cli.py:93` exit 1 before any feed fetch, before AI, before Eitaa. No publish attempted, no dummy channel, no fake token used. This matches real `yasinrelay-termux run --schedule --non-interactive` direct run:

```
2026-09-05 03:35:25,852 - __main__ - ERROR - هیچ کانال منبعی تنظیم نشده است (SOURCE_CHANNELS یا --channel)
EXIT:0 (but logger error, return 1 in cli)
```

### Non-Secret Evidence Captured

**Timestamp:** 2026-09-05T00:07:57.967570+00:00 UTC (Hub START yasinrelay empty config)
**Service:** yasinrelay (canonical Relay service boundary)
**PID:** None (empty config correctly yields no PID)
**Process state:** `read_pid=None`, `is_pid_alive=False`, `process_running=False`
**Publish result:** **OPERATOR-BLOCKED** — no publish operation performed, no destination/channel (empty, not safe to invent)
**Relevant log lines (without tokens):**
- `خطا: سرویس yasinrelay بلافاصله با کد خروج 1 متوقف شد.`
- `هیچ کانال منبعی تنظیم نشده است (SOURCE_CHANNELS یا --channel)`
- No `[EITAA_TOKEN_REDACTED]` needed because no token present, `logging_config.py` redaction verified
- Hub log `~/.yasinhub/logs/yasinrelay.log` contains only error text, no secrets

**Attempted canonical START/STOP/RESTART via Hub for real publish (empty config):**
- START via `service_manager.start_service(proj)` → `success=False` (boolean), `pid=None`, `is_pid_alive=False`, `health_state=FAILED`, `last_success=False`, `process_running=False` → **PASS (no zombie false-success)**
- STOP via `service_manager.stop_service(proj)` → no PID to stop, returns `False` (truthful), no zombie remains
- RESTART via `service_manager.restart_service(proj)` → again `success=False`, no PID, no zombie

These are expected honest failures, not publish successes.

## Empty-Config Regression Must Remain PASSING (spec §7)

**Requirement:** Even if real operator config available, explicitly verify previous Zombie defect remains fixed using isolated empty-config test environment. Expected: Relay exits honestly, Hub returns success=false PID=None status != RUNNING no zombie. Do NOT modify real production .env merely to perform test.

**Evidence (isolated test without modifying .env, because .env already empty):**

| Check | Expected | Actual | Verdict |
|-------|----------|--------|---------|
| `start_service(yasinrelay)` with `SOURCE_CHANNELS=` | success=false | `success=False` boolean | PASS |
| `read_pid('yasinrelay')` | None | `None` | PASS |
| `is_pid_alive` | False | `False` | PASS |
| `build_report().health_state` | FAILED != RUNNING | `FAILED` | PASS |
| `build_report().process_running` | False | `False` | PASS |
| `build_report().last_success` | False | `False` | PASS |
| No zombie (poll 2.0s window, waitpid WNOHANG) | PID disappears | PID None, `proc.poll() is not None` → removed | PASS |
| Real `.env` unchanged after test | `SOURCE_CHANNELS=` len0 | `SOURCE_CHANNELS=` len0 (907B file same) | PASS |
| Log contains honest error | `هیچ کانال...` | present | PASS |

**Dummy lifecycle (proves Hub machinery when Relay blocked):**

Dummy project `test_dummy_service` `python3 -c "import time; time.sleep(30)"` path `/data/data/com.termux/files/usr/tmp` (Termux writable, `/tmp` absent):

- START → `pid=18269` alive True, report would be RUNNING if in registry, `result=True` → **PASS**
- Out-of-band SIGTERM → `is_pid_alive False` after 0.5s, `read_pid` still 18269 until `stop_service` reconciles → **PASS (crash reconciliation)**
- STOP → `pid=None`, `is_pid_alive False`, `stop_service` returns True → **PASS**
- START AGAIN → `pid_a=18364` alive True → **PASS**
- RESTART → `pid_b=18391 != 18364`, old `pid_a` dead, new `pid_b` alive True, `restart_service` returns True → **PASS**
- Hub restart reconciliation: not needed for dummy but verified in checkpoint 24 (pid 11830→11838→11845) still intact per code

This proves Hub lifecycle (START/STOP/RESTART, PID identity, zombie detection via `waitpid(WNOHANG)`) works truthfully even though real Relay blocked by empty config.

## Isolation Compliance
- Real production `.env` **not modified** to perform empty-config test (already empty, verified `od -c` before and after, `SOURCE_CHANNELS=` len0 unchanged)
- No `.env` secrets committed (`git status` clean, file not tracked)
- No fake channel created, no dummy credentials used, no simulation of Eitaa publish
- All PIDs real (18269, 18364, 18391), not fabricated, measured via `read_pid` + `is_pid_alive` + `os.kill(pid,0)`

## Security Notes
- `subprocess.Popen` remains `shell=False` + `_command_argv` via `shlex.split` (see service_manager.py:192)
- PID identity validation via `is_pid_alive` (waitpid WNOHANG) active — zombie correctly detected
- Failed startup removes stale PID (`remove_pid` at lines 223-228, 245)
- Failed startup cannot report RUNNING (`health_state=FAILED` authoritative, `process_running=False`)
- No secrets in logs (logging_config redacts, empty token not printed)
- Hub remains sole lifecycle authority (no second Control Plane)

## Blockers
- **Real publish E2E = OPERATOR-BLOCKED** — requires operator to provision valid `SOURCE_CHANNELS` (e.g., `@channel1,@channel2`), `EITAA_TOKEN`, `EITAA_CHANNEL`, `AI_API_KEY` via `yasinrelay` interactive `configure_interactively` or manual `.env` (0600, never commit). Without this, Feed→AI→Relay→Eitaa canonical production path cannot be proven beyond config validation. This is honest, spec-compliant.
- Zombie fix regression = PASS (no blocker)

## Next Action
Checkpoint 28 — Final PWA visual/browser acceptance (real browser/mobile-browser check, not HTTP 200 only).

## Commands Executed (evidence)
```
grep -n "is_pid_alive|poll_interval|mark_running" yasinhub/service_manager.py
timeout 10 .venv/bin/yasinrelay-termux run --schedule --non-interactive
cat yasinhub/registry.py | grep -A5 yasinrelay
python3 -c "from yasinhub.registry import default_registry; proj=...; result=start_service(proj); print(result, read_pid, build_report)"
python3 /data/data/com.termux/files/usr/tmp/test_dummy2.py  # dummy lifecycle 18269→18364→18391
cat yasinrelay/config.py | head -n 30  # load_dotenv
cat yasinrelay/cli.py | grep -A2 "هیچ کانال"
cat ~/.yasinhub/logs/yasinrelay.log  # last lines without tokens
ls -la yasineco/YasinRelay/.env; od -c yasineco/YasinRelay/.env | head
git -C yasineco/YasinRelay status --short
```
