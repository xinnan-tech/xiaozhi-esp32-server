import os
import time
from memu import MemuClient

# Initialize MemU client
memu_client = MemuClient(
    base_url="https://api.memu.so",
    api_key=os.getenv("MEMU_API_KEY")
)

print("✅ MemU client initialized successfully!")