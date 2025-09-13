#!/usr/bin/env python3
"""
Test script for Ticketmaster API integration.
"""

import sys
sys.path.insert(0, 'src')

from src.ticketmaster_api import TicketmasterAPI
import json

# Test API client initialization and basic functionality
try:
    api = TicketmasterAPI()
    print('✅ API client initialized successfully')
    
    # Test with a working event ID
    event_id = 'rZ7HnEZ1AKPb0f'  # Taylor Swift Trivia event
    print(f'Testing with event ID: {event_id}')
    
    # Test event details retrieval
    print('Fetching event details...')
    event = api.get_event_details(event_id)
    
    if event:
        print('✅ Event details retrieved:')
        print(f'  Name: {event.get("name", "N/A")}')
        print(f'  Venue: {event.get("venue", "N/A")}')
        print(f'  City: {event.get("city", "N/A")}')
        print(f'  Date: {event.get("date", "N/A")}')
        print(f'  Status: {event.get("status", "N/A")}')
        print(f'  Price ranges: {len(event.get("price_ranges", []))}')
        
        # Test ticket pricing
        print('\nFetching ticket prices...')
        prices = api.get_ticket_prices(event_id)
        
        if prices:
            print(f'✅ Found {len(prices)} price entries:')
            for i, price in enumerate(prices[:3]):  # Show first 3
                print(f'  {i+1}. Section: {price.get("section", "N/A")}, Price: ${price.get("price", "N/A")}')
        else:
            print('⚠️  No pricing data available')
            
        # Test API stats
        stats = api.get_api_usage_stats()
        print(f'\nAPI Usage: {stats.get("requests_made", 0)} requests made')
        
    else:
        print('❌ No event data retrieved')
        
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()