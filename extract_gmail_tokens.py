#!/usr/bin/env python3
"""
Extract Gmail OAuth tokens for GitHub Codespaces deployment.

This script extracts the OAuth tokens from the local pickle files
and converts them to JSON format suitable for environment variables.
"""

import os
import json
import pickle
import sys
from pathlib import Path


def extract_token_from_pickle(token_file: str = 'gmail_token.pickle') -> dict:
    """
    Extract token data from pickle file.

    Args:
        token_file: Path to the token pickle file

    Returns:
        Dictionary with token data
    """
    if not os.path.exists(token_file):
        print(f"❌ Token file not found: {token_file}")
        print("Please run 'python main.py' locally first to authenticate with Gmail.")
        return None

    try:
        with open(token_file, 'rb') as f:
            creds = pickle.load(f)

        # Extract the necessary fields
        token_data = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri or 'https://oauth2.googleapis.com/token',
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes or [
                'https://www.googleapis.com/auth/gmail.send',
                'https://www.googleapis.com/auth/gmail.compose'
            ]
        }

        return token_data

    except Exception as e:
        print(f"❌ Error extracting token: {e}")
        return None


def extract_credentials_from_json(creds_file: str = 'gmail_credentials.json') -> dict:
    """
    Extract client credentials from JSON file.

    Args:
        creds_file: Path to the credentials JSON file

    Returns:
        Dictionary with client configuration
    """
    if not os.path.exists(creds_file):
        print(f"❌ Credentials file not found: {creds_file}")
        print("Please download the credentials from Google Cloud Console.")
        return None

    try:
        with open(creds_file, 'r') as f:
            creds = json.load(f)
        return creds

    except Exception as e:
        print(f"❌ Error reading credentials: {e}")
        return None


def main():
    """Main function to extract and display tokens."""
    print("=" * 70)
    print("Gmail OAuth Token Extractor for GitHub Codespaces")
    print("=" * 70)
    print()

    # Extract token data
    print("📂 Extracting token data...")
    token_data = extract_token_from_pickle()

    if not token_data:
        sys.exit(1)

    # Extract credentials
    print("📂 Extracting client credentials...")
    creds_data = extract_credentials_from_json()

    if not creds_data:
        print("⚠️  Warning: Client credentials not found.")
        print("   You'll need to provide GMAIL_CREDENTIALS_JSON separately.")

    print()
    print("✅ Token extraction successful!")
    print()
    print("=" * 70)
    print("SETUP INSTRUCTIONS FOR GITHUB CODESPACES")
    print("=" * 70)
    print()
    print("1. Go to your GitHub repository settings")
    print("2. Navigate to: Settings > Secrets and variables > Codespaces")
    print("3. Add these repository secrets:")
    print()
    print("-" * 70)
    print("Secret Name: GMAIL_TOKEN_JSON")
    print("Secret Value: (copy the JSON below)")
    print("-" * 70)
    print(json.dumps(token_data, indent=2))
    print()

    if creds_data:
        print("-" * 70)
        print("Secret Name: GMAIL_CREDENTIALS_JSON")
        print("Secret Value: (copy the JSON below)")
        print("-" * 70)
        print(json.dumps(creds_data, indent=2))
        print()

    print("=" * 70)
    print("USAGE IN CODESPACES")
    print("=" * 70)
    print()
    print("Once the secrets are added, your app will automatically use them.")
    print("No code changes needed - the gmail_auth.py module checks for:")
    print("  1. GMAIL_TOKEN_JSON environment variable")
    print("  2. GMAIL_CREDENTIALS_JSON environment variable")
    print()
    print("The app will use these if available, otherwise falls back to local files.")
    print()

    # Optional: Save to .env.codespaces file for reference
    env_file = Path('.env.codespaces')
    if input("💾 Save to .env.codespaces file for reference? (y/n): ").lower() == 'y':
        with open(env_file, 'w') as f:
            f.write("# GitHub Codespaces Environment Variables\n")
            f.write("# Add these as repository secrets in GitHub\n\n")
            f.write(f"GMAIL_TOKEN_JSON='{json.dumps(token_data)}'\n\n")
            if creds_data:
                f.write(f"GMAIL_CREDENTIALS_JSON='{json.dumps(creds_data)}'\n")

        print(f"✅ Saved to {env_file}")
        print("⚠️  Remember: Do NOT commit this file to git!")
        print("   Add .env.codespaces to your .gitignore")

    print()
    print("✨ Done!")


if __name__ == "__main__":
    main()