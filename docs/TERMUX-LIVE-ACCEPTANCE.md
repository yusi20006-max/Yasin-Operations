# Termux / runit live acceptance (P4.4)

Authoritative, **read-only** verification of Yasin-Operations against a real
Termux/runit service root. Hosted CI remains distinct from live evidence.

## Classification

| Status | Meaning |
| --- | --- |
| `PASS` | Observation succeeded (healthy service or environment gate OK) |
| `FAIL` | Product/runtime defect (e.g. service present but down/failed) |
| `SKIP` | Optional service directory absent, or live checks not applicable |
| `BLOCKED` | Environment blocker (missing service root, unreadable root, missing `sv`) |

Missing optional service directories (`hermes-agent`, `yasin-ai`, `yasinpress`,
`yasinrelay`) are **SKIP**, never product **FAIL**.

`down: … normally up` is **stopped** (actual), not running. Desired state is
never substituted for observed state.

## Hosted vs live

```sh
# Hosted / offline acceptance (default)
python scripts/production_acceptance.py --json

# Live Termux/runit (read-only)
python scripts/production_acceptance.py --live --json
```

Default live service set:

```text
hermes-agent,yasin-ai,yasinpress,yasinrelay
```

Override:

```sh
python scripts/production_acceptance.py --live --services hermes-agent,yasinpress --json
```

Environment overrides:

```text
YASIN_OPERATIONS_SERVICE_ROOT   # default: /data/data/com.termux/files/usr/var/service
YASIN_OPERATIONS_SV_PATH        # or YASIN_OPERATIONS_SV / PATH lookup for `sv`
YASIN_OPERATIONS_SERVICE_NAMES  # Operations registry (separate from live set)
```

## Termux operator commands

On the device (after installing the package):

```sh
# Diagnostics without calling sv status
python -m yasin_operations doctor --json

# Combined monitoring snapshot (status + health + doctor)
python -m yasin_operations monitor

# Live acceptance (read-only)
python scripts/production_acceptance.py --live --json
```

Inspect a single service with stock runit (for comparison only):

```sh
sv status "$PREFIX/var/service/yasinpress"
```

## Failure isolation

- One service observation failure does not stop observation of other services.
- Environment blockers are listed under `environment:*` results.
- Service directory drift (extra directories under the root not in the live set)
  is reported as an `observation:*` PASS with detail, not as a product FAIL.

## Programmatic API

```python
from yasin_operations.runtime.termux.live_acceptance import evaluate_live_services

report = evaluate_live_services(("hermes-agent", "yasinpress"))
print(report.as_dict())
```
