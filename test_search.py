#!/usr/bin/env python3
"""
Test Ticketmaster search API directly.
"""

import requests
import os
from dotenv import load_dotenv
import json

load_dotenv()
api_key = os.getenv('TICKETMASTER_API_KEY')

# Test different search approaches
base_url = "https://app.ticketmaster.com/discovery/v2"

print("Testing Ticketmaster search API...")

# Test 1: Basic events search
print("\n1. Testing basic events search...")
params = {
    'apikey': api_key,
    'size': 5
}

try:
    response = requests.get(f"{base_url}/events", params=params, timeout=10)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        events = data.get('_embedded', {}).get('events', [])
        print(f"Found {len(events)} events")
        
        if events:
            for i, event in enumerate(events[:3]):
                print(f"  {i+1}. {event.get('name')} (ID: {event.get('id')})")
    else:
        print(f"Error: {response.text}")

    # Test 2: Search with keyword
    print("\n2. Testing search with keyword...")
    params['keyword'] = 'backstreet boys'
    
    response = requests.get(f"{base_url}/events", params=params, timeout=10)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        events = data.get('_embedded', {}).get('events', [])
        print(f"Found {len(events)} Backstreet Boys events")
        
        for event in events:
            print(f"  - {event.get('name')} (ID: {event.get('id')})")
            if '_embedded' in event and 'venues' in event['_embedded']:
                venue = event['_embedded']['venues'][0]
                print(f"    Venue: {venue.get('name')}")
    else:
        print(f"Error: {response.text}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()