#!/usr/bin/env python3
"""
Script to update mem0 API key via the Manager API
This updates the model configuration through the API instead of direct database access
"""

import requests
import json
import sys
from datetime import datetime

# API Configuration
MANAGER_API_BASE_URL = "http://192.168.1.105:8002/xiaozhi"
SECRET = "66122e75-3b2a-45d7-a082-0f0894529348"

# The actual mem0 API key
MEM0_API_KEY = "m0-WNBvGhsBGZU1NDKDF42ecLNAgMk0GRaToaKLT0wN"

# You might need to login first to get a session
# Update these with your admin credentials
ADMIN_USERNAME = "admin"  # Update this
ADMIN_PASSWORD = "admin"  # Update this

# Colors for output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """Print a formatted header"""
    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}")

def print_success(text):
    """Print success message"""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_error(text):
    """Print error message"""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_info(text):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")

def print_warning(text):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def login():
    """Login to get session cookie"""
    print_header("Logging in to Manager API")
    
    url = f"{MANAGER_API_BASE_URL}/login"
    data = {
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD
    }
    
    try:
        session = requests.Session()
        response = session.post(url, json=data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0:
                print_success("Login successful")
                return session
            else:
                print_error(f"Login failed: {result.get('msg')}")
                return None
        else:
            print_error(f"HTTP {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Login request failed: {str(e)}")
        return None

def get_memory_configs(session):
    """Get all memory model configurations"""
    print_header("Fetching Memory Configurations")
    
    url = f"{MANAGER_API_BASE_URL}/models/list"
    params = {
        "modelType": "memory",
        "page": "0",
        "limit": "100"
    }
    
    headers = {
        "Authorization": f"Bearer {SECRET}",
        "Content-Type": "application/json"
    }
    
    try:
        response = session.get(url, params=params, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0:
                data = result.get("data", {})
                configs = data.get("list", [])
                
                mem0_configs = []
                for config in configs:
                    config_json = config.get("configJson", {})
                    if config_json.get("type") == "mem0ai":
                        mem0_configs.append(config)
                        print_info(f"Found mem0ai config: {config.get('modelName')} (ID: {config.get('id')})")
                        
                        current_key = config_json.get("api_key", "")
                        if current_key == "***":
                            print_warning(f"  Current API key: {current_key} (MASKED)")
                        elif current_key == MEM0_API_KEY:
                            print_success(f"  Current API key: {current_key[:10]}...{current_key[-10:]} (Already correct)")
                        else:
                            print_warning(f"  Current API key: {current_key[:10] if len(current_key) > 10 else current_key}...")
                
                return mem0_configs
            else:
                print_error(f"API error: {result.get('msg')}")
                return []
        else:
            print_error(f"HTTP {response.status_code}: {response.text}")
            return []
            
    except Exception as e:
        print_error(f"Request failed: {str(e)}")
        return []

def update_config(session, config):
    """Update a single configuration"""
    config_id = config.get("id")
    model_name = config.get("modelName")
    
    print_info(f"\nUpdating {model_name} (ID: {config_id})")
    
    # Get the current configuration
    url = f"{MANAGER_API_BASE_URL}/models/{config_id}"
    headers = {
        "Authorization": f"Bearer {SECRET}",
        "Content-Type": "application/json"
    }
    
    try:
        response = session.get(url, headers=headers)
        if response.status_code != 200 or response.json().get("code") != 0:
            print_error("Failed to get current configuration")
            return False
        
        current_config = response.json().get("data", {})
        
        # Update the configuration with the new API key
        config_json = current_config.get("configJson", {})
        config_json["api_key"] = MEM0_API_KEY
        
        # Prepare update payload
        update_data = {
            "modelName": current_config.get("modelName"),
            "isDefault": current_config.get("isDefault", 0),
            "isEnabled": current_config.get("isEnabled", 1),
            "configJson": config_json,
            "docLink": current_config.get("docLink", ""),
            "remark": current_config.get("remark", ""),
            "sort": current_config.get("sort", 0)
        }
        
        # Send update request
        update_url = f"{MANAGER_API_BASE_URL}/models/memory/mem0ai/{config_id}"
        
        response = session.put(update_url, json=update_data, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0:
                print_success(f"Successfully updated {model_name}")
                return True
            else:
                print_error(f"Update failed: {result.get('msg')}")
                return False
        else:
            print_error(f"HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Update request failed: {str(e)}")
        return False

def main():
    """Main function"""
    print_header("Mem0 API Key Update via Manager API")
    print_info(f"Target API Key: {MEM0_API_KEY[:10]}...{MEM0_API_KEY[-10:]}")
    print_info(f"API URL: {MANAGER_API_BASE_URL}")
    print_info(f"Timestamp: {datetime.now().isoformat()}")
    
    # Login to get session
    session = login()
    if not session:
        print_error("Cannot proceed without authentication")
        print_info("\nPlease update ADMIN_USERNAME and ADMIN_PASSWORD in this script")
        return 1
    
    # Get memory configurations
    configs = get_memory_configs(session)
    
    if not configs:
        print_warning("No mem0ai configurations found")
        return 0
    
    # Check if any need updating
    configs_to_update = []
    for config in configs:
        config_json = config.get("configJson", {})
        current_key = config_json.get("api_key", "")
        if current_key != MEM0_API_KEY:
            configs_to_update.append(config)
    
    if not configs_to_update:
        print_success("\nAll mem0ai configurations already have the correct API key")
        return 0
    
    # Ask for confirmation
    print_warning(f"\nFound {len(configs_to_update)} configuration(s) that need updating")
    response = input(f"{Colors.WARNING}Do you want to proceed? (yes/no): {Colors.ENDC}").lower()
    
    if response not in ['yes', 'y']:
        print_info("Update cancelled by user")
        return 0
    
    # Update configurations
    print_header("Updating Configurations")
    success_count = 0
    
    for config in configs_to_update:
        if update_config(session, config):
            success_count += 1
    
    # Summary
    print_header("Update Summary")
    if success_count == len(configs_to_update):
        print_success(f"✅ Successfully updated {success_count} configuration(s)")
        print_info("\nNext steps:")
        print_info("1. Clear Redis cache if enabled")
        print_info("2. Restart the xiaozhi-server")
        return 0
    else:
        print_warning(f"Updated {success_count} out of {len(configs_to_update)} configurations")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nScript interrupted by user")
        sys.exit(0)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        sys.exit(1)