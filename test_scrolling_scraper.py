#!/usr/bin/env python3
"""
Test script to verify the updated scraper with scrolling simulation 
can find General Admission pricing for Backstreet Boys.
"""

import sys
import os
import logging
from pathlib import Path

# Add src directory to Python path
sys.path.append(str(Path(__file__).parent / 'src'))

from optimized_scraper import TicketmasterOptimizedScraper

# Set up logging
logging.basicConfig(level=logging.DEBUG)

def test_ga_pricing():
    """Test General Admission pricing extraction with scrolling."""
    
    # Backstreet Boys event URL (correct event with GA tickets)
    event_url = "https://www.ticketmaster.com/backstreet-boys-into-the-millennium-las-vegas-nevada-12-26-2025/event/1700630C79D40EAD"
    
    print("🎵 Testing Backstreet Boys General Admission pricing with scrolling simulation...")
    print(f"URL: {event_url}")
    
    # Initialize scraper (non-headless so we can see what's happening)
    with TicketmasterOptimizedScraper(headless=False, timeout=30) as scraper:
        # Target General Admission sections
        target_sections = ['General Admission', 'GA']
        
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
                for i, price_data in enumerate(section_data['prices'][:3]):
                    print(f"    Price {i+1}: ${price_data['price']:.2f} - {price_data['element_text'][:50]}...")
        else:
            print(f"❌ Error: {results.get('error', 'Unknown error')}")
        
        # Also try getting all sections to see what's available
        print("\n🔍 Checking all available sections...")
        all_results = scraper.scrape_section_pricing(event_url, target_sections=None)
        
        if all_results['success']:
            print("📋 All sections found:")
            for section_name in all_results['sections'].keys():
                print(f"  - {section_name}")
        
        return results

if __name__ == "__main__":
    test_ga_pricing()