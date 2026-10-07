# claude-juice 🧃

A juice glass that fills to show how much Claude Code usage you have left.

```
   ________________
  |\     FRESH      \
  | \    JUICE       \__
  |  \________________\ \
   \ |                | |
    \|________________| |
                       |
                       :
                       !
               |       |       |    CLAUDE JUICE
               |               |
               |               |    5h   ▓▓▓▓▓░░░░░  54% left
               \               /         resets in 4h 40m
                |             |     week ▓▓▓▓▓▓▓▓░░  83% left
                |~≈~~≈~~≈~~≈~~|          resets in 5h 20m
                |▓▓▓▓▓▓▓▓▓▓▓▓▓|
                \▓▓▓▓▓▓▓o▓▓▓▓▓/     updated just now
                 |▓▓▓▓▓▓▓▓▓▓▓|
                 |▓▓▓▓▓▓▓▓▓o▓|
                 \___________/
```

You get:

- **A status line meter** at the bottom of Claude Code: `🧃 ▓▓▓▓▓░░░░░ 54% (5h) · 83% wk`
- **`juice`** in any terminal: an animated pour that fills the glass to your 5-hour % left. It turns red under 20%.
- **`/juice`** inside Claude Code: the same glass, drawn in chat.

Needs a Claude Pro or Max login (that's where the rate-limit numbers come from) and `python3`. No other dependencies.

## Install

In Claude Code:

```
/plugin marketplace add jakenbear/claude-juice
/plugin install juice@claude-juice
/juice:setup
```

Then send any message so the status line picks up your usage.

Without the plugin system:

```sh
git clone https://github.com/jakenbear/claude-juice.git
cd claude-juice && ./install.sh
```

## What setup changes

- Copies the scripts to `~/.claude/juice/`
- Links `~/.local/bin/juice`
- Sets `statusLine` in `~/.claude/settings.json`, after backing it up to `settings.json.bak-juice`. **This replaces any existing status line.**

To undo: restore `settings.json.bak-juice` and delete `~/.claude/juice` and `~/.local/bin/juice`.

## Usage

```sh
juice            # animated pour (needs a real terminal)
juice --static   # final frame only
juice --plain    # final frame, no colors
```

`! juice` inside Claude Code isn't a real terminal, so it shows the static glass.

## How it works

Claude Code pipes session JSON, including `rate_limits`, into the status line command. `statusline.py` caches that to `~/.claude/juice/usage.json` and prints the meter. `juice` reads the cache, so its numbers are as fresh as your last Claude Code reply. It shows "(stale)" after an hour.

## Tests

```sh
python3 -m unittest discover -s tests
```
