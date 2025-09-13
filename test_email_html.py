#!/usr/bin/env python3
"""
Test script to generate daily email HTML without sending it.
"""

import sys
import os
import logging
from pathlib import Path

# Add src directory to Python path
sys.path.append(str(Path(__file__).parent / 'src'))

from src.config_manager import ConfigManager
from src.price_monitor import PriceMonitor
from src.email_client import EmailClient

# Set up logging
logging.basicConfig(level=logging.INFO)

def generate_email_html():
    """Generate daily email HTML and save to file."""
    
    print("📧 Generating daily email HTML for inspection...")
    
    try:
        # Load configuration
        config = ConfigManager()
        api_key = config.get_ticketmaster_api_key()
        
        # Initialize price monitor
        monitor = PriceMonitor(
            api_key=api_key,
            db_path='tickets.db',
            enable_scraping=True
        )
        
        # Initialize email client separately to access HTML generation
        email_client = EmailClient(db_path='tickets.db')
        
        print("💰 Running price check to get fresh data...")
        # Get fresh pricing data
        price_results = monitor.check_all_prices()
        print(f"Found {price_results['prices_checked']} prices across {price_results['total_concerts']} concerts")
        
        # Generate the HTML content by replicating the daily summary logic
        print("🎨 Generating email HTML content...")
        
        # Get the same data that send_daily_summary would use
        from src.db_operations import get_all_concerts, get_latest_price
        from src.models import EmailType, EmailLog
        from decimal import Decimal
        from datetime import datetime
        
        # Get all concerts
        concerts = get_all_concerts('tickets.db')
        if not concerts:
            print("No concerts to include in daily summary")
            return False
        
        # Prepare concert data (same logic as in send_daily_summary)
        concert_data = []
        price_drops = 0
        below_threshold = 0
        total_savings = Decimal('0')
        
        for concert in concerts:
            latest_price = get_latest_price(concert.event_id, 'tickets.db')
            
            if latest_price:
                # Calculate price change (placeholder)
                price_change = 0  # Same as in original
                current_price = float(latest_price.price)
                
                is_below_threshold = latest_price.price <= concert.threshold_price
                if is_below_threshold:
                    below_threshold += 1
                    if price_change < 0:
                        total_savings += abs(Decimal(str(price_change)))
                
                if price_change < 0:
                    price_drops += 1
                
                # Generate individual chart
                chart_image = email_client.chart_generator.generate_price_trend_chart(
                    concert.event_id, days=7, db_path='tickets.db'
                )
                
                concert_data.append({
                    'name': concert.name,
                    'venue': concert.venue or 'TBA',
                    'date': concert.event_date.strftime('%m/%d/%Y') if concert.event_date else 'TBA',
                    'current_price': f"{current_price:.0f}",
                    'threshold_price': f"{concert.threshold_price:.0f}",
                    'price_change': f"+{abs(price_change):.0f}%" if price_change > 0 else f"{price_change:.0f}%",
                    'price_trend_class': 'price-down' if price_change < 0 else ('price-up' if price_change > 0 else 'price-same'),
                    'below_threshold': is_below_threshold,
                    'threshold_class': 'below-threshold' if is_below_threshold else 'above-threshold',
                    'chart_image': chart_image,
                    'purchase_url': f"https://www.ticketmaster.com/search?q={concert.name.replace(' ', '+')}"
                })
        
        # Generate summary chart
        summary_chart = email_client.chart_generator.generate_summary_chart(
            [{'name': c['name'], 'current_price': float(c['current_price']), 
              'price_change_percent': 0, 'threshold_price': float(c['threshold_price'])} 
             for c in concert_data],
            'tickets.db'
        )
        
        # Prepare template context
        context = {
            'date': datetime.now().strftime('%B %d, %Y'),
            'total_concerts': len(concerts),
            'price_drops': price_drops,
            'below_threshold': below_threshold,
            'avg_savings': f"{total_savings / max(below_threshold, 1):.0f}",
            'concerts': concert_data,
            'summary_chart': summary_chart,
            'summary_time': datetime.now().strftime('%I:%M %p'),
            'user_email': email_client.authenticator.get_user_email()
        }
        
        # Render email content using the same method
        html_content = email_client._render_template('daily_summary', context)
        
        # Save to file
        output_file = "daily_email_output.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ HTML content saved to: {output_file}")
        print(f"📄 File size: {len(html_content)} characters")
        
        print(f"📊 Email data summary:")
        print(f"  Total concerts: {len(concerts)}")
        print(f"  Price drops: {price_drops}")
        print(f"  Below threshold: {below_threshold}")
        print(f"  Concert data items: {len(concert_data)}")
        
        # Show a preview of the HTML
        print("\n🔍 HTML Preview (first 500 characters):")
        print("-" * 50)
        print(html_content[:500])
        print("..." if len(html_content) > 500 else "")
        print("-" * 50)
        
        return True
        
    except Exception as e:
        print(f"❌ Error generating email HTML: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = generate_email_html()
    if success:
        print("\n🎉 Email HTML generation completed successfully!")
        print("Open 'daily_email_output.html' in a web browser to inspect the formatting.")
    else:
        print("\n💥 Email HTML generation failed!")