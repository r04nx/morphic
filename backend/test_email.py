#!/usr/bin/env python3
"""
Test script for email notifications
"""
import os
import sys
from services.notifications import EmailService

def test_email_service():
    """Test the email service configuration"""
    print("🧪 Testing Email Service Configuration...")
    
    # Create email service with test config
    config = {
        'enabled': True,
        'destination': 'singhsudhanshu0404@gmail.com'  # Test email
    }
    
    email_service = EmailService(config)
    
    # Test connection
    print("\n📡 Testing SMTP connection...")
    connection_result = email_service.test_connection()
    
    if connection_result:
        print("✅ SMTP connection successful!")
        
        # Test sending email
        print("\n📧 Sending test email...")
        send_result = email_service.send_alert(
            monitor_id="test-monitor-123",
            status="DEGRADED",
            message="This is a test notification from Morphic's email service"
        )
        
        if send_result:
            print("✅ Test email sent successfully!")
            print("📬 Check your inbox for the test email.")
        else:
            print("❌ Failed to send test email")
    else:
        print("❌ SMTP connection failed")
        print("Please check your SMTP configuration:")
        print(f"  - SMTP_HOST: {os.getenv('SMTP_HOST')}")
        print(f"  - SMTP_PORT: {os.getenv('SMTP_PORT')}")
        print(f"  - EMAIL_FROM: {os.getenv('EMAIL_FROM')}")
        print(f"  - EMAIL_PASSWORD: {'*' * len(os.getenv('EMAIL_PASSWORD', '')) if os.getenv('EMAIL_PASSWORD') else 'NOT SET'}")

if __name__ == "__main__":
    test_email_service()
