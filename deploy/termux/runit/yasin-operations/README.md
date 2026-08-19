# Yasin-Operations runit service

This directory contains an optional standalone `runit` service definition.
It does not alter Hermes, Yasin-AI, YasinPress, or YasinRelay service definitions.

## Install

Copy this directory to the Termux service directory as `yasin-operations`.
The `run` file must be executable before enabling the service.

```sh
chmod +x /data/data/com.termux/files/usr/var/service/yasin-operations/run
```

## Environment

- `YASIN_OPERATIONS_SERVICE_ROOT` — runit service root
- `YASIN_OPERATIONS_SV_PATH` — `sv` executable path
- `YASIN_OPERATIONS_SERVICE_NAMES` — comma-separated service names Operations may inspect/control
- `YASIN_OPERATIONS_HEALTH_INTERVAL_SECONDS` — daemon health interval
- `YASIN_OPERATIONS_EXECUTION_TIMEOUT_SECONDS` — per-attempt policy timeout
- `YASIN_OPERATIONS_ALWAYS_ON` — enable/disable always-on intent

No target service command line is copied into Operations. Service names are registered and lifecycle control remains behind the runit adapter and safety policy.

## Lifecycle verification

Use the CLI before enabling the service:

```sh
python -m yasin_operations.cli doctor
python -m yasin_operations.cli status
python -m yasin_operations.cli health
```

Mutating operations require explicit confirmation:

```sh
python -m yasin_operations.cli restart <service> --confirm
```

Use `--dry-run` to verify the plan without changing service state.
