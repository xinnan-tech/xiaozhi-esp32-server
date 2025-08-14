#!/usr/bin/env python3
import sys
sys.path.append('.')

print("🌟 Quick Test: Indian News System 🌟\n")

try:
    from plugins_func.functions.get_indian_news_api import SAMPLE_INDIAN_NEWS
    print(f"✅ Indian news module loaded successfully")
    print(f"📰 Sample news available: {len(SAMPLE_INDIAN_NEWS)} items")
    print(f"📄 First news: {SAMPLE_INDIAN_NEWS[0]['title']}")
    print(f"📺 Source: {SAMPLE_INDIAN_NEWS[0]['source']}")
    print(f"🏷️ Category: {SAMPLE_INDIAN_NEWS[0]['category']}")

    print("\n🎯 Configuration Status:")
    # Check config
    import yaml
    with open('data/.config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    functions = config.get('Intent', {}).get(
        'function_call', {}).get('functions', [])
    print(f"✅ Enabled functions: {', '.join(functions)}")

    if 'get_indian_news_api' in functions:
        print("✅ Indian news API is enabled in configuration")
    else:
        print("❌ Indian news API not found in configuration")

    print("\n🚀 System Ready!")
    print("Your Xiaozhi server now supports Indian news queries!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
