#!/usr/bin/env python3
"""
Test script for Manager API configuration endpoints
This script tests the getAgentModels endpoint that xiaozhi-server uses to get device configuration
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
MANAGER_API_BASE_URL = "http://192.168.1.105:8002/xiaozhi"
SECRET = "66122e75-3b2a-45d7-a082-0f0894529348"

# Test device information
TEST_DEVICE_MAC = "68:25:dd:bb:4d:44"  # Your actual device MAC
TEST_CLIENT_ID = "test-client-001"

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
    UNDERLINE = '\033[4m'

def print_header(text):
    """Print a formatted header"""
    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}")

def print_success(text):
    """Print success message"""
    print(f"{Colors.OKGREEN}[OK] {text}{Colors.ENDC}")

def print_error(text):
    """Print error message"""
    print(f"{Colors.FAIL}[ERROR] {text}{Colors.ENDC}")

def print_info(text):
    """Print info message"""
    print(f"{Colors.OKCYAN}[INFO] {text}{Colors.ENDC}")

def print_json(data, indent=2):
    """Pretty print JSON data"""
    print(json.dumps(data, indent=indent, ensure_ascii=False))

def test_server_config():
    """Test getting server configuration"""
    print_header("Testing Server Configuration Endpoint")
    
    url = f"{MANAGER_API_BASE_URL}/config/server-base"
    
    # Use Bearer token authentication like the actual client
    headers = {
        "Authorization": f"Bearer {SECRET}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "PythonClient/2.0 Test"
    }
    
    try:
        print_info(f"POST {url}")
        response = requests.post(url, headers=headers, json={})
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                print_success("Server configuration retrieved successfully")
                print_info("Server Configuration:")
                print_json(data.get("data", {}))
                return data.get("data")
            else:
                print_error(f"API returned error: {data.get('msg')}")
        else:
            print_error(f"HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print_error(f"Request failed: {str(e)}")
    
    return None

def test_agent_models(mac_address=TEST_DEVICE_MAC, client_id=TEST_CLIENT_ID):
    """Test getting agent models configuration for a device"""
    print_header("Testing Agent Models Configuration Endpoint")
    
    url = f"{MANAGER_API_BASE_URL}/config/agent-models"
    
    # Build request body (no secret in body, it's in the header)
    request_data = {
        "macAddress": mac_address,
        "clientId": client_id,
        "selectedModule": {
            "VAD": None,
            "ASR": None,
            "LLM": None,
            "TTS": None,
            "Memory": None,
            "Intent": None,
            "VLLM": None
        }
    }
    
    # Use Bearer token authentication
    headers = {
        "Authorization": f"Bearer {SECRET}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "PythonClient/2.0 Test"
    }
    
    try:
        print_info(f"POST {url}")
        print_info(f"Device MAC: {mac_address}")
        print_info(f"Client ID: {client_id}")
        print_info("Request Body:")
        print_json(request_data)
        
        response = requests.post(url, json=request_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                print_success("Agent models configuration retrieved successfully")
                config = data.get("data", {})
                
                # Analyze the configuration
                analyze_configuration(config)
                
                # Save to file for analysis
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"agent_config_{timestamp}.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                print_success(f"Configuration saved to {filename}")
                
                return config
            else:
                print_error(f"API returned error: {data.get('msg')}")
                if "OTA_DEVICE_NEED_BIND" in str(data.get("code", "")):
                    print_info("Device needs binding. Bind code: " + data.get("msg", ""))
        else:
            print_error(f"HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print_error(f"Request failed: {str(e)}")
    
    return None

def analyze_configuration(config):
    """Analyze and display key configuration details"""
    print_header("Configuration Analysis")
    
    # Check selected modules
    if "selected_module" in config:
        print_info("Selected Modules:")
        for module, value in config["selected_module"].items():
            status = f"{Colors.OKGREEN}[OK]{Colors.ENDC}" if value else f"{Colors.WARNING}[X]{Colors.ENDC}"
            print(f"  {status} {module}: {value or 'Not configured'}")
    
    # Check Memory configuration specifically
    if "Memory" in config:
        print_info("\nMemory Configuration:")
        for mem_id, mem_config in config["Memory"].items():
            print(f"  Module: {mem_id}")
            if isinstance(mem_config, dict):
                for key, value in mem_config.items():
                    if key == "api_key":
                        # Check if API key is masked
                        if value == "***":
                            print_error(f"    {key}: {value} (MASKED - This is the problem!)")
                        elif value and len(value) > 20:
                            print_success(f"    {key}: {value[:10]}...{value[-10:]} (length: {len(value)})")
                        else:
                            print_warning(f"    {key}: {value} (Suspicious - too short!)")
                    else:
                        print(f"    {key}: {value}")
    
    # Check LLM configuration
    if "LLM" in config:
        print_info("\nLLM Configuration:")
        for llm_id, llm_config in config["LLM"].items():
            print(f"  Module: {llm_id}")
            if isinstance(llm_config, dict):
                for key, value in llm_config.items():
                    if key == "api_key":
                        if value == "***":
                            print_error(f"    {key}: {value} (MASKED)")
                        else:
                            print(f"    {key}: {value[:10]}...{value[-10:] if len(str(value)) > 20 else value}")
                    elif key in ["base_url", "model_name"]:
                        print(f"    {key}: {value}")
    
    # Check other important settings
    print_info("\nOther Settings:")
    print(f"  Chat History Config: {config.get('chat_history_conf', 'Not set')}")
    print(f"  Device Max Output Size: {config.get('device_max_output_size', 'Not set')}")
    print(f"  Summary Memory: {config.get('summaryMemory', 'Not set')}")
    
    # Check plugins
    if "plugins" in config:
        print_info("\nPlugins:")
        for plugin_name in config["plugins"].keys():
            print(f"  + {plugin_name}")

def print_warning(text):
    """Print warning message"""
    print(f"{Colors.WARNING}[WARNING] {text}{Colors.ENDC}")

def test_device_registration():
    """Test device registration status"""
    print_header("Testing Device Registration")
    
    url = f"{MANAGER_API_BASE_URL}/device/info/{TEST_DEVICE_MAC}"
    
    # Use Bearer token authentication
    headers = {
        "Authorization": f"Bearer {SECRET}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "PythonClient/2.0 Test"
    }
    
    try:
        print_info(f"GET {url}")
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                device_info = data.get("data")
                if device_info:
                    print_success("Device is registered")
                    print_info(f"Device ID: {device_info.get('id')}")
                    print_info(f"Agent ID: {device_info.get('agentId')}")
                    print_info(f"User ID: {device_info.get('userId')}")
                else:
                    print_warning("Device not found in database")
            else:
                print_error(f"API returned error: {data.get('msg')}")
        else:
            print_error(f"HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print_error(f"Request failed: {str(e)}")

def main():
    """Main test function"""
    print_header("Manager API Configuration Test Script")
    print_info(f"Manager API URL: {MANAGER_API_BASE_URL}")
    print_info(f"Test Device MAC: {TEST_DEVICE_MAC}")
    print_info(f"Timestamp: {datetime.now().isoformat()}")
    
    # Test server configuration
    server_config = test_server_config()
    
    # Test device registration
    test_device_registration()
    
    # Test agent models configuration
    agent_config = test_agent_models()
    
    # Summary
    print_header("Test Summary")
    if agent_config:
        # Check for masked API keys
        memory_config = agent_config.get("Memory", {})
        masked_keys = []
        
        for module_id, module_config in memory_config.items():
            if isinstance(module_config, dict):
                api_key = module_config.get("api_key")
                if api_key == "***":
                    masked_keys.append(f"Memory/{module_id}")
        
        llm_config = agent_config.get("LLM", {})
        for module_id, module_config in llm_config.items():
            if isinstance(module_config, dict):
                api_key = module_config.get("api_key")
                if api_key == "***":
                    masked_keys.append(f"LLM/{module_id}")
        
        if masked_keys:
            print_error("PROBLEM FOUND: The following API keys are masked:")
            for key in masked_keys:
                print(f"  - {key}")
            print_warning("\nSolution Options:")
            print("  1. Add system parameter 'mem0.api_key' with the actual API key")
            print("  2. Update the database directly with the actual API key")
            print("  3. Modify the backend to not mask API keys for device connections")
        else:
            print_success("All API keys appear to be properly configured")
    else:
        print_error("Failed to retrieve agent configuration")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(0)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        sys.exit(1)