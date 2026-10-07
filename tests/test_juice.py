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


if __name__ == "__main__":
    unittest.main()
