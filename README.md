# NYC Event Lead Scraper & Outreach Automator

Automated system for discovering NYC photography opportunities and sending outreach emails to event organizers.

## Overview

This system automatically:
1. **Scrapes** event listings from multiple NYC event websites daily
2. **Sends** a digest email to the photographer with new events
3. **Monitors** email replies to identify selected events
4. **Sends** personalized outreach emails to event organizers
5. **Syncs** all data with Google Sheets for easy review

## Automated Workflow

### 🕐 Daily Schedule (GitHub Actions)

#### 1. Main Workflow - Daily at 9 AM EST
**File**: `.github/workflows/cron.yml`
- Scrapes events from all sources
- Saves to JSON/CSV files
- Syncs with Google Sheets (optional)
- Sends digest email to photographer
- Runs in under 15 minutes

#### 2. Reply Monitor - Every Hour
**File**: `.github/workflows/check-replies.yml`
- Checks for photographer's email replies
- Parses event selections (e.g., "1, 3, 5")
- Sends outreach emails to selected events
- Updates Google Sheets status

#### 3. Manual Test Workflow
**File**: `.github/workflows/test.yml`
- Trigger manually from GitHub Actions tab
- Test individual commands
- Run in test mode without sending emails

## Manual Usage

### Setup Commands

```bash
# Initial setup
pip install -r requirements.txt

# Gmail authentication
python setup_gmail_with_sheets.py

# Google Sheets setup (optional)
python setup_sheets.py
```

### Core Commands

#### 1. Scrape Events
```bash
# Basic scraping
python main.py scrape

# Scrape and sync to Google Sheets
python main.py scrape --sheets
```

**What it does:**
- Scrapes Eventbrite, NYC For Free, Average Socialite
- Removes duplicates
- Saves to `data/events_YYYYMMDD_HHMMSS.json`
- Optionally syncs to Google Sheets

#### 2. Send Digest Email
```bash
# Test mode (preview only)
python main.py send-digest

# Actually send email
python main.py send-digest --send
```

**What it does:**
- Filters new events not previously sent
- Creates HTML/text digest with numbered events
- Sends to photographer's email
- Tracks sent events to avoid duplicates

#### 3. Check Email Replies
```bash
python main.py check-replies
```

**What it does:**
- Checks Gmail for replies to digest emails
- Parses selections like "1, 3, 5" or "events 2,4,6"
- Saves selections to `data/selections.json`
- Shows which events were selected

#### 4. Send Outreach Emails
```bash
# Test mode (preview only)
python main.py send-outreach

# Actually send emails
python main.py send-outreach --send
```

**What it does:**
- Loads selected events
- Generates personalized emails for each event
- Sends to organizers (if contact info available)
- Tracks sent outreach to avoid duplicates

### Google Sheets Commands

```bash
# Sync existing data to sheets
python sync_to_sheets.py

# Sync specific file
python sync_to_sheets.py --file data/events_20250715.json

# Get sheet URL
python sync_to_sheets.py --url

# Mark events as selected
python sync_to_sheets.py --update-selected event_id1 event_id2

# Mark outreach as sent
python sync_to_sheets.py --update-outreach event_id1 event_id2
```

## Complete Manual Workflow

### Morning Routine
```bash
# 1. Scrape new events
python main.py scrape --sheets

# 2. Send digest to photographer
python main.py send-digest --send
```

### Afternoon Routine
```bash
# 3. Check for replies
python main.py check-replies

# 4. Send outreach to selected events
python main.py send-outreach --send
```

### Using Google Sheets
1. Open your sheet (run `python sync_to_sheets.py --url`)
2. Review events in the "Events" tab
3. Mark events as "Yes" in the Selected column
4. Run sync to process selections:
   ```bash
   python sync_to_sheets.py
   python main.py send-outreach --send
   ```

## File Structure

```
data/
├── events_*.json          # Scraped events
├── events_*.csv           # CSV version
├── digest_tracking.json   # Sent digest history
├── selections.json        # Photographer selections
├── selected_events.json   # Events to contact
└── outreach_sent.json     # Outreach history

logs/
└── scraper_*.log         # Detailed logs

templates/
├── digest_email.html     # Digest email template
├── digest_email.txt      # Plain text version
├── outreach_template.html # Outreach template
└── outreach_template.txt  # Plain text version
```

## Environment Variables

Create a `.env` file with:

```bash
# Required
PHOTOGRAPHER_EMAIL=contact@keithmorse.com

# For Gmail API (after running setup_gmail.py)
# Automatically created: credentials.json, token.json

# For Google Sheets (optional)
GOOGLE_SHEETS_ID=your-sheet-id

# For SMTP fallback (optional)
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

## Testing

```bash
# Run all tests
python run_tests.py

# Run specific test suites
python run_tests.py scrapers
python run_tests.py email
python run_tests.py data

# Run with coverage
python run_tests.py coverage
```

## Troubleshooting

### No events found
- Websites may have changed their HTML structure
- Check `logs/` for detailed error messages
- Try running scrapers individually

### Emails not sending
- Ensure `token.json` exists and is valid
- Check Gmail API quotas
- Verify `PHOTOGRAPHER_EMAIL` in `.env`

### Google Sheets not syncing
- Verify `GOOGLE_SHEETS_ID` in `.env`
- Ensure Drive API is enabled
- Re-run `python setup_gmail_with_sheets.py`

### Replies not detected
- Check email subject contains "NYC Event"
- Ensure reply is in the same thread
- Verify photographer email matches

## GitHub Secrets Required

For GitHub Actions automation:

1. `GMAIL_CREDENTIALS` - Contents of `credentials.json`
2. `GMAIL_TOKEN` - Contents of `token.json`
3. `PHOTOGRAPHER_EMAIL` - Photographer's email address
4. `GOOGLE_SHEETS_ID` - Google Sheet ID (optional)
5. `GOOGLE_SHEETS_CREDENTIALS` - Service account JSON (optional)

## Quick Start

1. **Clone and setup**:
   ```bash
   git clone <repository>
   cd nyc-event-automation
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure authentication**:
   ```bash
   python setup_gmail_with_sheets.py
   python setup_sheets.py  # Optional
   ```

3. **Create `.env`**:
   ```bash
   echo "PHOTOGRAPHER_EMAIL=contact@keithmorse.com" > .env
   ```

4. **Test the system**:
   ```bash
   python main.py scrape
   python main.py send-digest  # Test mode
   ```

5. **Deploy to GitHub**:
   - Add secrets to repository
   - Enable Actions
   - Automation runs daily at 9 AM EST

## Support

For issues or questions:
- Check logs in `logs/` directory
- Review error messages carefully
- Ensure all dependencies are installed
- Verify API credentials are valid