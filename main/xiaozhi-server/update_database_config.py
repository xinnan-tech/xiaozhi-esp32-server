#!/usr/bin/env python3
"""
Script to update database configuration with fixes
"""
import json
import httpx

# Configuration
API_URL = "http://139.59.7.72:8002/toy"
SECRET = "66122e75-3b2a-45d7-a082-0f0894529348"

def update_config():
    """Update the database configuration with fixes"""
    headers = {
        "Authorization": f"Bearer {SECRET}",
        "Content-Type": "application/json"
    }
    
    # The main fix: correct the corrupted log_level
    config_fixes = {
        "log": {
            "log_level": "INFO"
        }
    }
    
    print("Updating database configuration...")
    print(f"Fixing log_level to: INFO")
    
    response = httpx.put(f"{API_URL}/config/server-base", headers=headers, json=config_fixes)
    response.raise_for_status()
    
    result = response.json()
    print(f"Update result: {json.dumps(result, indent=2)}")
    
    return result

if __name__ == "__main__":
    try:
        result = update_config()
        print("\nConfiguration updated successfully!")
        print("The corrupted log_level has been fixed.")
        print("You can now try running the application again.")
    except Exception as e:
        print(f"Error updating configuration: {e}")
        import traceback
        traceback.print_exc()