---
description: Install the juice status line meter and the `juice` terminal command
allowed-tools: Bash(bash:*)
---

Run the installer that ships with this plugin:

```
bash "${CLAUDE_PLUGIN_ROOT}/install.sh"
```

If `${CLAUDE_PLUGIN_ROOT}` is empty, find `install.sh` under `~/.claude/plugins` in a directory containing `.claude-plugin/plugin.json` with `"name": "juice"`, and run that one.

Then relay the installer's output in a few short lines and tell the user to send one message so the status line picks up their usage.
