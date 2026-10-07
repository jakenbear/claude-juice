#!/usr/bin/env bash
# Installs juice: copies scripts to ~/.claude/juice, links the `juice`
# command into ~/.local/bin, and points the Claude Code status line at it.
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)/scripts"
DEST="$HOME/.claude/juice"
BIN="$HOME/.local/bin"

mkdir -p "$DEST" "$BIN"
cp "$SRC/juice.py" "$SRC/statusline.py" "$DEST/"
chmod +x "$DEST/juice.py" "$DEST/statusline.py"
ln -sf "$DEST/juice.py" "$BIN/juice"
echo "Installed scripts to $DEST and linked $BIN/juice"

python3 - "$HOME/.claude/settings.json" <<'PY'
import json, shutil, sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text()) if path.exists() else {}
cmd = 'python3 "$HOME/.claude/juice/statusline.py"'
current = (data.get("statusLine") or {}).get("command")
if current == cmd:
    print("Status line already set")
else:
    if path.exists():
        shutil.copy(path, f"{path}.bak-juice")
        print(f"Backed up settings to {path}.bak-juice")
    if current:
        print(f"Replaced old status line: {current}")
    data["statusLine"] = {"type": "command", "command": cmd}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")
    print("Status line set to the juice meter")
PY

case ":$PATH:" in
  *":$BIN:"*) ;;
  *) echo "Note: add $BIN to your PATH to run \`juice\` from any terminal" ;;
esac
