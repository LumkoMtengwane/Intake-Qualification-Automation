"""Minimal Gmail and Sheets REST client using the OAuth refresh token."""
import base64
import os
import re
from email.message import EmailMessage
from html import unescape

from common import ApiError, http

GMAIL = "https://gmail.googleapis.com/gmail/v1/users/me"
SHEETS = "https://sheets.googleapis.com/v4/spreadsheets"


class Google:
    def __init__(self, retries=3, backoff=2):
        self.retries, self.backoff = retries, backoff
        self._token = None

    def _headers(self):
        if not self._token:
            resp = http(
                "POST", "https://oauth2.googleapis.com/token", retries=self.retries, backoff=self.backoff,
                data={
                    "client_id": os.environ["GOOGLE_CLIENT_ID"],
                    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
                    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
                    "grant_type": "refresh_token",
                },
            )
            self._token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {self._token}"}

    def _call(self, method, url, **kw):
        return http(method, url, retries=self.retries, backoff=self.backoff, headers=self._headers(), **kw).json()

    # ---------- Gmail ----------
    def list_messages(self, query, limit):
        data = self._call("GET", f"{GMAIL}/messages", params={"q": query, "maxResults": limit})
        return [m["id"] for m in data.get("messages", [])]

    def get_message(self, msg_id):
        msg = self._call("GET", f"{GMAIL}/messages/{msg_id}", params={"format": "full"})
        headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
        return {
            "id": msg_id,
            "from": headers.get("from", ""),
            "subject": headers.get("subject", ""),
            "date": headers.get("date", ""),
            "body": _extract_body(msg["payload"]),
        }

    def send_email(self, to, subject, body):
        em = EmailMessage()
        em["To"], em["Subject"] = to, subject
        em.set_content(body)
        raw = base64.urlsafe_b64encode(em.as_bytes()).decode()
        self._call("POST", f"{GMAIL}/messages/send", json={"raw": raw})

    # ---------- Sheets ----------
    def create_sheet(self, title, tab, header, hidden_tab, hidden_header, format_reqs):
        sheet = self._call("POST", SHEETS, json={"properties": {"title": title}, "sheets": [
            {"properties": {"title": tab, "sheetId": 0}},
            {"properties": {"title": hidden_tab, "sheetId": 1, "hidden": True}}]})
        sheet_id = sheet["spreadsheetId"]
        for name, head in ((tab, header), (hidden_tab, hidden_header)):
            self._call("PUT", f"{SHEETS}/{sheet_id}/values/{name}!A1", params={"valueInputOption": "RAW"}, json={"values": [head]})
        self._call("POST", f"{SHEETS}/{sheet_id}:batchUpdate", json={"requests": format_reqs})
        return sheet_id

    def read_rows(self, sheet_id, tab):
        return self._call("GET", f"{SHEETS}/{sheet_id}/values/{tab}!A:Z").get("values", [])

    def update_cell(self, sheet_id, a1_range, value):
        self._call("PUT", f"{SHEETS}/{sheet_id}/values/{a1_range}", params={"valueInputOption": "RAW"},
                   json={"values": [[value]]})

    def append_row(self, sheet_id, tab, row, gid):
        """Write into the next empty row. INSERT_ROWS would copy the header's style onto new rows and
        push the colour-rule ranges down, so OVERWRITE is used and the grid is grown when it runs out."""
        url, params = f"{SHEETS}/{sheet_id}/values/{tab}!A1:append", {"valueInputOption": "RAW", "insertDataOption": "OVERWRITE"}
        try:
            self._call("POST", url, params=params, json={"values": [row]})
        except ApiError as exc:
            if "400" not in str(exc):
                raise
            self._call("POST", f"{SHEETS}/{sheet_id}:batchUpdate", json={"requests": [
                {"appendDimension": {"sheetId": gid, "dimension": "ROWS", "length": 500}}]})
            self._call("POST", url, params=params, json={"values": [row]})

    @staticmethod
    def sheet_url(sheet_id):
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}"


def _decode(data):
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="replace")


def _extract_body(payload):
    """Prefer text/plain; fall back to stripped text/html."""
    plain, html = [], []

    def walk(part):
        mime, data = part.get("mimeType", ""), part.get("body", {}).get("data")
        if data and mime == "text/plain":
            plain.append(_decode(data))
        elif data and mime == "text/html":
            html.append(_decode(data))
        for sub in part.get("parts", []):
            walk(sub)

    walk(payload)
    if plain:
        return "\n".join(plain).strip()
    text = re.sub(r"<(script|style).*?</\1>", " ", "\n".join(html), flags=re.S | re.I)
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", text))).strip()
