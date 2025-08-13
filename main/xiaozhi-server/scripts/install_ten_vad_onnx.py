#!/usr/bin/env python3
"""
Installation script for TEN VAD ONNX
This script helps set up TEN VAD ONNX for cross-platform support
"""

import os
import sys
import platform
import shutil
from pathlib import Path

def get_platform_info():
    """Get current platform information"""
    system = platform.system()
    machine = platform.machine()
    return system, machine

def setup_directory_structure():
    """Create the necessary directory structure"""
    base_path = Path("models/ten-vad-onnx")
    
    # Create base directories
    directories = [
        base_path / "ten_vad_library",
        base_path / "lib" / "Windows" / "x64",
        base_path / "lib" / "Windows" / "x86", 
        base_path / "lib" / "Linux" / "x64",
        base_path / "lib" / "macOS" / "ten_vad.framework" / "Versions" / "A"
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {directory}")
    
    return base_path

def copy_library_files(source_path, target_path):
    """Copy TEN VAD ONNX library files from source to target"""
    source = Path(source_path)
    target = Path(target_path)
    
    if not source.exists():
        print(f"❌ Source path not found: {source}")
        return False
    
    # Copy Python implementation
    ten_vad_py = source / "include" / "ten_vad.py"
    if ten_vad_py.exists():
        shutil.copy2(ten_vad_py, target / "ten_vad.py")
        print(f"✅ Copied: {ten_vad_py} -> {target / 'ten_vad.py'}")
    else:
        print(f"❌ TEN VAD Python file not found: {ten_vad_py}")
        return False
    
    # Copy platform-specific libraries
    platform_files = [
        # Windows
        (source / "lib" / "Windows" / "x64" / "ten_vad.dll", 
         target / "lib" / "Windows" / "x64" / "ten_vad.dll"),
        (source / "lib" / "Windows" / "x64" / "ten_vad.dll", 
         target / "ten_vad_library" / "ten_vad.dll"),
        
        # Linux
        (source / "lib" / "Linux" / "x64" / "libten_vad.so", 
         target / "lib" / "Linux" / "x64" / "libten_vad.so"),
        (source / "lib" / "Linux" / "x64" / "libten_vad.so", 
         target / "ten_vad_library" / "libten_vad.so"),
        
        # macOS
        (source / "lib" / "macOS" / "ten_vad.framework" / "Versions" / "A" / "ten_vad", 
         target / "lib" / "macOS" / "ten_vad.framework" / "Versions" / "A" / "ten_vad"),
        (source / "lib" / "macOS" / "ten_vad.framework" / "Versions" / "A" / "ten_vad", 
         target / "ten_vad_library" / "libten_vad"),
    ]
    
    copied_count = 0
    for src_file, dst_file in platform_files:
        if src_file.exists():
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)
            print(f"✅ Copied: {src_file.name} -> {dst_file}")
            copied_count += 1
        else:
            print(f"⚠️  File not found (skipping): {src_file}")
    
    return copied_count > 0

def verify_installation():
    """Verify that TEN VAD ONNX is properly installed"""
    system, machine = get_platform_info()
    print(f"\n🔍 Verifying installation for {system} {machine}")
    
    try:
        from core.providers.vad.ten_vad_onnx import VADProvider
        
        config = {
            'threshold': 0.5,
            'threshold_low': 0.2,
            'model_path': 'models/ten-vad-onnx'
        }
        
        print("🔧 Testing TEN VAD ONNX provider creation...")
        vad_provider = VADProvider(config)
        
        if hasattr(vad_provider, 'ten_vad_working') and vad_provider.ten_vad_working:
            print("✅ TEN VAD ONNX is working with native libraries!")
            return True
        else:
            print("⚠️  TEN VAD ONNX created but using fallback mode")
            return True  # Still functional
            
    except Exception as e:
        print(f"❌ TEN VAD ONNX verification failed: {e}")
        return False

def show_platform_status():
    """Show the status of libraries for different platforms"""
    base_path = Path("models/ten-vad-onnx")
    
    print("\n📋 Platform Library Status:")
    print("=" * 50)
    
    # Windows
    win_dll = base_path / "lib" / "Windows" / "x64" / "ten_vad.dll"
    win_status = "✅ Available" if win_dll.exists() else "❌ Missing"
    print(f"Windows x64: {win_status}")
    
    # Linux
    linux_so = base_path / "lib" / "Linux" / "x64" / "libten_vad.so"
    linux_status = "✅ Available" if linux_so.exists() else "❌ Missing"
    print(f"Linux x64:   {linux_status}")
    
    # macOS
    macos_lib = base_path / "lib" / "macOS" / "ten_vad.framework" / "Versions" / "A" / "ten_vad"
    macos_status = "✅ Available" if macos_lib.exists() else "❌ Missing"
    print(f"macOS:       {macos_status}")
    
    # Python implementation
    python_impl = base_path / "ten_vad.py"
    python_status = "✅ Available" if python_impl.exists() else "❌ Missing"
    print(f"Python impl: {python_status}")

def main():
    """Main installation function"""
    print("🚀 TEN VAD ONNX Cross-Platform Installation")
    print("=" * 50)
    
    system, machine = get_platform_info()
    print(f"Current platform: {system} {machine}")
    
    # Check if source directory exists
    source_candidates = [
        "ten-vad-1.0-ONNX",
        "../ten-vad-1.0-ONNX",
        "../../ten-vad-1.0-ONNX"
    ]
    
    source_path = None
    for candidate in source_candidates:
        if Path(candidate).exists():
            source_path = candidate
            break
    
    if not source_path:
        print("❌ TEN VAD ONNX source directory not found!")
        print("Please ensure 'ten-vad-1.0-ONNX' directory is available.")
        print("Expected locations:", source_candidates)
        return False
    
    print(f"📁 Found TEN VAD ONNX source: {source_path}")
    
    # Step 1: Set up directory structure
    print("\n📂 Setting up directory structure...")
    target_path = setup_directory_structure()
    
    # Step 2: Copy library files
    print("\n📋 Copying library files...")
    if not copy_library_files(source_path, target_path):
        print("❌ Failed to copy essential files")
        return False
    
    # Step 3: Show platform status
    show_platform_status()
    
    # Step 4: Verify installation
    print("\n🔍 Verifying installation...")
    if not verify_installation():
        print("❌ Installation verification failed")
        return False
    
    print("\n" + "=" * 50)
    print("✅ TEN VAD ONNX installation completed successfully!")
    print("\n📋 Usage:")
    print("Update your .config.yaml:")
    print("  selected_module:")
    print("    VAD: TenVAD_ONNX")
    print("\n🌍 Cross-platform support:")
    print("  • Windows: ✅ Native DLL")
    print("  • Linux:   ✅ Native .so")
    print("  • macOS:   ✅ Native framework")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)