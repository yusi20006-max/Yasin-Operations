#!/data/data/com.termux/files/usr/bin/bash
# Whole-system clone/sync bootstrap for the Yasin ecosystem (Issue #218).
#
# Mode A (default): synchronize existing checkouts with origin/<branch>.
# Mode B: clone every repository fresh (see usage).
#
# Branch contract (explicit, never assumed):
#   - every repository below uses `main`, EXCEPT YasinCoder which uses `master`.
#   - YasinCoder lives outside the ecosystem root at ~/YASIN-REPOS/YasinCoder.
#
# Safety contract:
#   - fail fast (set -euo pipefail);
#   - fetch + fast-forward only; never reset, rebase, clean, or force-push;
#   - never delete or overwrite user changes: any dirty tree, ahead branch,
#     or diverged state aborts that repository with a report (exit != 0);
#   - never starts daemons or services; clone/sync/install only.
#
# Usage:
#   bash scripts/bootstrap-system.sh          # Mode A: sync existing checkouts
#   bash scripts/bootstrap-system.sh --clone  # Mode B: fresh clone (skips existing dirs)
set -euo pipefail

MODE="${1:-sync}"
if [[ "$MODE" != "sync" && "$MODE" != "--clone" ]]; then
  echo "usage: $0 [--clone]" >&2
  exit 2
fi

ECO_ROOT="${YASIN_ECOSYSTEM_ROOT:-$HOME/yasineco}"
ORG="${YASIN_GITHUB_ORG:-yusi20006-max}"

# Explicit branch map: name|branch|parent-dir. YasinCoder is the only
# `master` repository; everything else tracks `main`.
REPOS=(
  "Openfeed|main|$ECO_ROOT"
  "YASIN-DOCS|main|$ECO_ROOT"
  "Yasin-AI|main|$ECO_ROOT"
  "Yasin-MCP|main|$ECO_ROOT"
  "Yasin-Operations|main|$ECO_ROOT"
  "Yasin-agent|main|$ECO_ROOT"
  "Yasin-cli|main|$ECO_ROOT"
  "Yasin-core|main|$ECO_ROOT"
  "YasinHub|main|$ECO_ROOT"
  "YasinPress-Rewrite-|main|$ECO_ROOT"
  "YasinRelay|main|$ECO_ROOT"
  "Yasinfeed|main|$ECO_ROOT"
  "api-token-manager-pwa|main|$ECO_ROOT"
  "YasinPress|main|$ECO_ROOT"
  "YasinCoder|master|$HOME/YASIN-REPOS"
)

failures=0

sync_repo() {
  local name="$1" branch="$2" dir="$3/$1"
  if [[ ! -d "$dir/.git" ]]; then
    echo "SKIP: $name (no checkout at $dir)"
    return 0
  fi
  local head origin_ref status current
  head="$(git -C "$dir" rev-parse HEAD)"
  git -C "$dir" fetch origin --prune
  origin_ref="$(git -C "$dir" rev-parse "origin/$branch")"
  status="$(git -C "$dir" status --short)"
  current="$(git -C "$dir" branch --show-current)"
  if [[ "$current" != "$branch" ]]; then
    echo "BLOCKED (wrong branch '$current', expected '$branch', preserved): $name"
    failures=$((failures + 1))
    return 0
  fi
  local ahead behind
  ahead="$(git -C "$dir" rev-list --count "origin/$branch..HEAD")"
  behind="$(git -C "$dir" rev-list --count "HEAD..origin/$branch")"
  if [[ -n "$status" ]]; then
    echo "BLOCKED (dirty tree, preserved): $name"
    failures=$((failures + 1))
    return 0
  fi
  if [[ "$ahead" != "0" ]]; then
    echo "BLOCKED (local commits preserved): $name ahead=$ahead"
    failures=$((failures + 1))
    return 0
  fi
  if [[ "$behind" == "0" ]]; then
    echo "SYNCED: $name $branch ${head:0:7}"
    return 0
  fi
  git -C "$dir" merge --ff-only "origin/$branch"
  echo "FAST-FORWARDED: $name $branch ${head:0:7}..$(git -C "$dir" rev-parse --short HEAD)"
}

clone_repo() {
  local name="$1" branch="$2" parent="$3"
  local dir="$parent/$1"
  if [[ -e "$dir" ]]; then
    echo "SKIP: $name (already exists at $dir; use sync mode)"
    return 0
  fi
  mkdir -p "$parent"
  git clone --branch "$branch" "https://github.com/$ORG/$name.git" "$dir"
  echo "CLONED: $name $branch $(git -C "$dir" rev-parse --short HEAD)"
}

for entry in "${REPOS[@]}"; do
  IFS='|' read -r name branch parent <<< "$entry"
  if [[ "$MODE" == "--clone" ]]; then
    clone_repo "$name" "$branch" "$parent"
  else
    sync_repo "$name" "$branch" "$parent"
  fi
done

if [[ "$failures" != "0" ]]; then
  echo "$failures repositor(y/ies) need manual attention; nothing was destroyed." >&2
  exit 1
fi
echo "bootstrap $MODE complete."
