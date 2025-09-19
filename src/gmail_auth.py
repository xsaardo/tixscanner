"""
Gmail API OAuth2 authentication for TixScanner.

This module handles secure authentication with Gmail API using OAuth2,
eliminating the need for app passwords or credential storage.
"""

import os
import json
import logging
import pickle
import base64
from pathlib import Path
from typing import Optional, Dict, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# Gmail API scopes - only requesting what we need
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',  # Send emails only
    'https://www.googleapis.com/auth/gmail.compose'  # Compose emails
]

# Default paths for credential files
DEFAULT_CREDENTIALS_FILE = 'gmail_credentials.json'
DEFAULT_TOKEN_FILE = 'gmail_token.pickle'


class GmailAuthError(Exception):
    """Exception raised for Gmail authentication errors."""
    pass


class GmailAuthenticator:
    """
    Gmail API authenticator using OAuth2.
    
    Handles the OAuth2 flow, token storage, and refresh automatically.
    Provides a secure way to authenticate with Gmail without storing passwords.
    """
    
    def __init__(self, credentials_file: Optional[str] = None, 
                 token_file: Optional[str] = None):
        """
        Initialize Gmail authenticator.
        
        Args:
            credentials_file: Path to client_secret.json from Google Cloud Console
            token_file: Path to store user tokens (created automatically)
        """
        self.credentials_file = credentials_file or DEFAULT_CREDENTIALS_FILE
        self.token_file = token_file or DEFAULT_TOKEN_FILE
        self._service = None
        self._credentials = None
        
        logger.debug("Gmail authenticator initialized")
    
    def setup_instructions(self) -> str:
        """
        Return detailed setup instructions for users.
        
        Returns:
            Formatted setup instructions
        """
        instructions = """
📧 Gmail API Setup Instructions:

1. Create Google Cloud Project:
   • Go to: https://console.cloud.google.com/
   • Create a new project or select existing one
   • Name it something like "TixScanner Email"

2. Enable Gmail API:
   • In the project dashboard, go to "APIs & Services" > "Library"
   • Search for "Gmail API" and click on it
   • Click "Enable"

3. Create OAuth2 Credentials:
   • Go to "APIs & Services" > "Credentials"
   • Click "+ CREATE CREDENTIALS" > "OAuth client ID"
   • If prompted, configure OAuth consent screen:
     - User Type: External (for personal use)
     - App name: "TixScanner"
     - User support email: your email
     - Developer contact: your email
   • Application type: "Desktop application"
   • Name: "TixScanner Desktop Client"
   • Click "Create"

4. Download Credentials:
   • Click the download button for your OAuth client
   • Save the file as 'gmail_credentials.json' in your TixScanner directory
   • Keep this file secure and never commit it to git

5. First Run:
   • The first time you run TixScanner, it will open a browser
   • Sign in with your Gmail account ({}@gmail.com)
   • Grant permissions to send emails
   • The app will save a token file for future use

Security Notes:
• Your email password is never stored or accessed
• Tokens are stored locally and encrypted by Google's libraries  
• You can revoke access anytime in your Google Account settings
• Only email sending permissions are requested
        """.strip()
        
        # Get email from environment if available
        email = os.getenv('GMAIL_USER', 'your.email')
        return instructions.format(email)

    def _load_credentials_from_env(self) -> Optional[Credentials]:
        """
        Load Gmail credentials from environment variables.

        Returns:
            Credentials object or None if not available or invalid
        """
        try:
            token_json = os.getenv('GMAIL_TOKEN_JSON')
            if not token_json:
                return None

            # Parse the JSON string
            token_data = json.loads(token_json)

            # Create credentials from the token data
            creds = Credentials(
                token=token_data.get('token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=token_data.get('client_id'),
                client_secret=token_data.get('client_secret'),
                scopes=token_data.get('scopes', SCOPES)
            )

            return creds

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Failed to parse GMAIL_TOKEN_JSON environment variable: {e}")
            return None

    def _save_credentials_to_env_format(self, creds: Credentials) -> Dict[str, Any]:
        """
        Convert credentials to a format suitable for environment variables.

        Args:
            creds: Google OAuth2 credentials

        Returns:
            Dictionary that can be JSON serialized for environment variables
        """
        return {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes
        }

    def _get_client_config(self):
        """
        Get client configuration from environment or file.

        Returns:
            Either a file path (str) or a config dictionary, or None
        """
        # Check for environment variable first
        if os.getenv('GMAIL_CREDENTIALS_JSON'):
            try:
                config_json = os.getenv('GMAIL_CREDENTIALS_JSON')
                config = json.loads(config_json)
                logger.info("Using client credentials from environment")
                return config
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse GMAIL_CREDENTIALS_JSON: {e}")

        # Fall back to file
        if os.path.exists(self.credentials_file):
            logger.info("Using client credentials from file")
            return self.credentials_file

        return None
    
    def authenticate(self) -> bool:
        """
        Authenticate with Gmail API using OAuth2.

        Supports both environment variable and file-based authentication.

        Returns:
            True if authentication successful, False otherwise

        Raises:
            GmailAuthError: If authentication fails
        """
        try:
            creds = None

            # First check for environment variables (for Codespaces deployment)
            if os.getenv('GMAIL_TOKEN_JSON'):
                creds = self._load_credentials_from_env()
                if creds:
                    logger.info("Loaded credentials from environment variables")

            # Fall back to file-based token if no env var
            elif os.path.exists(self.token_file):
                try:
                    with open(self.token_file, 'rb') as token:
                        creds = pickle.load(token)
                        logger.debug("Loaded existing token from file")
                except Exception as e:
                    logger.warning(f"Failed to load existing token: {e}")
                    # Delete corrupted token file
                    os.remove(self.token_file)
            
            # If there are no valid credentials, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        logger.info("Refreshing expired token...")
                        creds.refresh(Request())
                        logger.info("Token refreshed successfully")
                    except Exception as e:
                        logger.warning(f"Failed to refresh token: {e}")
                        creds = None
                
                if not creds:
                    # Try to get credentials from environment or file
                    client_config = self._get_client_config()
                    if not client_config:
                        raise GmailAuthError(
                            f"Credentials not found.\n\n"
                            f"Please follow the setup instructions:\n{self.setup_instructions()}"
                        )

                    try:
                        logger.info("Starting OAuth2 flow...")
                        if isinstance(client_config, str):
                            # File path
                            flow = InstalledAppFlow.from_client_secrets_file(
                                client_config, SCOPES)
                        else:
                            # Dictionary from environment
                            flow = InstalledAppFlow.from_client_config(
                                client_config, SCOPES)
                        
                        # Run local server for OAuth callback
                        creds = flow.run_local_server(
                            port=0,  # Use random available port
                            prompt='consent',  # Always show consent screen
                            open_browser=True
                        )
                        logger.info("OAuth2 flow completed successfully")
                        
                    except Exception as e:
                        raise GmailAuthError(f"OAuth2 flow failed: {e}")
                
                # Save the credentials for future use
                try:
                    with open(self.token_file, 'wb') as token:
                        pickle.dump(creds, token)
                        logger.info(f"Token saved to {self.token_file}")
                except Exception as e:
                    logger.warning(f"Failed to save token: {e}")
            
            # Build Gmail service
            self._credentials = creds
            self._service = build('gmail', 'v1', credentials=creds)
            
            # Test the connection
            profile = self._service.users().getProfile(userId='me').execute()
            email_address = profile.get('emailAddress', 'unknown')
            logger.info(f"Successfully authenticated as: {email_address}")
            
            return True
            
        except GmailAuthError:
            raise
        except Exception as e:
            logger.error(f"Gmail authentication failed: {e}")
            raise GmailAuthError(f"Authentication failed: {e}")
    
    def get_service(self):
        """
        Get the Gmail service object.
        
        Returns:
            Gmail service object
            
        Raises:
            GmailAuthError: If not authenticated
        """
        if not self._service:
            raise GmailAuthError("Not authenticated. Call authenticate() first.")
        return self._service
    
    def get_credentials(self) -> Credentials:
        """
        Get the current credentials object.
        
        Returns:
            Google OAuth2 credentials
            
        Raises:
            GmailAuthError: If not authenticated
        """
        if not self._credentials:
            raise GmailAuthError("Not authenticated. Call authenticate() first.")
        return self._credentials
    
    def is_authenticated(self) -> bool:
        """
        Check if currently authenticated with valid credentials.
        
        Returns:
            True if authenticated with valid credentials
        """
        return (self._credentials is not None and 
                self._credentials.valid and 
                self._service is not None)
    
    def get_user_email(self) -> Optional[str]:
        """
        Get the email address of the authenticated user.
        
        Returns:
            User's email address or None if not authenticated
        """
        if not self.is_authenticated():
            return None
        
        try:
            profile = self._service.users().getProfile(userId='me').execute()
            return profile.get('emailAddress')
        except Exception as e:
            logger.error(f"Failed to get user email: {e}")
            return None
    
    def revoke_authentication(self) -> bool:
        """
        Revoke authentication and remove stored tokens.
        
        Returns:
            True if revocation successful
        """
        try:
            # Remove token file
            if os.path.exists(self.token_file):
                os.remove(self.token_file)
                logger.info("Token file removed")
            
            # Clear in-memory credentials
            self._credentials = None
            self._service = None
            
            logger.info("Authentication revoked")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke authentication: {e}")
            return False
    
    def test_connection(self) -> bool:
        """
        Test the Gmail API connection.
        
        Returns:
            True if connection works, False otherwise
        """
        try:
            if not self.is_authenticated():
                logger.error("Not authenticated")
                return False
            
            # Simple API call to test connection
            profile = self._service.users().getProfile(userId='me').execute()
            email = profile.get('emailAddress')
            
            logger.info(f"Connection test successful for: {email}")
            return True
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


def setup_gmail_auth() -> GmailAuthenticator:
    """
    Set up Gmail authentication with user guidance.
    
    Returns:
        Configured GmailAuthenticator instance
        
    Raises:
        GmailAuthError: If setup fails
    """
    print("🔐 Setting up Gmail API authentication...\n")
    
    authenticator = GmailAuthenticator()
    
    # Check if credentials file exists
    if not os.path.exists(DEFAULT_CREDENTIALS_FILE):
        print("❌ Gmail credentials not found!")
        print(authenticator.setup_instructions())
        raise GmailAuthError("Please complete the setup instructions above")
    
    print("📁 Found credentials file, authenticating...")
    
    try:
        if authenticator.authenticate():
            email = authenticator.get_user_email()
            print(f"✅ Successfully authenticated as: {email}")
            print("🔒 Your tokens are securely stored for future use")
            return authenticator
        else:
            raise GmailAuthError("Authentication failed")
            
    except GmailAuthError as e:
        print(f"❌ Setup failed: {e}")
        raise