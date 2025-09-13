#!/usr/bin/env python3
"""
Test script to target the specific sections found for Backstreet Boys event.
"""

import sys
import os
import logging
from pathlib import Path

# Add src directory to Python path
sys.path.append(str(Path(__file__).parent / 'src'))

from optimized_scraper import TicketmasterOptimizedScraper

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_numbered_sections():
    """Test targeting specific numbered sections that were found."""
    
    # Backstreet Boys event URL
    event_url = "https://www.ticketmaster.com/backstreet-boys-into-the-millennium-las-vegas-nevada-12-26-2025/event/1700630C79D40EAD"
    
    print("🎵 Testing Backstreet Boys numbered section pricing...")
    print(f"URL: {event_url}")
    
    # Initialize scraper (headless this time for speed)
    with TicketmasterOptimizedScraper(headless=True, timeout=30) as scraper:
        # Target specific numbered sections that were found
        target_sections = ['101', '102', '110']
        
        print(f"🎯 Targeting sections: {target_sections}")
        
        # Scrape with section targeting
        results = scraper.scrape_section_pricing(event_url, target_sections=target_sections)
        
        print("\n📊 Results:")
        print(f"Success: {results['success']}")
        print(f"Total sections found: {len(results.get('sections', {}))}")
        print(f"Total prices found: {results.get('total_prices', 0)}")
        
        if results['success']:
            print(f"Price range: ${results['min_price']:.2f} - ${results['max_price']:.2f}")
            
            print("\n🎫 Section Details:")
            for section_name, section_data in results['sections'].items():
                print(f"\n  {section_name}:")
                print(f"    Min Price: ${section_data['min_price']:.2f}")
                print(f"    Max Price: ${section_data['max_price']:.2f}")
                print(f"    Avg Price: ${section_data['avg_price']:.2f}")
                print(f"    Price Count: {len(section_data['prices'])}")
                
                # Show first few prices for verification
                for i, price_data in enumerate(section_data['prices'][:2]):
                    print(f"    Price {i+1}: ${price_data['price']:.2f} - {price_data['element_text'][:50]}...")
        else:
            print(f"❌ Error: {results.get('error', 'Unknown error')}")
        
        return results

if __name__ == "__main__":
    test_numbered_sections()