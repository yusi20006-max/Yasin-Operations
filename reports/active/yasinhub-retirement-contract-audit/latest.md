# YasinHub Retirement Contract Audit — latest

## Scope
- READ-ONLY audit. No production code changed, no commit to production repos, no service created, no stale implementation built, no secrets shown.
- Basis: repair report `../yasinhub-registry-repair/latest.md`; production repair commit `aec9289` (YasinHub `fix/registry-wiring-repair`); YasinHub HEAD at audit time `aec9289` (branch `fix/registry-wiring-repair`, tree clean except untracked `yasin_hub.egg-info/`).
- Question: canonical backward-compatible path for `backup_manager`, `eitaa_news_v2`, `yasin-coder`.

## SCHEMA_VERDICT
- Registry schema (`yasinhub/registry.py:30-37` `ProjectEntry`, mirrored in `yasinhub/config_manager.py:31-37` + validation `config_manager.py:126-130`) has exactly: name / path / process_pattern / description / start_command / stop_command. **No `enabled` / `disabled` / `retired` / `deprecated` state exists.**
- Graceful-degradation paths verified in code (no crash): unknown name → `success:false "service not found"` (`api/server.py` control handler + control_routes); `start_command` null/empty → `start_service` prints message + returns False (`service_manager.py:226-228`); removal → entry vanishes from `/api/services`, `/api/status` (`report.build_report` iterates `default_registry()`), CLI, and PWA (dashboard JS renders dynamically — **no hardcoded service names** in `dashboard/js/*.js`, `dashboard/*.js`).
- YASIN-DOCS has only generic deprecation concepts (ADR lifecycle `Proposed|Accepted|Deprecated|Superseded`; `AI_CHANGE_IMPACT_PROTOCOL`: "Remove deprecated behavior only after compatibility window"). **No Hub service-registry retired semantics defined anywhere.**
- Therefore: retirement today = deletion (schema change to add a state would itself be a bigger breaking surface: dataclass + validation + API serialization + tests).

## BACKWARD_COMPATIBILITY
- **Removal is BREAKING_CHANGE: YES**: (1) `tests/test_config_manager.py:20` pins `eitaa_news_v2` in defaults-via-fallback — deletion fails the suite until the test is updated; (2) `/api/services` + `/api/status` list contract shrinks 8→5 and control on removed names flips to `service not found` for any external consumer; (3) per docs protocol, removal needs a compatibility window/announcement first.
- **Null-command is non-breaking but worse**: entry stays listed with dead Start controls; FAILED status persists. Not a retirement — a dead button. Rejected.
- **KEEP (current state) is fully compatible**: entries listed, FAILED honestly, no processes spawned.
- **Critical layering fact**: effective registry = live `~/.yasinhub/config.yaml` (non-empty → `DEFAULT_PROJECTS` unused at runtime). Repo-side deletion alone is live-invisible; both layers must change in sync, plus orphan cleanup (`~/.yasinhub/logs/<svc>.log`, `~/.yasinhub/pids/`, `~/.yasin_status/<svc>`) — none automatic.

## BACKUP_MANAGER — recommendation: RETIRE (pending decision; interim KEEP)
- Must it be a registry entry? **No.** 56-line one-shot file in YasinPress, no `__main__` guard, no loop — cannot satisfy the long-running contract (would exit 0 instantly and fail startup grace). Valid utility, invalid service.
- Correct home: external scheduler/cron or manual run with cwd=YasinPress (cwd-coupled `from config import …`). NOT Hub-managed, NOT daemonized.

## EITAA_NEWS_V2 — recommendation: RETIRE (pending decision; interim KEEP)
- CANONICAL_IMPLEMENTATION: NOT FOUND (exhaustive find; only eitaa modules inside other packages; Hub refs are tests/registry placeholders). Nothing to wire; nothing built per rules. Stale/retirement candidate.

## YASIN_CODER — recommendation: RETIRE (pending decision; interim KEEP)
- CANONICAL_IMPLEMENTATION: NOT FOUND (docs-only architecture, self-described planned expansion; zero refs outside Hub registry). No fake executable per rules. Stale/retirement candidate.

## RECOMMENDED_CHANGE (not applied)
- When approved: delete the 3 entries from `DEFAULT_PROJECTS` + live `config.yaml` in one change; update `tests/test_config_manager.py:20`; clean orphan status/pid/log files; announce per compatibility-window protocol. Until then: KEEP all three UNCHANGED (matches live state: FAILED, zero processes — verified via `pgrep`).

## Verdicts
- SCHEMA_VERDICT: no retired/disabled state; deletion is the only retirement path and it is breaking.
- BACKWARD_COMPATIBILITY: KEEP = compatible; removal = BREAKING_CHANGE: YES.
- BACKUP_MANAGER: RETIRE (pending). EITAA_NEWS_V2: RETIRE (pending). YASIN_CODER: RETIRE (pending).
- RECOMMENDED_CHANGE: staged above, awaiting explicit approval. BREAKING_CHANGE: YES (if executed).
- CODE_CHANGE: NO (this report only).
