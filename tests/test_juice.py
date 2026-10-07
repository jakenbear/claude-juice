import tempfile
import time
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import juice  # noqa: E402


def glass_rows(lines):
    top = len(juice.CARTON_ART) + juice.GAP_ROWS
    return lines[top:top + juice.GLASS_ROWS]


def juice_rows(lines):
    return sum(1 for row in glass_rows(lines) if "▓" in row[:juice.INFO_COL] or "~" in row[:juice.INFO_COL])


class FillTest(unittest.TestCase):
    def test_fill_rows(self):
        self.assertEqual(juice.fill_rows(0), 0)
        self.assertEqual(juice.fill_rows(100), juice.GLASS_ROWS)
        self.assertEqual(juice.fill_rows(50), 5)
        self.assertEqual(juice.fill_rows(2), 1)  # a sliver still shows

    def test_frame_fill_matches_level(self):
        for pct in (0, 50, 100):
            lines = juice.render_frame(juice.fill_rows(pct), color=False)
            self.assertEqual(juice_rows(lines), juice.fill_rows(pct), pct)

    def test_low_juice_is_red(self):
        lines = juice.render_frame(1, low=True)
        self.assertIn(juice.LOW, "".join(lines))
        lines = juice.render_frame(8, low=False)
        self.assertNotIn(juice.LOW, "".join(lines))

    def test_pouring_draws_stream(self):
        lines = juice.render_frame(3, pouring=True, color=False)
        below_carton = lines[len(juice.CARTON_ART)]
        self.assertIn(below_carton[juice.STREAM_COL], "|:!")


class CacheTest(unittest.TestCase):
    def test_missing_and_corrupt(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "usage.json"
            self.assertIsNone(juice.load_usage(path))
            path.write_text("{nope")
            self.assertIsNone(juice.load_usage(path))

    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "usage.json"
            rl = {"five_hour": {"used_percentage": 38}}
            juice.save_usage(rl, path, now=123)
            self.assertEqual(juice.load_usage(path), {"rate_limits": rl, "updated_at": 123})


class InfoTest(unittest.TestCase):
    def usage(self, age):
        now = time.time()
        return now, {
            "updated_at": now - age,
            "rate_limits": {
                "five_hour": {"used_percentage": 38, "resets_at": now + 2 * 3600 + 300},
                "seven_day": {"used_percentage": 19, "resets_at": now + 3 * 86400 + 3600},
            },
        }

    def test_fresh(self):
        now, usage = self.usage(30)
        text = "\n".join(t for _, t in juice.info_lines(usage, now))
        self.assertIn(" 62% left", text)
        self.assertIn(" 81% left", text)
        self.assertIn("resets in 2h 5m", text)
        self.assertIn("resets in 3d 1h", text)
        self.assertIn("updated just now", text)

    def test_stale(self):
        now, usage = self.usage(2 * 3600)
        text = "\n".join(t for _, t in juice.info_lines(usage, now))
        self.assertIn("2h ago (stale)", text)

    def test_status_text(self):
        plain = juice.ANSI_RE.sub("", juice.status_text({
            "five_hour": {"used_percentage": 38},
            "seven_day": {"used_percentage": 19},
        }))
        self.assertEqual(plain, "🧃 ▓▓▓▓▓▓░░░░ 62% (5h) · 81% wk")
        self.assertEqual(juice.status_text(None), "🧃 --")

    def test_iso_reset(self):
        self.assertEqual(juice.parse_reset("1970-01-01T00:01:00Z"), 60.0)


class RefillTest(unittest.TestCase):
    NOW = 1_000_000.0

    def limits(self, five=None, week=None, five_reset=None, week_reset=None):
        rl = {}
        if five is not None:
            rl["five_hour"] = {"used_percentage": five, "resets_at": five_reset}
        if week is not None:
            rl["seven_day"] = {"used_percentage": week, "resets_at": week_reset}
        return rl

    def status(self, rl):
        return juice.ANSI_RE.sub("", juice.status_text(rl, now=self.NOW))

    def test_empty_five_hour_counts_down(self):
        rl = self.limits(100, 60, five_reset=self.NOW + 3600 + 23 * 60 + 30)
        self.assertEqual(self.status(rl), "🧃 ░░░░░░░░░░ empty (5h) · refills in 1h 23m · 40% wk")

    def test_empty_week_takes_priority(self):
        rl = self.limits(100, 100, five_reset=self.NOW + 600, week_reset=self.NOW + 2 * 86400 + 3 * 3600)
        self.assertEqual(self.status(rl), "🧃 ░░░░░░░░░░ empty (wk) · refills in 2d 3h")

    def test_empty_week_with_juice_left_in_five(self):
        rl = self.limits(20, 100, week_reset=self.NOW + 5 * 3600)
        self.assertEqual(self.status(rl), "🧃 ░░░░░░░░░░ empty (wk) · refills in 5h 0m")

    def test_empty_without_reset_time(self):
        self.assertEqual(self.status(self.limits(100, 60)), "🧃 ░░░░░░░░░░ empty (5h) · 40% wk")

    def test_empty_is_red(self):
        self.assertIn(juice.LOW, juice.status_text(self.limits(100), now=self.NOW))

    def test_refill_target(self):
        self.assertIsNone(juice.refill_target(self.limits(50, 50)))
        self.assertEqual(juice.refill_target(self.limits(100, 50, five_reset=5.0)), ("5h", 5.0))
        self.assertEqual(juice.refill_target(self.limits(100, 100, 5.0, 9.0)), ("wk", 9.0))

    def test_clock(self):
        self.assertEqual(juice.fmt_clock(0), "0:00:00")
        self.assertEqual(juice.fmt_clock(3600 + 23 * 60 + 45), "1:23:45")
        self.assertEqual(juice.fmt_clock(2 * 86400 + 5), "2d 0:00:05")
        self.assertEqual(juice.fmt_clock(-10), "0:00:00")

    def test_countdown_line(self):
        rl = self.limits(100, five_reset=self.NOW + 65)
        self.assertEqual(juice.countdown_line(rl, self.NOW), "refills in 0:01:05")
        self.assertEqual(juice.countdown_line(rl, self.NOW + 100), "refilled! send a message")
        self.assertIsNone(juice.countdown_line(self.limits(100), self.NOW))
        self.assertIsNone(juice.countdown_line(self.limits(50), self.NOW))


if __name__ == "__main__":
    unittest.main()
