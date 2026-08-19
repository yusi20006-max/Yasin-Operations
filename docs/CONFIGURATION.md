# Runtime Configuration

Yasin-Operations uses one validated configuration model for the standalone CLI and the Termux/runit adapter.

## Precedence

Values are resolved in this order, from lowest to highest priority:

1. Built-in defaults
2. Environment variables
3. Explicit CLI/caller overrides

Explicit overrides therefore always win over environment variables.

## Defaults

| Setting | Default |
| --- | --- |
| `service_root` | `/data/data/com.termux/files/usr/var/service` |
| `sv_path` | `/data/data/com.termux/files/usr/bin/sv` |
| `service_names` | empty registry |
| `execution_timeout_seconds` | `30` |
| `startup_grace_seconds` | `2` |
| `always_on` | `true` |
| `log_level` | `INFO` |

The Termux paths are platform defaults, not user-specific paths. No account name or home directory is embedded in the configuration.

## Environment variables

- `YASIN_OPERATIONS_SERVICE_ROOT`
- `YASIN_OPERATIONS_SV_PATH`
- `YASIN_OPERATIONS_SERVICE_NAMES` — comma-separated service names
- `YASIN_OPERATIONS_EXECUTION_TIMEOUT_SECONDS`
- `YASIN_OPERATIONS_STARTUP_GRACE_SECONDS`
- `YASIN_OPERATIONS_ALWAYS_ON` — `1/true/yes/on` or `0/false/no/off`
- `YASIN_OPERATIONS_LOG_LEVEL` — `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`

Invalid values fail fast with a configuration error.

## CLI overrides

The CLI can override the same runtime settings without modifying the environment:

```sh
python -m yasin_operations --service-root /tmp/services --services yasin-ai,yasinpress doctor
python -m yasin_operations --timeout 60 --no-always-on health
```

The configuration layer validates absolute paths, positive timeout values, non-negative startup grace, boolean values, log levels, and simple runit service names.

## Service registry diagnostics

The configured service registry is declarative. Loading configuration never creates, deletes, starts, stops, or modifies service directories. `doctor` reports registered service names that are missing from `service_root` so operators can distinguish configuration from filesystem state.
