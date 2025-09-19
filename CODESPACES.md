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
| `GMAIL_TOKEN_JSON` | OAuth tokens with refresh token | Yes |
| `GMAIL_CREDENTIALS_JSON` | Client credentials from Google Cloud | Optional* |

*Optional if tokens include client_id and client_secret

## Security Notes

1. **Never commit secrets**: The `.env.codespaces` file should be in `.gitignore`
2. **Use repository secrets**: Store sensitive data in GitHub Codespaces secrets
3. **Token rotation**: Refresh tokens have long expiration but can be revoked
4. **Scope limitation**: Tokens only have Gmail send/compose permissions

## Troubleshooting

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

## Migration from Local

If you've been running locally and want to switch to Codespaces:

1. Run `extract_gmail_tokens.py` locally
2. Set up Codespaces secrets
3. Push any local changes to GitHub
4. Create Codespace and run

The same configuration files (`config.ini`) work in both environments.