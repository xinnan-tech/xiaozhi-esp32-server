#!/usr/bin/env python3
"""Test TEN VAD ONNX installation on Linux"""

import os
import sys
import platform
from pathlib import Path

print(f"Platform: {platform.system()} {platform.machine()}")
print(f"Python: {sys.version}")

# Add the model path to sys.path
model_path = Path("models/ten-vad-onnx")
print(f"Model path: {model_path.absolute()}")

# Check if files exist
ten_vad_py = model_path / "ten_vad.py"
lib_so = model_path / "lib" / "Linux" / "x64" / "libten_vad.so"
lib_so_alt = model_path / "ten_vad_library" / "libten_vad.so"

print(f"\nFile checks:")
print(f"ten_vad.py exists: {ten_vad_py.exists()}")
print(f"libten_vad.so (main) exists: {lib_so.exists()}")
print(f"libten_vad.so (alt) exists: {lib_so_alt.exists()}")

# Set library path
os.environ['LD_LIBRARY_PATH'] = f"{lib_so.parent}:{lib_so_alt.parent}:{os.environ.get('LD_LIBRARY_PATH', '')}"
print(f"\nLD_LIBRARY_PATH: {os.environ['LD_LIBRARY_PATH']}")

# Try to import
sys.path.insert(0, str(model_path))
try:
    print("\nAttempting to import ten_vad...")
    from ten_vad import TenVad
    print("✅ Successfully imported TenVad")
    
    # Try to create instance
    vad = TenVad(hop_size=256, threshold=0.5)
    print("✅ Successfully created TenVad instance")
    
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()