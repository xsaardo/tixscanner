#!/usr/bin/env python3
"""
Live demonstration of price extraction strategies on real Ticketmaster page.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.web_scraper import TicketmasterScraper

def demonstrate_live_price_extraction():
    """Demonstrate all extraction strategies on real Ticketmaster page."""
    
    print("🎭 Live Price Extraction Strategy Demonstration")
    print("=" * 60)
    
    test_url = "https://www.ticketmaster.com/backstreet-boys-into-the-millennium-las-vegas-nevada-12-26-2025/event/1700630C79D40EAD"
    
    print(f"🎯 Target URL: {test_url}")
    print()
    
    with TicketmasterScraper(headless=True, timeout=30) as scraper:
        print("🌐 Fetching page and analyzing extraction strategies...")
        print()
        
        # Get page content
        scraper.driver.get(test_url)
        import time
        time.sleep(3)
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(scraper.driver.page_source, 'html.parser')
        
        # Manually run each strategy to show results
        print("📊 STRATEGY BREAKDOWN:")
        print("-" * 40)
        
        # Strategy 1: Meta tags
        meta_prices = scraper._extract_prices_from_meta(soup)
        print(f"1️⃣ Meta Tags: {len(meta_prices)} prices found")
        for price in meta_prices[:3]:
            print(f"   • ${price['price']:.2f} (source: {price['source']}, section: {price['section']})")
        
        # Strategy 2: JSON-LD
        json_prices = scraper._extract_prices_from_json_ld(soup)
        print(f"2️⃣ JSON-LD: {len(json_prices)} prices found")
        for price in json_prices[:3]:
            print(f"   • ${price['price']:.2f} (source: {price['source']}, section: {price['section']})")
        
        # Strategy 3: Element selectors  
        element_prices = scraper._extract_prices_from_elements(soup)
        print(f"3️⃣ Element Selectors: {len(element_prices)} prices found")
        for price in element_prices[:5]:
            print(f"   • ${price['price']:.2f} (source: {price['source']}, section: {price['section']})")
        if len(element_prices) > 5:
            print(f"   ... and {len(element_prices) - 5} more")
        
        # Strategy 4: Text regex
        text_prices = scraper._extract_prices_from_text(soup)  
        print(f"4️⃣ Text Regex: {len(text_prices)} prices found")
        for price in text_prices[:3]:
            print(f"   • ${price['price']:.2f} (source: {price['source']}, section: {price['section']})")
        
        print()
        print("🔄 COMBINED RESULTS (after deduplication):")
        print("-" * 40)
        
        # Run full extraction
        full_results = scraper.scrape_event_pricing(test_url)
        
        if full_results['success']:
            prices = full_results['prices']
            print(f"✅ Total Unique Prices: {len(prices)}")
            print(f"💰 Price Range: ${full_results['min_price']:.2f} - ${full_results['max_price']:.2f}")
            
            # Show source breakdown
            source_counts = {}
            for price in prices:
                source = price.get('source', 'unknown')
                source_counts[source] = source_counts.get(source, 0) + 1
            
            print(f"\n📊 Source Breakdown:")
            for source, count in source_counts.items():
                print(f"   • {source}: {count} prices")
            
            print(f"\n🎯 Sample Extracted Prices:")
            # Show variety of prices from different sources
            shown_sources = set()
            for price in prices:
                source = price.get('source')
                if source not in shown_sources or len(shown_sources) < 4:
                    section = price.get('section', 'general')
                    print(f"   • ${price['price']:.2f} - {section} (via {source})")
                    shown_sources.add(source)
                if len(shown_sources) >= 8:  # Show max 8 examples
                    break
            
            print(f"\n🏆 EXTRACTION SUCCESS ANALYSIS:")
            print("-" * 30)
            total_found = len(meta_prices) + len(json_prices) + len(element_prices) + len(text_prices)
            print(f"   • Raw extractions: {total_found}")
            print(f"   • After deduplication: {len(prices)}")
            print(f"   • Deduplication efficiency: {((total_found - len(prices)) / total_found * 100):.1f}%")
            print(f"   • Primary source: {max(source_counts.items(), key=lambda x: x[1])[0]}")
            
        else:
            print(f"❌ Extraction failed: {full_results.get('error', 'Unknown error')}")

if __name__ == "__main__":
    demonstrate_live_price_extraction()