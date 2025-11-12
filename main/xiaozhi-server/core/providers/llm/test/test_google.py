"""
Google Gemini LLM Test (Streaming with TTFT Measurement)

This script tests Google's Gemini API using streaming mode.
Focuses on measuring Time to First Token (TTFT) latency.

Usage:
    # Default prompt and model
    python3 -m core.providers.llm.test.test_google
    
    # Custom prompt
    python3 -m core.providers.llm.test.test_google "What is the capital of France?"
    
    # Custom model
    python3 -m core.providers.llm.test.test_google --model gemini-1.5-pro
    
    # Custom prompt and model
    python3 -m core.providers.llm.test.test_google "Tell me a joke" --model gemini-1.5-flash

Environment:
    GOOGLE_API_KEY - Your Google AI API key (required)
    GOOGLE_MODEL - Default model name (optional, default: gemini-2.0-flash-exp)

Examples:
    export GOOGLE_API_KEY="your_api_key_here"
    python3 -m core.providers.llm.test.test_google
    python3 -m core.providers.llm.test.test_google "解释一下什么是人工智能"
    python3 -m core.providers.llm.test.test_google --model gemini-1.0-pro
"""

import sys
import os
import time

# Check if Google Generative AI SDK is installed
try:
    import google.generativeai as genai
except ImportError:
    print("❌ Error: google-generativeai package not installed")
    print("   Install with: pip install google-generativeai")
    sys.exit(1)


def test_google_llm_streaming(prompt: str, model_name: str = None):
    """
    Test Google Gemini LLM with streaming mode and measure TTFT
    
    Args:
        prompt: User prompt text
        model_name: Model name (optional, uses env or default)
        
    Returns:
        Tuple of (response_text, ttft_ms, total_latency_ms, token_count)
    """
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("❌ Error: GOOGLE_API_KEY not set")
        print("   export GOOGLE_API_KEY='your_api_key_here'")
        print("\n💡 Get your API key from: https://aistudio.google.com/apikey")
        sys.exit(1)
    
    if model_name is None:
        model_name = os.environ.get("GOOGLE_MODEL", "gemini-2.0-flash-exp")
    
    print(f"🤖 Google Gemini LLM Test (Streaming)")
    print(f"   API: Google AI Studio")
    print(f"   Model: {model_name}")
    print(f"   Prompt: {prompt[:50]}{'...' if len(prompt) > 50 else ''}\n")
    
    # Configure Google AI
    genai.configure(api_key=api_key)
    
    try:
        print("⏳ Generating response...\n")
        print("=" * 60)
        
        # Initialize model
        model = genai.GenerativeModel(model_name)
        
        start_time = time.time()
        ttft = None
        full_response = ""
        token_count = 0
        
        # Generate content with streaming
        response = model.generate_content(
            prompt,
            stream=True,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=1024,
                temperature=0.7,
            )
        )
        
        # Process stream
        for chunk in response:
            if chunk.text:
                content = chunk.text
                
                # Record time to first token
                if ttft is None:
                    ttft = (time.time() - start_time) * 1000
                
                full_response += content
                token_count += 1
                print(content, end="", flush=True)
        
        end_time = time.time()
        total_latency = (end_time - start_time) * 1000
        
        print("\n" + "=" * 60)
        
        return full_response, ttft, total_latency, token_count
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    # Parse command line arguments
    prompt = "Hello! Please introduce yourself briefly in 2-3 sentences."
    model = None
    
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--model" and i + 1 < len(args):
            model = args[i + 1]
            i += 2
        elif not args[i].startswith("--"):
            prompt = args[i]
            i += 1
        else:
            i += 1
    
    try:
        # Run streaming test
        response, ttft, total_latency, token_count = test_google_llm_streaming(prompt, model)
        
        # Print metrics
        print(f"\n📊 Performance Metrics:")
        print(f"   ⚡ TTFT (Time to First Token): {ttft:.0f} ms")
        print(f"   ⏱️  Total Latency: {total_latency:.0f} ms ({total_latency/1000:.2f}s)")
        print(f"   📝 Response Length: {len(response)} characters")
        print(f"   🔢 Token Chunks: {token_count}")
        
        if token_count > 0 and total_latency > ttft:
            avg_token_time = (total_latency - ttft) / token_count
            print(f"   🚀 Avg Time per Token: {avg_token_time:.1f} ms")
        
        print("\n✅ Test completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

