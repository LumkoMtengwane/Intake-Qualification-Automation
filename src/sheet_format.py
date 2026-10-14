"""Sheet look: header style, column widths, wrapped text, frozen header, filter, status row colours."""

WIDTHS = {"Ref ID": 140, "Received": 130, "Status": 100, "Priority": 90, "Name": 140, "Email": 210, "Phone": 120,
          "Project type": 160, "Location": 160, "Description": 380, "Timeline": 140, "Urgent": 70, "Missing data": 180}
STATUS_COLOURS = {"New": "#d9ead3", "Needs info": "#fff2cc", "Duplicate": "#cfe2f3", "Spam": "#d9d9d9", "Error": "#ea9999",
                  # Set by the owner by hand as a lead moves on.
                  "Contacted": "#d0e0e3", "Quoted": "#fce5cd", "Won": "#93c47d", "Lost": "#b7b7b7"}
HEADER_BG = "#1f3a5f"


def _rgb(hex_code):
    h = hex_code.lstrip("#")
    return {"red": int(h[0:2], 16) / 255, "green": int(h[2:4], 16) / 255, "blue": int(h[4:6], 16) / 255}


def format_requests(header, sheet_id=0):
    cols = len(header)
    grid = {"sheetId": sheet_id, "startColumnIndex": 0, "endColumnIndex": cols}
    reqs = [
        # Body: wrap text and align to the top so long descriptions are fully visible.
        {"repeatCell": {"range": {**grid, "startRowIndex": 1},
                        "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP", "verticalAlignment": "TOP"}},
                        "fields": "userEnteredFormat(wrapStrategy,verticalAlignment)"}},
        # Header row.
        {"repeatCell": {"range": {**grid, "startRowIndex": 0, "endRowIndex": 1},
                        "cell": {"userEnteredFormat": {"backgroundColor": _rgb(HEADER_BG), "wrapStrategy": "WRAP",
                                                       "verticalAlignment": "MIDDLE",
                                                       "textFormat": {"bold": True, "foregroundColor": _rgb("#ffffff")}}},
                        "fields": "userEnteredFormat(backgroundColor,wrapStrategy,verticalAlignment,textFormat)"}},
        {"updateSheetProperties": {"properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}},
                                   "fields": "gridProperties.frozenRowCount"}},
        {"setBasicFilter": {"filter": {"range": {**grid, "startRowIndex": 0}}}},
    ]
    for i, name in enumerate(header):
        reqs.append({"updateDimensionProperties": {
            "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1},
            "properties": {"pixelSize": WIDTHS.get(name, 140)}, "fields": "pixelSize"}})
    status_col = chr(ord("A") + header.index("Status"))
    for status, colour in STATUS_COLOURS.items():
        reqs.append({"addConditionalFormatRule": {"index": 0, "rule": {
            "ranges": [{**grid, "startRowIndex": 1}],
            "booleanRule": {"condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": f'=${status_col}2="{status}"'}]},
                            "format": {"backgroundColor": _rgb(colour)}}}}})
    urgent_col = header.index("Urgent")
    reqs.append({"addConditionalFormatRule": {"index": 0, "rule": {
        "ranges": [{"sheetId": sheet_id, "startRowIndex": 1, "startColumnIndex": urgent_col, "endColumnIndex": urgent_col + 1}],
        "booleanRule": {"condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": "Yes"}]},
                        "format": {"textFormat": {"bold": True, "foregroundColor": _rgb("#cc0000")}}}}}})
    prio_col = header.index("Priority")
    prio_rng = [{"sheetId": sheet_id, "startRowIndex": 1, "startColumnIndex": prio_col, "endColumnIndex": prio_col + 1}]
    for label, colour in (("Hot", "#cc0000"), ("Warm", "#b45f06"), ("Cold", "#666666")):
        reqs.append({"addConditionalFormatRule": {"index": 0, "rule": {"ranges": prio_rng, "booleanRule": {
            "condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": label}]},
            "format": {"textFormat": {"bold": True, "foregroundColor": _rgb(colour)}}}}}})
    return reqs
