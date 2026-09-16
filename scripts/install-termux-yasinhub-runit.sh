#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$ROOT/deploy/termux/runit/yasinhub"
SERVICE_ROOT="${YASIN_RUNIT_SERVICE_ROOT:-${PREFIX:?}/var/service}"
TARGET="$SERVICE_ROOT/yasinhub"
HUB_ROOT="${YASINHUB_ROOT:-$HOME/yasineco/YasinHub-runtime}"

[[ -f "$SOURCE/run" ]] || { echo "yasinhub run definition missing: $SOURCE/run" >&2; exit 1; }
[[ -x "$HUB_ROOT/.venv/bin/python" ]] || { echo "YasinHub venv python missing: $HUB_ROOT/.venv/bin/python" >&2; exit 1; }
[[ -f "$HUB_ROOT/yasinhub/startup.py" ]] || { echo "YasinHub startup module missing: $HUB_ROOT/yasinhub/startup.py" >&2; exit 1; }
command -v sv >/dev/null 2>&1 || { echo "Termux runit sv is required" >&2; exit 1; }

mkdir -p "$SERVICE_ROOT"

if [[ -e "$TARGET" || -L "$TARGET" ]]; then
    sv down yasinhub >/dev/null 2>&1 || true
    backup="$TARGET.backup.$(date +%Y%m%d%H%M%S)"
    mv "$TARGET" "$backup"
    echo "Backed up existing yasinhub service to $backup"
fi

# Generate a small service wrapper so a custom YASINHUB_ROOT is persisted in
# the supervised service itself. The caller's shell environment is not relied
# upon after installation/reboot.
mkdir -p "$TARGET"
cat >"$TARGET/run" <<EOF
#!/data/data/com.termux/files/usr/bin/sh
set -eu

YASINHUB_ROOT=$(printf '%s' "$HUB_ROOT" | sed 's/[\\&]/\\&/g; s/["`$]/\\&/g')
cd "\$YASINHUB_ROOT" || exit 1
exec "\$YASINHUB_ROOT/.venv/bin/python" -m yasinhub.startup
EOF
chmod 0755 "$TARGET/run"

sv up yasinhub

echo "Installed YasinHub Runit service: $TARGET"
echo "Entrypoint: python -m yasinhub.startup"
echo "Root: $HUB_ROOT"
