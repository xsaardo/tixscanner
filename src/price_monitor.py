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
from .section_scraper import SectionBasedScraper
from .models import Concert, PriceHistory
from .db_operations import (
    get_all_concerts, get_latest_price, add_price_record,
    get_price_history, log_email
)
from .config_manager import ConfigManager

logger = logging.getLogger(__name__)


class PriceMonitor:
    """
    Main price monitoring engine.
    
    Coordinates API calls, price comparison, and email notifications.
    """
    
    def __init__(self, api_key: str, db_path: Optional[str] = None,
                 email_client: Optional[EmailClient] = None,
                 enable_scraping: bool = True,
                 config_path: Optional[str] = 'config.ini'):
        """
        Initialize price monitor.

        Args:
            api_key: Ticketmaster API key
            db_path: Database path for storage
            email_client: Email client for notifications
            enable_scraping: Enable web scraping fallback
            config_path: Path to configuration file
        """
        self.api_key = api_key
        self.db_path = db_path
        self.api_client = TicketmasterAPI(api_key)
        self.email_client = email_client or EmailClient(db_path=db_path)
        self.enable_scraping = enable_scraping
        self.scraper = None
        self.section_scraper = None

        # Load configuration for sections
        self.config_manager = ConfigManager(config_path) if config_path else None
        self.section_preferences = {}
        self.section_thresholds = {}
        if self.config_manager:
            self._load_section_preferences()
            self._load_section_thresholds()

        # Configuration defaults
        self.min_price_drop_percent = 10.0  # Minimum % drop to trigger alert
        self.check_frequency_hours = 2  # How often to check prices

        logger.info(f"Price monitor initialized (scraping: {'enabled' if enable_scraping else 'disabled'})")

    def _load_section_preferences(self):
        """Load section preferences from configuration."""
        try:
            sections_config = self.config_manager.config.items('sections')
            for event_id, sections_str in sections_config:
                # Parse comma-separated sections
                sections = [s.strip() for s in sections_str.split(',')]
                self.section_preferences[event_id] = sections
                logger.info(f"Loaded section preferences for {event_id}: {sections}")
        except Exception as e:
            logger.warning(f"Could not load section preferences: {e}")

    def _load_section_thresholds(self):
        """Load section-specific thresholds from configuration."""
        try:
            if self.config_manager.config.has_section('section_thresholds'):
                thresholds_config = self.config_manager.config.items('section_thresholds')
                for key, threshold_str in thresholds_config:
                    # Parse event_id.section_name format
                    if '.' in key:
                        event_id, section_name = key.split('.', 1)
                        if event_id not in self.section_thresholds:
                            self.section_thresholds[event_id] = {}
                        self.section_thresholds[event_id][section_name] = Decimal(threshold_str)
                        logger.info(f"Loaded threshold for {event_id}/{section_name}: ${threshold_str}")
        except Exception as e:
            logger.warning(f"Could not load section thresholds: {e}")

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
            section_prices = {}
            if not current_price and self.enable_scraping:
                logger.info(f"No API pricing for {concert.name}, trying web scraping...")
                section_prices = self._scrape_event_prices(concert.event_id)
                if section_prices:
                    data_source = 'scraping'
                    logger.info(f"Web scraping found {len(section_prices)} section prices for {concert.name}")

            # If we got API price, convert to section format
            if current_price:
                section_prices = {'General': current_price}

            if not section_prices:
                logger.warning(f"No price data found for {concert.name} (tried API and {'scraping' if self.enable_scraping else 'API only'})")
                return result

            result['section_prices'] = section_prices
            result['price_found'] = True
            result['data_source'] = data_source
            
            # Store all section prices in database and track changes
            result['section_changes'] = {}
            min_current_price = None

            for section_name, price in section_prices.items():
                # Get previous price for this section
                from .db_operations import get_latest_section_price
                previous_section_price = get_latest_section_price(concert.event_id, section_name, self.db_path)

                section_change_data = {
                    'current': price,
                    'previous': previous_section_price.price if previous_section_price else None,
                    'change': None,
                    'change_percent': None
                }

                if previous_section_price:
                    price_change = price - previous_section_price.price
                    section_change_data['change'] = price_change
                    if previous_section_price.price > 0:
                        change_percent = (price_change / previous_section_price.price) * 100
                        section_change_data['change_percent'] = float(change_percent)

                result['section_changes'][section_name] = section_change_data

                # Track minimum current price for threshold comparison
                if min_current_price is None or price < min_current_price:
                    min_current_price = price

                # Store price in database
                price_history = PriceHistory(
                    event_id=concert.event_id,
                    price=price,
                    section=section_name,
                    recorded_at=datetime.now()
                )
                add_price_record(price_history, self.db_path)
                logger.debug(f"Stored price for {concert.name}/{section_name}: ${price}")
            
            # Check section prices against thresholds and for significant drops
            sections_below_threshold = []
            significant_drops = []

            for section_name, section_data in result['section_changes'].items():
                # Get threshold for this section (use section-specific or fall back to default)
                section_threshold = self._get_section_threshold(concert.event_id, section_name, concert.threshold_price)

                # Check if price is below threshold
                if section_data['current'] <= section_threshold:
                    sections_below_threshold.append({
                        'section': section_name,
                        'current': section_data['current'],
                        'threshold': section_threshold
                    })

                # Check for significant price drop
                if (section_data['change_percent'] is not None and
                    section_data['change_percent'] <= -self.min_price_drop_percent):
                    significant_drops.append({
                        'section': section_name,
                        'previous': section_data['previous'],
                        'current': section_data['current'],
                        'drop_percent': abs(section_data['change_percent']),
                        'threshold': section_threshold
                    })

            result['sections_below_threshold'] = sections_below_threshold
            result['significant_drops'] = significant_drops

            # Send price alert if conditions are met
            if significant_drops or sections_below_threshold:
                try:
                    # For now use existing send_price_alert with the lowest price
                    alert_prices = [s['current'] for s in sections_below_threshold] + [s['current'] for s in significant_drops]
                    if alert_prices:
                        min_alert_price = min(alert_prices)
                        # Find previous price for this section
                        prev_price = min_alert_price
                        for section_name, section_data in result['section_changes'].items():
                            if section_data['current'] == min_alert_price and section_data['previous']:
                                prev_price = section_data['previous']
                                break

                        if self.email_client.send_price_alert(
                            concert.event_id,
                            prev_price,
                            min_alert_price
                        ):
                            result['alert_sent'] = True
                            logger.info(f"Price alert sent for {concert.name}: {len(sections_below_threshold)} sections below threshold, {len(significant_drops)} significant drops")
                except Exception as e:
                    logger.error(f"Failed to send price alert for {concert.name}: {e}")

            logger.debug(f"Price check completed for {concert.name}: {len(section_prices)} sections tracked")
            
        except Exception as e:
            logger.error(f"Error checking price for {concert.name}: {e}")
            result['error'] = str(e)
        
        return result
    
    def _get_section_threshold(self, event_id: str, section_name: str, default_threshold: Decimal) -> Decimal:
        """
        Get threshold for a specific section, falling back to default if not configured.

        Args:
            event_id: Event identifier
            section_name: Section name
            default_threshold: Default threshold to use if no section-specific threshold exists

        Returns:
            Threshold price for the section
        """
        if event_id in self.section_thresholds and section_name in self.section_thresholds[event_id]:
            return self.section_thresholds[event_id][section_name]
        return default_threshold

    def _scrape_event_prices(self, event_id: str) -> Dict[str, Decimal]:
        """
        Scrape prices for all sections of an event using web scraping.

        Args:
            event_id: Ticketmaster event ID

        Returns:
            Dictionary mapping section names to prices (Decimal)
        """
        try:
            # First try to get the proper URL from API
            event_details = self.api_client.get_event_details(event_id)
            if event_details and event_details.get('url'):
                event_url = event_details['url']
            else:
                # Fallback to constructed URL
                event_url = f"https://www.ticketmaster.com/event/{event_id}"

            logger.debug(f"Scraping URL for {event_id}: {event_url}")

            # Check if this event has section preferences
            if event_id in self.section_preferences:
                # Use section-based scraper for this event
                target_sections = self.section_preferences[event_id]
                logger.info(f"Using section-based scraping for {event_id}, sections: {target_sections}")

                # Initialize section scraper if needed
                if not self.section_scraper:
                    self.section_scraper = SectionBasedScraper(headless=False, timeout=30)

                # Scrape prices for the specified sections
                result = self.section_scraper.scrape_section_prices(event_url, sections=target_sections)

                if result['success'] and result['sections']:
                    # Collect prices for all sections
                    section_prices = {}
                    for section_name, section_data in result['sections'].items():
                        if section_data.get('price'):
                            section_prices[section_name] = Decimal(str(section_data['price']))
                            logger.info(f"Found price for {section_name}: ${section_data['price']}")

                    if section_prices:
                        logger.info(f"Section scraping found {len(section_prices)} section prices for {event_id}")
                        return section_prices
                    else:
                        logger.warning(f"Section scraping found no prices for {event_id}")
                        return {}
                else:
                    logger.warning(f"Section scraping failed for {event_id}: {result.get('error')}")
                    return {}

            # Fallback to regular scraping if no section preferences
            logger.info(f"Using standard scraping for {event_id}")

            # Initialize optimized scraper if needed
            if not self.scraper:
                self.scraper = TicketmasterOptimizedScraper(headless=True, timeout=30)

            # Get user-configured target sections for this event (legacy config check)
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
                # Return general admission with the min price if no specific sections
                return {'General': Decimal(str(pricing_data['min_price']))}
            else:
                logger.debug(f"Web scraping failed for {event_id}: {pricing_data.get('error', 'No pricing data')}")
                return {}

        except Exception as e:
            logger.error(f"Error during web scraping for {event_id}: {e}")
            return {}
    
    def _cleanup_scraper(self) -> None:
        """Clean up web scraper resources."""
        if self.scraper:
            try:
                self.scraper.close()
                self.scraper = None
                logger.debug("Web scraper cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up scraper: {e}")

        if self.section_scraper:
            try:
                self.section_scraper.close()
                self.section_scraper = None
                logger.debug("Section scraper cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up section scraper: {e}")
    
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