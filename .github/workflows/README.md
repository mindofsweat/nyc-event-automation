# GitHub Actions Workflows

This directory contains automated workflows for the NYC Event Automation project.

## Workflows

### 1. `cron.yml` - Daily Event Scraping and Digest
- **Schedule**: Runs daily at 9 AM EST (2 PM UTC)
- **Purpose**: Scrapes events and sends digest email to photographer
- **Manual trigger**: Can be triggered manually from Actions tab

### 2. `check-replies.yml` - Hourly Reply Checking
- **Schedule**: Runs every hour
- **Purpose**: Checks for photographer replies and sends outreach emails
- **Manual trigger**: Can be triggered manually from Actions tab

### 3. `test.yml` - Manual Testing
- **Schedule**: Manual only
- **Purpose**: Test individual commands with optional test mode
- **Options**: Choose command and whether to actually send emails

## Required GitHub Secrets

To use these workflows, you need to configure the following secrets in your repository:

1. **GMAIL_CREDENTIALS**
   - The contents of your `credentials.json` file
   - Get this from Google Cloud Console after setting up OAuth2
   - Format: JSON string

2. **GMAIL_TOKEN**
   - The contents of your `token.json` file
   - Generated after first authentication
   - Format: JSON string

3. **PHOTOGRAPHER_EMAIL**
   - Email address of the photographer (Keith Morse)
   - Example: `contact@keithmorse.com`

4. **SMTP_USERNAME** (Optional - for IMAP/SMTP fallback)
   - Gmail username for SMTP sending
   - Usually your Gmail address

5. **SMTP_PASSWORD** (Optional - for IMAP/SMTP fallback)
   - Gmail app-specific password
   - Generate from Google Account settings

## Setting Up Secrets

1. Go to your repository on GitHub
2. Click on "Settings" tab
3. Click on "Secrets and variables" → "Actions"
4. Click "New repository secret"
5. Add each secret with the appropriate name and value

### Getting Gmail Credentials

1. Set up OAuth2 credentials locally:
   ```bash
   python setup_gmail.py --gmail-api
   ```

2. After authentication, encode the files:
   ```bash
   # For GMAIL_CREDENTIALS
   cat credentials.json | base64

   # For GMAIL_TOKEN
   cat token.json | base64
   ```

3. Copy the base64 output and paste as the secret value

### Security Notes

- Never commit credentials to the repository
- Use GitHub Secrets for all sensitive information
- Credentials are automatically masked in logs
- Consider using environment-specific credentials

## Workflow Permissions

Ensure your repository has the following permissions:
- Actions: Read and write
- Contents: Read
- Pull requests: Read (if using PR workflows)

## Monitoring

- Check the Actions tab for workflow runs
- Failed runs will show ❌
- Successful runs will show ✅
- Click on a run to see detailed logs

## Troubleshooting

### Common Issues

1. **Authentication failures**
   - Check if secrets are properly set
   - Verify credentials haven't expired
   - Try regenerating token locally

2. **Timeout errors**
   - Workflows have 15-minute timeout
   - Check if scrapers are taking too long
   - Consider optimizing or splitting workflows

3. **Missing dependencies**
   - Ensure requirements.txt is up to date
   - Check Python version compatibility

### Debug Mode

To debug workflows:
1. Add `ACTIONS_RUNNER_DEBUG: true` to secrets
2. This will show additional debug information in logs