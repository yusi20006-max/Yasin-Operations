# Yasin-Operations on Termux

Termux is the canonical runtime for Yasin-Operations. Debian/proot may be used for development or compatibility checks, but it is not the production acceptance environment.

## Runtime assumptions

- Python is provided by Termux.
- Service lifecycle uses Termux's runit tree under `$PREFIX/var/service`.
- `sv` is normally `$PREFIX/bin/sv`.
- The Operations process itself does not require systemd, Docker, or a desktop Linux service manager.
- Hermes, Yasin-AI, YasinPress, and YasinRelay are optional integration boundaries. Their absence must not make the standalone Operations runtime unhealthy.

## Recommended environment variables

```sh
export YASIN_OPERATIONS_SERVICE_ROOT="${PREFIX}/var/service"
export YASIN_OPERATIONS_SV_PATH="${PREFIX}/bin/sv"
```

`YASIN_OPERATIONS_SV` remains accepted for compatibility with older deployments.

## Validation

From the repository root:

```sh
python -m pytest -q
python scripts/production_acceptance.py --json
python scripts/production_acceptance.py --live --json
```

`--live` checks only services that are actually installed in the configured runit service root. Missing optional services are reported as `SKIP`; an installed service that is present but failed is a real acceptance failure.

## MCP / Hermes

The MCP bridge is an integration surface, not a replacement for the standalone gateway. Validate the Operations gateway first, then validate MCP/Hermes integration against the same Termux Python environment.

## Deployment rule

Do not copy a Debian/proot service path into Termux configuration. Prefer `$PREFIX`-based paths so the same deployment instructions work across supported Termux installations.
