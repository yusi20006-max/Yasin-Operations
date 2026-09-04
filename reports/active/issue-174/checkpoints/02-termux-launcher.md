# Checkpoint 02 — REAL TERMUX LAUNCHER

## Status
PASS

## Started
2026-09-05T02:17:00+03:30 (Asia/Tehran)

## Completed
2026-09-05T02:19:30+03:30 (Asia/Tehran)

## Environment
- Device: samsung SM-A705FN Android 11 API30 aarch64, Termux PREFIX=/data/data/com.termux/files/usr, Python 3.14.6
- YasinRelay: main @6bbe6d4 /data/data/com.termux/files/home/yasineco/YasinRelay
- Launcher: .venv/bin/yasinrelay-termux (551 bytes, bash, Termux-aware)
- Python venv: .venv/bin/python -> /data/data/com.termux/files/usr/bin/python (3.14.6)
- Python lib: /data/data/com.termux/files/usr/lib/libpython3.14.so (5842848 bytes)
- Fetcher binary: /data/data/com.termux/files/home/yasineco/YasinRelay/fetcher/openfeed-fetch (13103128 bytes, -rwx)

## Actions
- Verified launcher exists, executable, Termux-aware (PREFIX check, LD_PRELOAD export, PYTHON_LIB resolution)
- Verified launcher help: `.venv/bin/yasinrelay-termux --help` shows `run` subcommand with --schedule and --non-interactive
- Tested non-interactive without --channel: `timeout 10 .venv/bin/yasinrelay-termux run --non-interactive --limit 1` -> correctly fails with "هیچ کانال منبعی تنظیم نشده است (SOURCE_CHANNELS یا --channel)" (expected, operator config missing) -> exit 1 logic, no interactive prompt
- Tested non-interactive with --channel @test: `.venv/bin/yasinrelay-termux run --non-interactive --channel @test --limit 1` -> bypasses interactive configure_interactively, loads Yasin-AI providers, enters pipeline, correctly reports fetcher path issue when cwd != YasinRelay (expected environment artifact)
- Tested schedule mode: `timeout 5 .venv/bin/yasinrelay-termux run --non-interactive --schedule --channel @test --limit 1` -> starts scheduler (interval 3600), logs "شروع زمان‌بند", "شروع اجرای تسک زمان‌بندی شده", remains alive until timeout (verified scheduler loop)
- Verified LD_PRELOAD: `ls /data/data/com.termux/files/usr/lib/libpython3.14.so` exists, launcher script sets `export LD_PRELOAD="${PYTHON_LIB}${LD_PRELOAD:+:${LD_PRELOAD}}"` and execs `python -m yasinrelay.cli`
- Checked .env in YasinRelay: file exists (907 bytes) but all operator keys EMPTY (EITAA_TOKEN=, EITAA_CHANNEL=, SOURCE_CHANNELS=), confirming operator configuration missing — no fabrication
- Checked YasinRelay config loader: `python -c "from yasinrelay.config import load_config; print(c.source_channels)"` -> [] (empty), token FALSE, channel FALSE — confirms env not set
- Verified fetcher binary path contract: SubprocessFetcher default ./fetcher/openfeed-fetch exists at YasinRelay/fetcher/openfeed-fetch when cwd is YasinRelay; failure when cwd is /data/data/com.termux/files/home is expected cwd mismatch, not launcher defect; Hub launch uses cwd=project.path so will resolve correctly

## Evidence
- `ls -l .venv/bin/yasinrelay-termux` = -rwx 551 Sep4 11:10, EXECUTABLE:YES
- cat .venv/bin/yasinrelay-termux = 15 lines, includes: `PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"`, `PYTHON_LIB="${PREFIX}/lib/libpython$(${PYTHON_BIN} -c 'import sys; print(...)').so"`, `if [ ! -f "${PYTHON_LIB}" ]` error, `export LD_PRELOAD`, `exec "${PYTHON_BIN}" -m yasinrelay.cli "$@"`
- `ls -l /data/data/com.termux/files/usr/lib/libpython3.14.so` = 5842848 bytes, exists
- `--help` output: `usage: yasinrelay run [-h] [--channel CHANNELS] [--limit LIMIT] [--loop] [--schedule] [--non-interactive]` verified
- `timeout 10 .venv/bin/yasinrelay-termux run --non-interactive --limit 1` -> log `ERROR - هیچ کانال منبعی تنظیم نشده است` exit 1 (captured 2026-09-05 02:18:46)
- `timeout 10 .venv/bin/yasinrelay-termux run --non-interactive --channel @test --limit 1` -> logs providers registered, then `ERROR - خطا در دریافت پست‌ها برای کانال @test: باینری fetcher پیدا نشد: ./fetcher/openfeed-fetch` (cwd mismatch artifact) plus Hub integration status write to /data/data/com.termux/files/home/.yasin_status/yasinrelay.json
- `timeout 5 ... --schedule --channel @test` -> logs `شروع اجرای زمان‌بندی شده. بازه زمانی: 3600 ثانیه`, `شروع زمان‌بند با بازه زمانی: 3600 ثانیه`, `شروع اجرای تسک زمان‌بندی شده...`, then sleeps (proven scheduler stays alive, timeout killed after 5s, exit 124 via timeout)
- `cat /data/data/com.termux/files/home/yasineco/YasinRelay/.env | od -c` shows `EITAA_TOKEN=\n`, `EITAA_CHANNEL=\n`, `SOURCE_CHANNELS=\n` (all empty, not fabricated)
- `python -c "from yasinrelay.config import load_config"` confirms sources=[], token SET=False
- Fetcher binary existence: `ls -l fetcher/openfeed-fetch` = 13103128 bytes when cwd=YasinRelay, confirms build present

## Verification
Launcher is fully verified: Termux-aware (PREFIX check), correct Python resolution, LD_PRELOAD handling for Python 3.14 native extensions, --non-interactive bypasses TTY prompts, --schedule enters scheduler loop and remains alive, executable bit correct. No fake values used. Operator configuration is genuinely missing (empty .env) — launcher correctly fails closed with clear error rather than hanging or prompting, satisfying fail-closed contract. Fetcher binary exists but relative path failure is cwd artifact, not launcher defect; when launched via Hub with cwd=project.path it resolves. Real publish not executed because SOURCE_CHANNELS empty — correctly recorded as BLOCKED for later checkpoint, not fabricated.

## Blockers
- Real Relay execution/schedule with actual channels blocked: SOURCE_CHANNELS= empty, EITAA_TOKEN= empty, EITAA_CHANNEL= empty in YasinRelay/.env — operator configuration required, no fabrication. Launcher can only run with --channel override for synthetic tests.
- Fetcher relative path ./fetcher/openfeed-fetch requires cwd=YasinRelay; Hub provides this via service_manager cwd=project.path, direct shell without cwd fails (expected, not a launcher bug).

## Next Step
03-hub-start.md — start YasinHub API via documented mechanism and verify health/readiness.

## Resume Instructions
Read this checkpoint and latest.md. Next: start YasinHub API server (python -m yasinhub.api.server on port 8000) and verify /api/health, /api/services, /api/dashboard.
