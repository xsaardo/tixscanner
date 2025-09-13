#!/usr/bin/env python3
"""
Test script to send a daily email summary.
"""

import sys
import os
import logging
from pathlib import Path

# Add src directory to Python path
sys.path.append(str(Path(__file__).parent / 'src'))

from src.config_manager import ConfigManager
from src.price_monitor import PriceMonitor

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_daily_email():
    """Test sending daily email summary."""
    
    print("📧 Testing daily email summary functionality...")
    
    try:
        # Load configuration
        config = ConfigManager()
        
        print("📋 Validating configuration...")
        validation = config.validate_configuration()
        if not validation['valid']:
            print(f"❌ Configuration issues: {validation['errors']}")
            return False
        
        # Get API key and initialize monitor
        api_key = config.get_ticketmaster_api_key()
        print(f"🔑 Using API key: {'*' * (len(api_key) - 4)}{api_key[-4:]}")
        
        # Initialize price monitor with database and email
        print("🚀 Initializing price monitor...")
        monitor = PriceMonitor(
            api_key=api_key,
            db_path='tickets.db',
            enable_scraping=True
        )
        
        # Test monitoring setup first
        print("🔧 Testing monitoring setup...")
        setup_test = monitor.test_monitoring_setup()
        
        print("Setup Test Results:")
        for key, value in setup_test.items():
            status = "✅" if value else "❌"
            print(f"  {status} {key}: {value}")
        
        if not setup_test['ready_for_monitoring']:
            print("⚠️ System not ready for monitoring, but continuing with email test...")
        
        # Check current monitoring stats
        print("\n📊 Current monitoring statistics:")
        stats = monitor.get_monitoring_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # Run a quick price check to populate data
        print("\n💰 Running price check to populate recent data...")
        price_results = monitor.check_all_prices()
        
        print(f"Price Check Results:")
        print(f"  Total concerts: {price_results['total_concerts']}")
        print(f"  Prices found: {price_results['prices_checked']}")
        print(f"  Alerts sent: {price_results['alerts_sent']}")
        print(f"  Errors: {price_results['errors']}")
        
        # Show details of what was found
        if price_results['results']:
            print("\n🎫 Concert pricing details:")
            for result in price_results['results']:
                concert = result['concert']
                print(f"\n  {concert.name}:")
                print(f"    Current Price: ${result.get('current_price', 'N/A')}")
                print(f"    Threshold: ${concert.threshold_price}")
                print(f"    Price Found: {result.get('price_found', False)}")
                print(f"    Below Threshold: {result.get('below_threshold', False)}")
                if result.get('error'):
                    print(f"    Error: {result['error']}")
        
        # Now send the daily summary email
        print("\n📨 Sending daily summary email...")
        email_success = monitor.send_daily_summary()
        
        if email_success:
            print("✅ Daily summary email sent successfully!")
            print("\nCheck your email inbox for the daily summary.")
        else:
            print("❌ Failed to send daily summary email")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error during email test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_daily_email()
    if success:
        print("\n🎉 Daily email test completed successfully!")
    else:
        print("\n💥 Daily email test failed!")