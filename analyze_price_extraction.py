#!/usr/bin/env python3
"""
Deep dive analysis of price extraction strategies used in TixScanner web scraper.

This script demonstrates and analyzes the 4-tier approach to extracting pricing data
from Ticketmaster event pages.
"""

import sys
import re
from pathlib import Path
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent / "src"))

def analyze_price_extraction_strategies():
    """Demonstrate and analyze each price extraction strategy."""
    
    print("🔍 Deep Dive: TixScanner Price Extraction Strategies")
    print("=" * 60)
    
    # Let's analyze each strategy with examples
    
    print("\n🎯 STRATEGY 1: META TAG EXTRACTION")
    print("-" * 40)
    analyze_meta_tag_strategy()
    
    print("\n🎯 STRATEGY 2: JSON-LD STRUCTURED DATA")
    print("-" * 40)
    analyze_json_ld_strategy()
    
    print("\n🎯 STRATEGY 3: CSS CLASS/ATTRIBUTE SELECTORS")
    print("-" * 40)
    analyze_element_selector_strategy()
    
    print("\n🎯 STRATEGY 4: REGEX TEXT PATTERN MATCHING")
    print("-" * 40)
    analyze_regex_text_strategy()
    
    print("\n🎯 PRICE PARSING & DEDUPLICATION")
    print("-" * 40)
    analyze_price_parsing()

def analyze_meta_tag_strategy():
    """Analyze Strategy 1: Meta tag extraction."""
    
    print("📋 Purpose: Extract prices from HTML meta tags")
    print("🎯 Target: SEO/social media structured data")
    
    # Example meta tags that would be found
    example_html = """
    <meta property="product:price:amount" content="99.99">
    <meta name="price" content="149.50">
    <meta itemprop="price" content="75.00">
    <meta itemprop="lowPrice" content="50.00">
    <meta itemprop="highPrice" content="200.00">
    """
    
    print(f"\n📄 Example HTML:")
    print(example_html.strip())
    
    # Selectors used
    meta_selectors = [
        'meta[property="product:price:amount"]',
        'meta[name="price"]', 
        'meta[itemprop="price"]',
        'meta[itemprop="lowPrice"]',
        'meta[itemprop="highPrice"]'
    ]
    
    print(f"\n🎯 CSS Selectors Used:")
    for selector in meta_selectors:
        print(f"   • {selector}")
    
    print(f"\n✅ Strengths:")
    print("   • Very clean, structured data")
    print("   • No parsing complexity")
    print("   • SEO-optimized sites often include these")
    
    print(f"\n⚠️ Limitations:")
    print("   • Not all sites use meta tags for pricing")
    print("   • May only show price ranges, not specific seat prices")
    
    # Demo with BeautifulSoup
    soup = BeautifulSoup(example_html, 'html.parser')
    print(f"\n🧪 Extraction Demo:")
    for selector in meta_selectors:
        elements = soup.select(selector)
        for elem in elements:
            content = elem.get('content', '')
            if content:
                print(f"   Found: {selector} → ${content}")

def analyze_json_ld_strategy():
    """Analyze Strategy 2: JSON-LD structured data extraction."""
    
    print("📋 Purpose: Extract prices from JSON-LD structured data scripts")
    print("🎯 Target: Schema.org structured data for search engines")
    
    # Example JSON-LD that would be found
    example_json = '''
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "Event",
      "name": "Concert Event",
      "offers": {
        "@type": "Offer",
        "price": "125.00",
        "lowPrice": "85.00", 
        "highPrice": "250.00",
        "priceCurrency": "USD"
      }
    }
    </script>
    '''
    
    print(f"\n📄 Example JSON-LD:")
    print(example_json.strip())
    
    # Price paths searched
    price_paths = [
        ['offers', 'price'],
        ['offers', 'lowPrice'], 
        ['offers', 'highPrice'],
        ['priceRange'],
        ['price']
    ]
    
    print(f"\n🗺️  JSON Paths Searched:")
    for path in price_paths:
        print(f"   • {' → '.join(path)}")
    
    print(f"\n✅ Strengths:")
    print("   • Rich, structured data format")
    print("   • Google/SEO best practices")
    print("   • Can include price ranges and currency info")
    print("   • Handles nested data structures")
    
    print(f"\n⚠️ Limitations:")
    print("   • JSON parsing can fail if malformed")
    print("   • Not all sites implement Schema.org")
    print("   • May not reflect dynamic pricing")

