# Google Sheets Integration Setup

This guide explains how to set up Google Sheets integration for the NYC Event Automation system.

## Overview

Google Sheets integration allows you to:
- Store all scraped events in a spreadsheet
- Mark events as selected by the photographer
- Track which events have had outreach emails sent
- Generate summary statistics
- Share event data with team members

## Setup Options

### Option 1: Service Account (Recommended for Automation)

Best for automated workflows and GitHub Actions.

1. **Create a Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project or select existing
   - Enable Google Sheets API

2. **Create Service Account**
   - Go to IAM & Admin → Service Accounts
   - Click "Create Service Account"
   - Give it a name (e.g., "nyc-event-automation")
   - Grant role: "Editor"
   - Create and download JSON key

3. **Run Setup Script**
   ```bash
   python setup_sheets.py
   ```
   - Choose option 1 (Service Account)
   - Provide path to downloaded JSON key
   - Follow prompts to create spreadsheet

4. **Share Spreadsheet**
   - Open the created spreadsheet
   - Share with the service account email (found in JSON file)
   - Grant "Editor" permissions

### Option 2: OAuth2 (Use Existing Gmail Credentials)

Simpler setup using your existing Gmail authentication.

1. **Ensure Gmail Setup Complete**
   ```bash
   python setup_gmail.py --gmail-api
   ```

2. **Run Sheets Setup**
   ```bash
   python setup_sheets.py
   ```
   - Choose option 2 (OAuth2)
   - May require re-authentication to add Sheets scope

## Usage

### Command Line

```bash
# Scrape and sync to sheets
python main.py scrape --sheets

# Sync existing data to sheets
python sync_to_sheets.py

# Sync specific file
python sync_to_sheets.py --file data/events_20250715.json

# Get sheet URL
python sync_to_sheets.py --url

# Mark events as selected
python sync_to_sheets.py --update-selected event_123 event_456

# Mark outreach as sent
python sync_to_sheets.py --update-outreach event_123 event_456
```

### In Code

```python
from data_store import GoogleSheetsManager, EventCollection

# Initialize manager
manager = GoogleSheetsManager()

# Sync events
events = EventCollection()
# ... add events ...
stats = manager.sync_events(events)

# Get selected events
selected = manager.storage.get_selected_events()

# Update status
manager.storage.mark_events_selected(['event_123', 'event_456'])
manager.storage.mark_outreach_sent(['event_123'])
```

## Spreadsheet Structure

The spreadsheet contains two sheets:

### Events Sheet
| Column | Description |
|--------|-------------|
| Event ID | Unique identifier |
| Name | Event name |
| Date | Event date/time |
| Location | Event location |
| Source | Where event was scraped from |
| Source URL | Original event URL |
| Contact Email | Organizer email (if found) |
| Description | Event description |
| Scraped At | When event was found |
| Status | Current status (New, Selected, etc.) |
| Selected | Mark "Yes" to select for outreach |
| Outreach Sent | Timestamp when outreach sent |

### Summary Sheet
- Total events count
- Selected events count
- Outreach sent count
- Events by source breakdown
- Last updated timestamp

## Manual Workflow

1. **Review Events in Sheet**
   - Open Google Sheet
   - Review new events
   - Mark interesting ones as "Yes" in Selected column

2. **Process Selections**
   ```bash
   # Sync selections from sheet
   python sync_to_sheets.py
   
   # Send outreach to selected events
   python main.py send-outreach --send
   ```

## GitHub Actions Integration

Add to your workflow:

```yaml
- name: Sync to Google Sheets
  env:
    GOOGLE_SHEETS_ID: ${{ secrets.GOOGLE_SHEETS_ID }}
    GOOGLE_SHEETS_CREDENTIALS: ${{ secrets.GOOGLE_SHEETS_CREDENTIALS }}
  run: |
    echo "$GOOGLE_SHEETS_CREDENTIALS" > sheets_credentials.json
    python main.py scrape --sheets
```

## Environment Variables

```bash
# Required
GOOGLE_SHEETS_ID=your-spreadsheet-id

# For service account
GOOGLE_SHEETS_CREDENTIALS=sheets_credentials.json

# Or use existing OAuth
# (uses token.json from Gmail setup)
```

## Troubleshooting

### "Spreadsheet not found"
- Ensure spreadsheet is shared with service account email
- Check GOOGLE_SHEETS_ID is correct

### "Permission denied"
- Service account needs Editor access
- For OAuth, re-run setup_gmail.py with Sheets scope

### "Credentials not found"
- Run setup_sheets.py first
- Ensure sheets_credentials.json exists

### Rate Limits
- Google Sheets API: 100 requests per 100 seconds
- Batch operations when possible

## Security Notes

- Never commit credentials files
- Add to .gitignore:
  - `sheets_credentials.json`
  - `token.json`
- Use GitHub Secrets for automation
- Limit spreadsheet sharing to necessary users

## Advanced Features

### Custom Views
Create filtered views in Google Sheets:
- Upcoming events only
- Events by source
- Selected but not sent
- Events needing contact info

### Formulas
Add helpful formulas:
- Days until event: `=DAYS(C2, TODAY())`
- Missing contact: `=IF(G2="", "NEEDS EMAIL", "OK")`
- Selection rate: `=COUNTIF(K:K, "Yes")/COUNTA(A:A)`

### Conditional Formatting
- Highlight events happening soon
- Color code by source
- Mark missing contact info
- Show sent outreach in green