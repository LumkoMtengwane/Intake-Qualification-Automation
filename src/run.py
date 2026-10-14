"""Joinery inquiry intake. Run: python src/run.py [--dry-run] [--limit N]

Gmail (query in config.json) -> Claude extraction -> Google Sheet row -> owner email.
Safe to re-run: emails already in the sheet (by Gmail message ID) are skipped.
"""
import argparse
import hashlib
import os
import re
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from common import ApiError, load_config, load_env, load_state, require_env, save_state, setup_logging
from dashboard import build as build_dashboard
from extract import extract, missing_data, priority_for, status_for
from google_api import Google
from notify import housekeeping
from schema import COL, HEADER, INTERNAL_HEADER, INTERNAL_TAB, TAB
from sheet_format import format_requests


def pretty_date(raw):
    try:
        return parsedate_to_datetime(raw).astimezone().strftime("%Y-%m-%d %H:%M")  # machine's local time
    except (TypeError, ValueError):
        return raw


def content_hash(msg, sender_email):
    text = re.sub(r"\s+", " ", msg["body"].lower()).strip()[:2000]
    return hashlib.sha256(f"{(sender_email or '').lower()}|{text}".encode()).hexdigest()[:16]


def next_ref(refs, today):
    prefix = f"JNR-{today}-"
    nums = [int(r.split("-")[-1]) for r in refs if r.startswith(prefix)]
    return f"{prefix}{max(nums, default=0) + 1:03d}"


def alert_recipients(cfg):
    """Owner first, then anyone in notify_also, without duplicates. Failure alerts stay owner-only."""
    seen, out = set(), []
    for addr in [cfg["owner_email"], *cfg.get("notify_also", [])]:
        if addr and addr.lower() not in seen:
            seen.add(addr.lower())
            out.append(addr)
    return out


