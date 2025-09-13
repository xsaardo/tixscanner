"""
Price monitoring engine for TixScanner.

This module handles the core price monitoring logic, including:
- Checking prices for all tracked concerts
- Detecting price changes and drops
- Triggering email notifications
- Managing monitoring schedules
"""

import logging
from decimal import Decimal
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from .ticketmaster_api import TicketmasterAPI
from .email_client import EmailClient
from .optimized_scraper import TicketmasterOptimizedScraper
from .models import Concert, PriceHistory
from .db_operations import (
    get_all_concerts, get_latest_price, add_price_record,
    get_price_history, log_email
)

logger = logging.getLogger(__name__)


class PriceMonitor:
    """
    Main price monitoring engine.
    
    Coordinates API calls, price comparison, and email notifications.
    """
    
    def __init__(self, api_key: str, db_path: Optional[str] = None,
                 email_client: Optional[EmailClient] = None, 
                 enable_scraping: bool = True):
        """
        Initialize price monitor.
        
        Args:
            api_key: Ticketmaster API key
            db_path: Database path for storage
            email_client: Email client for notifications
            enable_scraping: Enable web scraping fallback
        """
        self.api_key = api_key
        self.db_path = db_path
        self.api_client = TicketmasterAPI(api_key)
        self.email_client = email_client or EmailClient(db_path=db_path)
        self.enable_scraping = enable_scraping
        self.scraper = None
        
        # Configuration defaults
        self.min_price_drop_percent = 10.0  # Minimum % drop to trigger alert
        self.check_frequency_hours = 2  # How often to check prices
        
        logger.info(f"Price monitor initialized (scraping: {'enabled' if enable_scraping else 'disabled'})")
    
    def configure(self, min_price_drop_percent: float = 10.0,
                 check_frequency_hours: int = 2) -> None:
        """
        Configure monitoring parameters.
        
        Args:
            min_price_drop_percent: Minimum price drop % to trigger alert
            check_frequency_hours: Hours between price checks
        """
        self.min_price_drop_percent = min_price_drop_percent
        self.check_frequency_hours = check_frequency_hours
        logger.info(f"Price monitor configured: {min_price_drop_percent}% drop threshold, "
                   f"check every {check_frequency_hours}h")
    
    def check_all_prices(self) -> Dict[str, Any]:
        """
        Check prices for all tracked concerts.
        
        Returns:
            Dictionary with monitoring results and statistics
        """
        logger.info("Starting price check for all concerts")
        
        concerts = get_all_concerts(self.db_path)
        if not concerts:
            logger.info("No concerts to monitor")
            return {
                'total_concerts': 0,
                'prices_checked': 0,
                'alerts_sent': 0,
                'errors': 0,
                'results': []
            }
        
        results = {
            'total_concerts': len(concerts),
            'prices_checked': 0,
            'alerts_sent': 0,
            'errors': 0,
            'results': []
        }
        
        for concert in concerts:
            try:
                result = self._check_concert_price(concert)
                results['results'].append(result)
                
                if result['price_found']:
                    results['prices_checked'] += 1
                    
                if result['alert_sent']:
                    results['alerts_sent'] += 1
                    
            except Exception as e:
                logger.error(f"Error checking price for {concert.name}: {e}")
                results['errors'] += 1
                results['results'].append({
                    'concert': concert,
                    'error': str(e),
                    'price_found': False,
                    'alert_sent': False
                })
        
        logger.info(f"Price check completed: {results['prices_checked']}/{results['total_concerts']} "
                   f"prices found, {results['alerts_sent']} alerts sent, {results['errors']} errors")
        
        return results
    
    def _check_concert_price(self, concert: Concert) -> Dict[str, Any]:
        """
        Check price for a single concert.
        
        Args:
            concert: Concert to check
            
        Returns:
            Dictionary with check results
        """
        logger.debug(f"Checking price for {concert.name}")
        
        result = {
            'concert': concert,
            'current_price': None,
            'previous_price': None,
            'price_change': None,
            'price_change_percent': None,
            'below_threshold': False,
            'significant_drop': False,
            'alert_sent': False,
            'price_found': False,
            'error': None
        }
        
        try:
            # Try API first
            current_price = None
            data_source = 'api'
            
            event_details = self.api_client.get_event_details(concert.event_id)
            if event_details and event_details.get('priceRanges'):
                # Extract minimum price (most relevant for alerts)
                price_ranges = event_details['priceRanges']
                min_price = min(float(pr.get('min', float('inf'))) for pr in price_ranges if pr.get('min'))
                
                if min_price != float('inf'):
                    current_price = Decimal(str(min_price))
                    logger.debug(f"API pricing found for {concert.name}: ${current_price}")
            
            # Fallback to web scraping if API didn't provide pricing
            if not current_price and self.enable_scraping:
                logger.info(f"No API pricing for {concert.name}, trying web scraping...")
                current_price = self._scrape_event_price(concert.event_id)
                if current_price:
                    data_source = 'scraping'
                    logger.info(f"Web scraping found price for {concert.name}: ${current_price}")
            
            if not current_price:
                logger.warning(f"No price data found for {concert.name} (tried API and {'scraping' if self.enable_scraping else 'API only'})")
                return result
            
            result['current_price'] = current_price
            result['price_found'] = True
            result['data_source'] = data_source
            
            # Get previous price from database
            latest_price = get_latest_price(concert.event_id, self.db_path)
            if latest_price:
                result['previous_price'] = latest_price.price
                price_change = current_price - latest_price.price
                result['price_change'] = price_change
                
                if latest_price.price > 0:
                    change_percent = (price_change / latest_price.price) * 100
                    result['price_change_percent'] = float(change_percent)
            
            # Store new price in database
            section_name = 'General'  # Default section name
            
            # Try to get section from API data if available
            if data_source == 'api' and event_details and event_details.get('priceRanges'):
                section_name = event_details['priceRanges'][0].get('type', 'General')
            elif data_source == 'scraping':
                section_name = 'Web-scraped'
                
            price_history = PriceHistory(
                event_id=concert.event_id,
                price=current_price,
                section=section_name,
                recorded_at=datetime.now()
            )
            add_price_record(price_history, self.db_path)
            
            # Check if price is below threshold
            result['below_threshold'] = current_price <= concert.threshold_price
            
            # Check for significant price drop
            if (result['price_change_percent'] is not None and 
                result['price_change_percent'] <= -self.min_price_drop_percent):
                result['significant_drop'] = True
                
                # Send price alert if conditions are met
                if result['below_threshold'] or abs(result['price_change_percent']) >= self.min_price_drop_percent:
                    try:
                        if self.email_client.send_price_alert(
                            concert.event_id, 
                            result['previous_price'],
                            current_price
                        ):
                            result['alert_sent'] = True
                            logger.info(f"Price alert sent for {concert.name}: "
                                      f"${result['previous_price']} → ${current_price}")
                    except Exception as e:
                        logger.error(f"Failed to send price alert for {concert.name}: {e}")
            
            logger.debug(f"Price check completed for {concert.name}: ${current_price}")
            
        except Exception as e:
            logger.error(f"Error checking price for {concert.name}: {e}")
            result['error'] = str(e)
        
        return result
    
    def _scrape_event_price(self, event_id: str) -> Optional[Decimal]:
        """
        Scrape price for an event using web scraping.
        
        Args:
            event_id: Ticketmaster event ID
            
        Returns:
            Minimum price as Decimal or None if scraping fails
        """
        try:
            # Initialize optimized scraper if needed
            if not self.scraper:
                self.scraper = TicketmasterOptimizedScraper(headless=True, timeout=30)
            
            # First try to get the proper URL from API
            event_details = self.api_client.get_event_details(event_id)
            if event_details and event_details.get('url'):
                event_url = event_details['url']
            else:
                # Fallback to constructed URL
                event_url = f"https://www.ticketmaster.com/event/{event_id}"
            
            logger.debug(f"Scraping URL for {event_id}: {event_url}")
            
            # Get user-configured target sections for this event
            from .config_manager import ConfigManager
            config = ConfigManager()
            section_config = config.get_section_config()
            target_sections = section_config.get(event_id, None)
            
            if target_sections:
                logger.info(f"Targeting user-specified sections for {event_id}: {target_sections}")
                pricing_data = self.scraper.scrape_section_pricing(event_url, target_sections=target_sections)
            else:
                logger.info(f"No section config for {event_id}, using cheapest sections strategy")
                pricing_data = self.scraper.get_cheapest_sections(event_url, section_count=1)
            
            if pricing_data['success'] and pricing_data.get('min_price'):
                return Decimal(str(pricing_data['min_price']))
            else:
                logger.debug(f"Web scraping failed for {event_id}: {pricing_data.get('error', 'No pricing data')}")
                return None
                
        except Exception as e:
            logger.error(f"Error during web scraping for {event_id}: {e}")
            return None
    
    def _cleanup_scraper(self) -> None:
        """Clean up web scraper resources."""
        if self.scraper:
            try:
                self.scraper.close()
                self.scraper = None
                logger.debug("Web scraper cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up scraper: {e}")
    
    def send_daily_summary(self) -> bool:
        """
        Send daily price summary email.
        
        Returns:
            True if summary sent successfully
        """
        logger.info("Sending daily price summary")
        
        try:
            success = self.email_client.send_daily_summary()
            if success:
                logger.info("Daily summary sent successfully")
            else:
                logger.error("Failed to send daily summary")
            return success
            
        except Exception as e:
            logger.error(f"Error sending daily summary: {e}")
            return False
    
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """
        Get monitoring statistics.
        
        Returns:
            Dictionary with monitoring statistics
        """
        concerts = get_all_concerts(self.db_path)
        stats = {
            'total_concerts': len(concerts),
            'active_monitoring': True,  # Would be configurable
            'last_check': None,
            'next_check': None,
            'check_frequency_hours': self.check_frequency_hours,
            'min_price_drop_percent': self.min_price_drop_percent,
            'concerts_below_threshold': 0,
            'recent_price_drops': 0
        }
        
        # Count concerts below threshold and recent drops
        for concert in concerts:
            latest_price = get_latest_price(concert.event_id, self.db_path)
            if latest_price:
                if latest_price.price <= concert.threshold_price:
                    stats['concerts_below_threshold'] += 1
                
                # Check for recent price drops (last 24 hours)
                yesterday = datetime.now() - timedelta(days=1)
                recent_prices = get_price_history(concert.event_id, days=1, db_path=self.db_path)
                if len(recent_prices) >= 2:
                    recent_change_percent = ((recent_prices[0].price - recent_prices[-1].price) / recent_prices[-1].price) * 100
                    if recent_change_percent <= -self.min_price_drop_percent:
                        stats['recent_price_drops'] += 1
        
        return stats
    
    def test_monitoring_setup(self) -> Dict[str, Any]:
        """
        Test monitoring system setup.
        
        Returns:
            Dictionary with test results
        """
        logger.info("Testing monitoring setup")
        
        test_results = {
            'api_connection': False,
            'database_connection': False,
            'email_system': False,
            'concerts_configured': 0,
            'ready_for_monitoring': False
        }
        
        try:
            # Test API connection
            test_results['api_connection'] = self.api_client.test_connection()
            
            # Test database
            concerts = get_all_concerts(self.db_path)
            test_results['concerts_configured'] = len(concerts)
            test_results['database_connection'] = True
            
            # Test email system
            if self.email_client:
                test_results['email_system'] = self.email_client.test_connection()
            
            # Overall readiness
            test_results['ready_for_monitoring'] = all([
                test_results['api_connection'],
                test_results['database_connection'],
                test_results['email_system'],
                test_results['concerts_configured'] > 0
            ])
            
        except Exception as e:
            logger.error(f"Error testing monitoring setup: {e}")
        
        return test_results
    
    def should_check_now(self, last_check: Optional[datetime] = None) -> bool:
        """
        Determine if price check should run now.
        
        Args:
            last_check: When prices were last checked
            
        Returns:
            True if should check prices now
        """
        if not last_check:
            return True
        
        time_since_check = datetime.now() - last_check
        return time_since_check >= timedelta(hours=self.check_frequency_hours)
    
    def cleanup_old_data(self, days_to_keep: int = 90) -> int:
        """
        Clean up old price history data.
        
        Args:
            days_to_keep: Number of days of history to retain
            
        Returns:
            Number of records deleted
        """
        logger.info(f"Cleaning up price history older than {days_to_keep} days")
        
        try:
            from .db_operations import cleanup_old_prices
            deleted_count = cleanup_old_prices(days_to_keep, self.db_path)
            
            # Also cleanup scraper resources
            self._cleanup_scraper()
            
            logger.info(f"Cleaned up {deleted_count} old price records")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
            return 0