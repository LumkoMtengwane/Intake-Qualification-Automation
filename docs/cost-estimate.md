# Cost estimate

Measured on the live test run of 14 fictional inquiries (2026-10-14), with the draft reply and priority features on.

## Per inquiry (Claude Haiku 5.5)
- Average: about 750 input tokens and 340 output tokens per email (the output includes the AI draft reply).
- Price: $0.10 per million input tokens, $0.50 per million output tokens (Anthropic list price, prompts up to 100K tokens; checked 2026-10-14).
- Cost: about **$0.00024 per inquiry**, roughly **R0.004** (assumes about R18 per US dollar, check the current rate).
- Hidden reasoning is switched off for extraction. It had been using about as many tokens as the answer.

## Per month (API only)
| Inquiries per month | USD | Rand (approx.) |
|---|---|---|
| 50 | $0.012 | R0.22 |
| 200 | $0.049 | R0.88 |
| 500 | $0.122 | R2.20 |

Runs that find no new email make no AI calls. Reminders, the weekly digest and the dashboard are plain code with no AI cost, so frequent polling (for example every 15 minutes) adds nothing.

## Everything else
| Item | Cost |
|---|---|
| Gmail and Google Sheets APIs | Free (within Google's standard quotas) |
| Hosting | Free: Windows Task Scheduler, cron, or GitHub Actions free tier |
| Alert, reminder and digest emails | Free (sent through Gmail, well inside the daily send limit) |
| Dashboard | Free: one static HTML file. Optional free hosting on GitHub Pages (demo data only) |
| **Total** | **Under R3 per month at 500 inquiries** |

## Where the number could change
- Longer emails raise input tokens. Bodies are capped at 4,000 characters.
- Anthropic prices can change. Re-check before quoting a client.
- If Haiku starts missing fields on a client's real emails, moving to Sonnet 5.5 ($2 / $10 per million tokens) would cost about 20 times more, roughly R18 per 200 inquiries. Still small.

## Not included
- The builder's time.
- Setup help or monthly support, if sold separately.
- Cost of a published Google app, a domain, or a client's own Workspace licences.
