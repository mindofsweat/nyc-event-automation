# Digest Tracking Persistence

This document explains how the NYC Event Automation system tracks which events have been sent to avoid duplicates.

## How It Works

### Local Development
- Events sent are tracked in `data/digest_tracking.json`
- This file records:
  - Which event IDs have been sent
  - When each digest was sent
  - How many events were in each digest

### GitHub Actions Persistence
- Uses GitHub Artifacts to persist tracking between workflow runs
- After each digest is sent, the tracking file is uploaded as an artifact
- Before each run, the tracking file is downloaded from the previous run
- This ensures no duplicate emails are sent

## Workflow Steps

1. **First Run** (No tracking exists)
   - All scraped events are considered "new"
   - Email sent with all events
   - Tracking file created and uploaded

2. **Subsequent Runs**
   - Download tracking from previous run
   - Compare current events with tracking
   - Only send email if new events found
   - Update tracking and upload

## Manual Reset

If you need to reset tracking (e.g., to resend all events):

### Option 1: Reset Locally
```bash
python3 reset_tracking.py
git add data/digest_tracking.json
git commit -m "Reset digest tracking"
git push
```

### Option 2: Delete GitHub Artifact
1. Go to Actions → Test Tracking Persistence
2. Run workflow manually
3. This will show current tracking status

### Option 3: Force New Tracking
Simply delete the artifact from GitHub:
- Go to your repo → Actions tab
- Click on a recent workflow run
- Find "digest-tracking" artifact
- Delete it

## Debugging

To check current tracking status:
```bash
# Locally
python3 debug_email_send.py

# In GitHub Actions
# Run the "Test Tracking Persistence" workflow
```

## Important Notes

- Tracking is separate between local and GitHub Actions
- First GitHub Actions run will send all events (expected behavior)
- Artifacts are kept for 90 days
- If artifact expires, system will treat all events as new again