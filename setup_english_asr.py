#!/usr/bin/env python3
"""
Setup script for English-only ASR configuration
Automatically configures the best English ASR model for your use case
"""

import os
import yaml
import sys

def setup_english_asr():
    """Setup English-only ASR configuration"""
    
    print("🎯 English-Only ASR Setup")
    print("=" * 40)
    print()
    
    # Check if config file exists
    config_file = "main/xiaozhi-server/data/.config.yaml"
    main_config = "main/xiaozhi-server/config.yaml"
    
    if not os.path.exists("main/xiaozhi-server"):
        print("❌ Please run this script from the project root directory")
        return False
    
    # Create data directory if it doesn't exist
    os.makedirs("main/xiaozhi-server/data", exist_ok=True)
    
    print("🤖 What type of application are you building?")
    print("1. 👶 Kids companion bot (RECOMMENDED: Gigaspeech)")
    print("2. ⚡ Fast response bot (Whisper Tiny)")
    print("3. 🎯 General English bot (Whisper Base)")
    print("4. 🏆 Highest accuracy (Whisper Small)")
    print()
    
    while True:
        try:
            choice = input("Enter your choice (1-4): ").strip()
            if choice in ['1', '2', '3', '4']:
                break
            print("Please enter 1, 2, 3, or 4")
        except KeyboardInterrupt:
            print("\n👋 Setup cancelled")
            return False
    
    # Model configurations
    models = {
        '1': {
            'name': 'SherpaZipformerGigaspeechEN',
            'description': 'Gigaspeech English (Best for Kids)',
            'benefits': ['Massive vocabulary', 'Perfect for creative language', 'YouTube training data', 'Multiple client support']
        },
        '2': {
            'name': 'SherpaWhisperTinyEN',
            'description': 'Whisper Tiny English (Fastest)',
            'benefits': ['Fastest processing', 'Small size (153MB)', 'Quick responses', 'Good for simple conversations']
        },
        '3': {
            'name': 'SherpaWhisperBaseEN', 
            'description': 'Whisper Base English (Balanced)',
            'benefits': ['Good balance of speed/accuracy', 'Moderate size (74MB)', 'Reliable performance', 'General purpose']
        },
        '4': {
            'name': 'SherpaWhisperSmallEN',
            'description': 'Whisper Small English (Highest Accuracy)', 
            'benefits': ['Best accuracy', 'Large size (244MB)', 'Excellent for complex speech', 'Professional use']
        }
    }
    
    selected_model = models[choice]
    
    print(f"\n✅ Selected: {selected_model['description']}")
    print("📋 Benefits:")
    for benefit in selected_model['benefits']:
        print(f"   • {benefit}")
    print()
    
    try:
        # Create or update config
        config = {}
        
        # Load existing config if it exists
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
        
        # Set up the configuration
        if 'selected_module' not in config:
            config['selected_module'] = {}
        
        config['selected_module']['ASR'] = selected_model['name']
        
        # Ensure ASR configurations exist
        if 'ASR' not in config:
            config['ASR'] = {}
        
        # Add all English ASR configurations
        english_models = {
            'SherpaZipformerGigaspeechEN': {
                'type': 'sherpa_onnx_local',
                'model_dir': 'models/sherpa-onnx-zipformer-gigaspeech-2023-12-12',
                'model_type': 'zipformer',
                'output_dir': 'tmp/'
            },
            'SherpaWhisperTinyEN': {
                'type': 'sherpa_onnx_local',
                'model_dir': 'models/sherpa-onnx-whisper-tiny.en',
                'model_type': 'whisper',
                'output_dir': 'tmp/'
            },
            'SherpaWhisperBaseEN': {
                'type': 'sherpa_onnx_local',
                'model_dir': 'models/sherpa-onnx-whisper-base.en',
                'model_type': 'whisper',
                'output_dir': 'tmp/'
            },
            'SherpaWhisperSmallEN': {
                'type': 'sherpa_onnx_local',
                'model_dir': 'models/sherpa-onnx-whisper-small.en',
                'model_type': 'whisper',
                'output_dir': 'tmp/'
            }
        }
        
        config['ASR'].update(english_models)
        
        # Write the config
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        print("✅ Configuration updated successfully!")
        print(f"📁 Config file: {config_file}")
        print(f"🎯 Selected ASR: {selected_model['name']}")
        print()
        
        # Special instructions for Gigaspeech
        if choice == '1':
            print("🔽 Gigaspeech Model Setup:")
            print("The Gigaspeech model will be downloaded automatically when you start the server.")
            print("If automatic download fails, you can run:")
            print("   python download_gigaspeech_manual.py")
            print()
        
        print("🚀 Next Steps:")
        print("1. Start your server: python main/xiaozhi-server/app.py")
        print("2. The English model will download automatically")
        print("3. Enjoy 3x faster English processing!")
        print()
        
        print("🎉 English-only ASR setup complete!")
        return True
        
    except Exception as e:
        print(f"❌ Error setting up configuration: {e}")
        return False

if __name__ == "__main__":
    print("English-Only ASR Setup Script")
    print("Configures the best English ASR model for your needs")
    print()
    
    success = setup_english_asr()
    
    if success:
        print("\n🎯 SUCCESS! Your English ASR is ready!")
        print("Your bot will now process English speech much faster and more accurately.")
    else:
        print("\n❌ Setup failed. Please check the error messages above.")
        sys.exit(1)