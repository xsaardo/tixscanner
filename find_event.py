#!/usr/bin/env python3
"""
Script to find Ticketmaster event IDs by searching.
"""

import sys
sys.path.insert(0, 'src')

from src.ticketmaster_api import TicketmasterAPI

try:
    api = TicketmasterAPI()
    print('🔍 Searching for Backstreet Boys events at The Sphere...\n')
    
    # Search for Backstreet Boys events
    events = api.search_events("Backstreet Boys", city="Las Vegas", size=10)
    
    if events:
        print(f'Found {len(events)} Backstreet Boys events:')
        print('=' * 60)
        
        for i, event in enumerate(events, 1):
            print(f'{i}. Event ID: {event.get("id")}')
            print(f'   Name: {event.get("name")}')
            print(f'   Venue: {event.get("venue", "N/A")}')
            print(f'   Date: {event.get("date", "N/A")}')
            print(f'   Status: {event.get("status", "N/A")}')
            if event.get("url"):
                print(f'   URL: {event.get("url")}')
            print()
    else:
        print('❌ No Backstreet Boys events found.')
        print('\nTrying broader search...')
        
        # Try searching just for "sphere" to see what events are there
        sphere_events = api.search_events("sphere", city="Las Vegas", size=5)
        
        if sphere_events:
            print(f'Found {len(sphere_events)} events at venues with "sphere" in the name:')
            print('=' * 60)
            
            for i, event in enumerate(sphere_events, 1):
                print(f'{i}. Event ID: {event.get("id")}')
                print(f'   Name: {event.get("name")}')
                print(f'   Venue: {event.get("venue", "N/A")}')
                print(f'   Date: {event.get("date", "N/A")}')
                print()
        else:
            print('❌ No Sphere events found either.')

except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()