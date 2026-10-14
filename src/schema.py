"""Sheet layout shared by run.py, notify.py and dashboard.py."""

TAB = "Inquiries"
HEADER = ["Ref ID", "Received", "Status", "Priority", "Name", "Email", "Phone", "Project type", "Location",
          "Description", "Timeline", "Urgent", "Missing data"]
COL = {name: i for i, name in enumerate(HEADER)}

# Hidden tab: dedupe keys, processing time, AI draft reply and nudge marker, kept out of the owner's view.
INTERNAL_TAB = "_internal"
INTERNAL_HEADER = ["Ref ID", "Gmail message ID", "Content hash", "Processed at", "Draft reply", "Nudged at"]
ICOL = {name: i for i, name in enumerate(INTERNAL_HEADER)}

# Leads the owner has not acted on yet. The owner moves a lead on by changing Status by hand
# (Contacted, Quoted, Won, Lost).
OPEN_STATUSES = ("New", "Needs info")


def cell(row, name, cols=COL):
    """Value of a named column; Sheets trims trailing empty cells, so short rows are normal."""
    i = cols[name]
    return row[i] if i < len(row) else ""
