import unittest
from pathlib import Path

import verify as v

ROOT = Path(__file__).resolve().parent.parent


class FakeClient:
    def __init__(self, content, tool_calls=None, ok=True):
        self.content, self.tool_calls, self.ok = content, tool_calls or [], ok

    def chat(self, messages, tools=None, **_kw):
        self.tools = tools
        if not self.ok:
            return {"ok": False, "error": "every model failed", "attempts": [{"model": "m", "ok": False}]}
        return {"ok": True, "model": "m", "content": self.content, "otari_tool_calls": self.tool_calls, "attempts": []}


ROW = {"item": "X", "deadline": "Wed 2026-11-11 5:59 PM", "link": "https://dorahacks.io/hackathon/x/detail"}
RECEIPT = [{"type": "web_fetch", "status": "ok", "url": "https://dorahacks.io/hackathon/x/detail"}]


class TestTimeMath(unittest.TestCase):
    def ts(self, claim):
        t, has, _ = v.page_deadline(claim, 2026)
        return t.astimezone(v.ET).strftime("%Y-%m-%d %H:%M") if t else None

    def test_aoe(self):
        self.assertEqual(self.ts({"date": "December 13", "deadline_text": "December 13 at 11:59 PM Anywhere on Earth (AoE)"}), "2026-12-14 06:59")

    def test_utc(self):
        self.assertEqual(self.ts({"date": "2026-11-11", "time": "16:59", "zone": "UTC", "deadline_text": "x"}), "2026-11-11 11:59")

    def test_jst(self):
        self.assertEqual(self.ts({"date": "2026-11-11", "time": "23:59", "zone": "JST", "deadline_text": "x"}), "2026-11-11 09:59")

    def test_pt_dst_aware(self):
        self.assertEqual(self.ts({"date": "2026-11-12", "time": "12:00", "zone": "PT", "deadline_text": "x"}), "2026-11-12 15:00")

    def test_utc_offset(self):
        self.assertEqual(self.ts({"date": "2026-11-11", "time": "23:59", "zone": "UTC+8", "deadline_text": "x"}), "2026-11-11 10:59")

    def test_unknown_zone_is_none(self):
        self.assertIsNone(self.ts({"date": "2026-11-11", "time": "10:00", "zone": "Mars", "deadline_text": "x"}))


class TestCompare(unittest.TestCase):
    def test_moved_earlier(self):
        r = v.compare(ROW["deadline"], {"date": "2026-11-11", "time": "16:59", "zone": "UTC", "deadline_text": "Deadline 2026/11/11 16:59"}, None, True)
        self.assertEqual(r["verdict"], "MOVED")
        self.assertEqual(r["minutes"], -360)

    def test_unchanged(self):
        r = v.compare(ROW["deadline"], {"date": "2026-11-11", "time": "22:59", "zone": "UTC", "deadline_text": "q"}, None, True)
        self.assertEqual(r["verdict"], "UNCHANGED")

    def test_date_only_matches(self):
        r = v.compare("Wed 2026-11-11", {"date": "November 11, 2026", "deadline_text": "Submission Deadline: November 11, 2026"}, None, True)
        self.assertEqual(r["verdict"], "UNCHANGED")

    def test_no_receipt_unverified(self):
        r = v.compare(ROW["deadline"], {"date": "2026-11-11", "time": "16:59", "zone": "UTC", "deadline_text": "q"}, None, False)
        self.assertEqual(r["verdict"], "UNVERIFIED")

    def test_quote_not_on_page_unverified(self):
        r = v.compare(ROW["deadline"], {"date": "2026-11-11", "time": "16:59", "zone": "UTC", "deadline_text": "made up"}, "real page text", True)
        self.assertEqual(r["verdict"], "UNVERIFIED")

    def test_null_date_unverified(self):
        self.assertEqual(v.compare(ROW["deadline"], {"date": None, "deadline_text": None}, None, True)["verdict"], "UNVERIFIED")

    def test_closed(self):
        r = v.compare(ROW["deadline"], {"closed": True, "closed_text": "Registration closed"}, "Registration closed on Sep 8", True)
        self.assertEqual(r["verdict"], "CLOSED")

    def test_closed_chrome_with_future_deadline_is_not_closed(self):
        import datetime as dt
        claim = {"closed": True, "closed_text": "The submission window has closed.", "date": "December 13",
                 "deadline_text": "Submissions close Sunday, December 13 at 11:59 PM Anywhere on Earth (AoE)."}
        page = "The submission window has closed. ... Submissions close Sunday, December 13 at 11:59 PM Anywhere on Earth (AoE)."
        r = v.compare("Mon 2026-11-30 6:59 AM", claim, page, True, now=dt.datetime(2026, 11, 10, tzinfo=dt.timezone.utc))
        self.assertEqual(r["verdict"], "MOVED")
        self.assertIn("page chrome", r["note"])

    def test_no_json(self):
        self.assertEqual(v.compare(ROW["deadline"], v.parse_claim("sorry I can't"), None, True)["verdict"], "UNVERIFIED")


class TestVerifyRow(unittest.TestCase):
    def test_declares_otari_tools(self):
        c = FakeClient('{"deadline_text":"Deadline 2026/11/11 16:59","date":"2026-11-11","time":"16:59","zone":"UTC","closed":false}', RECEIPT)
        r = v.verify_row(ROW, c, code_exec=True, search=True)
        self.assertEqual([t["type"] for t in c.tools], ["otari_web_fetch", "otari_web_search", "otari_code_execution"])
        self.assertEqual(r["verdict"], "MOVED")

    def test_failed_fetch_receipt_is_unverified(self):
        failed = [{"type": "web_fetch", "status": "failed", "url": ROW["link"], "error": {"tag": "url_invalid"}}]
        c = FakeClient('{"deadline_text":"q","date":"2026-11-11","time":"16:59","zone":"UTC"}', failed)
        self.assertEqual(v.verify_row(ROW, c)["verdict"], "UNVERIFIED")

    def test_gateway_down_is_unverified(self):
        self.assertEqual(v.verify_row(ROW, FakeClient("", ok=False))["verdict"], "UNVERIFIED")

    def test_no_link(self):
        self.assertEqual(v.verify_row(dict(ROW, link="—"), FakeClient(""))["verdict"], "UNVERIFIED")

    def test_open_rows_skip_closed(self):
        text = (ROOT / "examples" / "hackathon-deadlines.md").read_text()
        items = [r["item"] for r in v.open_rows(text)]
        self.assertNotIn("Catalog Preflight (parked)", items)


if __name__ == "__main__":
    unittest.main()
