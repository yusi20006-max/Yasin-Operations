# Investigation

## Phase 1 conflict
PR #56 dirty vs main on scripts/install_termux.sh.
Resolution: rebased branch feat/termux-canonical-launcher-rebased, PR #57, CI green, squash-merged d977541.

## Phase 2 Hub state
Registry already has:
- name=yasinrelay
- start_command=.venv/bin/yasinrelay-termux run --schedule --non-interactive
- process_pattern=yasinrelay.cli
Service manager already has startup verification, identity checks, stop ownership (PR #167).
Gap was explicit E2E regression coverage for the Relay contract.
