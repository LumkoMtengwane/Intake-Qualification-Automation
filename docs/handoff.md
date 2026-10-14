# Handoff document

Technical guide for whoever runs or extends this system.

## What was built
A Python script (`src/run.py`) that turns customer inquiry emails into structured Google Sheet rows with a reference ID, status and priority. It emails the owner (and a second recipient) with a summary and an AI draft reply, reminds the owner about leads left waiting, sends a weekly digest, and can build a static dashboard. Safe to re-run. Tested on fictional inquiries plus a deliberate failure.

## Files
| File | Purpose |
|---|---|
| `src/run.py` | Main script: fetch, extract, write, alert, error handling |
| `src/extract.py` | Claude prompt, response parsing, missing-data, status and priority rules |
| `src/notify.py` | Stale-lead reminders and the weekly digest (plain code, no AI) |
| `src/dashboard.py`, `src/dashboard_template.html` | Builds `dashboard/index.html` (one offline file, contacts masked) |
| `src/schema.py` | Sheet columns shared by the other modules |
| `src/sheet_format.py` | Sheet look: header, widths, status colours |
| `src/google_api.py` | Gmail and Sheets calls using the OAuth refresh token |
| `src/common.py` | Config, logging, HTTP retries with backoff |
| `config.example.json` | Template for the per-business settings. Copy to `config.json` (git-ignored) |
| `scripts/google_auth.py` | One-off Google sign-in helper. Writes `GOOGLE_REFRESH_TOKEN` into `.env` |
| `requirements.txt` | Python dependencies |
| `.env` | Secrets (never commit). Names listed in `.env.example` |
| `state.json` | Created on first run, holds the Sheet ID (not committed) |
| `logs/intake.log` | Run log with token counts |
| `tests/` | Offline unit tests, 10 sample inquiries, and a script to send them |

## Setup on a new machine
1. Install Python 3 and `pip install -r requirements.txt`.
2. Copy `.env.example` to `.env` and fill in `ANTHROPIC_API_KEY`, `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`. Then run `python scripts/google_auth.py` to sign in and save `GOOGLE_REFRESH_TOKEN` (Google Cloud setup steps are in the README).
3. Copy `config.example.json` to `config.json` and edit it (see below).
4. `python src/run.py --dry-run` to check extraction without writing anything.
5. `python src/run.py` for the first live run. It creates the Sheet and saves its ID in `state.json`.

## Config options (`config.json`)
| Key | Meaning |
|---|---|
| `business_name` | Label only |
| `owner_email` | Receives alerts and failure emails (can be overridden with `OWNER_EMAIL` in `.env`) |
| `notify_also` | List of extra addresses that get the same New and Needs info alerts, reminders and digest. Failure emails stay owner-only |
| `inquiry_address` | The `+inquiries` alias customers write to. Used by `tests/send_samples.py` |
| `stale_hours` | Hours an open lead can wait before the one-off reminder (default 48) |
| `digest_day`, `digest_hour` | When the weekly digest goes out (default Monday, from 08:00 local time) |
| `dashboard_mask_contacts` | `true` (default) masks emails and phones in the dashboard. Keep it on for anything public |
| `gmail_query` | Which emails count as inquiries. Default: sent to the `+inquiries` address in the last 30 days |
| `max_emails_per_run` | Safety cap per run |
| `sheet_title` | Name of the Sheet created on first run |
| `model` | Claude model. Default Haiku 5.5. Use Sonnet 5.5 only if extraction quality is poor |
| `max_output_tokens`, `max_body_chars` | Cost caps |
| `retries`, `backoff_seconds` | Retry behaviour for network and API errors |

## Running on a schedule
- **Windows Task Scheduler:** create a task that runs `python C:\path\to\project\src\run.py` every 15 minutes. Set "Start in" to the project folder.
- **Linux/macOS:** `*/15 * * * * cd /path/to/project && python src/run.py`
- **GitHub Actions** (free tier) also works: store secrets as repository secrets, but the Sheet ID in `state.json` must then be set via a `SHEET_ID` secret or committed config.

A non-zero exit code means at least one email failed. Exit code 1 is also used for setup failures.

## Command line options
| Command | What it does |
|---|---|
| `python src/run.py --dry-run` | Extract and print only. No sheet writes, no emails |
| `python src/run.py --dashboard` | Run, then rebuild `dashboard/index.html` |
| `python src/run.py --digest-now` | Send the weekly digest now (testing) |
| `python src/dashboard.py [--no-mask]` | Rebuild the dashboard only. `--no-mask` shows real contacts, private use only |

## Dashboard
`dashboard/index.html` is one self-contained file with the data embedded and no external libraries, so it works offline and from disk. It is generated, not committed. If you publish it (for example on GitHub Pages), publish only a masked build made from fictional data.

## How to reuse for another business
1. Copy the project folder, give it a new name.
2. Copy `config.example.json` to `config.json` and change owner, notification list, inquiry address, Gmail query and sheet title.
3. Change the trade wording in `SYSTEM` in `src/extract.py` (for example plumbing instead of joinery). Keep the JSON keys the same.
4. Create a new OAuth sign-in for that client's Google account, or add the client as a user.
5. Run the 10-sample test again with samples written for that trade.

## Design decisions
- **No Gmail labelling.** The Google sign-in only allows reading and sending mail, so processed emails are tracked by Gmail message ID in a hidden `_internal` tab of the Sheet instead (deleting an Error row from the visible tab releases that email for a retry). Least privilege.
- **Missing data, status and priority are calculated by code, not the AI**, so they are consistent. The AI supplies only extracted fields, an urgency flag and a weeks-until-needed estimate.
- **The AI never takes actions.** It returns text and data only. Email text is treated as untrusted (tested with a prompt-injection email). Draft replies are shown to the owner and never sent automatically. The prompt bans prices and promised dates.
- **Hidden reasoning is switched off** for extraction (`thinking: disabled`). It added cost and sometimes used up the token cap before the answer.
- **The owner moves leads on by typing a Status** (Contacted, Quoted, Won, Lost). Reminders only look at New and Needs info.
- **Errors are written to the Sheet** so nothing disappears silently, and the owner gets one failure email per run.

## Known limitations
1. **Google sign-in expires every 7 days while the Google app is in Testing mode.** Symptom: token refresh fails with `invalid_grant`, the run stops, and no alert is sent (the alert uses the same Google login). Fixes: publish the Google app (needs a homepage and privacy policy), use the client's Google Workspace with an internal app, or add an alert outside Google (Slack or a heartbeat monitor). The current build only has a weekly manual check in the SOP.
2. Replies to customers are not automated, by design.
3. One run at a time. Do not schedule overlapping runs.
   The weekly-digest marker (`last_digest_week`) lives in the local `state.json`. On a machine without a persistent disk (for example GitHub Actions) it is lost, and the digest can repeat on every Monday run after 08:00.
   Reminders rely on the owner updating Status by hand.
4. A failed email is not retried automatically. Delete its Error row to retry.
5. Attachments and images are ignored.
6. Tested only on short English and one Afrikaans sample.
7. Real client data has not been used. Check Anthropic's terms and POPIA/GDPR obligations first.

## Credentials to rotate when handing over
Anthropic API key, Google client secret and refresh token. Use the client's own accounts for production.
