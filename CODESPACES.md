# GitHub Codespaces Deployment Guide

This guide explains how to deploy TixScanner to GitHub Codespaces with Gmail OAuth integration.

## Overview

TixScanner supports both local file-based authentication and environment variable-based authentication, making it compatible with GitHub Codespaces where local files aren't persistent.

## Prerequisites

1. **Local Setup First**: You must run TixScanner locally at least once to complete the OAuth flow
2. **Gmail OAuth Setup**: Follow the Gmail API setup instructions to get your credentials
3. **GitHub Repository**: Your TixScanner code should be in a GitHub repository

## Step 1: Local Authentication

Before deploying to Codespaces, authenticate locally:

```bash
# Run locally to complete OAuth flow
python3 main.py
```

This creates two important files:
- `gmail_credentials.json` - Client credentials from Google Cloud Console
- `gmail_token.pickle` - OAuth tokens with refresh token

## Step 2: Extract Tokens for Codespaces

Run the extraction script to get the data for environment variables:

```bash
python3 extract_gmail_tokens.py
```

This script will:
- Extract token data from `gmail_token.pickle`
- Extract client credentials from `gmail_credentials.json`
- Display the JSON data needed for Codespaces secrets
- Optionally save to `.env.codespaces` for reference

## Step 3: Configure GitHub Codespaces Secrets

1. Go to your GitHub repository
2. Navigate to: **Settings > Secrets and variables > Codespaces**
3. Add these repository secrets:

### Required Secret: TICKETMASTER_API_KEY

Add your Ticketmaster API key for price monitoring:

- **Name**: `TICKETMASTER_API_KEY`
- **Value**: Your actual Ticketmaster API key (e.g., `aBc123XyZ789...`)

The application will automatically load this via environment variables using the existing configuration in `src/config_manager.py`.

### Required Secret: GMAIL_TOKEN_JSON
```json
{
  "token": "ya29.a0AQQ_BDRh...",
  "refresh_token": "1//06L545DimkTx...",
  "token_uri": "https://oauth2.googleapis.com/token",
  "client_id": "1004785508303-6dk...",
  "client_secret": "GOCSPX-NdBfK5o...",
  "scopes": [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose"
  ]
}
```

### Optional Secret: GMAIL_CREDENTIALS_JSON
```json
{
  "installed": {
    "client_id": "1004785508303-6dk...",
    "project_id": "tixscanner-email",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_secret": "GOCSPX-NdBfK5o..."
  }
}
```

## Step 4: Deploy to Codespaces

1. **Create a Codespace**:
   - Go to your repository on GitHub
   - Click "Code" > "Codespaces" > "Create codespace on main"

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run TixScanner**:
   ```bash
   python3 main.py
   ```

The application will automatically detect and use the environment variables.

## How It Works

The Gmail authentication module (`src/gmail_auth.py`) now supports a flexible authentication flow:

1. **Check Environment Variables**: First looks for `GMAIL_TOKEN_JSON`
2. **Fallback to Files**: If no env vars, uses local files
3. **OAuth Flow**: Only if neither env vars nor files are available

## Authentication Priority

```
Environment Variables (Codespaces) → Local Files → OAuth Flow
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TICKETMASTER_API_KEY` | Ticketmaster API key for price monitoring | Yes |
| `GMAIL_TOKEN_JSON` | OAuth tokens with refresh token | Yes |
| `GMAIL_CREDENTIALS_JSON` | Client credentials from Google Cloud | Optional* |

*Optional if tokens include client_id and client_secret

### API Key Priority

The application loads the Ticketmaster API key using this priority:
1. **Environment Variable**: `TICKETMASTER_API_KEY` (Codespaces secret)
2. **Config File**: `config.ini` [api] section (local development)
3. **Error**: Throws ConfigError if neither is configured

## Security Notes

