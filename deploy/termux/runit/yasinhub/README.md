# YasinHub Runit service

This directory is the canonical Termux/runit definition for the YasinHub Control Plane.

- Service name: `yasinhub`
- Default repository root: `$HOME/yasineco/YasinHub`
- Entrypoint: `python -m yasinhub.startup`
- Canonical Control Plane port: `7000`
- Supervisor: Termux `runit`
- `yasin-agent` is a separate Runit service and is not launched by this service.

## Install on Termux

From this repository:

```sh
bash scripts/install-termux-yasinhub-runit.sh
```

The installer stops the existing `yasinhub` service, preserves an existing service definition under a timestamped backup, installs the repository-managed service as a symlink, and asks runit to bring it up.

A non-default YasinHub checkout can be supplied with `YASINHUB_ROOT=/path/to/YasinHub`.

## Verify

```sh
sv status yasinhub
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:7000/api/health
```

Do not configure this service as `python -m yasinhub.cli start yasin-agent`; that command belongs to the agent lifecycle path, not the YasinHub Control Plane supervisor.