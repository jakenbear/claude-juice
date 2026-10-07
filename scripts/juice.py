#!/usr/bin/env python3
"""juice: animated Claude Code usage meter.

Reads the rate limits cached by statusline.py and pours a glass filled to the
share of your 5-hour window that's left. When a window runs dry it counts down
to the refill. `juice --static` skips the animation; `juice --plain` also drops
colors.
"""
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

CACHE = Path.home() / ".claude" / "juice" / "usage.json"
STALE_SECS = 3600
LOW_PCT = 20
GLASS_ROWS = 10
FPS = 25
POUR_FRAMES = 40
SETTLE_FRAMES = 12

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
JUICE = "\033[38;5;208m"
FOAM = "\033[38;5;222m"
LOW = "\033[38;5;196m"
GLASS = "\033[38;5;250m"
CARTON = "\033[38;5;214m"
ANSI_RE = re.compile(r"\033\[[0-9;?]*[A-Za-z]")

CARTON_ART = [
    r"   ________________",
    r"  |\     FRESH      \ ",
    r"  | \    JUICE       \__",
    r"  |  \________________\ \ ",
    r"   \ |                | |",
    r"    \|________________| |",
]
STREAM_COL = 23
GAP_ROWS = 3
GLASS_LEFT, GLASS_RIGHT = 15, 31
INFO_COL = 36
WIDTH = 64


def pct_left(window):
    if not isinstance(window, dict) or window.get("used_percentage") is None:
        return None
    return max(0.0, min(100.0, 100.0 - float(window["used_percentage"])))


