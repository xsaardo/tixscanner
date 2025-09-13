"""
Web scraper for Ticketmaster event pricing.

Uses Selenium WebDriver to bypass anti-bot protection and extract
pricing information from event pages.
"""

import logging
import time
import random
from typing import Optional, List, Dict, Any
from decimal import Decimal
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)


class WebScrapingError(Exception):
    """Exception raised for web scraping errors."""
    pass


class TicketmasterScraper:
    """
    Web scraper for extracting pricing data from Ticketmaster event pages.
    
    Uses Selenium WebDriver with Chrome to handle JavaScript-heavy pages
    and bypass anti-bot protection.
    """
    
    def __init__(self, headless: bool = True, timeout: int = 30):
        """
        Initialize the scraper.
        
        Args:
            headless: Run browser in headless mode
            timeout: Page load timeout in seconds
        """
        self.headless = headless
        self.timeout = timeout
        self.driver = None
        self._setup_driver()
        
        logger.info("Ticketmaster scraper initialized")
    
    def _setup_driver(self) -> None:
        """Set up Chrome WebDriver with optimal settings."""
        try:
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument("--headless")
            
            # Anti-detection measures
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")
            chrome_options.add_argument("--disable-javascript")  # We'll enable when needed
            
            # Realistic browser settings
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # Install ChromeDriver automatically
            service = Service(ChromeDriverManager().install())
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(self.timeout)
            
            logger.debug("Chrome WebDriver initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            raise WebScrapingError(f"WebDriver initialization failed: {e}")
    
    def scrape_event_pricing(self, event_url: str) -> Dict[str, Any]:
        """
        Scrape pricing information from a Ticketmaster event page.
        
        Args:
            event_url: Full URL to the Ticketmaster event page
            
        Returns:
            Dictionary with pricing information
            
        Raises:
            WebScrapingError: If scraping fails
        """
        logger.info(f"Scraping pricing for: {event_url}")
        
        if not self.driver:
            raise WebScrapingError("WebDriver not initialized")
        
        pricing_data = {
            'url': event_url,
            'prices': [],
            'min_price': None,
            'max_price': None,
            'currency': 'USD',
            'scraped_at': time.time(),
            'success': False,
            'error': None
        }
        
        try:
            # Navigate to the page
            logger.debug(f"Loading page: {event_url}")
            self.driver.get(event_url)
            
            # Wait for page to load
            time.sleep(random.uniform(2, 5))  # Random delay
            
            # Check if page loaded successfully
            if "Access to this page has been denied" in self.driver.page_source:
                raise WebScrapingError("Access denied - bot detection")
            
            if self.driver.current_url != event_url and "error" in self.driver.current_url.lower():
                raise WebScrapingError("Page redirected to error page")
            
            # Get page source for parsing
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Extract pricing information using multiple strategies
            prices = self._extract_prices_from_html(soup)
            
            if prices:
                pricing_data['prices'] = prices
                pricing_data['min_price'] = min(p['price'] for p in prices)
                pricing_data['max_price'] = max(p['price'] for p in prices)
                pricing_data['success'] = True
                
                logger.info(f"Successfully scraped {len(prices)} price points")
                logger.debug(f"Price range: ${pricing_data['min_price']:.2f} - ${pricing_data['max_price']:.2f}")
            else:
                logger.warning("No pricing data found on page")
                pricing_data['error'] = "No pricing data found"
            
            return pricing_data
            
        except TimeoutException:
            error_msg = f"Page load timeout for {event_url}"
            logger.error(error_msg)
            pricing_data['error'] = error_msg
            return pricing_data
            
        except WebDriverException as e:
            error_msg = f"WebDriver error: {e}"
            logger.error(error_msg)
            pricing_data['error'] = error_msg
            return pricing_data
            
        except Exception as e:
            error_msg = f"Scraping error: {e}"
            logger.error(error_msg)
            pricing_data['error'] = error_msg
            return pricing_data
    
    def _extract_prices_from_html(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract pricing data from parsed HTML.
        
        Args:
            soup: BeautifulSoup parsed HTML
            
        Returns:
            List of price dictionaries
        """
        prices = []
        
        # Strategy 1: Look for price in meta tags
        prices.extend(self._extract_prices_from_meta(soup))
        
        # Strategy 2: Look for JSON-LD structured data
        prices.extend(self._extract_prices_from_json_ld(soup))
        
        # Strategy 3: Look for price classes and data attributes
        prices.extend(self._extract_prices_from_elements(soup))
        
        # Strategy 4: Look for price patterns in text
        prices.extend(self._extract_prices_from_text(soup))
        
        # Remove duplicates and invalid prices
        unique_prices = []
        seen_prices = set()
        
        for price_data in prices:
            price_key = (price_data['price'], price_data.get('section', ''))
            if price_key not in seen_prices and price_data['price'] > 0:
                unique_prices.append(price_data)
                seen_prices.add(price_key)
        
        return unique_prices
    
    def _extract_prices_from_meta(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract prices from meta tags."""
        prices = []
        
        # Common meta tag patterns
        meta_selectors = [
            'meta[property="product:price:amount"]',
            'meta[name="price"]',
            'meta[itemprop="price"]',
            'meta[itemprop="lowPrice"]',
            'meta[itemprop="highPrice"]'
        ]
        
        for selector in meta_selectors:
            elements = soup.select(selector)
            for elem in elements:
                price_str = elem.get('content', '')
                price = self._parse_price_string(price_str)
                if price:
                    prices.append({
                        'price': price,
                        'source': 'meta_tag',
                        'section': elem.get('data-section', 'general')
                    })
        
        return prices
    
    def _extract_prices_from_json_ld(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract prices from JSON-LD structured data."""
        prices = []
        
        scripts = soup.find_all('script', type='application/ld+json')
        
        for script in scripts:
            try:
                import json
                data = json.loads(script.string)
                
                # Handle different JSON-LD structures
                if isinstance(data, dict):
                    prices.extend(self._parse_json_ld_prices(data))
                elif isinstance(data, list):
                    for item in data:
                        prices.extend(self._parse_json_ld_prices(item))
                        
            except (json.JSONDecodeError, AttributeError):
                continue
        
        return prices
    
    def _parse_json_ld_prices(self, data: Dict) -> List[Dict[str, Any]]:
        """Parse prices from JSON-LD data structure."""
        prices = []
        
        # Common JSON-LD price patterns
        price_paths = [
            ['offers', 'price'],
            ['offers', 'lowPrice'],
            ['offers', 'highPrice'],
            ['priceRange'],
            ['price']
        ]
        
        for path in price_paths:
            value = data
            for key in path:
                value = value.get(key) if isinstance(value, dict) else None
                if value is None:
                    break
            
            if value:
                price = self._parse_price_string(str(value))
                if price:
                    prices.append({
                        'price': price,
                        'source': 'json_ld',
                        'section': 'structured_data'
                    })
        
        return prices
    
    def _extract_prices_from_elements(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract prices from HTML elements with price-related classes."""
        prices = []
        
        # Common price selectors
        price_selectors = [
            '[class*="price"]',
            '[class*="Price"]',
            '[data-price]',
            '[class*="cost"]',
            '[class*="amount"]',
            '.ticket-price',
            '.price-display',
            '.ticket-cost'
        ]
        
        for selector in price_selectors:
            elements = soup.select(selector)
            for elem in elements:
                # Try getting price from data attribute first
                price_str = elem.get('data-price', '') or elem.get_text(strip=True)
                price = self._parse_price_string(price_str)
                
                if price:
                    section = elem.get('data-section', '') or self._extract_section_from_context(elem)
                    prices.append({
                        'price': price,
                        'source': 'element_class',
                        'section': section or 'general'
                    })
        
        return prices
    
    def _extract_prices_from_text(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract prices from text content using regex patterns."""
        prices = []
        
        # Price regex patterns
        price_patterns = [
            r'\\$([0-9]+(?:\\.[0-9]{2})?)',  # $99.99
            r'([0-9]+(?:\\.[0-9]{2})?)\\s*(?:USD|dollars?)',  # 99.99 USD
            r'(?:from|starting|as low as)\\s*\\$([0-9]+(?:\\.[0-9]{2})?)',  # from $99.99
        ]
        
        text_content = soup.get_text()
        
        for pattern in price_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            for match in matches:
                price = self._parse_price_string(str(match))
                if price and 10 <= price <= 10000:  # Reasonable price range
                    prices.append({
                        'price': price,
                        'source': 'text_regex',
                        'section': 'general'
                    })
        
        return prices
    
    def _parse_price_string(self, price_str: str) -> Optional[float]:
        """
        Parse a price string into a float value.
        
        Args:
            price_str: String containing price information
            
        Returns:
            Price as float or None if parsing fails
        """
        if not price_str:
            return None
        
        # Clean the string
        price_str = str(price_str).strip().replace(',', '').replace('$', '')
        
        # Extract numeric value
        match = re.search(r'([0-9]+(?:\.[0-9]{1,2})?)', price_str)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        
        return None
    
    def _extract_section_from_context(self, element) -> str:
        """Extract section information from element context."""
        # Look for section info in parent elements
        current = element.parent
        for _ in range(3):  # Check up to 3 levels up
            if current:
                class_names = current.get('class', [])
                for class_name in class_names:
                    if any(section in class_name.lower() for section in ['section', 'tier', 'level', 'area']):
                        return class_name
                current = current.parent
        return 'general'
    
    def close(self) -> None:
        """Close the WebDriver."""
        if self.driver:
            try:
                self.driver.quit()
                logger.debug("WebDriver closed successfully")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {e}")
            finally:
                self.driver = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        
    def test_scraping_capability(self) -> Dict[str, Any]:
        """
        Test the scraper's capability with a simple page.
        
        Returns:
            Dictionary with test results
        """
        test_url = "https://httpbin.org/html"
        
        try:
            logger.info("Testing scraper capability...")
            self.driver.get(test_url)
            time.sleep(2)
            
            page_title = self.driver.title
            page_length = len(self.driver.page_source)
            
            return {
                'success': True,
                'page_title': page_title,
                'page_length': page_length,
                'driver_ready': self.driver is not None
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'driver_ready': self.driver is not None
            }