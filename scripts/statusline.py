#!/usr/bin/env python3
"""Claude Code status line: caches rate limits for `juice` and prints a meter."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import juice  # noqa: E402


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        data = {}
    rate_limits = data.get("rate_limits") if isinstance(data, dict) else None
    if rate_limits:
        juice.save_usage(rate_limits)
    else:
        cached = juice.load_usage() or {}
        rate_limits = cached.get("rate_limits")
    print(juice.status_text(rate_limits))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("🧃 --")
