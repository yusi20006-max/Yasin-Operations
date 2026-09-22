# Yasin System Releases

This document defines the system-level release contract for the Yasin ecosystem.

A **Yasin System Release** is a coordinated, reproducible snapshot of the
repositories that make up the supported Yasin system. It is not a replacement
for the individual repository release/version schemes.

## v1.0.0 baseline

The first verified baseline is defined by:

`releases/YASIN-SYSTEM-v1.0.0.yml`

The manifest records the exact `main` commit for each of the 14 included
repositories, plus synchronization, runtime, shutdown, and limitation status.

The 2026-09-22 verification established:

- 14 included repositories synchronized to origin (0 ahead / 0 behind).
- 0 tracked repository changes.
- Runtime verification PASS for the applicable services.
- Graceful shutdown verification PASS.
- Yasin-MCP is explicitly recorded as PASS WITH LIMITATIONS because live stdio
  could not be exercised without the MCP SDK in native Termux.
- YasinCoder and the dated YasinHub backup checkout are excluded.

## Release contract

Each future system release MUST:

1. Identify a single release version such as `1.1.0`.
2. Record the exact immutable commit SHA for every included repository.
3. Record the branch/ref used to establish the snapshot.
4. Record repository synchronization state before the release snapshot.
5. Record runtime verification and graceful shutdown evidence.
6. Record limitations explicitly instead of converting blocked tests into PASS.
7. Exclude retired repositories and backup checkouts unless the release scope
   explicitly changes.
8. Be reproducible from its manifest without relying on mutable tags alone.
9. Update this documentation when the release procedure itself changes.
10. Create the public tag/release artifact only after the final verification
    passes.

## Release procedure

From the canonical native Termux ecosystem root:

```sh
cd ~/yasineco

# 1. Fetch and fast-forward every included repository.
# 2. Confirm each HEAD equals its origin/main and record the full SHA.
# 3. Run the canonical Operations and service runtime verification.
# 4. Shut down test-started services and verify ports/processes are released.
# 5. Write the manifest with the exact verified SHAs.
# 6. Validate the manifest.
cd ~/yasineco/Yasin-Operations
python scripts/validate_system_release.py releases/YASIN-SYSTEM-v<version>.json
```

The manifest is the source of truth for the coordinated snapshot. Individual
repository releases remain owned by their respective repositories.

## Safety boundaries

System-release work must not:

- change unrelated service behavior;
- create artificial Termux-runit service directories;
- bypass YasinHub lifecycle authority;
- treat an environment limitation as a product defect without evidence;
- include the YasinHub dated backup checkout;
- include YasinCoder in a system release without the explicit Issue #218
  scope (branch `master`, exact SHA, CLI/workflow lifecycle — never
  Hub/Runit-managed, never a rewrite of the frozen v1.0.0 manifest).

## Evidence classification

Use these states consistently:

- **PASS** — the check was actually executed and passed.
- **PASS WITH LIMITATIONS** — the release remains usable/verified, but a
  declared check could not be exercised.
- **SKIP** — intentionally not applicable to the release.
- **BLOCKED** — required verification could not be completed and release
  readiness must not be claimed.

A system release must not silently promote SKIP or BLOCKED evidence to PASS.
