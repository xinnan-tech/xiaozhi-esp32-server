"""
OpenAI LLM Test (Streaming with TTFT Measurement)

This script tests OpenAI's chat completion API using streaming mode.
Focuses on measuring Time to First Token (TTFT) latency.

Usage:
    # Default prompt and model
    python3 -m core.providers.llm.test.test_openai
    
    # Custom prompt
    python3 -m core.providers.llm.test.test_openai "What is the capital of France?"
    
    # Custom model
    python3 -m core.providers.llm.test.test_openai --model gpt-4o
    
    # Custom prompt and model
    python3 -m core.providers.llm.test.test_openai "Tell me a joke" --model gpt-4-turbo

Environment:
    OPENAI_API_KEY - Your OpenAI API key (required)
    OPENAI_MODEL - Default model name (optional, default: gpt-4o-mini)

Examples:
    export OPENAI_API_KEY="sk-proj-your_key_here"
    python3 -m core.providers.llm.test.test_openai
    python3 -m core.providers.llm.test.test_openai "解释一下什么是人工智能"
    python3 -m core.providers.llm.test.test_openai --model gpt-3.5-turbo
"""

import sys
import os
import time

# Check if OpenAI SDK is installed
try:
    from openai import OpenAI
except ImportError:
    print("❌ Error: openai package not installed")
    print("   Install with: pip install openai")
    sys.exit(1)


def test_openai_llm_streaming(prompt: str, model: str = None):
    """
    Test OpenAI LLM with streaming mode and measure TTFT
    
    Args:
        prompt: User prompt text
        model: Model name (optional, uses env or default)
        
    Returns:
        Tuple of (response_text, ttft_ms, total_latency_ms, token_count)
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not set")
        print("   export OPENAI_API_KEY='sk-proj-your_key_here'")
        print("\n💡 Get your API key from: https://platform.openai.com/api-keys")
        sys.exit(1)
    
    if model is None:
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    
    print(f"🤖 OpenAI LLM Test (Streaming)")
    print(f"   API: https://api.openai.com/v1")
    print(f"   Model: {model}")
    print(f"   Prompt: {prompt[:50]}{'...' if len(prompt) > 50 else ''}\n")
    
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    
    try:
        print("⏳ Generating response...\n")
        print("=" * 60)
        
        start_time = time.time()
        ttft = None
        full_response = ""
        token_count = 0
        
        # Create streaming chat completion
        stream = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            stream=True,
            max_tokens=1024,
            temperature=0.7
        )
        
        # Process stream
        for chunk in stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                
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
        response, ttft, total_latency, token_count = test_openai_llm_streaming(prompt, model)
        
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

