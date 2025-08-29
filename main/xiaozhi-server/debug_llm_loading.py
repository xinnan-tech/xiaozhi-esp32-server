#!/usr/bin/env python3
"""
Debug script to check LLM provider loading
"""
import os
import sys

def debug_llm_loading():
    """Debug the LLM loading mechanism"""
    print("=== LLM Loading Debug ===")
    
    # Check current working directory
    cwd = os.getcwd()
    print(f"Current working directory: {cwd}")
    
    # Check the path that the code is looking for
    class_name = "openai"
    provider_path = os.path.join('core', 'providers', 'llm', class_name, f'{class_name}.py')
    absolute_provider_path = os.path.abspath(provider_path)
    
    print(f"Looking for provider at: {provider_path}")
    print(f"Absolute path: {absolute_provider_path}")
    print(f"Path exists: {os.path.exists(provider_path)}")
    
    # Check if the core directory exists
    core_path = os.path.join('core')
    print(f"Core directory exists: {os.path.exists(core_path)}")
    
    if os.path.exists(core_path):
        providers_path = os.path.join('core', 'providers')
        print(f"Providers directory exists: {os.path.exists(providers_path)}")
        
        if os.path.exists(providers_path):
            llm_path = os.path.join('core', 'providers', 'llm')
            print(f"LLM directory exists: {os.path.exists(llm_path)}")
            
            if os.path.exists(llm_path):
                openai_dir = os.path.join('core', 'providers', 'llm', 'openai')
                print(f"OpenAI directory exists: {os.path.exists(openai_dir)}")
                
                if os.path.exists(openai_dir):
                    openai_file = os.path.join('core', 'providers', 'llm', 'openai', 'openai.py')
                    print(f"OpenAI file exists: {os.path.exists(openai_file)}")
                else:
                    # List what's in the llm directory
                    try:
                        llm_contents = os.listdir(llm_path)
                        print(f"Contents of {llm_path}: {llm_contents}")
                    except Exception as e:
                        print(f"Error listing {llm_path}: {e}")
    
    # Check Python path
    print(f"Python path: {sys.path[:3]}...")  # Show first 3 entries
    
    # Try to see if we can import the module directly
    try:
        import core.providers.llm.openai.openai
        print("✅ Direct import of openai module successful")
    except ImportError as e:
        print(f"❌ Direct import failed: {e}")

if __name__ == "__main__":
    debug_llm_loading()