"""
Section-based web scraper for Ticketmaster event pricing.

Uses Selenium WebDriver to hover over specific sections and extract
pricing information from popups.
"""

import logging
import time
import random
from typing import Optional, List, Dict, Any
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import re

logger = logging.getLogger(__name__)


class SectionScrapingError(Exception):
    """Exception raised for section scraping errors."""
    pass


class SectionBasedScraper:
    """
    Web scraper that extracts ticket prices by hovering over specific sections.

    Uses Selenium WebDriver with Chrome to handle JavaScript interactions
    and extract pricing from hover popups.
    """

    def __init__(self, headless: bool = False, timeout: int = 30):
        """
        Initialize the scraper.

        Args:
            headless: Run browser in headless mode (False for hover interactions)
            timeout: Page load timeout in seconds
        """
        self.headless = headless
        self.timeout = timeout
        self.driver = None
        self.wait = None
        self._setup_driver()

        logger.info("Section-based scraper initialized")

    def _setup_driver(self) -> None:
        """Set up Chrome WebDriver with optimal settings for hover interactions."""
        try:
            chrome_options = Options()

            if self.headless:
                chrome_options.add_argument("--headless=new")

            # Essential options for stability
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            # Window size for proper rendering
            chrome_options.add_argument("--window-size=1920,1080")

            # User agent to appear more legitimate
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

            # Performance optimizations
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")

            # Install ChromeDriver automatically
            service = Service(ChromeDriverManager().install())

            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(self.timeout)
            self.wait = WebDriverWait(self.driver, self.timeout)

            # Execute script to remove webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            logger.debug("Chrome WebDriver initialized successfully for section scraping")

        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            raise SectionScrapingError(f"WebDriver initialization failed: {e}")

    def scrape_section_prices(self, event_url: str, sections: List[str] = None) -> Dict[str, Any]:
        """
        Scrape pricing information for specific sections from a Ticketmaster event page.

        Args:
            event_url: Full URL to the Ticketmaster event page
            sections: List of section names to check (e.g., ["GENERAL ADMISSION - Standing Room Only"])
                     If None, defaults to general admission

        Returns:
            Dictionary with pricing information by section

        Raises:
            SectionScrapingError: If scraping fails
        """
        if sections is None:
            sections = ["GENERAL ADMISSION - Standing Room Only"]

        logger.info(f"Scraping section prices for: {event_url}")
        logger.info(f"Target sections: {sections}")

        if not self.driver:
            raise SectionScrapingError("WebDriver not initialized")

        result = {
            'url': event_url,
            'sections': {},
            'scraped_at': time.time(),
            'success': False,
            'error': None
        }

        try:
            # Navigate to the page
            logger.debug(f"Loading page: {event_url}")
            self.driver.get(event_url)

            # Wait for initial page load
            time.sleep(random.uniform(3, 5))

            # Check for bot detection
            if "Access to this page has been denied" in self.driver.page_source:
                raise SectionScrapingError("Access denied - bot detection")

            # Wait for interactive map to load
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-section-name]'))
                )
                logger.debug("Interactive map loaded")
            except TimeoutException:
                logger.warning("Interactive map not found, trying alternative selectors")

            # Process each section
            for section_name in sections:
                section_data = self._extract_section_price(section_name)
                if section_data:
                    result['sections'][section_name] = section_data

            if result['sections']:
                result['success'] = True
                logger.info(f"Successfully scraped {len(result['sections'])} sections")
            else:
                result['error'] = "No section prices found"
                logger.warning("No section prices found")

            return result

        except TimeoutException:
            error_msg = f"Page load timeout for {event_url}"
            logger.error(error_msg)
            result['error'] = error_msg
            return result

        except WebDriverException as e:
            error_msg = f"WebDriver error: {e}"
            logger.error(error_msg)
            result['error'] = error_msg
            return result

        except Exception as e:
            error_msg = f"Scraping error: {e}"
            logger.error(error_msg)
            result['error'] = error_msg
            return result

    def _extract_section_price(self, section_name: str) -> Optional[Dict[str, Any]]:
        """
        Extract price for a specific section by hovering and reading popup.

        Args:
            section_name: The section name to hover over

        Returns:
            Dictionary with price information or None if not found
        """
        try:
            logger.debug(f"Looking for section: {section_name}")

            # Find the section element
            section_selector = f'[data-section-name="{section_name}"]'

            # Try multiple strategies to find the element
            section_element = None

            # Strategy 1: Direct data-section-name attribute
            try:
                section_element = self.driver.find_element(By.CSS_SELECTOR, section_selector)
                logger.debug(f"Found section using data-section-name: {section_name}")
            except NoSuchElementException:
                pass

            # Strategy 2: Partial match on data-section-name
            if not section_element:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-section-name]')
                    for elem in elements:
                        if section_name.lower() in elem.get_attribute('data-section-name').lower():
                            section_element = elem
                            logger.debug(f"Found section using partial match: {elem.get_attribute('data-section-name')}")
                            break
                except Exception:
                    pass

            # Strategy 3: Look for section in text content
            if not section_element:
                try:
                    xpath = f"//*[contains(text(), '{section_name}')]"
                    section_element = self.driver.find_element(By.XPATH, xpath)
                    logger.debug(f"Found section using text content: {section_name}")
                except NoSuchElementException:
                    pass

            if not section_element:
                logger.warning(f"Section not found: {section_name}")
                return None

            # Scroll element into view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", section_element)
            time.sleep(1)

            # Hover over the section
            actions = ActionChains(self.driver)
            actions.move_to_element(section_element).perform()
            logger.debug(f"Hovering over section: {section_name}")

            # Wait for popup to appear
            time.sleep(2)

            # Extract price from popup
            price_data = self._extract_popup_price()

            if price_data:
                price_data['section'] = section_name
                logger.info(f"Found price for {section_name}: ${price_data.get('price', 'N/A')}")
                return price_data
            else:
                logger.warning(f"No price found in popup for {section_name}")
                return None

        except Exception as e:
            logger.error(f"Error extracting price for section {section_name}: {e}")
            return None

    def _extract_popup_price(self) -> Optional[Dict[str, Any]]:
        """
        Extract price information from the hover popup.

        Returns:
            Dictionary with price information or None if not found
        """
        try:
            # Common popup selectors
            popup_selectors = [
                '.tooltip',
                '.popover',
                '.popup',
                '[role="tooltip"]',
                '.price-tooltip',
                '.section-tooltip',
                '.hover-popup',
                '.map-tooltip',
                '[class*="tooltip"]',
                '[class*="popup"]',
                '[class*="popover"]'
            ]

            popup_element = None

            # Try to find the popup
            for selector in popup_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        if elem.is_displayed():
                            popup_element = elem
                            logger.debug(f"Found popup using selector: {selector}")
                            break
                    if popup_element:
                        break
                except Exception:
                    continue

            if not popup_element:
                # Try to get any visible overlay
                try:
                    overlays = self.driver.find_elements(By.XPATH, "//*[contains(@style, 'position: absolute') or contains(@style, 'position: fixed')]")
                    for overlay in overlays:
                        if overlay.is_displayed() and overlay.text:
                            popup_element = overlay
                            logger.debug("Found popup using overlay detection")
                            break
                except Exception:
                    pass

            if not popup_element:
                logger.debug("No popup found")
                return None

            # Get popup text
            popup_text = popup_element.text
            logger.debug(f"Popup text: {popup_text}")

            # Extract price from popup text
            price_patterns = [
                r'\$([0-9]+(?:\.[0-9]{2})?)',  # $99.99
                r'([0-9]+(?:\.[0-9]{2})?)\s*(?:USD|dollars?)',  # 99.99 USD
                r'(?:from|starting at|as low as)\s*\$([0-9]+(?:\.[0-9]{2})?)',  # from $99.99
                r'Price:\s*\$([0-9]+(?:\.[0-9]{2})?)',  # Price: $99.99
            ]

            for pattern in price_patterns:
                match = re.search(pattern, popup_text, re.IGNORECASE)
                if match:
                    try:
                        price = float(match.group(1))

                        return {
                            'price': price,
                            'text': popup_text,
                            'currency': 'USD'
                        }
                    except ValueError:
                        continue

            # If no price found but popup has text, return the text
            if popup_text:
                return {
                    'price': None,
                    'text': popup_text,
                    'currency': 'USD'
                }

            return None

        except Exception as e:
            logger.error(f"Error extracting popup price: {e}")
            return None

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
                self.wait = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()