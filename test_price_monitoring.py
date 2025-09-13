#!/usr/bin/env python3
"""
Test script for TixScanner price monitoring system.

Tests the complete price monitoring workflow including:
- Price monitoring setup
- API integration with Ticketmaster
- Price change detection
- Email notifications
- Database operations
"""

import sys
import logging
from pathlib import Path
from decimal import Decimal
from datetime import datetime

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config_manager import ConfigManager
from src.price_monitor import PriceMonitor
from src.scheduler import MonitoringScheduler
from src.email_client import EmailClient
from src.models import Concert
from src.db_operations import add_concert, get_all_concerts

def setup_logging():
    """Set up logging for test script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

def test_price_monitoring():
    """Test the complete price monitoring system."""
    print("🎫 Testing TixScanner Price Monitoring System\n")
    
    try:
        # Load configuration
        print("1️⃣ Loading Configuration...")
        config = ConfigManager()
        api_key = config.get_ticketmaster_api_key()
        if not api_key or api_key == "your_api_key_here":
            print("   ❌ No valid Ticketmaster API key found")
            print("   Please set TICKETMASTER_API_KEY in .env file")
            return False
        print(f"   ✅ Configuration loaded (API key: {'*' * len(api_key[:-4])}{api_key[-4:]})")
        
        # Initialize email client
        print("\n2️⃣ Initializing Email Client...")
        email_client = EmailClient()
        if email_client.authenticate():
            print(f"   ✅ Email client authenticated as: {email_client.authenticator.get_user_email()}")
        else:
            print("   ❌ Email client authentication failed")
            return False
        
        # Initialize price monitor
        print("\n3️⃣ Initializing Price Monitor...")
        price_monitor = PriceMonitor(
            api_key=api_key,
            email_client=email_client
        )
        
        # Configure monitoring parameters
        price_monitor.configure(
            min_price_drop_percent=10.0,
            check_frequency_hours=2
        )
        print("   ✅ Price monitor initialized and configured")
        
        # Test monitoring setup
        print("\n4️⃣ Testing Monitoring Setup...")
        test_results = price_monitor.test_monitoring_setup()
        
        print(f"   API Connection: {'✅' if test_results['api_connection'] else '❌'}")
        print(f"   Database Connection: {'✅' if test_results['database_connection'] else '❌'}")
        print(f"   Email System: {'✅' if test_results['email_system'] else '❌'}")
        print(f"   Concerts Configured: {test_results['concerts_configured']}")
        print(f"   Ready for Monitoring: {'✅' if test_results['ready_for_monitoring'] else '❌'}")
        
        if not test_results['ready_for_monitoring']:
            print("\n⚠️  System not ready for monitoring. Adding test concert...")
            
            # Add a test concert if none exist
            test_concert = Concert(
                event_id="1AvjZbYGksygZBc",  # Backstreet Boys at The Sphere
                name="Backstreet Boys: DNA World Tour",
                venue="Sphere at The Venetian Resort",
                event_date=None,
                threshold_price=Decimal('200.00')
            )
            
            if add_concert(test_concert):
                print(f"   ✅ Added test concert: {test_concert.name}")
            else:
                print("   ❌ Failed to add test concert")
                return False
        
        # Run price check
        print("\n5️⃣ Running Price Check...")
        print("   📡 Checking prices for all tracked concerts...")
        
        results = price_monitor.check_all_prices()
        
        print(f"   Total Concerts: {results['total_concerts']}")
        print(f"   Prices Checked: {results['prices_checked']}")
        print(f"   Alerts Sent: {results['alerts_sent']}")
        print(f"   Errors: {results['errors']}")
        
        if results['prices_checked'] > 0:
            print("   ✅ Price check completed successfully")
            
            # Display detailed results
            for result in results['results']:
                if result.get('price_found'):
                    concert = result['concert']
                    current_price = result['current_price']
                    below_threshold = result['below_threshold']
                    
                    status = "🟢 Below threshold" if below_threshold else "🟡 Above threshold"
                    print(f"   • {concert.name}: ${current_price} ({status})")
                    
                    if result.get('price_change_percent'):
                        change = result['price_change_percent']
                        trend = "📉 Down" if change < 0 else "📈 Up" if change > 0 else "➡️ Same"
                        print(f"     Price change: {change:+.1f}% ({trend})")
        else:
            print("   ⚠️  No prices were successfully checked")
        
        # Test scheduler
        print("\n6️⃣ Testing Scheduler...")
        scheduler = MonitoringScheduler(price_monitor)
        scheduler.configure(
            price_check_interval=2,
            cleanup_interval_days=7
        )
        
        status = scheduler.get_status()
        print(f"   Price check interval: {status['price_check_interval']} hours")
        print(f"   Daily summary time: {status['daily_summary_time']}")
        print(f"   Cleanup interval: {status['cleanup_interval_days']} days")
        print("   ✅ Scheduler configured successfully")
        
        # Test daily summary (non-interactive for automated testing)
        print("\n7️⃣ Testing Daily Summary Email...")
        print("   📧 Sending daily summary...")
        summary_success = price_monitor.send_daily_summary()
        
        if summary_success:
            print("   ✅ Daily summary sent successfully!")
            print("   📨 Check your email inbox")
        else:
            print("   ❌ Daily summary failed to send")
        
        # Display monitoring statistics
        print("\n8️⃣ Monitoring Statistics...")
        stats = price_monitor.get_monitoring_stats()
        
        print(f"   Total Concerts Tracked: {stats['total_concerts']}")
        print(f"   Concerts Below Threshold: {stats['concerts_below_threshold']}")
        print(f"   Recent Price Drops: {stats['recent_price_drops']}")
        print(f"   Check Frequency: Every {stats['check_frequency_hours']} hours")
        print(f"   Minimum Drop Alert: {stats['min_price_drop_percent']}%")
        
        # Test database cleanup
        print("\n9️⃣ Testing Database Cleanup...")
        deleted_count = price_monitor.cleanup_old_data(days_to_keep=90)
        print(f"   ✅ Cleanup completed: {deleted_count} old records removed")
        
        print("\n🎉 Price Monitoring Test Completed Successfully!")
        print("\nNext Steps:")
        print("• Run 'python main.py' to perform a one-time price check")
        print("• Uncomment scheduler lines in main.py for continuous monitoring")
        print("• Add more concerts to config.ini to track additional events")
        print("• Monitor logs/tixscanner.log for detailed operation logs")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Price monitoring test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    setup_logging()
    
    success = test_price_monitoring()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()