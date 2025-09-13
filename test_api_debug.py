#!/usr/bin/env python3
"""
Debug script for Ticketmaster API integration.
"""

import sys
sys.path.insert(0, 'src')

import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Test basic API connectivity first
api_key = os.getenv('TICKETMASTER_API_KEY')
print(f'API Key loaded: {api_key[:10]}...' if api_key else 'No API key found')

# Test a simple search first
base_url = "https://app.ticketmaster.com/discovery/v2"

try:
    # Test basic connectivity with a search
    print('\nTesting basic API connectivity...')
    
    params = {
        'apikey': api_key,
        'size': 1,
        'keyword': 'taylor swift'
    }
    
    response = requests.get(f"{base_url}/events", params=params, timeout=10)
    print(f'Search API Response Status: {response.status_code}')
    
    if response.status_code == 200:
        data = response.json()
        events = data.get('_embedded', {}).get('events', [])
        if events:
            event = events[0]
            print(f'✅ Found event: {event.get("name")}')
            print(f'  Event ID: {event.get("id")}')
            print(f'  URL: {event.get("url")}')
            
            # Try getting details for this event
            event_id = event.get('id')
            print(f'\nTesting event details API with ID: {event_id}')
            
            detail_response = requests.get(f"{base_url}/events/{event_id}", 
                                         params={'apikey': api_key}, timeout=10)
            print(f'Event Details API Response Status: {detail_response.status_code}')
            
            if detail_response.status_code == 200:
                detail_data = detail_response.json()
                print(f'✅ Event details retrieved successfully')
                print(f'  Name: {detail_data.get("name")}')
                if '_embedded' in detail_data and 'venues' in detail_data['_embedded']:
                    venue = detail_data['_embedded']['venues'][0]
                    print(f'  Venue: {venue.get("name")}')
            else:
                print(f'❌ Event details failed: {detail_response.text}')
        else:
            print('No events found in search')
    else:
        print(f'❌ Search failed: {response.text}')
        
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()