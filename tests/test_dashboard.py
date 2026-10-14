"""Offline tests for the dashboard data builder. Run: python -m unittest discover -s tests"""
import json
import re
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dashboard import build_leads, mask_email, mask_phone, render  # noqa: E402
from schema import HEADER, INTERNAL_HEADER  # noqa: E402

NOW = datetime(2026, 10, 19, 9, 0, tzinfo=timezone.utc)


def row(ref, **kw):
    r = [""] * len(HEADER)
    r[0] = ref
    for name, value in kw.items():
        r[HEADER.index(name.replace("_", " ").capitalize() if name != "ref" else "Ref ID")] = value
    return r


def irow(ref, hours_ago, reply=""):
    r = [""] * len(INTERNAL_HEADER)
    r[0], r[3], r[4] = ref, (NOW - timedelta(hours=hours_ago)).isoformat(), reply
    return r


class Tests(unittest.TestCase):
    def test_masking(self):
        self.assertEqual(mask_email("thandi.nkosi@example.com"), "t•••@example.com")
        self.assertEqual(mask_phone("082 555 0141"), "••• ••• ••41")
        self.assertEqual(mask_email("not an email"), "not an email")

    def test_leads_are_masked_joined_and_newest_first(self):
        rows = [row("A", received="2026-10-18 10:00", email="a.b@x.com", phone="082 555 0141"),
                row("B", received="2026-10-19 08:00")]
        data = build_leads(rows, [irow("A", 30, "Hi A"), irow("B", 1)], NOW, 48, mask=True)
        self.assertEqual([lead["ref"] for lead in data["leads"]], ["B", "A"])
        a = data["leads"][1]
        self.assertEqual((a["email"], a["phone"], a["draftReply"], a["waitingHours"]), ("a•••@x.com", "••• ••• ••41", "Hi A", 30.0))

    def test_no_mask_keeps_real_contacts(self):
        data = build_leads([row("A", email="a@x.com")], [], NOW, 48, mask=False)
        self.assertEqual(data["leads"][0]["email"], "a@x.com")

    def test_render_embeds_valid_json_and_survives_script_tags(self):
        template = "<title>__BUSINESS__</title><script>const D = /*__DATA__*/null;</script>"
        data = {"leads": [{"description": "</script><b>x"}]}
        html = render(data, "A & B", template)
        self.assertIn("A &amp; B", html)
        blob = re.search(r"const D = (.*);</script>", html).group(1)
        self.assertEqual(json.loads(blob.replace("<\\/", "</")), data)
        self.assertEqual(html.count("</script>"), 1)


if __name__ == "__main__":
    unittest.main()
