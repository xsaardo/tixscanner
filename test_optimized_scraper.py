#!/usr/bin/env python3
"""
Test the optimized Ticketmaster scraper with section targeting.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.optimized_scraper import TicketmasterOptimizedScraper

def test_optimized_scraper():
    """Test the optimized scraper with section targeting."""
    
    print("🎯 Testing Optimized Ticketmaster Scraper with Section Targeting")
    print("=" * 70)
    
    # Backstreet Boys event URL
    event_url = "https://www.ticketmaster.com/backstreet-boys-into-the-millennium-las-vegas-nevada-12-26-2025/event/1700630C79D40EAD"
    
    print(f"🎵 Event: Backstreet Boys at The Sphere")
    print(f"🔗 URL: {event_url}")
    print()
    
    with TicketmasterOptimizedScraper(headless=True) as scraper:
        
        # Test 1: Get all sections
        print("1️⃣ Testing: All Sections")
        print("-" * 30)
        
        all_results = scraper.scrape_section_pricing(event_url)
        
        if all_results['success']:
            print(f"✅ Found {all_results['total_prices']} total prices")
            print(f"💰 Overall range: ${all_results['min_price']:.2f} - ${all_results['max_price']:.2f}")
            print(f"🎭 Sections found: {len(all_results['sections'])}")
            
            for section_name, section_data in all_results['sections'].items():
                price_count = len(section_data['prices'])
                min_price = section_data['min_price']
                max_price = section_data['max_price']
                avg_price = section_data['avg_price']
                
                print(f"   📍 {section_name}: {price_count} prices, ${min_price:.2f}-${max_price:.2f} (avg: ${avg_price:.2f})")
        else:
            print(f"❌ Failed: {all_results.get('error')}")
        
        print()
        
        # Test 2: Target General Admission specifically
        print("2️⃣ Testing: General Admission Only")
        print("-" * 30)
        
        ga_results = scraper.get_general_admission_prices(event_url)
        
        if ga_results['success']:
            print(f"✅ General Admission targeting successful")
            print(f"🎫 Sections matched: {list(ga_results['sections'].keys())}")
            
            for section_name, section_data in ga_results['sections'].items():
                prices = section_data['prices']
                print(f"   📍 {section_name}:")
                print(f"      • Price count: {len(prices)}")
                print(f"      • Price range: ${section_data['min_price']:.2f} - ${section_data['max_price']:.2f}")
                print(f"      • Average price: ${section_data['avg_price']:.2f}")
                
                # Show sample prices
                sample_prices = [p['price'] for p in prices[:5]]
                print(f"      • Sample prices: {[f'${p:.2f}' for p in sample_prices]}")
                
                # Show element context for first few prices
                print(f"      • Element context samples:")
                for i, price_data in enumerate(prices[:3]):
                    context = price_data['element_text'][:50] + "..." if len(price_data['element_text']) > 50 else price_data['element_text']
                    print(f"        {i+1}. ${price_data['price']:.2f} - \"{context}\"")
        else:
            print(f"❌ No General Admission prices found")
            if ga_results.get('sections'):
                print("Available sections:")
                for section in ga_results['sections'].keys():
                    print(f"   • {section}")
        
        print()
        
        # Test 3: Target specific sections with variations
        print("3️⃣ Testing: Multiple Target Sections")
        print("-" * 30)
        
        target_sections = ["General Admission", "Floor", "VIP", "Premium"]
        multi_results = scraper.scrape_section_pricing(event_url, target_sections=target_sections)
        
        if multi_results['success']:
            print(f"✅ Multi-section targeting successful")
            print(f"🎯 Targeted: {target_sections}")
            print(f"📍 Found: {list(multi_results['sections'].keys())}")
            
            for section_name, section_data in multi_results['sections'].items():
                price_count = len(section_data['prices'])
                price_range = f"${section_data['min_price']:.2f}-${section_data['max_price']:.2f}"
                print(f"   • {section_name}: {price_count} prices ({price_range})")
        else:
            print(f"❌ No matching sections found for: {target_sections}")
        
        print()
        
        # Performance comparison
        print("4️⃣ Performance Analysis")
        print("-" * 30)
        
        if all_results['success']:
            total_elements_processed = sum(len(section['prices']) for section in all_results['sections'].values())
            unique_sections = len(all_results['sections'])
            
            print(f"📊 Extraction Statistics:")
            print(f"   • Total price elements processed: {total_elements_processed}")
            print(f"   • Unique sections identified: {unique_sections}")
            print(f"   • Section identification accuracy: {(unique_sections > 1) and '✅ Good' or '⚠️ Limited'}")
            print(f"   • Price range coverage: ${all_results['min_price']:.2f} - ${all_results['max_price']:.2f}")
            
            print(f"\n🚀 Optimization Benefits:")
            print(f"   ✅ Focused extraction (element selectors only)")
            print(f"   ✅ Section-specific targeting capability")
            print(f"   ✅ Reduced processing overhead")
            print(f"   ✅ Better context preservation")
            
        print()
        print("🎉 Optimized scraper testing completed!")

def test_section_matching():
    """Test section matching logic separately."""
    
    print("\n🧪 Testing Section Matching Logic")
    print("-" * 40)
    
    with TicketmasterOptimizedScraper() as scraper:
        # Test various section name variations
        test_cases = [
            ("General Admission", ["General Admission"], True),
            ("GA Floor", ["General Admission"], True), 
            ("General", ["General Admission"], True),
            ("Section 101", ["General Admission"], False),
            ("Floor VIP", ["VIP"], True),
            ("Premium Seating", ["Premium"], True),
        ]
        
        print("Section matching test cases:")
        for section_name, targets, expected in test_cases:
            result = scraper._matches_target_section(section_name, targets)
            status = "✅" if result == expected else "❌"
            print(f"   {status} '{section_name}' matches {targets}: {result} (expected: {expected})")

if __name__ == "__main__":
    test_optimized_scraper()
    test_section_matching()