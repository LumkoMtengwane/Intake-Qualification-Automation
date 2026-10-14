"""Build dashboard/index.html from the Sheet. Run: python src/dashboard.py [--no-mask]

One self-contained HTML file (data embedded, no external libraries), safe to open from disk.
Contacts are masked by default so the page can be shown or published without exposing real people.
"""
import argparse
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from common import ROOT, load_config, load_env, load_state, require_env
from google_api import Google
from notify import processed_at
from schema import COL, ICOL, INTERNAL_TAB, TAB, cell

TEMPLATE = Path(__file__).with_name("dashboard_template.html")
OUT = ROOT / "dashboard" / "index.html"


def mask_email(value):
    if "@" not in value:
        return value
    name, _, domain = value.partition("@")
    return f"{name[:1]}•••@{domain}"


def mask_phone(value):
    digits = re.sub(r"\D", "", value)
    return f"••• ••• ••{digits[-2:]}" if len(digits) >= 2 else value


def build_leads(rows, internal, now, stale_hours, mask=True):
    """Join visible rows with their hidden details and return plain dicts for the page."""
    extra = {i[0]: i for i in internal if i}
    leads = []
    for r in rows:
        if not r or not r[0]:
            continue
        irow = extra.get(r[0], [])
        when = processed_at(irow) if irow else None
        email, phone = cell(r, "Email"), cell(r, "Phone")
        leads.append({
            "ref": r[0], "received": cell(r, "Received"), "status": cell(r, "Status"), "priority": cell(r, "Priority"),
            "name": cell(r, "Name"), "email": mask_email(email) if mask else email,
            "phone": mask_phone(phone) if mask else phone, "project": cell(r, "Project type"),
            "location": cell(r, "Location"), "description": cell(r, "Description"), "timeline": cell(r, "Timeline"),
            "urgent": cell(r, "Urgent") == "Yes", "missing": cell(r, "Missing data"),
            "draftReply": cell(irow, "Draft reply", ICOL) if irow else "",
            "waitingHours": round((now - when).total_seconds() / 3600, 1) if when else None,
        })
    leads.sort(key=lambda lead: lead["received"], reverse=True)
    return {"generatedAt": now.strftime("%Y-%m-%d %H:%M"), "staleHours": stale_hours, "masked": mask, "leads": leads}


def render(data, business_name, template=None):
    template = template or TEMPLATE.read_text(encoding="utf-8")
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")  # keep </script> out of the data
    return template.replace("/*__DATA__*/null", blob).replace("__BUSINESS__", html.escape(business_name))


def build(g, cfg, sheet_id, mask=None):
    mask = cfg.get("dashboard_mask_contacts", True) if mask is None else mask
    rows = g.read_rows(sheet_id, TAB)[1:]
    internal = g.read_rows(sheet_id, INTERNAL_TAB)[1:]
    data = build_leads(rows, internal, datetime.now().astimezone(), cfg["stale_hours"], mask)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(render(data, cfg["business_name"]), encoding="utf-8")
    return OUT, len(data["leads"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-mask", action="store_true", help="show real emails and phones (private use only)")
    args = ap.parse_args()
    load_env()
    require_env("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN")
    cfg = load_config()
    sheet_id = load_state().get("sheet_id")
    if not sheet_id:
        sys.exit("No sheet yet. Run python src/run.py first.")
    path, count = build(Google(cfg["retries"], cfg["backoff_seconds"]), cfg, sheet_id, mask=not args.no_mask)
    print(f"Wrote {path} ({count} inquiries, contacts {'visible' if args.no_mask else 'masked'})")