1. **Never commit secrets**: The `.env.codespaces` file should be in `.gitignore`
2. **Use repository secrets**: Store sensitive data in GitHub Codespaces secrets
3. **Token rotation**: Refresh tokens have long expiration but can be revoked
4. **Scope limitation**: Tokens only have Gmail send/compose permissions

## Testing Configuration

### Verify API Key Setup

After setting up Codespaces, test that both API keys are configured correctly:

```bash
# In Codespaces terminal
python3 -c "
from src.config_manager import ConfigManager
config = ConfigManager()

# Test Ticketmaster API key
try:
    api_key = config.get_ticketmaster_api_key()
    print(f'✅ Ticketmaster API key loaded: {api_key[:8]}...')
except Exception as e:
    print(f'❌ Ticketmaster API key error: {e}')

# Test email configuration
try:
    email_config = config.get_email_config()
    print(f'✅ Email config loaded: {email_config}')
except Exception as e:
    print(f'❌ Email config error: {e}')
"
```

### Test Full Application Setup

```bash
# Run setup test
python3 main.py --mode check
```

This should:
- ✅ Load both API configurations successfully
- ✅ Authenticate with Gmail using environment variables
- ✅ Perform a single price check
- ✅ Send alerts if any prices are below threshold

## Troubleshooting

### API Key Configuration Failed
- Verify `TICKETMASTER_API_KEY` is set as a Codespaces secret
- Check that the API key value doesn't have extra spaces or characters
- Ensure the secret name matches exactly: `TICKETMASTER_API_KEY`

### Authentication Failed
- Verify `GMAIL_TOKEN_JSON` is correctly formatted JSON
- Check that all required fields are present
- Ensure client_id and client_secret are correct

### Token Expired
- The refresh token should automatically renew access tokens
- If refresh fails, re-run local OAuth flow and update secrets

### Missing Dependencies
```bash
pip install -r requirements.txt
```

### Port Issues
- Codespaces handles port forwarding automatically
- No special configuration needed for OAuth redirects

## Continuous Monitoring

For continuous monitoring in Codespaces:

1. **Enable scheduler** in `main.py`:
   ```python
   # Uncomment these lines for continuous monitoring
   scheduler = MonitoringScheduler(price_monitor)
   scheduler.start()
   ```

2. **Keep Codespace active**:
   - Codespaces auto-suspend after inactivity
   - Consider using `screen` or `tmux` for long-running processes

## Cost Considerations

- **GitHub Codespaces**: Free tier includes 120 core hours/month
- **Always-on monitoring**: May consume hours quickly
- **Alternative**: Use GitHub Actions with scheduled workflows

## Complete Setup Summary

### Required Codespaces Secrets

Set up these two secrets in **Settings > Secrets and variables > Codespaces**:

1. **TICKETMASTER_API_KEY**
   - Your Ticketmaster API key for price monitoring
   - Example: `aBc123XyZ789...`

2. **GMAIL_TOKEN_JSON**
   - Complete OAuth token JSON from `extract_gmail_tokens.py`
   - Includes refresh token for automatic authentication

### Deployment Checklist

- [ ] Extract Gmail tokens locally with `extract_gmail_tokens.py`
- [ ] Set both Codespaces secrets (TICKETMASTER_API_KEY, GMAIL_TOKEN_JSON)
- [ ] Create Codespace with **Write** permissions for database persistence
- [ ] Run `./deploy/setup_codespaces.sh` in Codespace
- [ ] Test configuration with `python3 main.py --mode check`
- [ ] Start continuous monitoring with `screen -S tixscanner && python3 main.py`

## Migration from Local

If you've been running locally and want to switch to Codespaces:

1. Run `extract_gmail_tokens.py` locally to get tokens
2. Set up both Codespaces secrets (API key + Gmail tokens)
3. Push any local changes to GitHub
4. Create Codespace with Write permissions
5. Run setup script and start monitoring

The same configuration files (`config.ini`) work in both environments.