#!/usr/bin/env python3
"""
Test getting details for Backstreet Boys event.
"""

import sys
sys.path.insert(0, 'src')

from src.ticketmaster_api import TicketmasterAPI

try:
    api = TicketmasterAPI()
    
    # Test with first Backstreet Boys event ID
    event_id = '1AvjZbYGksygZBc'
    print(f'🎵 Getting details for Backstreet Boys event: {event_id}\n')
    
    event = api.get_event_details(event_id)
    
    if event:
        print('✅ Event Details:')
        print('=' * 50)
        print(f'Name: {event.get("name")}')
        print(f'Venue: {event.get("venue")}') 
        print(f'City: {event.get("city")}')
        print(f'Date: {event.get("date")}')
        print(f'Time: {event.get("time")}')
        print(f'Status: {event.get("status")}')
        print(f'URL: {event.get("url")}')
        
        # Test pricing
        print(f'\n💰 Price Information:')
        prices = api.get_ticket_prices(event_id)
        
        if prices:
            print(f'Found {len(prices)} price entries:')
            for price in prices:
                print(f'  - {price.get("section")}: ${price.get("price")} - ${price.get("price_max", price.get("price"))}')
        else:
            print('No specific pricing data available')
            
        # Show price ranges from event data
        price_ranges = event.get('price_ranges', [])
        if price_ranges:
            print(f'\nPrice Ranges:')
            for pr in price_ranges:
                print(f'  - {pr.get("type")}: ${pr.get("min")} - ${pr.get("max")} {pr.get("currency")}')
        
        print(f'\n📊 API Usage: {api.get_api_usage_stats().get("requests_made", 0)} requests made')
        
    else:
        print('❌ Could not get event details')

except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()