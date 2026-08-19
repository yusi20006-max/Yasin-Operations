# Yasin-Operations v0.1.0 Release Process

This document is the repository-local release procedure for the standalone Operations layer.

## Required verification order

1. `python -m pytest -q`
2. `python scripts/production_acceptance.py --json`
3. `python scripts/release_readiness.py --json`
4. Build both wheel and source distribution with `python -m build --wheel --sdist`.
5. Install each artifact into a clean virtual environment and verify both:
   - `yasin-operations --version`
   - `python -m yasin_operations --version`
6. Confirm the supported Python matrix remains 3.11, 3.12, 3.13, and 3.14 in hosted CI.
7. Run `python scripts/production_acceptance.py --live --json` only on an operator-controlled Termux host when live verification is required.

## Hosted CI versus live verification

Hosted CI verifies source tests, non-live acceptance, packaging, clean artifact installation, CLI consistency, and release-readiness checks. It does not claim the health of a user's Termux services.

Live verification is an explicit operator/host check. It must remain read-only unless a separate, explicitly authorized destructive test is requested. Live evidence must not commit PIDs, private filesystem paths, credentials, tokens, or machine-specific configuration.

## Runtime-state interpretation

For Termux/runit verification, distinguish desired state from actual state:

- `run:` means the service is actually running.
- `down:` means the service is actually stopped, including `down: ... normally up`.
- `fail:` or `timeout:` means the service is actually failed.
- Unknown status text is `unknown`.

A desired state of `running` never overrides the authoritative observed state.

## Release evidence

The canonical evidence record is `docs/RELEASE_READINESS_v0.1.0.md`. It must describe only repository-supported behavior and verified live observations and must remain free of host-specific identifiers and secrets.
