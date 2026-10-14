"""Offline tests for stale-lead nudges and the weekly digest. Run: python -m unittest discover -s tests"""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from notify import digest_due, digest_email, find_stale, nudge_email  # noqa: E402
from schema import HEADER, INTERNAL_HEADER  # noqa: E402

NOW = datetime(2026, 10, 19, 9, 0, tzinfo=timezone.utc)  # a Monday


def row(ref, status, priority="Warm", name="Ann"):
    r = [""] * len(HEADER)
    r[0], r[HEADER.index("Status")], r[HEADER.index("Priority")], r[HEADER.index("Name")] = ref, status, priority, name
    return r


def irow(ref, hours_ago, nudged=""):
    r = [""] * len(INTERNAL_HEADER)
    r[0], r[3], r[5] = ref, (NOW - timedelta(hours=hours_ago)).isoformat(), nudged
    return r


class Tests(unittest.TestCase):
    def test_only_old_open_unnudged_leads_are_stale(self):
        rows = [row("A", "New"), row("B", "Needs info"), row("C", "Quoted"), row("D", "New"), row("E", "New"), row("F", "Spam")]
        internal = [irow("A", 60), irow("B", 49), irow("C", 100), irow("D", 10), irow("E", 100, nudged="x"), irow("F", 100)]
        self.assertEqual([s["ref"] for s in find_stale(rows, internal, NOW, 48)], ["A", "B"])
        self.assertEqual([s["ref"] for s in find_stale(rows, internal, NOW, 48, skip_nudged=False)], ["A", "B", "E"])

    def test_internal_row_numbers_account_for_the_header(self):
        stale = find_stale([row("A", "New")], [irow("A", 60)], NOW, 48)
        self.assertEqual(stale[0]["internal_row"], 2)

    def test_deleted_visible_row_is_ignored(self):
        self.assertEqual(find_stale([], [irow("A", 60)], NOW, 48), [])

    def test_digest_due_once_per_week_on_the_right_day(self):
        self.assertTrue(digest_due(NOW, {}, "Monday", 8))
        self.assertFalse(digest_due(NOW, {}, "Tuesday", 8))
        self.assertFalse(digest_due(NOW.replace(hour=7), {}, "Monday", 8))
        self.assertFalse(digest_due(NOW, {"last_digest_week": "2026-W43"}, "Monday", 8))
        self.assertTrue(digest_due(NOW, {"last_digest_week": "2026-W42"}, "Monday", 8))

    def test_nudge_email_lists_oldest_first(self):
        stale = find_stale([row("A", "New"), row("B", "New")], [irow("A", 50), irow("B", 100)], NOW, 48)
        subject, body = nudge_email(stale, 48, "http://sheet")
        self.assertIn("2 leads", subject)
        self.assertLess(body.index("- B"), body.index("- A"))

    def test_digest_counts_this_weeks_leads_and_hot_open_leads(self):
        rows = [row("A", "New", "Hot"), row("B", "Spam", ""), row("C", "New", "Warm")]
        internal = [irow("A", 5), irow("B", 30), irow("C", 24 * 10)]  # C is older than a week
        subject, body = digest_email(rows, internal, NOW, 48, "http://sheet")
        self.assertIn("2 inquiries this week", subject)
        self.assertIn("2 still open", subject)
        self.assertIn("Hot and still open: 1", body)


if __name__ == "__main__":
    unittest.main()
