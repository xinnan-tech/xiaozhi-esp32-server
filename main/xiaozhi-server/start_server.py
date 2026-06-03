import sys
import os

# Add current directory to path first
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Also add main directory to path
main_dir = os.path.dirname(current_dir)
if main_dir not in sys.path:
    sys.path.insert(0, main_dir)

# Add xiaozhi-memory to path
xiaozhi_memory_path = os.path.join(main_dir, '..', 'xiaozhi-memory')
if os.path.exists(xiaozhi_memory_path) and xiaozhi_memory_path not in sys.path:
    sys.path.insert(0, xiaozhi_memory_path)

print(f"Python path setup complete:")
print(f"  current_dir: {current_dir}")
print(f"  main_dir: {main_dir}")
print(f"  xiaozhi_memory: {xiaozhi_memory_path}")

# Now run the app
import app
