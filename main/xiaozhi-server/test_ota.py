import requests
import json

# Test OTA connection to Manager API
device_mac = "68:25:dd:ba:39:78"

manager_api_url = "http://192.168.1.105:8002/xiaozhi/ota/"

headers = {"device-id": device_mac}
data = {
    "application": {
        "version": "1.7.6"
    },
    "client_id": "test-client-id"
}

print(f"Testing OTA connection to Manager API at {manager_api_url}")
print(f"Device MAC: {device_mac}")
print("-" * 60)

try:
    response = requests.post(manager_api_url, headers=headers, json=data, timeout=5)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    # Check for activation code
    activation = response.json().get("activation")
    if activation:
        code = activation.get("code")
        if code:
            print("\n" + "=" * 60)
            print(f"🔐 ACTIVATION CODE: {code}")
            print("=" * 60)
            print(f"Please bind this device using code: {code}")
    else:
        print("\n⚠️ No activation code in response - device may already be registered")
        
except Exception as e:
    print(f"Error: {e}")