def analyze_element_selector_strategy():
    """Analyze Strategy 3: CSS class and attribute selectors."""
    
    print("📋 Purpose: Find price data in HTML elements with price-related classes")
    print("🎯 Target: Visible pricing elements on the page")
    
    # Selectors used in the scraper
    price_selectors = [
        '[class*="price"]',      # Any class containing "price"
        '[class*="Price"]',      # Any class containing "Price" (camelCase)
        '[data-price]',          # Elements with data-price attribute
        '[class*="cost"]',       # Any class containing "cost"
        '[class*="amount"]',     # Any class containing "amount" 
        '.ticket-price',         # Specific ticket price class
        '.price-display',        # Specific price display class
        '.ticket-cost'           # Specific ticket cost class
    ]
    
    print(f"\n🎯 CSS Selectors Used:")
    for selector in price_selectors:
        print(f"   • {selector}")
    
    # Example elements that would match
    example_elements = '''
    <div class="ticket-price">$125.00</div>
    <span class="Price-amount">$89.99</span>
    <div data-price="150.50" class="seat-pricing">Section A</div>
    <p class="ticket-cost-display">From $75</p>
    '''
    
    print(f"\n📄 Example Matching Elements:")
    print(example_elements.strip())
    
    print(f"\n✅ Strengths:")
    print("   • Catches most visible pricing displays")
    print("   • Works with various naming conventions")
    print("   • Can extract from data attributes AND text content")
    print("   • Most reliable for user-facing prices")
    
    print(f"\n⚠️ Limitations:")
    print("   • Dependent on CSS class naming")
    print("   • May catch non-price elements (false positives)")
    print("   • Requires text parsing for mixed content")
    
    # Demo the dual extraction approach
    print(f"\n🔄 Dual Extraction Process:")
    print("   1. Try data-price attribute first (clean)")
    print("   2. Fallback to element text content (parsed)")
    print("   3. Extract section context from parent elements")

def analyze_regex_text_strategy():
    """Analyze Strategy 4: Regex pattern matching in text."""
    
    print("📋 Purpose: Find price patterns in raw page text as final fallback")
    print("🎯 Target: Any price mentions in text content")
    
    # Regex patterns used
    price_patterns = [
        (r'\\$([0-9]+(?:\\.[0-9]{2})?)', 'Standard dollar format: $99.99'),
        (r'([0-9]+(?:\\.[0-9]{2})?)\\s*(?:USD|dollars?)', 'Number + currency: 99.99 USD'),
        (r'(?:from|starting|as low as)\\s*\\$([0-9]+(?:\\.[0-9]{2})?)', 'Prefix phrases: from $99.99')
    ]
    
    print(f"\n🔍 Regex Patterns:")
    for pattern, description in price_patterns:
        print(f"   • {description}")
        print(f"     Pattern: {pattern}")
    
    # Example text that would match
    example_text = '''
    Tickets start from $85.00 for general admission.
    Premium seats are 150.99 USD each.
    Prices range from $50 to $300 depending on section.
    VIP packages as low as $199.99 are available.
    '''
    
    print(f"\n📄 Example Text Content:")
    print(example_text.strip())
    
    # Demo pattern matching
    print(f"\n🧪 Pattern Matching Demo:")
    for pattern, description in price_patterns:
        # Fix the escaped regex for actual use
        actual_pattern = pattern.replace('\\\\', '\\')
        matches = re.findall(actual_pattern, example_text, re.IGNORECASE)
        if matches:
            print(f"   {description}: {matches}")
    
    print(f"\n✅ Strengths:")
    print("   • Ultimate fallback - catches any price mention")
    print("   • Works even when HTML structure changes")
    print("   • Handles various price formats and contexts")
    
    print(f"\n⚠️ Limitations:")
    print("   • High risk of false positives")
    print("   • No section/context information")
    print("   • Requires price range filtering (10-10000)")
    print("   • May catch irrelevant numbers")
    
    print(f"\n🛡️ Safety Measures:")
    print("   • Price range validation (10 ≤ price ≤ 10000)")
    print("   • Duplicate removal in final processing")
    print("   • Context-based filtering")

def analyze_price_parsing():
    """Analyze the price parsing and deduplication process."""
    
    print("📋 Purpose: Convert price strings to numbers and remove duplicates")
    print("🎯 Target: Clean, validated price data")
    
    print(f"\n🧹 Price String Cleaning Process:")
    print("   1. Strip whitespace")
    print("   2. Remove commas: '1,250.00' → '1250.00'") 
    print("   3. Remove dollar signs: '$99.99' → '99.99'")
    print("   4. Extract numeric pattern: '[0-9]+(?:\\.[0-9]{1,2})?'")
    print("   5. Convert to float")
    
    # Example price strings
    example_prices = [
        "$1,250.99",
        "99.50",
        "From $75.00",
        "  $150  ",
        "200.5",
        "$invalid.price"
    ]
    
    print(f"\n🧪 Price Parsing Examples:")
    for price_str in example_prices:
        cleaned = price_str.strip().replace(',', '').replace('$', '')
        match = re.search(r'([0-9]+(?:\.[0-9]{1,2})?)', cleaned)
        if match:
            try:
                result = float(match.group(1))
                print(f"   '{price_str}' → ${result:.2f} ✅")
            except ValueError:
                print(f"   '{price_str}' → Failed ❌")
        else:
            print(f"   '{price_str}' → No match ❌")
    
    print(f"\n🔄 Deduplication Process:")
    print("   • Key: (price, section) tuple")
    print("   • Removes exact duplicates from multiple strategies")
    print("   • Preserves different sections for same price")
    print("   • Filters out zero/negative prices")
    
    print(f"\n📊 Final Data Structure:")
    print("   • price: float (parsed value)")
    print("   • source: str (meta_tag, json_ld, element_class, text_regex)")
    print("   • section: str (seat section/tier context)")
    
    print(f"\n🎯 Why This Multi-Strategy Approach Works:")
    print("   ✅ Comprehensive coverage - catches prices regardless of format")
    print("   ✅ Redundancy - if one strategy fails, others succeed")
    print("   ✅ Source tracking - enables debugging and optimization")
    print("   ✅ Context preservation - maintains section information")
    print("   ✅ Robust parsing - handles various price formats")

if __name__ == "__main__":
    analyze_price_extraction_strategies()