def owner_alert(ref, status, priority, item, missing, url):
    flag = "URGENT " if item["urgent"] else ""
    subject = f"[{status}] [{priority}] {flag}{ref}: {item['project_type'] or 'new inquiry'} in {item['location'] or 'location unknown'}"
    body = (
        f"{item['summary']}\n\n"
        f"Customer: {item['customer_name'] or '-'}\nEmail: {item['email'] or '-'}\nPhone: {item['phone'] or '-'}\n"
        f"Project: {item['project_type'] or '-'}\nLocation: {item['location'] or '-'}\n"
        f"Timeline: {item['timeline'] or '-'}\n\nDescription: {item['description'] or '-'}\n\n"
        f"Missing: {', '.join(missing) or 'nothing'}\nPriority: {priority}\n\n"
        f"Suggested reply (AI draft, check before sending):\n{item['draft_reply'] or '-'}\n\nSheet: {url}\n"
    )
    return subject, body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="extract and print only; no sheet writes or emails")
    ap.add_argument("--limit", type=int, help="max emails this run")
    ap.add_argument("--digest-now", action="store_true", help="send the weekly digest now (testing)")
    ap.add_argument("--dashboard", action="store_true", help="rebuild dashboard/index.html after the run")
    args = ap.parse_args()

    load_env()
    require_env("ANTHROPIC_API_KEY", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN")
    cfg, log = load_config(), setup_logging()
    g = Google(cfg["retries"], cfg["backoff_seconds"])
    failures, processed, tokens_in, tokens_out = [], 0, 0, 0

    try:
        state = load_state()
        sheet_id = os.environ.get("SHEET_ID") or state.get("sheet_id")
        if not sheet_id and not args.dry_run:
            sheet_id = g.create_sheet(cfg["sheet_title"], TAB, HEADER, INTERNAL_TAB, INTERNAL_HEADER, format_requests(HEADER))
            save_state({**state, "sheet_id": sheet_id})
            log.info("Created sheet %s", g.sheet_url(sheet_id))
        rows = g.read_rows(sheet_id, TAB)[1:] if sheet_id else []
        internal = g.read_rows(sheet_id, INTERNAL_TAB)[1:] if sheet_id else []
        # A ref deleted from the visible tab (e.g. an Error row) releases its email for a retry.
        visible = {r[0] for r in rows if r}
        live = [r for r in internal if r and r[0] in visible and len(r) >= 3]
        seen_ids = {r[1] for r in live}
        seen_hashes = {r[2]: r[0] for r in live if r[2]}
        refs = visible | {r[0] for r in internal if r}
        ids = [i for i in reversed(g.list_messages(cfg["gmail_query"], args.limit or cfg["max_emails_per_run"])) if i not in seen_ids]
        log.info("%d new emails to process", len(ids))
    except Exception as exc:  # setup failure: nothing processed, alert and stop
        log.error("Setup failed: %s", exc)
        _fail_alert(g, cfg, log, [f"Setup failed: {exc}"])
        return 1

    for msg_id in ids:
        try:
            msg = g.get_message(msg_id)
            item, t_in, t_out = extract(msg, cfg)
            tokens_in, tokens_out = tokens_in + t_in, tokens_out + t_out
            missing = missing_data(item)
            status = status_for(item, missing)
            digest = content_hash(msg, item["email"])
            description = item["description"]
            if digest in seen_hashes and status != "Spam":
                status, description = "Duplicate", f"Duplicate of {seen_hashes[digest]}. {description or ''}".strip()
            now = datetime.now(timezone.utc)
            ref = next_ref(refs, now.strftime("%Y%m%d"))
            priority = priority_for(item, missing, status)
            row = [ref, pretty_date(msg["date"]), status, priority, item["customer_name"], item["email"], item["phone"],
                   item["project_type"], item["location"], description, item["timeline"],
                   "Yes" if item["urgent"] else "", ", ".join(missing)]
            row = ["" if v is None else v for v in row]
            if args.dry_run:
                print(f"{ref} | {status} | {priority} | {item['project_type']} | {item['location']} | "
                      f"weeks: {item['timeline_weeks']} | missing: {missing}")
                print(f"    reply: {item['draft_reply']}")
            else:
                g.append_row(sheet_id, INTERNAL_TAB, [ref, msg_id, digest, now.isoformat(timespec="seconds"),
                                                      item["draft_reply"] or ""], gid=1)
                g.append_row(sheet_id, TAB, row, gid=0)
                if status in ("New", "Needs info"):
                    subject, body = owner_alert(ref, status, priority, item, missing, g.sheet_url(sheet_id))
                    g.send_email(", ".join(alert_recipients(cfg)), subject, body)
            refs.add(ref)
            seen_hashes.setdefault(digest, ref)
            processed += 1
            log.info("%s %s (%d in / %d out tokens)", ref, status, t_in, t_out)
        except Exception as exc:  # one bad email must not stop the rest
            log.error("Failed on message %s: %s", msg_id, exc)
            failures.append(f"{msg_id}: {exc}")
            if not args.dry_run:
                _error_row(g, sheet_id, refs, msg_id, str(exc), log)

    if not args.dry_run and sheet_id:
        try:
            housekeeping(g, cfg, log, sheet_id, alert_recipients(cfg), args.digest_now)
        except Exception as exc:  # nudges and digest are extras: report, but never block intake
            log.error("Housekeeping failed: %s", exc)
            failures.append(f"Reminder or digest step failed: {exc}")
        if args.dashboard:
            try:
                path, count = build_dashboard(g, cfg, sheet_id)
                log.info("Dashboard written: %s (%d inquiries)", path, count)
            except Exception as exc:
                log.error("Dashboard failed: %s", exc)
                failures.append(f"Dashboard build failed: {exc}")

    log.info("Done: %d processed, %d failed, %d in / %d out tokens", processed, len(failures), tokens_in, tokens_out)
    if failures and not args.dry_run:
        _fail_alert(g, cfg, log, failures)
    return 1 if failures else 0


def _error_row(g, sheet_id, refs, msg_id, error, log):
    """Record the failure in the sheet so the owner can handle it manually."""
    try:
        now = datetime.now(timezone.utc)
        ref = next_ref(refs, now.strftime("%Y%m%d"))
        row = [""] * len(HEADER)
        row[COL["Ref ID"]], row[COL["Status"]] = ref, "Error"
        row[COL["Description"]] = f"Processing failed, check this email manually. {error[:200]}"
        g.append_row(sheet_id, INTERNAL_TAB, [ref, msg_id, "", now.isoformat(timespec="seconds")], gid=1)
        g.append_row(sheet_id, TAB, row, gid=0)
        refs.add(ref)
    except Exception as exc:
        log.error("Could not write error row: %s", exc)


def _fail_alert(g, cfg, log, failures):
    try:
        g.send_email(cfg["owner_email"], f"[Intake FAILED] {len(failures)} problem(s)", "\n".join(failures) +
                     "\n\nManual fallback: open the inquiries mailbox and handle these emails by hand. Fix, then re-run.")
    except Exception as exc:
        log.error("Failure alert could not be sent: %s", exc)


if __name__ == "__main__":
    sys.exit(main())
