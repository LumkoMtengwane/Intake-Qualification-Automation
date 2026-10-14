# Standard operating procedure: handling inquiries

For the business owner. No technical knowledge needed.

## What the system does
Every customer email sent to your inquiries address is read automatically. It is added to a Google Sheet with a reference number, and you get an email summary when it needs your attention.

## Daily routine (5 minutes)
1. Check your inbox for alert emails. The subject looks like `[New] [Hot] JNR-20261014-003: fitted wardrobes in Bellville`. Alerts go to the owner and to the second person on the notification list.
2. Open the alert. It has the customer's details, a one-line summary and a **suggested reply**.
3. Read the suggested reply, change anything you want, and send it yourself. It is an AI draft. The system never contacts customers.
4. In the Sheet, change the **Status** to show where the lead is now (see below). This is what stops reminders.

## Statuses
Set by the system:

| Status | Meaning | What you do |
|---|---|---|
| New | All key details found | Reply or arrange a site visit |
| Needs info | Something important is missing (see the "Missing data" column) | Send the suggested reply asking for the missing details |
| Duplicate | Same customer sent the same message again | Nothing. The row names the original reference |
| Spam | Not a real inquiry | Nothing. Glance over these now and then in case a real one was misjudged |
| Error | The system could not process this email | Read the email in your inbox and handle it by hand (see below) |

Set by you, by typing in the Status cell: **Contacted**, **Quoted**, **Won**, **Lost**. Type them exactly as written so the colours and reminders work.

## Priority
Each open lead gets a priority, so you know who to call first.

| Priority | Meaning |
|---|---|
| Hot | Urgent, or the customer wants it within about 4 weeks |
| Warm | Complete inquiry with a relaxed timeline, or only one detail missing |
| Cold | Far-off timeline (over about 12 weeks), or several details missing |

A message marked **Urgent** says "Yes" in the Urgent column and has `URGENT` in the alert subject.

## Reminders and the weekly digest
- **Reminder:** if a lead is still New or Needs info after 48 hours, you get one reminder email listing it. It is sent once per lead. Change the Status to Contacted (or later) and it drops out of the list.
- **Weekly digest:** every Monday morning you get a summary: inquiries received, how many are still open, the Hot leads, and the leads that have been waiting too long.

## Dashboard (optional)
Open `dashboard/index.html` for a visual overview: open leads, charts, a searchable list, and each lead's details and suggested reply. It is rebuilt when `python src/run.py --dashboard` runs.

## Weekly check (2 minutes)
Make sure an inquiry sent to the address recently has appeared in the Sheet. If nothing has appeared for several days while you know emails came in, see "Nothing is arriving" below.

## When something goes wrong
| What you see | Likely cause | Fix |
|---|---|---|
| Email with subject `[Intake FAILED]` | One or more emails could not be processed | Handle those emails by hand from the inbox. Tell your support contact if it repeats |
| A row with status Error | The AI service or Sheet had a problem for that email | Handle by hand. To retry, delete the Error row and the system picks the email up on the next run |
| Nothing is arriving in the Sheet | Google sign-in has expired. In the current demo set-up this happens about every 7 days and no alert is sent | Ask your support contact to re-run the sign-in step (about 1 minute) |
| Same inquiry appears twice as New | The customer wrote two different messages | Treat as one customer. Update one row, mark the other Duplicate |
| Reminders keep arriving for a lead you dealt with | Its Status was not updated | Change the Status to Contacted, Quoted, Won or Lost |
| Suggested reply looks wrong | AI drafts can misread an email | Write your own reply. Never send a draft without reading it |

## Manual fallback
If the system is down, inquiries are never lost. They stay in your inbox. Work from the inbox until it is fixed.

## Privacy
Inquiry text (names, phone numbers, addresses) is sent to Anthropic's AI service to be read, and stored in your Google Sheet. Only share the Sheet with people who need it. Customers should be told this in your privacy policy (POPIA / GDPR).
