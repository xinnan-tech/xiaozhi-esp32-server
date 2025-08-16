#!/usr/bin/env python3
"""
Check which ASR model is currently selected in the config
"""

import sys
import os
sys.path.append('main/xiaozhi-server')

from config.settings import load_config

def check_current_config():
    """Check the current ASR configuration"""
    try:
        print("🔍 Checking current configuration...")
        
        # Load the config
        config = load_config()
        
        # Check selected ASR module
        selected_asr = config.get("selected_module", {}).get("ASR", "Not found")
        print(f"📋 Selected ASR module: {selected_asr}")
        
        # Check if the ASR config exists
        asr_configs = config.get("ASR", {})
        
        if selected_asr in asr_configs:
            asr_config = asr_configs[selected_asr]
            print(f"✅ ASR configuration found:")
            print(f"   Type: {asr_config.get('type', 'Not specified')}")
            print(f"   Model Dir: {asr_config.get('model_dir', 'Not specified')}")
            print(f"   Model Type: {asr_config.get('model_type', 'Not specified')}")
            print(f"   Output Dir: {asr_config.get('output_dir', 'Not specified')}")
            
            # Check if model files exist
            model_dir = asr_config.get('model_dir', '')
            if model_dir:
                print(f"\n📁 Checking model directory: {model_dir}")
                if os.path.exists(model_dir):
                    files = os.listdir(model_dir)
                    print(f"   Files found: {len(files)}")
                    for f in files[:5]:  # Show first 5 files
                        print(f"   - {f}")
                    if len(files) > 5:
                        print(f"   ... and {len(files) - 5} more files")
                else:
                    print("   ❌ Model directory does not exist")
        else:
            print(f"❌ ASR configuration '{selected_asr}' not found!")
            print(f"Available ASR configurations:")
            for name in asr_configs.keys():
                print(f"   - {name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking config: {e}")
        return False

if __name__ == "__main__":
    print("Configuration Checker")
    print("=" * 30)
    
    success = check_current_config()
    
    if success:
        print("\n✅ Configuration check completed!")
    else:
        print("\n❌ Configuration check failed!")
        print("Make sure you're running this from the correct directory.")