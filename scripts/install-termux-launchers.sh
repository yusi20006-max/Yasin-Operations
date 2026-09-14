#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="${YASIN_LAUNCHER_BIN_DIR:-$HOME/.local/bin}"
PYTHON="${PYTHON:-python}"
REGISTRY="$ROOT/yasin_operations/termux-launchers.json"
LAUNCHER="$ROOT/yasin_operations/termux_launcher.py"

[[ -f "$REGISTRY" ]] || { echo "launcher registry missing: $REGISTRY" >&2; exit 1; }
[[ -f "$LAUNCHER" ]] || { echo "launcher runtime missing: $LAUNCHER" >&2; exit 1; }
command -v "$PYTHON" >/dev/null 2>&1 || { echo "python is required" >&2; exit 1; }

mkdir -p "$BIN_DIR"

mapfile -t NAMES < <("$PYTHON" - "$REGISTRY" <<'PY'
import json, sys
from pathlib import Path
for item in json.loads(Path(sys.argv[1]).read_text())['launchers']:
    print(item['name'])
PY
)

for name in "${NAMES[@]}"; do
    cat > "$BIN_DIR/$name" <<EOF
#!$PREFIX/bin/bash
exec "$PYTHON" "$LAUNCHER" "$name" "\$@"
EOF
    chmod +x "$BIN_DIR/$name"
done

cat > "$BIN_DIR/yasin-launch" <<EOF
#!$PREFIX/bin/bash
exec "$PYTHON" "$LAUNCHER" "\$@"
EOF
chmod +x "$BIN_DIR/yasin-launch"

echo "Installed ${#NAMES[@]} named launchers into $BIN_DIR"
echo "Ensure $BIN_DIR is on PATH, then run: yasin-launch list"
