#!/usr/bin/env python3
"""
Test script for Indian localization changes
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_ip_location():
    """Test IP location detection with Indian service"""
    print("=== Testing IP Location Detection ===")

    from core.utils.util import get_ip_info
    from config.logger import setup_logging

    logger = setup_logging()

    # Test with a known Indian IP (example)
    test_ips = [
        "103.21.58.66",  # Example Indian IP
        "8.8.8.8",       # Google DNS (should show US)
        "",              # Empty IP (should use local)
    ]

    for ip in test_ips:
        try:
            result = get_ip_info(ip, logger)
            print(f"IP: {ip} -> Location: {result}")
        except Exception as e:
            print(f"Error testing IP {ip}: {e}")
    print()


def test_indian_time():
    """Test Indian Standard Time"""
    print("=== Testing Indian Standard Time ===")

    from core.utils.prompt_manager import PromptManager
    from config.logger import setup_logging

    logger = setup_logging()
    config = {}  # Minimal config for testing

    pm = PromptManager(config, logger)

    try:
        today_date, today_weekday, indian_date = pm._get_current_time_info()
        print(f"Today's Date: {today_date}")
        print(f"Weekday: {today_weekday}")
        print(f"Indian Calendar: {indian_date}")
    except Exception as e:
        print(f"Error testing time: {e}")
    print()


def test_indian_calendar():
    """Test Indian calendar function"""
    print("=== Testing Indian Calendar Function ===")

    try:
        from plugins_func.functions.get_time import get_lunar

        # Test current date
        result = get_lunar()
        print("Current Date Result:")
        print(result.result)
        print()

        # Test specific date
        result = get_lunar(date="2025-01-15",
                           query="Vikram Samvat year and Hindu month")
        print("Specific Date Result:")
        print(result.result)

    except Exception as e:
        print(f"Error testing Indian calendar: {e}")
    print()


def test_prompt_building():
    """Test enhanced prompt building"""
    print("=== Testing Enhanced Prompt Building ===")

    from core.utils.prompt_manager import PromptManager
    from config.logger import setup_logging

    logger = setup_logging()
    config = {}

    pm = PromptManager(config, logger)

    try:
        user_prompt = "You are a helpful AI assistant."
        device_id = "test_device_123"
        client_ip = "103.21.58.66"  # Example Indian IP

        # First update context
        pm.update_context_info(
            type('MockConn', (), {'config': config})(), client_ip)

        # Then build enhanced prompt
        enhanced = pm.build_enhanced_prompt(user_prompt, device_id, client_ip)

        print("Enhanced Prompt Preview (first 500 chars):")
        print(enhanced[:500] + "..." if len(enhanced) > 500 else enhanced)

    except Exception as e:
        print(f"Error testing prompt building: {e}")
    print()


if __name__ == "__main__":
    print("🇮🇳 Testing Indian Localization Changes 🇮🇳\n")

    # Install required dependency if not present
    try:
        import pytz
        print("✅ pytz is installed")
    except ImportError:
        print("❌ pytz not installed. Please run: pip install pytz")
        sys.exit(1)

    print()

    # Run tests
    test_ip_location()
    test_indian_time()
    test_indian_calendar()
    test_prompt_building()

    print("🎉 Testing completed!")
