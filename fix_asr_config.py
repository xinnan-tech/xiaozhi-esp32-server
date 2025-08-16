#!/usr/bin/env python3
"""
Fix ASR configuration to use working Whisper Tiny English model
"""

import os
import yaml

def fix_asr_config():
    """Fix the ASR configuration to use a working model"""
    
    config_file = "main/xiaozhi-server/data/.config.yaml"
    
    print("🔧 Fixing ASR Configuration")
    print("=" * 30)
    
    try:
        # Read current config
        if not os.path.exists(config_file):
            print(f"❌ Config file not found: {config_file}")
            return False
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Check current selection
        current_asr = config.get("selected_module", {}).get("ASR", "Unknown")
        print(f"📋 Current ASR: {current_asr}")
        
        # Force to use Whisper Tiny (which we know works)
        if "selected_module" not in config:
            config["selected_module"] = {}
        
        config["selected_module"]["ASR"] = "SherpaWhisperTinyEN"
        
        # Ensure the Whisper Tiny config exists
        if "ASR" not in config:
            config["ASR"] = {}
        
        config["ASR"]["SherpaWhisperTinyEN"] = {
            "type": "sherpa_onnx_local",
            "model_dir": "models/sherpa-onnx-whisper-tiny.en",
            "model_type": "whisper",
            "output_dir": "tmp/"
        }
        
        # Write back the config
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        print("✅ Configuration updated!")
        print("📋 New ASR: SherpaWhisperTinyEN")
        print("🎯 Model: Whisper Tiny English (fast, reliable)")
        
        # Check if model files exist
        model_dir = "models/sherpa-onnx-whisper-tiny.en"
        if os.path.exists(model_dir):
            files = [f for f in os.listdir(model_dir) if f.endswith('.onnx') or f.endswith('.txt')]
            print(f"📁 Model files found: {len(files)}")
            for f in files:
                print(f"   ✓ {f}")
        else:
            print("📥 Model files will be downloaded automatically when server starts")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing config: {e}")
        return False

if __name__ == "__main__":
    print("ASR Configuration Fixer")
    print("This will set your ASR to use Whisper Tiny English")
    print()
    
    success = fix_asr_config()
    
    if success:
        print("\n🎉 SUCCESS! Your ASR is now configured correctly!")
        print("🚀 You can now start your server:")
        print("   python app.py")
        print("\n✅ Benefits of Whisper Tiny English:")
        print("   - Fast processing")
        print("   - English-only (no multilingual overhead)")
        print("   - Perfect for multiple kids")
        print("   - Reliable downloads from Hugging Face")
    else:
        print("\n❌ Failed to fix configuration.")
        print("Please check the file permissions and try again.")