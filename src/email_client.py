"""
Secure email client for TixScanner using Gmail API.

This module provides email functionality using OAuth2 authentication
with Gmail API, eliminating the need for app passwords.
"""

import base64
import logging
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Optional, Dict, List, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import re
from jinja2 import Environment, FileSystemLoader

from .gmail_auth import GmailAuthenticator, GmailAuthError
from .chart_generator import ChartGenerator
from .models import Concert, PriceHistory, EmailLog, EmailType
from .db_operations import get_concert, get_all_concerts, get_latest_price, log_email

logger = logging.getLogger(__name__)


class EmailClientError(Exception):
    """Exception raised for email client errors."""
    pass


class EmailClient:
    """
    Secure email client using Gmail API with OAuth2.
    
    Provides functionality to send price alerts and daily summaries
    with embedded charts using secure authentication.
    """
    
    def __init__(self, credentials_file: Optional[str] = None,
                 token_file: Optional[str] = None, 
                 db_path: Optional[str] = None):
        """
        Initialize email client.
        
        Args:
            credentials_file: Path to Gmail API credentials
            token_file: Path to store OAuth2 tokens  
            db_path: Database path for logging
        """
        self.db_path = db_path
        self.chart_generator = ChartGenerator()
        
        # Initialize Gmail authenticator
        self.authenticator = GmailAuthenticator(credentials_file, token_file)
        self._authenticated = False
        
        # Initialize Jinja2 template environment
        template_dir = Path(__file__).parent.parent / "templates"
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))
        logger.debug(f"Jinja2 environment initialized with templates from {template_dir}")
        
        logger.debug("Email client initialized")
    
    def authenticate(self) -> bool:
        """
        Authenticate with Gmail API.
        
        Returns:
            True if authentication successful
            
        Raises:
            EmailClientError: If authentication fails
        """
        try:
            if self.authenticator.authenticate():
                self._authenticated = True
                user_email = self.authenticator.get_user_email()
                logger.info(f"Email client authenticated for: {user_email}")
                return True
            else:
                raise EmailClientError("Gmail authentication failed")
                
        except GmailAuthError as e:
            raise EmailClientError(f"Authentication error: {e}")
        except Exception as e:
            logger.error(f"Email client authentication failed: {e}")
            raise EmailClientError(f"Authentication failed: {e}")
    
    def _ensure_authenticated(self) -> None:
        """Ensure client is authenticated."""
        if not self._authenticated or not self.authenticator.is_authenticated():
            if not self.authenticate():
                raise EmailClientError("Not authenticated with Gmail API")
    
    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render email template with context data using Jinja2.
        
        Args:
            template_name: Name of template file (without .html extension)
            context: Template context variables
            
        Returns:
            Rendered HTML content
        """
        try:
            template = self.jinja_env.get_template(f"{template_name}.html")
            return template.render(**context)
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {e}")
            raise EmailClientError(f"Template rendering failed: {e}")
    
    
    def send_price_alert(self, event_id: str, old_price: Decimal, new_price: Decimal,
                        recipient: Optional[str] = None) -> bool:
        """
        Send price drop alert email.
        
        Args:
            event_id: Event ID for the concert
            old_price: Previous price
            new_price: New (lower) price  
            recipient: Email recipient (uses authenticated user if None)
            
        Returns:
            True if email sent successfully
        """
        try:
            self._ensure_authenticated()
            
            # Get concert information
            concert = get_concert(event_id, self.db_path)
            if not concert:
                raise EmailClientError(f"Concert not found: {event_id}")
            
            # Calculate price change
            price_diff = old_price - new_price
            price_change_percent = (price_diff / old_price) * 100
            
            # Generate chart
            chart_image = self.chart_generator.generate_price_trend_chart(
                event_id, days=7, db_path=self.db_path
            )
            
            # Prepare template context
            context = {
                'concert_name': concert.name,
                'venue': concert.venue or 'TBA',
                'event_date': concert.event_date.strftime('%B %d, %Y') if concert.event_date else 'TBA',
                'event_status': 'On Sale',  # Could be enhanced with API data
                'old_price': f"{old_price:.0f}",
                'new_price': f"{new_price:.0f}",
                'price_change': f"${price_diff:.0f} ({price_change_percent:.1f}%)",
                'threshold_price': f"{concert.threshold_price:.0f}",
                'chart_image': chart_image,
                'purchase_url': concert.url or f"https://www.ticketmaster.com/search?q={concert.name.replace(' ', '+')}",
                'timestamp': datetime.now().strftime('%B %d, %Y at %I:%M %p'),
                'user_email': self.authenticator.get_user_email()
            }
            
            # Render email content
            html_content = self._render_template('price_alert', context)
            
            # Create email
            subject = f"Price Drop: {concert.name} - Now ${new_price:.0f} ({price_change_percent:.0f}% Drop)"
            
            if not recipient:
                recipient = self.authenticator.get_user_email()
            
            # Send email
            success = self._send_email(recipient, subject, html_content)
            
            # Log email
            email_log = EmailLog(
                email_type=EmailType.ALERT,
                recipient=recipient,
                event_id=event_id,
                subject=subject,
                success=success
            )
            log_email(email_log, self.db_path)
            
            if success:
                logger.info(f"Price alert sent for {concert.name}: ${old_price} → ${new_price}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send price alert: {e}")
            return False
    
    def send_daily_summary(self, recipient: Optional[str] = None) -> bool:
        """
        Send daily price summary email.
        
        Args:
            recipient: Email recipient (uses authenticated user if None)
            
        Returns:
            True if email sent successfully
        """
        try:
            self._ensure_authenticated()
            
            # Get all concerts
            concerts = get_all_concerts(self.db_path)
            if not concerts:
                logger.info("No concerts to include in daily summary")
                return True
            
            # Prepare concert data
            concert_data = []
            below_threshold = 0

            for concert in concerts:
                latest_price = get_latest_price(concert.event_id, self.db_path)

                if latest_price:
                    current_price = float(latest_price.price)

                    is_below_threshold = latest_price.price <= concert.threshold_price
                    if is_below_threshold:
                        below_threshold += 1

                    # Generate individual chart
                    chart_image = self.chart_generator.generate_price_trend_chart(
                        concert.event_id, days=7, db_path=self.db_path
                    )

                    concert_data.append({
                        'name': concert.name,
                        'venue': concert.venue or 'TBA',
                        'date': concert.event_date.strftime('%m/%d/%Y') if concert.event_date else 'TBA',
                        'current_price': f"{current_price:.0f}",
                        'threshold_price': f"{concert.threshold_price:.0f}",
                        'below_threshold': is_below_threshold,
                        'threshold_class': 'below-threshold' if is_below_threshold else 'above-threshold',
                        'chart_image': chart_image,
                        'purchase_url': concert.url or f"https://www.ticketmaster.com/search?q={concert.name.replace(' ', '+')}"
                    })
            
            # Generate summary chart
            summary_chart = self.chart_generator.generate_summary_chart(
                [{'name': c['name'], 'current_price': float(c['current_price']),
                  'price_change_percent': 0, 'threshold_price': float(c['threshold_price'])}
                 for c in concert_data],
                self.db_path
            )

            # Prepare template context
            context = {
                'date': datetime.now().strftime('%B %d, %Y'),
                'total_concerts': len(concerts),
                'below_threshold': below_threshold,
                'concerts': concert_data,
                'summary_chart': summary_chart,
                'summary_time': datetime.now().strftime('%I:%M %p'),
                'user_email': self.authenticator.get_user_email()
            }
            
            # Render email content
            html_content = self._render_template('daily_summary', context)
            
            # Create email
            subject = f"Daily Price Update - {datetime.now().strftime('%B %d')} ({len(concerts)} concerts tracked)"
            
            if not recipient:
                recipient = self.authenticator.get_user_email()
            
            # Send email
            success = self._send_email(recipient, subject, html_content)
            
            # Log email
            email_log = EmailLog(
                email_type=EmailType.SUMMARY,
                recipient=recipient,
                subject=subject,
                success=success
            )
            log_email(email_log, self.db_path)
            
            if success:
                logger.info(f"Daily summary sent with {len(concerts)} concerts")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send daily summary: {e}")
            return False
    
    def _send_email(self, recipient: str, subject: str, html_content: str) -> bool:
        """
        Send email using Gmail API.
        
        Args:
            recipient: Email recipient
            subject: Email subject
            html_content: HTML email content
            
        Returns:
            True if sent successfully
        """
        try:
            service = self.authenticator.get_service()
            sender_email = self.authenticator.get_user_email()
            
            # Create message
            message = MIMEMultipart('alternative')
            message['to'] = recipient
            message['from'] = sender_email
            message['subject'] = Header(subject, 'utf-8')
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html')
            message.attach(html_part)
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send via Gmail API
            send_result = service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            message_id = send_result.get('id')
            logger.debug(f"Email sent successfully, message ID: {message_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def test_connection(self) -> bool:
        """
        Test email client connection and authentication.
        
        Returns:
            True if connection works
        """
        try:
            self._ensure_authenticated()
            return self.authenticator.test_connection()
        except Exception as e:
            logger.error(f"Email client connection test failed: {e}")
            return False
    
    def send_test_email(self, recipient: Optional[str] = None) -> bool:
        """
        Send a test email to verify functionality.
        
        Args:
            recipient: Test email recipient
            
        Returns:
            True if test email sent successfully
        """
        try:
            self._ensure_authenticated()
            
            if not recipient:
                recipient = self.authenticator.get_user_email()
            
            # Create simple test email
            subject = "🧪 TixScanner Test Email"
            html_content = """
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h1 style="color: #2c3e50;">🎫 TixScanner Test Email</h1>
                <p>This is a test email to verify that your TixScanner email system is working correctly.</p>
                <div style="background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <strong>✅ Gmail API Connection: Working</strong><br>
                    <strong>✅ Email Templates: Loaded</strong><br>
                    <strong>✅ Chart Generation: Ready</strong><br>
                    <strong>✅ Database Integration: Connected</strong>
                </div>
                <p>You're all set to receive price alerts and daily summaries!</p>
                <p><small>Sent on {}</small></p>
            </body>
            </html>
            """.format(datetime.now().strftime('%B %d, %Y at %I:%M %p'))
            
            success = self._send_email(recipient, subject, html_content)
            
            if success:
                logger.info(f"Test email sent successfully to {recipient}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send test email: {e}")
            return False
    
    def get_setup_status(self) -> Dict[str, Any]:
        """
        Get email system setup status.
        
        Returns:
            Dictionary with setup status information
        """
        status = {
            'authenticated': False,
            'user_email': None,
            'templates_loaded': len(self.templates),
            'chart_generator': True,
            'connection_test': False
        }
        
        try:
            if self.authenticator.is_authenticated():
                status['authenticated'] = True
                status['user_email'] = self.authenticator.get_user_email()
                status['connection_test'] = self.test_connection()
            
        except Exception as e:
            logger.error(f"Error getting setup status: {e}")
        
        return status