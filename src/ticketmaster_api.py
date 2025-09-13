"""
Ticketmaster API client for TixScanner.

This module provides integration with the Ticketmaster Discovery API
to fetch event details and ticket pricing information.
"""

import requests
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from urllib.parse import urljoin
import os
from dotenv import load_dotenv

from .rate_limiter import RateLimiter
from .api_cache import APICache

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class TicketmasterAPIError(Exception):
    """Base exception for Ticketmaster API errors."""
    pass


class RateLimitError(TicketmasterAPIError):
    """Raised when API rate limit is exceeded."""
    pass


class AuthenticationError(TicketmasterAPIError):
    """Raised when API authentication fails."""
    pass


class EventNotFoundError(TicketmasterAPIError):
    """Raised when event is not found."""
    pass


class TicketmasterAPI:
    """
    Ticketmaster Discovery API client with rate limiting and caching.
    
    Provides methods to fetch event details and ticket pricing information
    while respecting API rate limits and caching responses for efficiency.
    """
    
    BASE_URL = "https://app.ticketmaster.com/discovery/v2"
    
    def __init__(self, api_key: Optional[str] = None, cache_duration: int = 30):
        """
        Initialize the Ticketmaster API client.
        
        Args:
            api_key: Ticketmaster API key (if None, loads from environment)
            cache_duration: Cache duration in minutes (default: 30)
        """
        self.api_key = api_key or os.getenv('TICKETMASTER_API_KEY')
        if not self.api_key:
            raise AuthenticationError("Ticketmaster API key not provided")
        
        self.cache_duration = cache_duration
        self.session = requests.Session()
        
        # Initialize rate limiter and cache
        self.rate_limiter = RateLimiter(max_requests=5000, time_window=86400)  # 5000 per day
        self.cache = APICache(cache_duration_minutes=cache_duration)
        
        # Set up session headers
        self.session.headers.update({
            'User-Agent': 'TixScanner/1.0 (Ticket Price Monitor)',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        logger.info("Ticketmaster API client initialized")
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None, 
                     use_cache: bool = True) -> Optional[Dict]:
        """
        Make a request to the Ticketmaster API with rate limiting and caching.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            use_cache: Whether to use caching for this request
            
        Returns:
            API response data or None if failed
            
        Raises:
            RateLimitError: If rate limit is exceeded
            AuthenticationError: If authentication fails
            TicketmasterAPIError: For other API errors
        """
        # Set up parameters
        if params is None:
            params = {}
        params['apikey'] = self.api_key
        
        # Build full URL - ensure proper joining
        base_url = self.BASE_URL.rstrip('/')
        endpoint = endpoint.lstrip('/')
        url = f"{base_url}/{endpoint}"
        
        # Check cache first if enabled
        if use_cache:
            cache_key = f"{url}:{str(sorted(params.items()))}"
            cached_response = self.cache.get(cache_key)
            if cached_response is not None:
                logger.debug(f"Cache hit for {endpoint}")
                return cached_response
        
        # Check rate limit
        if not self.rate_limiter.can_make_request():
            raise RateLimitError("API rate limit exceeded")
        
        try:
            logger.debug(f"Making API request to {endpoint}")
            start_time = time.time()
            
            response = self.session.get(url, params=params, timeout=30)
            
            # Log response time
            response_time = time.time() - start_time
            logger.debug(f"API request completed in {response_time:.2f}s")
            
            # Record the request for rate limiting
            self.rate_limiter.record_request()
            
            # Handle different response codes
            if response.status_code == 200:
                data = response.json()
                
                # Cache successful response
                if use_cache:
                    self.cache.set(cache_key, data)
                
                return data
                
            elif response.status_code == 401:
                raise AuthenticationError("Invalid API key")
                
            elif response.status_code == 404:
                logger.warning(f"Resource not found: {endpoint}")
                return None
                
            elif response.status_code == 429:
                raise RateLimitError("API rate limit exceeded")
                
            else:
                logger.error(f"API request failed with status {response.status_code}: {response.text}")
                raise TicketmasterAPIError(f"API request failed: {response.status_code}")
        
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for {endpoint}")
            raise TicketmasterAPIError("Request timeout")
            
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error for {endpoint}")
            raise TicketmasterAPIError("Connection error")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {endpoint}: {e}")
            raise TicketmasterAPIError(f"Request error: {e}")
    
    def get_event_details(self, event_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific event.
        
        Args:
            event_id: Ticketmaster event ID
            
        Returns:
            Dictionary with event details or None if not found
            
        Example:
            {
                'id': 'G5vYZ4F1pE4G1',
                'name': 'Taylor Swift | The Eras Tour',
                'venue': 'MetLife Stadium',
                'city': 'East Rutherford',
                'state': 'NJ',
                'date': '2024-05-18',
                'time': '19:00:00',
                'timezone': 'America/New_York',
                'url': 'https://www.ticketmaster.com/event/...',
                'status': 'onsale',
                'price_ranges': [...]
            }
        """
        try:
            endpoint = f"/events/{event_id}"
            response = self._make_request(endpoint)
            
            if not response:
                return None
            
            # Extract event data
            event_data = self._parse_event_details(response)
            
            logger.info(f"Retrieved event details for {event_id}: {event_data.get('name', 'Unknown')}")
            return event_data
            
        except EventNotFoundError:
            logger.warning(f"Event not found: {event_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to get event details for {event_id}: {e}")
            return None
    
    def get_ticket_prices(self, event_id: str) -> List[Dict]:
        """
        Get current ticket pricing information for an event.
        
        Args:
            event_id: Ticketmaster event ID
            
        Returns:
            List of pricing information dictionaries
            
        Example:
            [
                {
                    'section': 'Floor',
                    'price': 150.00,
                    'currency': 'USD',
                    'type': 'primary',
                    'availability': 'available'
                },
                ...
            ]
        """
        try:
            # Get event details which includes pricing
            event_details = self.get_event_details(event_id)
            
            if not event_details:
                logger.warning(f"No event details found for {event_id}")
                return []
            
            # Extract pricing information
            prices = self._parse_pricing_data(event_details)
            
            logger.info(f"Retrieved {len(prices)} price entries for event {event_id}")
            return prices
            
        except Exception as e:
            logger.error(f"Failed to get ticket prices for {event_id}: {e}")
            return []
    
    def search_events(self, query: str, city: Optional[str] = None, 
                     size: int = 20, page: int = 0) -> List[Dict]:
        """
        Search for events by name and optionally by city.
        
        Args:
            query: Search query (artist name, event name, etc.)
            city: City to search in (optional)
            size: Number of results per page (max 200)
            page: Page number (0-based)
            
        Returns:
            List of event dictionaries
        """
        try:
            params = {
                'keyword': query,
                'size': min(size, 200),  # API max is 200
                'page': page,
                'sort': 'date,asc'
            }
            
            if city:
                params['city'] = city
            
            endpoint = "/events"
            response = self._make_request(endpoint, params)
            
            if not response or '_embedded' not in response:
                return []
            
            events = response['_embedded'].get('events', [])
            search_results = []
            
            for event in events:
                event_data = self._parse_event_details(event)
                if event_data:
                    search_results.append(event_data)
            
            logger.info(f"Found {len(search_results)} events for query '{query}'")
            return search_results
            
        except Exception as e:
            logger.error(f"Failed to search events for '{query}': {e}")
            return []
    
    def _parse_event_details(self, response: Dict) -> Optional[Dict]:
        """
        Parse event details from API response.
        
        Args:
            response: Raw API response
            
        Returns:
            Parsed event data dictionary
        """
        try:
            # Handle both single event and embedded events responses
            if '_embedded' in response and 'events' in response['_embedded']:
                events = response['_embedded']['events']
                if not events:
                    return None
                event = events[0]
            else:
                event = response
            
            # Extract basic event info
            event_data = {
                'id': event.get('id'),
                'name': event.get('name'),
                'url': event.get('url'),
                'status': event.get('dates', {}).get('status', {}).get('code', 'unknown'),
                'price_ranges': []
            }
            
            # Extract venue information
            if '_embedded' in event and 'venues' in event['_embedded']:
                venue = event['_embedded']['venues'][0]
                event_data.update({
                    'venue': venue.get('name'),
                    'city': venue.get('city', {}).get('name'),
                    'state': venue.get('state', {}).get('name'),
                    'country': venue.get('country', {}).get('name')
                })
            
            # Extract date and time information
            dates = event.get('dates', {})
            if 'start' in dates:
                start = dates['start']
                event_data.update({
                    'date': start.get('localDate'),
                    'time': start.get('localTime'),
                    'timezone': start.get('timeZone')
                })
            
            # Extract price ranges
            price_ranges = event.get('priceRanges', [])
            for price_range in price_ranges:
                event_data['price_ranges'].append({
                    'type': price_range.get('type'),
                    'currency': price_range.get('currency'),
                    'min': price_range.get('min'),
                    'max': price_range.get('max')
                })
            
            return event_data
            
        except Exception as e:
            logger.error(f"Failed to parse event details: {e}")
            return None
    
    def _parse_pricing_data(self, event_data: Dict) -> List[Dict]:
        """
        Parse pricing data from event details.
        
        Args:
            event_data: Parsed event data
            
        Returns:
            List of pricing dictionaries
        """
        prices = []
        
        try:
            # Extract price ranges
            for price_range in event_data.get('price_ranges', []):
                if price_range.get('min') is not None:
                    prices.append({
                        'section': price_range.get('type', 'General'),
                        'price': float(price_range['min']),
                        'price_max': float(price_range.get('max', price_range['min'])),
                        'currency': price_range.get('currency', 'USD'),
                        'type': 'primary',
                        'availability': 'available'
                    })
            
            # If no price ranges, create a placeholder
            if not prices:
                logger.debug("No price ranges found in event data")
            
            return prices
            
        except Exception as e:
            logger.error(f"Failed to parse pricing data: {e}")
            return []
    
    def get_api_usage_stats(self) -> Dict:
        """
        Get current API usage statistics.
        
        Returns:
            Dictionary with usage statistics
        """
        return {
            'requests_made': self.rate_limiter.get_current_usage(),
            'requests_remaining': self.rate_limiter.get_remaining_requests(),
            'cache_stats': self.cache.get_stats(),
            'rate_limit_resets_at': self.rate_limiter.get_reset_time()
        }
    
    def clear_cache(self) -> None:
        """Clear the API response cache."""
        self.cache.clear()
        logger.info("API cache cleared")
    
    def is_healthy(self) -> bool:
        """
        Check if the API client is healthy and can make requests.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try a simple API call to check connectivity
            response = self._make_request("/events", {'size': 1}, use_cache=False)
            return response is not None
        except Exception:
            return False
    
    def test_connection(self) -> bool:
        """
        Test API connection (alias for is_healthy).
        
        Returns:
            True if connection works, False otherwise
        """
        return self.is_healthy()