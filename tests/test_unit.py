"""Offline tests, no network. Run: python -m unittest discover -s tests"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from extract import missing_data, parse_response, priority_for, status_for  # noqa: E402
from run import alert_recipients, content_hash, next_ref  # noqa: E402

FULL = {"is_inquiry": True, "customer_name": "A", "email": "a@x.com", "phone": None, "project_type": "kitchen",
        "location": "Paarl", "description": "New cupboards", "timeline": "Dec", "urgent": False, "summary": "s"}


class Tests(unittest.TestCase):
    def test_parse_handles_code_fence_and_nulls(self):
        out = parse_response('```json\n{"is_inquiry": true, "location": "null", "summary": "x"}\n```')
        self.assertTrue(out["is_inquiry"])
        self.assertIsNone(out["location"])

    def test_parse_rejects_garbage(self):
        with self.assertRaises(ValueError):
            parse_response("sorry, I cannot help")

    def test_is_inquiry_must_be_real_boolean(self):
        self.assertFalse(parse_response('{"is_inquiry": "true"}')["is_inquiry"])

    def test_status_new_when_complete(self):
        self.assertEqual(status_for(FULL, missing_data(FULL)), "New")

    def test_missing_timeline_only_stays_new(self):
        item = {**FULL, "timeline": None}
        self.assertEqual(missing_data(item), ["timeline"])
        self.assertEqual(status_for(item, missing_data(item)), "New")

    def test_missing_location_needs_info(self):
        item = {**FULL, "location": None}
        self.assertEqual(status_for(item, missing_data(item)), "Needs info")

    def test_spam(self):
        item = {**FULL, "is_inquiry": False}
        self.assertEqual(status_for(item, missing_data(item)), "Spam")

    def test_ref_ids_increment_per_day(self):
        refs = {"JNR-20261014-001", "JNR-20261014-002", "JNR-20261013-009"}
        self.assertEqual(next_ref(refs, "20261014"), "JNR-20261014-003")
        self.assertEqual(next_ref(refs, "20261015"), "JNR-20261015-001")

    def test_priority_rules(self):
        def p(status, missing=(), **kw):
            item = {**FULL, "timeline_weeks": None, **kw}
            return priority_for(item, list(missing), status)
        self.assertEqual(p("New", urgent=True), "Hot")
        self.assertEqual(p("New", timeline_weeks=3), "Hot")
        self.assertEqual(p("New", timeline_weeks=8), "Warm")
        self.assertEqual(p("New"), "Warm")
        self.assertEqual(p("New", timeline_weeks=20), "Cold")
        self.assertEqual(p("Needs info", ["location"]), "Warm")
        self.assertEqual(p("Needs info", ["location", "timeline"]), "Cold")
        self.assertEqual(p("Needs info", ["location", "timeline"], urgent=True), "Hot")
        for status in ("Spam", "Duplicate", "Error", "Quoted"):
            self.assertEqual(p(status), "")

    def test_timeline_weeks_must_be_whole_number(self):
        self.assertEqual(parse_response('{"timeline_weeks": 6}')["timeline_weeks"], 6)
        for bad in ('"soon"', "true", "-2", "null", "2.5"):
            self.assertIsNone(parse_response('{"timeline_weeks": %s}' % bad)["timeline_weeks"])

    def test_alert_recipients_owner_first_no_duplicates(self):
        cfg = {"owner_email": "a@x.com", "notify_also": ["b@x.com", "A@x.com", ""]}
        self.assertEqual(alert_recipients(cfg), ["a@x.com", "b@x.com"])
        self.assertEqual(alert_recipients({"owner_email": "a@x.com"}), ["a@x.com"])

    def test_hash_ignores_whitespace_and_case(self):
        a = content_hash({"body": "Hello  World"}, "A@x.com")
        b = content_hash({"body": "hello world\n"}, "a@x.com")
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
