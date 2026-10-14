"""Housekeeping after each run: stale-lead nudge and weekly digest. Plain code, no AI calls."""
from collections import Counter
from datetime import datetime, timedelta

from common import load_state, save_state
from schema import ICOL, INTERNAL_TAB, OPEN_STATUSES, TAB, cell

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def processed_at(irow):
    try:
        return datetime.fromisoformat(cell(irow, "Processed at", ICOL))
    except ValueError:
        return None


def find_stale(rows, internal, now, stale_hours, skip_nudged=True):
    """Open leads processed more than stale_hours ago. Each: {ref, row, hours, internal_row}."""
    by_ref = {r[0]: r for r in rows if r}
    out = []
    for n, irow in enumerate(internal, start=2):  # row 1 of _internal is the header
        row = by_ref.get(irow[0]) if irow else None
        when = processed_at(irow) if row else None
        if when is None or cell(row, "Status") not in OPEN_STATUSES:
            continue
        if skip_nudged and cell(irow, "Nudged at", ICOL):
            continue
        hours = (now - when).total_seconds() / 3600
        if hours >= stale_hours:
            out.append({"ref": irow[0], "row": row, "hours": hours, "internal_row": n})
    return out


def digest_due(now, state, day_name, hour):
    iso = now.isocalendar()
    return (now.weekday() == DAYS.index(day_name.lower()) and now.hour >= hour
            and state.get("last_digest_week") != f"{iso[0]}-W{iso[1]:02d}")


def _age(hours):
    return f"{int(hours // 24)} days" if hours >= 48 else f"{int(hours)}h"


def lead_line(row, hours=None):
    wait = f", waiting {_age(hours)}" if hours is not None else ""
    place = f"in {cell(row, 'Location')}" if cell(row, "Location") else "(location not stated)"
    return (f"- {row[0]} [{cell(row, 'Priority') or '-'}] {cell(row, 'Name') or 'Unknown'}: "
            f"{cell(row, 'Project type') or 'project not stated'} {place} ({cell(row, 'Status')}{wait})")


def nudge_email(stale, stale_hours, url):
    stale = sorted(stale, key=lambda s: -s["hours"])
    subject = f"[Reminder] {len(stale)} lead{'s' if len(stale) != 1 else ''} waiting more than {stale_hours}h"
    body = ("These inquiries are still New or Needs info. Reply to the customer, then change the Status in the Sheet "
            "(Contacted, Quoted, Won or Lost) so they stop appearing here.\n\n"
            + "\n".join(lead_line(s["row"], s["hours"]) for s in stale) + f"\n\nSheet: {url}\n")
    return subject, body


def digest_email(rows, internal, now, stale_hours, url):
    week_ago = now - timedelta(days=7)
    by_ref = {r[0]: r for r in rows if r}
    week_rows = [by_ref[i[0]] for i in internal if i and i[0] in by_ref and (processed_at(i) or week_ago) > week_ago]
    counts = Counter(cell(r, "Status") for r in week_rows)
    open_rows = [r for r in rows if r and cell(r, "Status") in OPEN_STATUSES]
    hot = [r for r in open_rows if cell(r, "Priority") == "Hot"]
    stale = sorted(find_stale(rows, internal, now, stale_hours, skip_nudged=False), key=lambda s: -s["hours"])
    subject = f"[Weekly digest] {len(week_rows)} inquiries this week, {len(open_rows)} still open"
    lines = [f"Received this week: {len(week_rows)}"]
    lines += [f"  {s}: {counts[s]}" for s in ("New", "Needs info", "Duplicate", "Spam", "Error") if counts[s]]
    lines += ["", f"Still open (New or Needs info): {len(open_rows)}", f"Hot and still open: {len(hot)}"]
    lines += [lead_line(r) for r in hot]
    lines += ["", f"Waiting more than {stale_hours}h: {len(stale)}"]
    lines += [lead_line(s["row"], s["hours"]) for s in stale]
    return subject, "\n".join(lines) + f"\n\nSheet: {url}\n"


def housekeeping(g, cfg, log, sheet_id, recipients, force_digest=False):
    """Send one nudge email for newly stale leads and, when due, the weekly digest."""
    rows = g.read_rows(sheet_id, TAB)[1:]
    internal = g.read_rows(sheet_id, INTERNAL_TAB)[1:]
    now = datetime.now().astimezone()
    url, to, hours = g.sheet_url(sheet_id), ", ".join(recipients), cfg["stale_hours"]

    stale = find_stale(rows, internal, now, hours)
    if stale:
        g.send_email(to, *nudge_email(stale, hours, url))
        for s in stale:
            g.update_cell(sheet_id, f"{INTERNAL_TAB}!F{s['internal_row']}", now.isoformat(timespec="seconds"))
        log.info("Nudge sent for %d stale lead(s)", len(stale))

    state = load_state()
    if force_digest or digest_due(now, state, cfg["digest_day"], cfg["digest_hour"]):
        g.send_email(to, *digest_email(rows, internal, now, hours, url))
        if not force_digest:
            iso = now.isocalendar()
            save_state({**state, "last_digest_week": f"{iso[0]}-W{iso[1]:02d}"})
        log.info("Weekly digest sent")
