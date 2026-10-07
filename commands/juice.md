---
description: Show how much Claude usage juice you have left
allowed-tools: Bash(python3:*)
---

!`python3 "$HOME/.claude/juice/juice.py" --plain 2>&1 || echo "juice isn't installed yet. Run /juice:setup first."`

Reply with the output above exactly as-is inside a single ``` code block. Add nothing else.
