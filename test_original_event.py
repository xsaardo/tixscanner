#!/usr/bin/env python3
"""
Test the original event ID from config.
"""

import sys
sys.path.insert(0, 'src')

from src.ticketmaster_api import TicketmasterAPI

try:
    api = TicketmasterAPI()
    
    # Test with original event ID from config
    event_id = '1700630C79D40EAD'
    print(f'🎵 Testing original config event ID: {event_id}\n')
    
    event = api.get_event_details(event_id)
    
    if event:
        print('✅ SUCCESS! The original event ID works now!')
        print('=' * 50)
        print(f'Name: {event.get("name")}')
        print(f'Venue: {event.get("venue")}') 
        print(f'City: {event.get("city")}')
        print(f'Date: {event.get("date")}')
        print(f'Status: {event.get("status")}')
        
        # Test pricing
        prices = api.get_ticket_prices(event_id)
        print(f'\nPrice data available: {len(prices) > 0}')
        
        print(f'\nYour config.ini is already set up correctly!')
        
    else:
        print('❌ Still having issues with the original event ID')

except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()