def parse_reset(value):
    if isinstance(value, (int, float)):
        return float(value)
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def fmt_until(ts, now, verb="resets"):
    if ts is None:
        return ""
    secs = int(ts - now)
    if secs <= 0:
        return f"{verb} now"
    hours, mins = divmod(secs // 60, 60)
    days, hours = divmod(hours, 24)
    if days:
        return f"{verb} in {days}d {hours}h"
    if hours:
        return f"{verb} in {hours}h {mins}m"
    return f"{verb} in {mins}m"


def fmt_clock(secs):
    secs = max(0, int(secs))
    days, secs = divmod(secs, 86400)
    hours, secs = divmod(secs, 3600)
    mins, secs = divmod(secs, 60)
    clock = f"{hours}:{mins:02d}:{secs:02d}"
    return f"{days}d {clock}" if days else clock


def fmt_age(secs):
    if secs < 60:
        return "just now"
    if secs < 3600:
        return f"{int(secs // 60)}m ago"
    if secs < 86400:
        return f"{int(secs // 3600)}h ago"
    return f"{int(secs // 86400)}d ago"


def load_usage(path=CACHE):
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def save_usage(rate_limits, path=CACHE, now=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps({
        "rate_limits": rate_limits,
        "updated_at": time.time() if now is None else now,
    }))
    os.replace(tmp, path)


def bar(pct, width=10):
    filled = round(pct / 100 * width)
    return "▓" * filled + "░" * (width - filled)


def fill_rows(pct):
    rows = round(max(0.0, min(100.0, pct)) / 100 * GLASS_ROWS)
    return max(1, rows) if pct > 0 else 0


def refill_target(rate_limits):
    """(label, reset timestamp) of the window that's run dry, weekly first, else None."""
    rate_limits = rate_limits if isinstance(rate_limits, dict) else {}
    for label, key in (("wk", "seven_day"), ("5h", "five_hour")):
        window = rate_limits.get(key)
        if pct_left(window) == 0:
            return label, parse_reset(window.get("resets_at"))
    return None


def countdown_line(rate_limits, now):
    target = refill_target(rate_limits)
    if not target or target[1] is None:
        return None
    if now >= target[1]:
        return "refilled! send a message"
    return f"refills in {fmt_clock(target[1] - now)}"


def status_text(rate_limits, now=None):
    """One-line meter for the Claude Code status bar."""
    rate_limits = rate_limits if isinstance(rate_limits, dict) else {}
    five = pct_left(rate_limits.get("five_hour"))
    week = pct_left(rate_limits.get("seven_day"))
    if five is None and week is None:
        return "🧃 --"
    target = refill_target(rate_limits)
    if target:
        label, reset = target
        parts = [f"{LOW}{bar(0)}{RESET} empty ({label})"]
        if reset is not None:
            parts.append(fmt_until(reset, time.time() if now is None else now, "refills"))
        if label == "5h" and week is not None:
            parts.append(f"{week:.0f}% wk")
        return "🧃 " + " · ".join(parts)
    parts = []
    if five is not None:
        color = LOW if five < LOW_PCT else JUICE
        parts.append(f"{color}{bar(five)}{RESET} {five:.0f}% (5h)")
    if week is not None:
        parts.append(f"{week:.0f}% wk")
    return "🧃 " + " · ".join(parts)


def info_lines(usage, now):
    rate_limits = usage.get("rate_limits") or {}
    lines = [(BOLD, "CLAUDE JUICE"), (None, "")]
    for label, key in (("5h  ", "five_hour"), ("week", "seven_day")):
        window = rate_limits.get(key)
        pct = pct_left(window)
        if pct is None:
            continue
        lines.append((None, f"{label} {bar(pct)} {pct:3.0f}% left"))
        lines.append((DIM, "     " + fmt_until(parse_reset(window.get("resets_at")), now)))
    age = now - float(usage.get("updated_at") or 0)
    stale = age > STALE_SECS
    lines.append((None, ""))
    lines.append((LOW if stale else DIM, f"updated {fmt_age(age)}" + (" (stale)" if stale else "")))
    return lines


def render_frame(level, info=(), tick=0, pouring=False, drops=False, low=False, color=True):
    """Draw one frame as a list of strings. `level` is juice height in glass rows."""
    height = len(CARTON_ART) + GAP_ROWS + GLASS_ROWS + 1
    grid = [[(" ", None)] * WIDTH for _ in range(height)]

    def put(r, c, ch, col=None):
        if 0 <= r < height and 0 <= c < WIDTH:
            grid[r][c] = (ch, col)

    for r, line in enumerate(CARTON_ART):
        for c, ch in enumerate(line):
            if ch != " ":
                put(r, c, ch, CARTON)

    top = len(CARTON_ART) + GAP_ROWS
    juice = LOW if low else JUICE
    surface = top + GLASS_ROWS - int(level)
    for i in range(GLASS_ROWS):
        r, inset = top + i, i // 4
        left, right = GLASS_LEFT + inset, GLASS_RIGHT - inset
        slants = i < GLASS_ROWS - 1 and (i + 1) // 4 != inset
        put(r, left, "\\" if slants else "|", GLASS)
        put(r, right, "/" if slants else "|", GLASS)
        if r < surface:
            continue
        for c in range(left + 1, right):
            if r == surface:
                put(r, c, "≈" if (c + tick) % 3 == 0 else "~", LOW if low else FOAM)
            elif (c * 5 + r + tick) % 17 == 0:
                put(r, c, "o", FOAM)
            else:
                put(r, c, "▓", juice)

    base, inset = top + GLASS_ROWS, (GLASS_ROWS - 1) // 4
    put(base, GLASS_LEFT + inset, "\\", GLASS)
    for c in range(GLASS_LEFT + inset + 1, GLASS_RIGHT - inset):
        put(base, c, "_", GLASS)
    put(base, GLASS_RIGHT - inset, "/", GLASS)

    stream_bottom = surface - 1
    if pouring:
        for r in range(len(CARTON_ART), stream_bottom + 1):
            put(r, STREAM_COL, "|:!"[(r - tick) % 3], juice)
        if stream_bottom >= top:
            splash = "'`."[tick % 3]
            put(stream_bottom, STREAM_COL - 2, splash, FOAM)
            put(stream_bottom, STREAM_COL + 2, splash, FOAM)
    elif drops:
        span = stream_bottom - len(CARTON_ART) + 1
        if span > 0:
            put(len(CARTON_ART) + tick % span, STREAM_COL, ".", juice)

    for i, (col, text) in enumerate(info):
        for j, ch in enumerate(text):
            put(top + i, INFO_COL + j, ch, col)

    lines = []
    for row in grid:
        out, current = [], None
        for ch, col in row:
            if color and col != current:
                out.append(RESET + (col or ""))
                current = col
            out.append(ch)
        if color and current:
            out.append(RESET)
        lines.append("".join(out).rstrip())
    return lines


def with_countdown(info, rate_limits, now):
    line = countdown_line(rate_limits, now)
    return list(info) + [(None, ""), (BOLD + LOW, line)] if line else info


def animate(pct, info, low, rate_limits=None, out=sys.stdout):
    """Pour the glass. If a window is dry, keep dripping and tick the refill countdown until Ctrl-C."""
    target = fill_rows(pct)
    height = 0
    ticking = countdown_line(rate_limits, time.time()) is not None
    out.write("\033[?25l")
    try:
        tick = 0
        while tick < POUR_FRAMES + SETTLE_FRAMES or ticking:
            pouring = tick < POUR_FRAMES
            level = min(target, target * (tick + 1) / (POUR_FRAMES * 0.85))
            now = time.time()
            lines = render_frame(
                level,
                () if pouring else with_countdown(info, rate_limits, now),
                tick,
                pouring=pouring and target > 0,
                drops=(pouring or ticking) and target == 0,
                low=low,
            )
            if height:
                out.write(f"\033[{height}A")
            out.write("".join(f"\033[2K{line}\n" for line in lines))
            out.flush()
            height = len(lines)
            if ticking and not pouring and countdown_line(rate_limits, now).startswith("refilled"):
                break
            tick += 1
            time.sleep(1 / FPS)
    finally:
        out.write("\033[?25h")
        out.flush()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    usage = load_usage()
    if not usage:
        print("No data yet. Send one message in Claude Code first.")
        return 1
    rate_limits = usage.get("rate_limits") or {}
    pct = pct_left(rate_limits.get("five_hour"))
    if pct is None:
        pct = pct_left(rate_limits.get("seven_day"))
    if pct is None:
        print("No rate-limit data cached. Claude Code only reports it on Pro/Max plans.")
        return 1
    if refill_target(rate_limits):
        pct = 0.0  # a dry weekly window blocks you even with 5h juice left

    now = time.time()
    info, low = info_lines(usage, now), pct < LOW_PCT
    plain = "--plain" in argv or "NO_COLOR" in os.environ
    if plain or "--static" in argv or not sys.stdout.isatty():
        info = with_countdown(info, rate_limits, now)
        if plain:
            info = [(None, text) for _, text in info]
        print("\n".join(render_frame(fill_rows(pct), info, low=low, color=not plain)))
    else:
        try:
            animate(pct, info, low, rate_limits)
        except KeyboardInterrupt:
            return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
