"""
Data transformation utilities for TixScanner.

This module provides utilities to transform API responses into internal
data models and handle data validation and normalization.
"""

import logging
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Optional, Dict, List, Any
import re
from dateutil import parser as date_parser
import pytz

from .models import Concert, PriceHistory

logger = logging.getLogger(__name__)


class DataTransformationError(Exception):
    """Exception raised when data transformation fails."""
    pass


class TicketmasterTransformer:
    """
    Transformer for Ticketmaster API responses.
    
    Handles conversion of Ticketmaster API data to internal models
    with proper validation and error handling.
    """
    
    def __init__(self):
        """Initialize the transformer."""
        logger.debug("Ticketmaster transformer initialized")
    
    def api_event_to_concert(self, event_data: Dict, threshold_price: Decimal) -> Optional[Concert]:
        """
        Convert Ticketmaster event data to Concert model.
        
        Args:
            event_data: Raw event data from Ticketmaster API
            threshold_price: Price threshold for alerts
            
        Returns:
            Concert instance or None if transformation fails
        """
        try:
            # Extract basic event information
            event_id = event_data.get('id')
            if not event_id:
                raise DataTransformationError("Event ID is required")
            
            name = event_data.get('name')
            if not name:
                raise DataTransformationError("Event name is required")
            
            # Extract venue information
            venue = None
            city = None
            if '_embedded' in event_data and 'venues' in event_data['_embedded']:
                venue_data = event_data['_embedded']['venues'][0]
                venue = venue_data.get('name')
                if venue_data.get('city'):
                    city = venue_data['city'].get('name')
            
            # Combine venue and city for full venue string
            if venue and city:
                venue_full = f"{venue}, {city}"
            elif venue:
                venue_full = venue
            else:
                venue_full = None
            
            # Extract and parse event date
            event_date = None
            if 'dates' in event_data and 'start' in event_data['dates']:
                start_data = event_data['dates']['start']
                date_str = start_data.get('localDate')
                if date_str:
                    try:
                        event_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except ValueError as e:
                        logger.warning(f"Failed to parse event date '{date_str}': {e}")
            
            # Create Concert instance
            concert = Concert(
                event_id=event_id,
                name=name,
                venue=venue_full,
                event_date=event_date,
                threshold_price=threshold_price
            )
            
            logger.debug(f"Transformed event to concert: {concert.name}")
            return concert
            
        except Exception as e:
            logger.error(f"Failed to transform event data to concert: {e}")
            return None
    
    def api_prices_to_price_history(self, event_id: str, 
                                   price_data: List[Dict]) -> List[PriceHistory]:
        """
        Convert price data to PriceHistory models.
        
        Args:
            event_id: Ticketmaster event ID
            price_data: List of price dictionaries from API
            
        Returns:
            List of PriceHistory instances
        """
        price_records = []
        
        try:
            for price_info in price_data:
                try:
                    price_record = self._create_price_history(event_id, price_info)
                    if price_record:
                        price_records.append(price_record)
                except Exception as e:
                    logger.warning(f"Failed to transform price data: {e}")
                    continue
            
            logger.debug(f"Transformed {len(price_records)} price records for event {event_id}")
            return price_records
            
        except Exception as e:
            logger.error(f"Failed to transform price data: {e}")
            return []
    
    def _create_price_history(self, event_id: str, price_info: Dict) -> Optional[PriceHistory]:
        """
        Create a single PriceHistory instance from price data.
        
        Args:
            event_id: Event ID
            price_info: Single price information dictionary
            
        Returns:
            PriceHistory instance or None if creation fails
        """
        try:
            # Extract and validate price
            price_value = price_info.get('price')
            if price_value is None:
                return None
            
            try:
                price = Decimal(str(price_value))
                if price <= 0:
                    logger.warning(f"Invalid price value: {price_value}")
                    return None
            except (InvalidOperation, ValueError):
                logger.warning(f"Failed to parse price: {price_value}")
                return None
            
            # Extract other fields
            section = price_info.get('section', 'General')
            ticket_type = price_info.get('type', 'standard')
            availability = max(0, int(price_info.get('availability', 0)))
            
            # Create PriceHistory instance
            price_record = PriceHistory(
                event_id=event_id,
                price=price,
                section=section,
                ticket_type=ticket_type,
                availability=availability
            )
            
            return price_record
            
        except Exception as e:
            logger.error(f"Failed to create price history record: {e}")
            return None
    
    def normalize_venue_name(self, venue_name: str) -> str:
        """
        Normalize venue name for consistency.
        
        Args:
            venue_name: Raw venue name
            
        Returns:
            Normalized venue name
        """
        if not venue_name:
            return ""
        
        # Remove extra whitespace
        venue = venue_name.strip()
        
        # Common venue name normalizations
        normalizations = {
            r'\bStadium\b': 'Stadium',
            r'\bArena\b': 'Arena',
            r'\bCenter\b': 'Center',
            r'\bCentre\b': 'Centre',
            r'\bTheatre\b': 'Theatre',
            r'\bTheater\b': 'Theater',
            r'\bAmphitheatre\b': 'Amphitheatre',
            r'\bAmphitheater\b': 'Amphitheater'
        }
        
        for pattern, replacement in normalizations.items():
            venue = re.sub(pattern, replacement, venue, flags=re.IGNORECASE)
        
        return venue
    
    def parse_event_date(self, date_str: str, timezone_str: Optional[str] = None) -> Optional[date]:
        """
        Parse event date from various formats.
        
        Args:
            date_str: Date string in various formats
            timezone_str: Timezone string (optional)
            
        Returns:
            Parsed date or None if parsing fails
        """
        if not date_str:
            return None
        
        try:
            # Handle common date formats
            formats_to_try = [
                '%Y-%m-%d',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%SZ',
                '%m/%d/%Y',
                '%d/%m/%Y'
            ]
            
            for fmt in formats_to_try:
                try:
                    parsed_date = datetime.strptime(date_str, fmt).date()
                    return parsed_date
                except ValueError:
                    continue
            
            # Try using dateutil parser as fallback
            try:
                parsed_datetime = date_parser.parse(date_str)
                return parsed_datetime.date()
            except (ValueError, TypeError):
                pass
            
            logger.warning(f"Failed to parse date: {date_str}")
            return None
            
        except Exception as e:
            logger.error(f"Error parsing date '{date_str}': {e}")
            return None
    
    def extract_price_range(self, price_ranges: List[Dict]) -> Dict[str, Decimal]:
        """
        Extract min and max prices from price ranges.
        
        Args:
            price_ranges: List of price range dictionaries
            
        Returns:
            Dictionary with min_price and max_price
        """
        if not price_ranges:
            return {'min_price': None, 'max_price': None}
        
        all_prices = []
        
        try:
            for price_range in price_ranges:
                # Extract min and max from each range
                min_val = price_range.get('min')
                max_val = price_range.get('max')
                
                if min_val is not None:
                    try:
                        all_prices.append(Decimal(str(min_val)))
                    except (InvalidOperation, ValueError):
                        pass
                
                if max_val is not None and max_val != min_val:
                    try:
                        all_prices.append(Decimal(str(max_val)))
                    except (InvalidOperation, ValueError):
                        pass
            
            if not all_prices:
                return {'min_price': None, 'max_price': None}
            
            return {
                'min_price': min(all_prices),
                'max_price': max(all_prices)
            }
            
        except Exception as e:
            logger.error(f"Error extracting price range: {e}")
            return {'min_price': None, 'max_price': None}
    
    def validate_event_data(self, event_data: Dict) -> bool:
        """
        Validate that event data contains required fields.
        
        Args:
            event_data: Event data dictionary
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['id', 'name']
        
        for field in required_fields:
            if field not in event_data or not event_data[field]:
                logger.warning(f"Missing required field: {field}")
                return False
        
        # Check if event ID is valid format (alphanumeric)
        event_id = event_data['id']
        if not re.match(r'^[A-Za-z0-9]+$', event_id):
            logger.warning(f"Invalid event ID format: {event_id}")
            return False
        
        return True
    
    def clean_event_name(self, name: str) -> str:
        """
        Clean and normalize event name.
        
        Args:
            name: Raw event name
            
        Returns:
            Cleaned event name
        """
        if not name:
            return ""
        
        # Remove extra whitespace
        cleaned = name.strip()
        
        # Remove common suffixes that add no value
        suffixes_to_remove = [
            r'\s*\(Rescheduled\)',
            r'\s*\(Postponed\)',
            r'\s*\(New Date\)',
            r'\s*\(CANCELLED\)',
            r'\s*\(CANCELED\)'
        ]
        
        for suffix_pattern in suffixes_to_remove:
            cleaned = re.sub(suffix_pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Normalize multiple spaces to single space
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def extract_currency(self, price_ranges: List[Dict]) -> str:
        """
        Extract currency from price ranges.
        
        Args:
            price_ranges: List of price range dictionaries
            
        Returns:
            Currency code (defaults to 'USD')
        """
        for price_range in price_ranges:
            currency = price_range.get('currency')
            if currency:
                return currency.upper()
        
        return 'USD'  # Default currency
    
    def get_event_status_display(self, status_code: str) -> str:
        """
        Convert API status code to user-friendly display text.
        
        Args:
            status_code: Status code from API
            
        Returns:
            Human-readable status
        """
        status_mapping = {
            'onsale': 'On Sale',
            'offsale': 'Off Sale',
            'cancelled': 'Cancelled',
            'postponed': 'Postponed',
            'rescheduled': 'Rescheduled',
            'presale': 'Pre-sale',
            'soldout': 'Sold Out'
        }
        
        return status_mapping.get(status_code.lower(), status_code.title())