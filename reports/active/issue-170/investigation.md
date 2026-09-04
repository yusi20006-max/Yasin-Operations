# Investigation

## Environment probe (agent sandbox)
- uname: Linux x86_64
- PREFIX: unset
- /data/data/com.termux: absent
- SOURCE_CHANNELS / tokens: absent

## Code baseline
- Phase 1/2 complete on main
- Registry canonical launcher present
- _service_env uses os.environ.copy() (preserves LD_PRELOAD)
- Real lifecycle tests exist from #168

## Gap
Physical Termux ARM64 + operator credentials required for full publish E2E.
