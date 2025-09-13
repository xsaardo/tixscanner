#!/usr/bin/env python3
"""
Test script for Gmail API email system setup.
"""

import sys
sys.path.insert(0, 'src')

from src.gmail_auth import setup_gmail_auth
from src.email_client import EmailClient
from src.chart_generator import ChartGenerator

print("🚀 Testing TixScanner Email System Setup\n")

# Test 1: Check Gmail API setup
print("1️⃣ Testing Gmail API Authentication...")
try:
    authenticator = setup_gmail_auth()
    print(f"   ✅ Authenticated as: {authenticator.get_user_email()}")
except Exception as e:
    print(f"   ❌ Authentication failed: {e}")
    print("\n📋 Setup Instructions:")
    print(authenticator.setup_instructions() if 'authenticator' in locals() else """
    Please follow these steps to set up Gmail API:
    
    1. Go to https://console.cloud.google.com/
    2. Create a new project
    3. Enable Gmail API
    4. Create OAuth2 credentials (Desktop application)
    5. Download and save as 'gmail_credentials.json'
    """)
    sys.exit(1)

print()

# Test 2: Initialize email client
print("2️⃣ Testing Email Client Initialization...")
try:
    email_client = EmailClient()
    if email_client.authenticate():
        print("   ✅ Email client initialized and authenticated")
    else:
        print("   ❌ Email client authentication failed")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ Email client initialization failed: {e}")
    sys.exit(1)

print()

# Test 3: Check chart generation
print("3️⃣ Testing Chart Generation...")
try:
    chart_gen = ChartGenerator()
    print("   ✅ Chart generator initialized")
    
    # Test with dummy data chart
    no_data_chart = chart_gen._generate_no_data_chart("Test Event")
    if no_data_chart:
        print("   ✅ Chart generation working")
    else:
        print("   ❌ Chart generation failed")
        
except Exception as e:
    print(f"   ❌ Chart generation test failed: {e}")

print()

# Test 4: Send test email
print("4️⃣ Testing Email Sending...")
try:
    user_input = input("   Send a test email to verify everything works? (y/n): ").lower()
    if user_input == 'y':
        print("   📤 Sending test email...")
        
        if email_client.send_test_email():
            print("   ✅ Test email sent successfully!")
            print("   📧 Check your inbox for the test email")
        else:
            print("   ❌ Test email failed to send")
    else:
        print("   ⏭️  Skipping test email")
        
except Exception as e:
    print(f"   ❌ Test email failed: {e}")

print()

# Test 5: Setup status summary
print("5️⃣ System Status Summary...")
try:
    status = email_client.get_setup_status()
    
    print(f"   Email Authentication: {'✅' if status['authenticated'] else '❌'}")
    print(f"   User Email: {status['user_email']}")
    print(f"   Templates Loaded: {status['templates_loaded']}/2")
    print(f"   Chart Generator: {'✅' if status['chart_generator'] else '❌'}")
    print(f"   Connection Test: {'✅' if status['connection_test'] else '❌'}")
    
    if all([status['authenticated'], status['templates_loaded'] >= 2, status['chart_generator']]):
        print("\n🎉 Email system is fully configured and ready!")
        print("   You can now receive price alerts and daily summaries")
    else:
        print("\n⚠️  Some components need attention")
        
except Exception as e:
    print(f"   ❌ Status check failed: {e}")

print("\n" + "="*50)
print("Email system test completed!")
print("Your TixScanner is ready for secure email notifications")