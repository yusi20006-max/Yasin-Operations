# Yasin-Operations Release Candidate

## Release target

`0.1.0`

## Acceptance gates

- Python support: 3.11, 3.12, 3.13, and 3.14 through CI.
- Unit/integration/safety/adapter/CLI regression suite must pass on every supported Python version.
- Wheel packaging must succeed and the wheel must install into a clean virtual environment.
- Installed `yasin-operations` console entrypoint and `python -m yasin_operations` must both expose the CLI.
- `doctor` must be non-destructive and return a deterministic success/degraded result on supported and unsupported hosts.
- No service definitions may be modified by diagnostics or packaging checks.
- No secrets, virtual environments, bytecode, databases, or machine-specific development artifacts belong in the repository.

## Termux acceptance evidence

The project has been exercised on Termux with Python 3.14.6. The regression suite completed with 113 passing tests, and the module entrypoint was verified after the CLI entrypoint fix. `doctor` reported a valid Termux/runit environment with no diagnostics issues during the acceptance run.

The repository CI remains the authoritative repeatable regression gate; device-specific Termux acceptance remains an operator-level gate because GitHub Actions does not execute on the target Android/Termux device.

## Known limitations

- The CI environment is not an Android/Termux device, so device-specific filesystem and runit behavior must be rechecked after installation on a target Termux device.
- Service lifecycle tests remain non-destructive; they mock mutation boundaries rather than starting or stopping real services.

## Release procedure

1. Confirm the `tests` workflow is green for the release commit.
2. Confirm the packaging job builds and installs the wheel successfully.
3. Re-run the non-destructive Termux acceptance commands on the target device.
4. Verify the installed console entrypoint and module entrypoint.
5. Review `doctor --json` output and confirm no unexpected configuration or service-registry entries.
6. Only then publish the `0.1.0` release artifact/tag.
