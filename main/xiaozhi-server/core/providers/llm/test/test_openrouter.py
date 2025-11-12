"""
OpenRouter LLM Test (Streaming with TTFT Measurement)

This script tests OpenRouter's chat completion API using streaming mode.
Focuses on measuring Time to First Token (TTFT) latency.

Usage:
    # Default prompt and model
    python3 -m core.providers.llm.test.test_openrouter
    
    # Custom prompt
    python3 -m core.providers.llm.test.test_openrouter "What is the capital of France?"
    
    # Custom model
    python3 -m core.providers.llm.test.test_openrouter --model openai/gpt-4o-mini
    
    # Custom prompt and model
    python3 -m core.providers.llm.test.test_openrouter "Tell me a joke" --model anthropic/claude-3.5-sonnet

Environment:
    OPENROUTER_API_KEY - Your OpenRouter API key (required)
    OPENROUTER_MODEL - Default model name (optional, default: openai/gpt-4o)

Examples:
    export OPENROUTER_API_KEY="sk-or-v1-your_key_here"
    python3 -m core.providers.llm.test.test_openrouter
    python3 -m core.providers.llm.test.test_openrouter "解释一下什么是人工智能"
    python3 -m core.providers.llm.test.test_openrouter --model google/gemini-pro-1.5
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


def test_openrouter_llm_streaming(prompt: str, model: str = None):
    """
    Test OpenRouter LLM with streaming mode and measure TTFT
    
    Args:
        prompt: User prompt text
        model: Model name (optional, uses env or default)
        
    Returns:
        Tuple of (response_text, ttft_ms, total_latency_ms, token_count)
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ Error: OPENROUTER_API_KEY not set")
        print("   export OPENROUTER_API_KEY='sk-or-v1-your_key_here'")
        print("\n💡 Get your API key from: https://openrouter.ai/keys")
        sys.exit(1)
    
    if model is None:
        model = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o")
    
    print(f"🤖 OpenRouter LLM Test (Streaming)")
    print(f"   API: https://openrouter.ai/api/v1")
    print(f"   Model: {model}")
    print(f"   Prompt: {prompt[:50]}{'...' if len(prompt) > 50 else ''}\n")
    
    # Initialize OpenAI client with OpenRouter endpoint
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1"
    )
    
    try:
        print("⏳ Generating response...\n")
        print("=" * 60)
        
        start_time = time.time()
        ttft = None
        full_response = ""
        token_count = 0
        
        # Create streaming chat completion
        # OpenRouter supports additional headers for better tracking
        stream = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            stream=True,
            max_tokens=1024,
            temperature=0.7,
            extra_headers={
                "HTTP-Referer": "https://github.com/ai-bot-pro/live-agent",
                "X-Title": "Live Agent Test"
            }
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
        response, ttft, total_latency, token_count = test_openrouter_llm_streaming(prompt, model)
        
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

