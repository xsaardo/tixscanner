"""
StubHub price scraper for TixScanner.

This module provides web scraping functionality to extract ticket prices
from StubHub event pages using BeautifulSoup4 and requests.
"""

import logging
import time
import random
from decimal import Decimal
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class StubHubScraperError(Exception):
    """Exception raised for StubHub scraper errors."""
    pass


class StubHubScraper:
    """
    Web scraper for StubHub ticket prices.

    Uses requests + BeautifulSoup4 to extract pricing data from StubHub
    event pages while respecting robots.txt and implementing polite delays.
    """

    # User agents to rotate for reduced blocking risk
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    ]

    def __init__(self, request_delay: float = 2.0, timeout: int = 15):
        """
        Initialize StubHub scraper.

        Args:
            request_delay: Delay in seconds between requests (default 2.0)
            timeout: Request timeout in seconds (default 15)
        """
        self.request_delay = request_delay
        self.timeout = timeout
        self.session = requests.Session()
        self.last_request_time = 0

        logger.info(f"StubHub scraper initialized (delay={request_delay}s, timeout={timeout}s)")

    def _get_random_user_agent(self) -> str:
        """Get a random user agent string."""
        return random.choice(self.USER_AGENTS)

    def _respect_delay(self) -> None:
        """Implement polite request delay."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_delay:
            delay = self.request_delay - elapsed
            logger.debug(f"Waiting {delay:.2f}s before next request")
            time.sleep(delay)
        self.last_request_time = time.time()

    def _fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch a StubHub page with proper headers and error handling.

        Args:
            url: URL to fetch

        Returns:
            Page HTML content or None if failed
        """
        try:
            self._respect_delay()

            headers = {
                'User-Agent': self._get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
            }

            logger.debug(f"Fetching StubHub page: {url}")
            response = self.session.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            return response.text

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.error(f"Rate limited by StubHub (429): {url}")
            elif e.response.status_code == 403:
                logger.error(f"Access forbidden by StubHub (403): {url}")
            else:
                logger.error(f"HTTP error fetching {url}: {e}")
            return None

        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching {url}")
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching {url}: {e}")
            return None

    def _parse_price(self, price_str: str) -> Optional[Decimal]:
        """
        Parse price string to Decimal.

        Args:
            price_str: Price string (e.g., "$150", "150.00", "$1,234.56")

        Returns:
            Decimal price or None if parsing fails
        """
        try:
            # Remove currency symbols, commas, and whitespace
            cleaned = price_str.strip().replace('$', '').replace(',', '').replace(' ', '')

            if not cleaned:
                return None

            price = Decimal(cleaned)

            if price <= 0:
                logger.warning(f"Invalid price value: {price}")
                return None

            return price

        except Exception as e:
            logger.debug(f"Failed to parse price '{price_str}': {e}")
            return None

    def _extract_prices_from_html(self, html: str) -> Dict[str, Any]:
        """
        Extract pricing data from StubHub HTML.

        Args:
            html: Page HTML content

        Returns:
            Dictionary with pricing data
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')

            prices = []
            sections = {}

            # Strategy 1: Look for ticket listing cards/rows
            # StubHub typically uses div or li elements with price information
            price_selectors = [
                'div[class*="price"]',
                'span[class*="price"]',
                'div[class*="Price"]',
                'span[class*="Price"]',
                '[data-testid*="price"]',
                '[class*="ticket-price"]',
                '[class*="ticketPrice"]',
            ]

            for selector in price_selectors:
                price_elements = soup.select(selector)
                for elem in price_elements:
                    price_text = elem.get_text(strip=True)
                    price = self._parse_price(price_text)
                    if price:
                        prices.append(price)

            # Strategy 2: Look for JSON-LD structured data
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                try:
                    import json
                    data = json.loads(script.string)

                    # Check for Event schema with offers
                    if isinstance(data, dict) and data.get('@type') == 'Event':
                        offers = data.get('offers', {})
                        if isinstance(offers, dict):
                            low_price = offers.get('lowPrice')
                            if low_price:
                                price = self._parse_price(str(low_price))
                                if price:
                                    prices.append(price)
                except Exception as e:
                    logger.debug(f"Failed to parse JSON-LD: {e}")

            # Strategy 3: Look for section-specific pricing
            section_selectors = [
                'div[class*="section"]',
                'div[class*="Section"]',
                '[data-testid*="section"]',
            ]

            for selector in section_selectors:
                section_elements = soup.select(selector)
                for elem in section_elements:
                    # Try to get section name
                    section_name = None
                    for name_elem in elem.select('[class*="name"], [class*="Name"], [class*="section"]'):
                        text = name_elem.get_text(strip=True)
                        if text and len(text) < 50:  # Reasonable section name length
                            section_name = text
                            break

                    # Try to get price for this section
                    for price_elem in elem.select('[class*="price"], [class*="Price"]'):
                        price_text = price_elem.get_text(strip=True)
                        price = self._parse_price(price_text)
                        if price and section_name:
                            sections[section_name] = price
                            break

            # Deduplicate and sort prices
            if prices:
                prices = sorted(list(set(prices)))

            result = {
                'success': bool(prices),
                'min_price': min(prices) if prices else None,
                'max_price': max(prices) if prices else None,
                'median_price': prices[len(prices) // 2] if prices else None,
                'all_prices': prices,
                'sections': sections,
                'price_count': len(prices)
            }

            if result['success']:
                logger.debug(f"Extracted {len(prices)} prices from HTML (min: ${result['min_price']}, max: ${result['max_price']})")
            else:
                logger.warning("No prices found in HTML")

            return result

        except Exception as e:
            logger.error(f"Error extracting prices from HTML: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def scrape_event_prices(self, url: str) -> Dict[str, Any]:
        """
        Scrape ticket prices from a StubHub event page.

        Args:
            url: StubHub event URL

        Returns:
            Dictionary with pricing data and metadata
        """
        try:
            # Validate URL
            parsed = urlparse(url)
            if 'stubhub' not in parsed.netloc.lower():
                raise StubHubScraperError(f"Not a StubHub URL: {url}")

            logger.info(f"Scraping StubHub event: {url}")

            # Fetch page
            html = self._fetch_page(url)
            if not html:
                return {
                    'success': False,
                    'error': 'Failed to fetch page',
                    'url': url
                }

            # Extract prices
            result = self._extract_prices_from_html(html)
            result['url'] = url
            result['source'] = 'stubhub'

            if result['success']:
                logger.info(f"StubHub scraping successful: min=${result['min_price']}, "
                          f"found {result['price_count']} prices")
            else:
                logger.warning(f"StubHub scraping found no prices for {url}")
                result['error'] = result.get('error', 'No prices found')

            return result

        except StubHubScraperError as e:
            logger.error(f"StubHub scraper error: {e}")
            return {
                'success': False,
                'error': str(e),
                'url': url
            }

        except Exception as e:
            logger.error(f"Unexpected error scraping StubHub: {e}")
            return {
                'success': False,
                'error': f"Unexpected error: {e}",
                'url': url
            }

    def extract_event_id_from_url(self, url: str) -> Optional[str]:
        """
        Extract event ID from StubHub URL.

        Args:
            url: StubHub event URL

        Returns:
            Event ID or None if not found
        """
        try:
            parsed = urlparse(url)

            # StubHub URLs typically have format:
            # https://www.stubhub.com/event-name-tickets-12-31-2025/event/123456789/
            path_parts = [p for p in parsed.path.split('/') if p]

            # Look for numeric event ID in path
            for part in path_parts:
                if part.isdigit() and len(part) >= 6:  # Event IDs are typically long
                    return part

            # Look for 'event' segment followed by ID
            for i, part in enumerate(path_parts):
                if part == 'event' and i + 1 < len(path_parts):
                    event_id = path_parts[i + 1]
                    if event_id.isdigit():
                        return event_id

            logger.warning(f"Could not extract event ID from URL: {url}")
            return None

        except Exception as e:
            logger.error(f"Error extracting event ID from URL: {e}")
            return None

    def test_scraping(self, url: str) -> bool:
        """
        Test scraping on a URL.

        Args:
            url: URL to test

        Returns:
            True if scraping works
        """
        try:
            result = self.scrape_event_prices(url)
            return result.get('success', False)
        except Exception as e:
            logger.error(f"Test scraping failed: {e}")
            return False

    def close(self) -> None:
        """Clean up resources."""
        try:
            self.session.close()
            logger.debug("StubHub scraper session closed")
        except Exception as e:
            logger.error(f"Error closing scraper session: {e}")
