# Workflow diagram

Renders on GitHub and in VS Code (Markdown preview with Mermaid support).

```mermaid
flowchart TD
    A[Scheduler runs every 15 min] --> B[Read Google Sheet:<br/>message IDs and content hashes]
    B -->|setup fails| X1[Failure email to owner<br/>+ stop]
    B --> C[Gmail: find emails sent to<br/>the +inquiries address]
    C --> D{Message ID already<br/>in the Sheet?}
    D -->|yes| S[Skip]
    D -->|no| E[Claude Haiku extracts fields,<br/>writes a summary and a draft reply]
    E -->|API error, retries with backoff| F{Still failing?}
    F -->|yes| G[Sheet row: Error<br/>+ failure email at end of run]
    F -->|no| H
    E --> H[Code works out missing data,<br/>status and priority]
    H --> I{Status}
    I -->|not an inquiry| J[Row: Spam<br/>no alert]
    I -->|same sender and text as before| K[Row: Duplicate<br/>no alert]
    I -->|key details missing| L[Row: Needs info<br/>+ email to owner and second recipient]
    I -->|complete| M[Row: New<br/>+ email to owner and second recipient]
    L --> N
    M --> N
    J --> N
    K --> N
    N[Housekeeping, plain code] --> O{Open leads waiting<br/>more than 48h, not yet nudged?}
    O -->|yes| P[One reminder email]
    O -->|no| Q
    P --> Q{Monday after 08:00 and<br/>no digest this week?}
    Q -->|yes| R[Weekly digest email]
    Q -->|no| T
    R --> T[Optional: rebuild dashboard/index.html]
```

## Notes
- Every row gets a reference ID: `JNR-YYYYMMDD-###`, and a priority (Hot, Warm or Cold) for open leads.
- Duplicates are caught twice: by Gmail message ID (re-runs) and by a hash of sender plus text (repeat sends).
- The AI only reads and writes text. It never contacts customers, and email text cannot change what the code does.
- Human step: the owner reads each alert, checks the draft reply, replies to the customer, then moves the Status on (Contacted, Quoted, Won or Lost). That is also what stops reminders.
