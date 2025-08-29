#!/usr/bin/env python3
"""
Script to fix corrupted database configuration
"""
import json
import httpx

# Configuration
API_URL = "http://139.59.7.72:8002/toy"
SECRET = "66122e75-3b2a-45d7-a082-0f0894529348"

def get_current_config():
    """Get current configuration from database"""
    headers = {
        "Authorization": f"Bearer {SECRET}",
        "Content-Type": "application/json"
    }
    
    response = httpx.post(f"{API_URL}/config/server-base", headers=headers)
    response.raise_for_status()
    return response.json()["data"]

def update_config(config_data):
    """Update configuration in database"""
    headers = {
        "Authorization": f"Bearer {SECRET}",
        "Content-Type": "application/json"
    }
    
    # Assuming there's an update endpoint - we might need to find the correct one
    response = httpx.put(f"{API_URL}/config/server-base", headers=headers, json=config_data)
    response.raise_for_status()
    return response.json()

def fix_config():
    """Fix the corrupted configuration"""
    print("Getting current config...")
    config = get_current_config()
    
    # Fix the corrupted log_level
    if "log" in config and config["log"].get("log_level") == "http://139.59.7.72:8002/toy/ota/":
        print("Fixing corrupted log_level...")
        config["log"]["log_level"] = "INFO"
    
    # Ensure LLM configuration is correct (it seems to be already correct)
    if "LLM" in config and "Groq LLM" in config["LLM"]:
        llm_config = config["LLM"]["Groq LLM"]
        print(f"Current LLM config: {json.dumps(llm_config, indent=2)}")
        
        # Add missing fields that might be needed
        llm_config.update({
            "timeout": 15,
            "max_retries": 2,
            "retry_delay": 1
        })
    
    print("Fixed configuration:")
    print(json.dumps(config, indent=2))
    
    # For now, just print the config to see what needs to be fixed
    # We'll need to find the correct update endpoint
    return config

if __name__ == "__main__":
    try:
        fixed_config = fix_config()
        print("\nConfiguration has been analyzed. The main issue is the corrupted log_level.")
        print("You may need to use the admin interface to update this configuration.")
    except Exception as e:
        print(f"Error: {e}")