"""
Optimized Ticketmaster scraper focused on element selectors with section targeting.

This scraper removes unused extraction strategies and adds section-specific filtering
for more precise price monitoring.
"""

import logging
import os
import time
import random
import re
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

logger = logging.getLogger(__name__)


class TicketmasterOptimizedScraper:
    """
    Optimized scraper for Ticketmaster with section-specific targeting.
    
    Focuses only on element selectors (the strategy that works) and adds
    support for targeting specific seating sections.
    """
    
    def __init__(self, headless: bool = True, timeout: int = 30):
        """
        Initialize the optimized scraper.
        
        Args:
            headless: Run browser in headless mode
            timeout: Page load timeout in seconds
        """
        self.headless = headless
        self.timeout = timeout
        self.driver = None
        self._temp_profile_dir = None
        self._setup_driver()
        
        logger.info("Optimized Ticketmaster scraper initialized")
    
    def _setup_driver(self) -> None:
        """Set up Chrome WebDriver with optimized settings for Ticketmaster."""
        try:
            import tempfile
            import uuid

            options = Options()

            if self.headless:
                options.add_argument("--headless=new")

            # Essential container options (for Codespaces compatibility)
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")

            # Unique user data directory to avoid conflicts (essential for Codespaces)
            self._temp_profile_dir = tempfile.mkdtemp(prefix=f"chrome_profile_{uuid.uuid4().hex[:8]}_")
            options.add_argument(f"--user-data-dir={self._temp_profile_dir}")
            logger.debug(f"Using temporary Chrome profile directory: {self._temp_profile_dir}")

            # Optimized options for Ticketmaster (based on our testing)
            options.add_argument("--disable-images")  # Major speed boost
            # Note: JavaScript enabled for dynamic pricing content
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-extensions")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.7258.154 Safari/537.36")

            # Anti-detection (minimal but effective)
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_page_load_timeout(self.timeout)
            
            logger.debug("Chrome WebDriver initialized with optimized settings")
            
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            raise Exception(f"WebDriver initialization failed: {e}")
    
    def scrape_section_pricing(self, event_url: str, target_sections: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Scrape pricing for specific sections from Ticketmaster event page.
        
        Args:
            event_url: Full URL to Ticketmaster event page
            target_sections: List of section names to target (e.g., ["General Admission", "Floor"])
                           If None, returns all sections
            
        Returns:
            Dictionary with section-specific pricing information
        """
        logger.info(f"Scraping section pricing for: {event_url}")
        if target_sections:
            logger.info(f"Target sections: {target_sections}")
        
        if not self.driver:
            raise Exception("WebDriver not initialized")
        
        pricing_data = {
            'url': event_url,
            'target_sections': target_sections or ['all'],
            'sections': {},
            'min_price': None,
            'max_price': None,
            'total_prices': 0,
            'scraped_at': time.time(),
            'success': False,
            'error': None
        }
        
        try:
            # Navigate and wait for content
            logger.debug(f"Loading page: {event_url}")
            self.driver.get(event_url)
            time.sleep(random.uniform(2, 4))
            
            # Check for access issues
            page_source = self.driver.page_source
            if "Access to this page has been denied" in page_source:
                raise Exception("Access denied - bot detection")
            
            # Handle initial popup if present
            self._handle_initial_popup()
            
            # Simulate scrolling within pricing div to load dynamic content
            self._load_dynamic_content()
            
            # Get updated page source after scrolling
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Extract section-specific pricing
            section_prices = self._extract_section_prices(soup, target_sections)
            
            if section_prices:
                pricing_data['sections'] = section_prices
                
                # Calculate overall stats
                all_prices = []
                for section_name, section_data in section_prices.items():
                    all_prices.extend([p['price'] for p in section_data['prices']])
                
                if all_prices:
                    pricing_data['min_price'] = min(all_prices)
                    pricing_data['max_price'] = max(all_prices)
                    pricing_data['total_prices'] = len(all_prices)
                    pricing_data['success'] = True
                    
                    logger.info(f"Successfully scraped {len(all_prices)} prices across {len(section_prices)} sections")
                    logger.debug(f"Price range: ${pricing_data['min_price']:.2f} - ${pricing_data['max_price']:.2f}")
            else:
                logger.warning("No pricing data found for specified sections")
                pricing_data['error'] = f"No pricing found for sections: {target_sections or 'any'}"
            
            return pricing_data
            
        except Exception as e:
            error_msg = f"Scraping error: {e}"
            logger.error(error_msg)
            pricing_data['error'] = error_msg
            return pricing_data
    
    def _handle_initial_popup(self) -> None:
        """
        Handle the initial popup that requires clicking "Accept".
        
        Ticketmaster often shows a popup on page load that needs to be dismissed.
        """
        logger.debug("Checking for and handling initial popup")
        
        try:
            # Look for common "Accept" button patterns
            accept_selectors = [
                'button[data-testid*="accept"]',
                'button[aria-label*="accept"]',
                'button[aria-label*="Accept"]',
                'button:contains("Accept")',
                '[data-bdd*="accept"]',
                '.modal button:contains("Accept")',
                '.popup button:contains("Accept")',
                'button.accept',
                '#accept-button'
            ]
            
            for selector in accept_selectors:
                try:
                    # Wait up to 5 seconds for the Accept button to appear
                    accept_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    
                    logger.debug(f"Found Accept button with selector: {selector}")
                    accept_button.click()
                    logger.info("Successfully clicked Accept button")
                    
                    # Wait for popup to dismiss
                    time.sleep(random.uniform(1, 2))
                    return
                    
                except TimeoutException:
                    continue
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue
            
            # Also try JavaScript-based approach for text content
            try:
                accept_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'ACCEPT')]")
                if accept_button.is_enabled() and accept_button.is_displayed():
                    accept_button.click()
                    logger.info("Successfully clicked Accept button via XPath")
                    time.sleep(random.uniform(1, 2))
                    return
            except Exception:
                pass
                
            logger.debug("No Accept popup found or already dismissed")
            
        except Exception as e:
            logger.warning(f"Error handling popup: {e}")
            # Continue anyway - popup might not be present
    
    def _load_dynamic_content(self) -> None:
        """
        Simulate scrolling within the pricing div to load dynamic pricing content.
        
        Ticketmaster loads pricing information dynamically as users scroll within
        the specific pricing container div.
        """
        logger.debug("Loading dynamic content through pricing div scrolling simulation")
        
        try:
            # First, try to find the pricing div
            pricing_div = None
            pricing_selectors = [
                '[data-bdd="qp-split-scroll"]',
                '[data-testid="qp-split-scroll"]',
                '[data-bdd*="scroll"]',
                '[data-testid*="scroll"]',
                '.pricing-container',
                '.ticket-options',
                '[class*="pricing"]'
            ]
            
            for selector in pricing_selectors:
                try:
                    pricing_div = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    logger.debug(f"Found pricing div with selector: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if pricing_div:
                # Scroll within the pricing div
                logger.debug("Scrolling within pricing div")
                
                # Get the div's scroll height
                div_height = self.driver.execute_script("return arguments[0].scrollHeight", pricing_div)
                div_client_height = self.driver.execute_script("return arguments[0].clientHeight", pricing_div)
                
                # Scroll down in stages within the div
                scroll_positions = [0.25, 0.5, 0.75, 1.0]
                
                for position in scroll_positions:
                    scroll_to = int((div_height - div_client_height) * position)
                    
                    # Scroll within the div
                    self.driver.execute_script("arguments[0].scrollTop = arguments[1];", pricing_div, scroll_to)
                    
                    # Wait for content to load
                    time.sleep(random.uniform(2, 4))
                    
                    # Check for General Admission elements specifically
                    try:
                        ga_elements = self.driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'general admission') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'general adm')]")
                        if ga_elements:
                            logger.info(f"Found {len(ga_elements)} General Admission elements after scrolling to {position*100:.0f}%")
                            # Wait a bit longer for GA pricing to fully load
                            time.sleep(random.uniform(3, 5))
                    except Exception:
                        pass
                    
                    logger.debug(f"Scrolled pricing div to {position*100:.0f}%")
                
                # Final scroll to bottom of div
                self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", pricing_div)
                time.sleep(random.uniform(3, 5))
                
            else:
                # Fallback to page scrolling if pricing div not found
                logger.warning("Pricing div not found, falling back to page scrolling")
                
                initial_height = self.driver.execute_script("return document.body.scrollHeight")
                scroll_positions = [0.25, 0.5, 0.75, 1.0]
                
                for position in scroll_positions:
                    scroll_to = int(initial_height * position)
                    self.driver.execute_script(f"window.scrollTo(0, {scroll_to});")
                    time.sleep(random.uniform(2, 4))
                
                # Final page scroll
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(random.uniform(3, 5))
            
            # Final check for General Admission content
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda driver: any(
                        'general admission' in elem.text.lower() or 'general adm' in elem.text.lower()
                        for elem in driver.find_elements(By.CSS_SELECTOR, '*')
                        if elem.text.strip()
                    )
                )
                logger.info("Successfully found General Admission elements after scrolling")
            except TimeoutException:
                logger.debug("No General Admission elements found after scrolling")
                pass
                
        except Exception as e:
            logger.warning(f"Error during dynamic content loading: {e}")
            # Continue with static content if dynamic loading fails
    
    def _extract_section_prices(self, soup: BeautifulSoup, target_sections: Optional[List[str]] = None) -> Dict[str, Dict]:
        """
        Extract prices organized by seating section.
        
        Args:
            soup: BeautifulSoup parsed HTML
            target_sections: List of section names to target
            
        Returns:
            Dictionary mapping section names to price data
        """
        section_pricing = {}
        
        # Optimized selectors based on our Ticketmaster analysis
        price_selectors = [
            '[class*="price"]',
            '[class*="Price"]', 
            '[data-price]',
            '[class*="cost"]',
            '[class*="amount"]'
        ]
        
        all_price_elements = []
        for selector in price_selectors:
            elements = soup.select(selector)
            all_price_elements.extend(elements)
        
        logger.debug(f"Found {len(all_price_elements)} potential price elements")
        
        # Process each price element
        for elem in all_price_elements:
            # Extract price
            price_str = elem.get('data-price', '') or elem.get_text(strip=True)
            price = self._parse_price_string(price_str)
            
            if not price or price <= 0:
                continue
            
            # Extract section information
            section_name = self._extract_section_info(elem)
            
            # Filter by target sections if specified
            if target_sections and not self._matches_target_section(section_name, target_sections):
                continue
            
            # Organize by section
            if section_name not in section_pricing:
                section_pricing[section_name] = {
                    'section_name': section_name,
                    'prices': [],
                    'min_price': None,
                    'max_price': None,
                    'avg_price': None
                }
            
            # Add price data
            price_data = {
                'price': price,
                'element_text': elem.get_text(strip=True)[:100],  # First 100 chars for context
                'element_classes': elem.get('class', []),
                'extracted_from': 'element_class'
            }
            
            section_pricing[section_name]['prices'].append(price_data)
        
        # Calculate section statistics
        for section_name, section_data in section_pricing.items():
            prices = [p['price'] for p in section_data['prices']]
            if prices:
                section_data['min_price'] = min(prices)
                section_data['max_price'] = max(prices)
                section_data['avg_price'] = sum(prices) / len(prices)
                
                # Remove duplicates within section
                unique_prices = []
                seen_prices = set()
                for price_data in section_data['prices']:
                    price_key = price_data['price']
                    if price_key not in seen_prices:
                        unique_prices.append(price_data)
                        seen_prices.add(price_key)
                
                section_data['prices'] = unique_prices
        
        return section_pricing
    
    def _extract_section_info(self, element) -> str:
        """
        Extract section/seating area information from element context.
        
        Args:
            element: BeautifulSoup element containing price
            
        Returns:
            Section name or 'General' if not found
        """
        # Strategy 1: Check element's own text for section keywords
        element_text = element.get_text(strip=True)
        section_keywords = [
            'general admission', 'ga', 'floor', 'pit', 'vip', 'premium', 
            'section', 'sec', 'row', 'level', 'tier', 'balcony', 'mezzanine',
            'orchestra', 'loge', 'box', 'suite', 'reserved', 'lawn'
        ]
        
        for keyword in section_keywords:
            if keyword in element_text.lower():
                # Extract the relevant part
                if 'general admission' in element_text.lower() or 'ga' in element_text.lower():
                    return 'General Admission'
                elif 'floor' in element_text.lower():
                    return 'Floor'
                elif 'vip' in element_text.lower():
                    return 'VIP'
                elif 'premium' in element_text.lower():
                    return 'Premium'
                # Add more specific patterns as needed
        
        # Strategy 2: Look in parent elements (up to 3 levels)
        current = element.parent
        for level in range(3):
            if not current:
                break
                
            # Check parent's classes for section indicators
            parent_classes = current.get('class', [])
            parent_text = current.get_text(strip=True)
            
            for class_name in parent_classes:
                if any(keyword in class_name.lower() for keyword in ['section', 'seat', 'area', 'zone']):
                    # Try to extract section from class name or parent text
                    if 'general' in parent_text.lower() or 'ga' in parent_text.lower():
                        return 'General Admission'
                    elif 'floor' in parent_text.lower():
                        return 'Floor'
            
            current = current.parent
        
        # Strategy 3: Parse section from element text patterns
        section_match = re.search(r'(sec|section|level|tier)\s*([a-z0-9]+)', element_text, re.IGNORECASE)
        if section_match:
            return f"Section {section_match.group(2).upper()}"
        
        return 'General'
    
    def _matches_target_section(self, section_name: str, target_sections: List[str]) -> bool:
        """
        Check if section name matches any of the target sections.
        
        Args:
            section_name: Extracted section name
            target_sections: List of target section names
            
        Returns:
            True if section matches targets
        """
        section_lower = section_name.lower()
        
        for target in target_sections:
            target_lower = target.lower()
            
            # Exact match
            if section_lower == target_lower:
                return True
            
            # Partial match for common variations
            if 'general' in target_lower and 'general' in section_lower:
                return True
            if 'admission' in target_lower and 'admission' in section_lower:
                return True
            if 'floor' in target_lower and 'floor' in section_lower:
                return True
            if 'vip' in target_lower and 'vip' in section_lower:
                return True
            if 'premium' in target_lower and 'premium' in section_lower:
                return True
            
            # Handle section number patterns (e.g., "Section 101" matches "101")
            if target_lower.isdigit() and target_lower in section_lower:
                return True
            
            # Handle range patterns (e.g., "100s" matches sections 101-109)
            if target_lower.endswith('s') and target_lower[:-1].isdigit():
                section_num_match = re.search(r'(\d+)', section_name)
                if section_num_match:
                    section_num = int(section_num_match.group(1))
                    range_start = int(target_lower[:-1]) * 10
                    range_end = range_start + 99
                    if range_start <= section_num <= range_end:
                        return True
        
        return False
    
    def _parse_price_string(self, price_str: str) -> Optional[float]:
        """
        Parse price string to float (optimized for Ticketmaster format).
        
        Args:
            price_str: String containing price
            
        Returns:
            Price as float or None
        """
        if not price_str:
            return None
        
        # Clean string
        cleaned = str(price_str).strip().replace(',', '').replace('$', '')
        
        # Extract number pattern
        match = re.search(r'([0-9]+(?:\.[0-9]{1,2})?)', cleaned)
        if match:
            try:
                price = float(match.group(1))
                # Reasonable price range for concert tickets
                if 10 <= price <= 10000:
                    return price
            except ValueError:
                pass
        
        return None
    
    def get_general_admission_prices(self, event_url: str) -> Dict[str, Any]:
        """
        Convenience method to get General Admission prices specifically.
        
        Args:
            event_url: Ticketmaster event URL
            
        Returns:
            Dictionary with GA pricing data
        """
        return self.scrape_section_pricing(event_url, target_sections=['General Admission', 'GA'])
    
    def get_cheapest_sections(self, event_url: str, section_count: int = 3) -> Dict[str, Any]:
        """
        Get pricing for the cheapest sections.
        
        Args:
            event_url: Ticketmaster event URL
            section_count: Number of cheapest sections to return
            
        Returns:
            Dictionary with cheapest sections pricing data
        """
        # First get all sections
        all_results = self.scrape_section_pricing(event_url)
        
        if not all_results['success']:
            return all_results
        
        # Sort sections by minimum price
        sections_by_price = []
        for section_name, section_data in all_results['sections'].items():
            sections_by_price.append((section_data['min_price'], section_name, section_data))
        
        sections_by_price.sort(key=lambda x: x[0])  # Sort by min price
        
        # Get the cheapest sections
        cheapest_sections = {}
        for i, (min_price, section_name, section_data) in enumerate(sections_by_price[:section_count]):
            cheapest_sections[section_name] = section_data
        
        # Calculate overall stats for cheapest sections
        if cheapest_sections:
            all_prices = []
            for section_data in cheapest_sections.values():
                all_prices.extend([p['price'] for p in section_data['prices']])
            
            return {
                'url': event_url,
                'target_sections': [f'cheapest_{section_count}'],
                'sections': cheapest_sections,
                'min_price': min(all_prices) if all_prices else None,
                'max_price': max(all_prices) if all_prices else None,
                'total_prices': len(all_prices),
                'scraped_at': all_results['scraped_at'],
                'success': True,
                'error': None
            }
        
        return all_results
    
    def get_section_range(self, event_url: str, section_prefix: str) -> Dict[str, Any]:
        """
        Get prices for sections matching a prefix (e.g., all 100-level sections).
        
        Args:
            event_url: Ticketmaster event URL  
            section_prefix: Section prefix to match (e.g., "100s" for 100-199)
            
        Returns:
            Dictionary with matching sections pricing data
        """
        return self.scrape_section_pricing(event_url, target_sections=[section_prefix])
    
    def close(self) -> None:
        """Close the WebDriver and clean up temporary files."""
        if self.driver:
            try:
                self.driver.quit()
                logger.debug("WebDriver closed")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {e}")
            finally:
                self.driver = None

        # Clean up temporary profile directory
        if self._temp_profile_dir and os.path.exists(self._temp_profile_dir):
            try:
                import shutil
                shutil.rmtree(self._temp_profile_dir, ignore_errors=True)
                logger.debug(f"Cleaned up temporary Chrome profile directory: {self._temp_profile_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary directory {self._temp_profile_dir}: {e}")
            finally:
                self._temp_profile_dir = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()