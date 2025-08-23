#!/usr/bin/env python3
"""
Test script to verify OTA activation code generation
"""

import json
import asyncio
import httpx

async def test_ota_endpoint():
    """Test the OTA endpoint with a sample device"""
    
    # Sample device data (similar to what your ESP32 sends)
    device_data = {
        "version": 176,
        "flash_size": 4194304,
        "minimum_free_heap_size": 186020,
        "mac_address": "68:25:dd:bb:4d:44",
        "uuid": "848fc4d1-3db0-42e5-a0e6-e60a9b4477d8",
        "chip_model_name": "ESP32",
        "chip_info": {
            "model": 1,
            "cores": 2,
            "revision": 301,
            "features": 62
        },
        "application": {
            "name": "Xiaozhi_ESP32",
            "version": "1.7.6",
            "compile_time": "2025-08-23T10:00:00Z",
            "idf_version": "v5.2.1",
            "elf_sha256": "d4e77c78a2f8a0b4b2e1c4e77c78a2f8a0b4b2e1"
        },
        "partition_table": [],
        "ota": {
            "label": "ota_0"
        },
        "board": {
            "type": "doit-ai-01-kit",
            "ssid": "TestWiFi",
            "rssi": -45,
            "channel": 6,
            "ip": "192.168.1.74",
            "mac": "68:25:dd:bb:4d:44"
        }
    }
    
    # OTA endpoint URL
    ota_url = "http://192.168.1.105:8003/xiaozhi/ota/"
    
    # Headers that the device sends
    headers = {
        "device-id": "68:25:dd:bb:4d:44",
        "Content-Type": "application/json"
    }
    
    print(f"Testing OTA endpoint: {ota_url}")
    print(f"Device ID: {headers['device-id']}")
    print(f"Device firmware: {device_data['application']['version']}")
    print("-" * 50)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                ota_url,
                headers=headers,
                json=device_data,
                timeout=10.0
            )
            
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"Response data: {json.dumps(result, indent=2)}")
                
                # Check if activation code is present
                if "activation" in result:
                    activation = result["activation"]
                    print("\n" + "=" * 50)
                    print("ACTIVATION CODE RECEIVED!")
                    print(f"Code: {activation.get('code')}")
                    print(f"Message: {activation.get('message')}")
                    print("=" * 50)
                else:
                    print("\nNo activation code in response")
                    
            else:
                print(f"Error response: {response.text}")
                
    except Exception as e:
        print(f"Error testing OTA endpoint: {e}")

if __name__ == "__main__":
    asyncio.run(test_ota_endpoint())