"""
Section-based web scraper for Ticketmaster event pricing.

Uses Selenium WebDriver to hover over specific sections and extract
pricing information from popups.
"""

import logging
import os
import time
import random
import re
from typing import Optional, List, Dict, Any
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException, WebDriverException, NoSuchElementException,
    ElementNotInteractableException, StaleElementReferenceException,
    ElementClickInterceptedException
)
from webdriver_manager.chrome import ChromeDriverManager

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

    def _setup_driver(self) -> None:
        """Set up Chrome WebDriver with optimal settings for hover interactions."""
        try:
            chrome_options = Options()

            if self.headless:
                chrome_options.add_argument("--headless=new")

            # Essential options for stability and container compatibility
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-setuid-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            # Additional container/server options
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            chrome_options.add_argument("--disable-features=TranslateUI")
            chrome_options.add_argument("--disable-ipc-flooding-protection")

            # Window size for proper rendering
            chrome_options.add_argument("--window-size=1920,1080")

            # User agent to appear more legitimate
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

            # Performance optimizations
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")

            # Force explicit ChromeDriver path to avoid Selenium auto-detection issues in containers
            import shutil
            system_chromedriver = shutil.which('chromedriver')
            try:
                # First try the known system path
                explicit_chromedriver_paths = [
                    '/usr/local/bin/chromedriver',
                    '/usr/bin/chromedriver',
                    system_chromedriver
                ]

                chromedriver_path = None
                for path in explicit_chromedriver_paths:
                    if path and os.path.exists(path) and os.access(path, os.X_OK):
                        chromedriver_path = path
                        break

                if chromedriver_path:
                    service = Service(chromedriver_path)
                    logger.debug(f"Using ChromeDriver: {chromedriver_path}")
                else:
                    chromedriver_path = ChromeDriverManager().install()
                    service = Service(chromedriver_path)
                    logger.debug(f"ChromeDriver installed: {chromedriver_path}")

            except Exception as e:
                logger.error(f"ChromeDriver setup failed: {e}")
                raise SectionScrapingError(f"ChromeDriver setup failed: {e}")

            # Add additional Chrome options for container environments
            chrome_options.add_argument("--disable-background-networking")


            # Additional options for ARM64 and container stability
            chrome_options.add_argument("--disable-software-rasterizer")

            try:
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                self.driver.set_page_load_timeout(self.timeout)
                self.wait = WebDriverWait(self.driver, self.timeout)

                # Execute script to remove webdriver property
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

                logger.info("WebDriver initialized successfully")

            except Exception as webdriver_error:
                logger.error(f"WebDriver creation failed: {webdriver_error}")
                raise SectionScrapingError(f"WebDriver creation failed: {webdriver_error}")

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

        logger.info(f"Scraping prices: {event_url}")

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
            self.driver.get(event_url)

            # Wait for initial page load
            time.sleep(random.uniform(3, 5))

            # Check for bot detection
            if "Access to this page has been denied" in self.driver.page_source:
                raise SectionScrapingError("Access denied - bot detection")

            # Handle initial popup/consent dialog
            self._handle_initial_popup()

            # Wait for interactive map to load
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-section-name]'))
                )
            except TimeoutException:
                logger.debug("Interactive map not found")

            # Process each section
            successful_sections = []
            failed_sections = []

            for section_name in sections:
                section_data = self._extract_section_price(section_name)
                if section_data:
                    result['sections'][section_name] = section_data
                    successful_sections.append(section_name)
                else:
                    failed_sections.append(section_name)

            # Log summary
            if successful_sections:
                result['success'] = True
                logger.info(f"Scraped {len(successful_sections)}/{len(sections)} sections")
            else:
                result['error'] = "No section prices found"
                logger.warning(f"No section prices found for {len(sections)} sections")

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

    def _handle_initial_popup(self) -> None:
        """
        Handle the initial popup/consent dialog that requires clicking "Accept".

        Ticketmaster often shows a popup on page load that needs to be dismissed
        before any interactions can take place.
        """
        try:
            # Expanded modal selectors to catch more popup types
            modal_selectors = ', '.join([
                '[data-bdd*="modal"]',
                '[data-bdd*="popup"]',
                '[data-bdd*="consent"]'
            ])

            # Wait up to 10 seconds for any modal/popup to appear
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, modal_selectors))
                )
                modal_indicators = self.driver.find_elements(By.CSS_SELECTOR, modal_selectors)
            except TimeoutException:
                return

            # Filter to only displayed modals
            visible_modals = [modal for modal in modal_indicators if modal.is_displayed()]

            if not visible_modals:
                return

            # Expanded accept selectors to catch more button types
            combined_selector = ', '.join([
                'button[data-analytics="accept-modal-accept-button"]',
                'button[data-testid*="agree"]'
            ])

            try:
                # Wait for accept button to become clickable
                accept_button = WebDriverWait(self.driver, 6).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, combined_selector))
                )
                accept_button.click()
                logger.debug("Clicked popup accept button")
                time.sleep(1.5)  # Allow time for popup to dismiss
            except TimeoutException:
                logger.debug("No accept button found")

        except Exception as e:
            logger.debug(f"Error handling popup: {e}")

    def _extract_section_price(self, section_name: str) -> Optional[Dict[str, Any]]:
        """
        Extract price for a specific section by hovering and reading popup.

        Args:
            section_name: The section name to hover over

        Returns:
            Dictionary with price information or None if not found
        """
        try:
            # Find the section element
            section_selector = f'[data-section-name="{section_name}"]'
            section_element = None

            # Strategy 1: Direct data-section-name attribute
            try:
                section_element = self.driver.find_element(By.CSS_SELECTOR, section_selector)
            except NoSuchElementException:
                pass

            # Strategy 2: Partial match on data-section-name
            if not section_element:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-section-name]')
                    for elem in elements:
                        if section_name.lower() in elem.get_attribute('data-section-name').lower():
                            section_element = elem
                            break
                except Exception:
                    pass

            # Strategy 3: Look for section in text content
            if not section_element:
                try:
                    xpath = f"//*[contains(text(), '{section_name}')]"
                    section_element = self.driver.find_element(By.XPATH, xpath)
                except NoSuchElementException:
                    pass

            if not section_element:
                logger.debug(f"Section not found: {section_name}")
                return None

            # Scroll element into view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", section_element)
            time.sleep(1)

            # Try hovering with retry mechanism
            price_data = None
            max_retries = 2

            for attempt in range(max_retries):
                try:
                    # Hover over the section
                    actions = ActionChains(self.driver)
                    actions.move_to_element(section_element).perform()

                    # Wait for popup to appear with explicit wait
                    price_data = self._wait_for_popup_and_extract_price(section_name)

                    if price_data:
                        break  # Success, exit retry loop
                    elif attempt < max_retries - 1:
                        # Move mouse away and wait before retry
                        actions.move_by_offset(50, 50).perform()
                        time.sleep(1)

                except Exception as e:
                    if attempt == max_retries - 1:
                        raise

            if price_data:
                price_data['section'] = section_name
                logger.info(f"Found price for {section_name}: ${price_data.get('price', 'N/A')}")
                return price_data
            else:
                return None

        except (ElementNotInteractableException, StaleElementReferenceException, ElementClickInterceptedException):
            logger.debug(f"Section '{section_name}' not interactable")
            return None

        except Exception as e:
            logger.debug(f"Could not process section '{section_name}': {e}")
            return None

    def _wait_for_popup_and_extract_price(self, section_name: str, max_wait: float = 5) -> Optional[Dict[str, Any]]:
        """
        Wait for popup to appear after hover and extract price information.

        Args:
            section_name: Name of the section being hovered
            max_wait: Maximum seconds to wait for popup

        Returns:
            Dictionary with price information or None if not found
        """
        try:
            # Combine all popup selectors into a single efficient query
            combined_popup_selector = '[data-bdd="hover-tool-tip-container"]'
            popup_element = None

            # Single optimized wait for any popup
            try:
                popup_element = WebDriverWait(self.driver, max_wait).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, combined_popup_selector))
                )

                # Additional check that it has meaningful text content
                if not popup_element.text.strip():
                    popup_element = None

            except TimeoutException:
                return None

            if popup_element:
                # Extract price from the popup
                return self._extract_price_from_element(popup_element)
            else:
                return None

        except Exception as e:
            logger.debug(f"Error waiting for popup: {e}")
            return None

    def _extract_price_from_element(self, popup_element) -> Optional[Dict[str, Any]]:
        """
        Extract price information from a popup element.

        Args:
            popup_element: WebElement containing the popup

        Returns:
            Dictionary with price information or None if not found
        """
        try:
            # Get popup text
            popup_text = popup_element.text

            # Extract price from popup text
            price_patterns = [
                r'\$([0-9]+(?:\.[0-9]{2})?)\+?',  # $99.99 or $99.99+
                r'\$([0-9]+(?:\.[0-9]{2})?)',  # $99.99
                r'([0-9]+(?:\.[0-9]{2})?)\s*(?:USD|dollars?)',  # 99.99 USD
                r'(?:from|starting at|as low as)\s*\$([0-9]+(?:\.[0-9]{2})?)\+?',  # from $99.99+
                r'Price:\s*\$([0-9]+(?:\.[0-9]{2})?)\+?',  # Price: $99.99+
            ]

            for pattern in price_patterns:
                match = re.search(pattern, popup_text, re.IGNORECASE)
                if match:
                    price = float(match.group(1))
                    logger.debug(f"Extracted price: ${price}")

                    return {
                        'price': price,
                        'text': popup_text,
                        'currency': 'USD'
                    }

            return None

        except Exception as e:
            logger.debug(f"Error extracting price: {e}")
            return None

    def close(self) -> None:
        """Close the WebDriver and clean up temporary files."""
        if self.driver:
            try:
                # Force quit all Chrome processes before closing WebDriver
                self.driver.quit()
                # Additional cleanup for Codespaces - wait a bit for processes to terminate
                time.sleep(2)

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