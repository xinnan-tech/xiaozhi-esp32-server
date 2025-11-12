"""
LLM Model Benchmark Script

This script tests multiple LLM models from different providers with the same prompt
and generates a markdown report comparing their performance metrics.

Usage:
    python3 -m core.providers.llm.test.benchmark

Environment:
    GROQ_API_KEY - Your Groq API key (required for Groq models)
    OPENROUTER_API_KEY - Your OpenRouter API key (required for OpenRouter models)
    OPENAI_API_KEY - Your OpenAI API key (required for OpenAI models)

Output:
    benchmark_report.md - Performance comparison report
"""

import sys
import os
import time
from datetime import datetime

# Check if OpenAI SDK is installed
try:
    from openai import OpenAI
except ImportError:
    print("❌ Error: openai package not installed")
    print("   Install with: pip install openai")
    sys.exit(1)


# Test configuration
TEST_PROMPT = "What is artificial intelligence? Please explain in 2-3 sentences."

GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-120b",
    "groq/compound",
    "openai/gpt-oss-20b"
]

OPENROUTER_MODELS = [
    "openai/gpt-4o",
    "anthropic/claude-sonnet-4.5",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b"
]

OPENAI_MODELS = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
]


def test_model(provider: str, model: str, prompt: str, api_key: str, base_url: str):
    """
    Test a single model and return performance metrics
    
    Args:
        provider: Provider name (e.g., "Groq", "OpenRouter")
        model: Model name
        prompt: Test prompt
        api_key: API key
        base_url: API base URL
        
    Returns:
        dict with metrics or None if failed
    """
    try:
        print(f"   Testing {provider}/{model}... ", end="", flush=True)
        
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        start_time = time.time()
        ttft = None
        full_response = ""
        token_count = 0
        
        # Create streaming chat completion
        stream = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            max_tokens=1024,
            temperature=0.7
        )
        
        # Process stream
        for chunk in stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                
                if ttft is None:
                    ttft = (time.time() - start_time) * 1000
                
                full_response += content
                token_count += 1
        
        end_time = time.time()
        total_latency = (end_time - start_time) * 1000
        
        print(f"✅ TTFT: {ttft:.0f}ms")
        
        return {
            "provider": provider,
            "model": model,
            "ttft": ttft,
            "total_latency": total_latency,
            "response_length": len(full_response),
            "token_count": token_count,
            "response": full_response[:100] + "..." if len(full_response) > 100 else full_response,
            "success": True
        }
        
    except Exception as e:
        print(f"❌ Failed: {str(e)[:50]}")
        return {
            "provider": provider,
            "model": model,
            "error": str(e),
            "success": False
        }


def generate_markdown_report(results: list, prompt: str):
    """
    Generate a markdown report from test results
    
    Args:
        results: List of test results
        prompt: The test prompt used
        
    Returns:
        str: Markdown formatted report
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    md = f"""# LLM Model Benchmark Report

**Generated:** {timestamp}

## Test Configuration

**Test Prompt:**
```
{prompt}
```

**Tested Models:**
- Groq: {len([r for r in results if r['provider'] == 'Groq'])} models
- OpenRouter: {len([r for r in results if r['provider'] == 'OpenRouter'])} models
- OpenAI: {len([r for r in results if r['provider'] == 'OpenAI'])} models

---

## Performance Metrics Summary

### Time to First Token (TTFT) Comparison

Lower is better. This metric indicates how quickly the model starts responding.

| Rank | Provider | Model | TTFT (ms) | Status |
|------|----------|-------|-----------|--------|
"""
    
    # Sort by TTFT
    successful_results = [r for r in results if r['success']]
    sorted_by_ttft = sorted(successful_results, key=lambda x: x['ttft'])
    
    for i, result in enumerate(sorted_by_ttft, 1):
        ttft = f"{result['ttft']:.0f}" if result['ttft'] else "N/A"
        status = "✅" if result['success'] else "❌"
        md += f"| {i} | {result['provider']} | `{result['model']}` | **{ttft}** | {status} |\n"
    
    # Failed models
    failed_results = [r for r in results if not r['success']]
    if failed_results:
        md += "\n### Failed Models\n\n"
        md += "| Provider | Model | Error |\n"
        md += "|----------|-------|-------|\n"
        for result in failed_results:
            error = result.get('error', 'Unknown error')[:50]
            md += f"| {result['provider']} | `{result['model']}` | {error} |\n"
    
    md += "\n---\n\n"
    
    # Detailed metrics
    md += "## Detailed Performance Metrics\n\n"
    
    for provider in ["Groq", "OpenRouter", "OpenAI"]:
        provider_results = [r for r in successful_results if r['provider'] == provider]
        if not provider_results:
            continue
            
        md += f"### {provider} Models\n\n"
        md += "| Model | TTFT (ms) | Total Latency (ms) | Response Length | Token Chunks | Avg Token Time (ms) |\n"
        md += "|-------|-----------|-------------------|-----------------|--------------|--------------------|\n"
        
        for result in sorted(provider_results, key=lambda x: x['ttft']):
            ttft = f"{result['ttft']:.0f}"
            total = f"{result['total_latency']:.0f}"
            length = result['response_length']
            tokens = result['token_count']
            avg_token = f"{(result['total_latency'] - result['ttft']) / tokens:.1f}" if tokens > 0 else "N/A"
            
            md += f"| `{result['model']}` | {ttft} | {total} | {length} | {tokens} | {avg_token} |\n"
        
        md += "\n"
    
    # Response samples
    md += "## Response Samples\n\n"
    for result in successful_results:
        md += f"### {result['provider']} - {result['model']}\n\n"
        md += f"**TTFT:** {result['ttft']:.0f}ms\n\n"
        md += f"**Response Preview:**\n```\n{result['response']}\n```\n\n"
    
    # Performance analysis
    md += "---\n\n## Performance Analysis\n\n"
    
    if successful_results:
        fastest = min(successful_results, key=lambda x: x['ttft'])
        slowest = max(successful_results, key=lambda x: x['ttft'])
        avg_ttft = sum(r['ttft'] for r in successful_results) / len(successful_results)
        
        md += f"**Fastest Model:** `{fastest['model']}` ({fastest['provider']}) - {fastest['ttft']:.0f}ms TTFT\n\n"
        md += f"**Slowest Model:** `{slowest['model']}` ({slowest['provider']}) - {slowest['ttft']:.0f}ms TTFT\n\n"
        md += f"**Average TTFT:** {avg_ttft:.0f}ms\n\n"
        
        # Provider comparison
        groq_results = [r for r in successful_results if r['provider'] == 'Groq']
        openrouter_results = [r for r in successful_results if r['provider'] == 'OpenRouter']
        openai_results = [r for r in successful_results if r['provider'] == 'OpenAI']
        
        if groq_results or openrouter_results or openai_results:
            md += "### Provider Comparison\n\n"
            
            if groq_results:
                groq_avg = sum(r['ttft'] for r in groq_results) / len(groq_results)
                md += f"- **Groq Average TTFT:** {groq_avg:.0f}ms\n"
            
            if openrouter_results:
                openrouter_avg = sum(r['ttft'] for r in openrouter_results) / len(openrouter_results)
                md += f"- **OpenRouter Average TTFT:** {openrouter_avg:.0f}ms\n"
            
            if openai_results:
                openai_avg = sum(r['ttft'] for r in openai_results) / len(openai_results)
                md += f"- **OpenAI Average TTFT:** {openai_avg:.0f}ms\n"
            
            md += "\n"
    
    md += "---\n\n"
    md += "*Report generated by LLM Benchmark Script*\n"
    
    return md


def main():
    """Main benchmark execution"""
    print("=" * 60)
    print("LLM Model Benchmark")
    print("=" * 60)
    print(f"\nTest Prompt: {TEST_PROMPT}\n")
    
    # Check API keys
    groq_api_key = os.environ.get("GROQ_API_KEY")
    openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    
    if not groq_api_key:
        print("⚠️  Warning: GROQ_API_KEY not set, skipping Groq models")
    if not openrouter_api_key:
        print("⚠️  Warning: OPENROUTER_API_KEY not set, skipping OpenRouter models")
    if not openai_api_key:
        print("⚠️  Warning: OPENAI_API_KEY not set, skipping OpenAI models")
    
    if not groq_api_key and not openrouter_api_key and not openai_api_key:
        print("\n❌ Error: No API keys configured")
        print("   export GROQ_API_KEY='your_key'")
        print("   export OPENROUTER_API_KEY='your_key'")
        print("   export OPENAI_API_KEY='your_key'")
        sys.exit(1)
    
    print()
    results = []
    
    # Test Groq models
    if groq_api_key:
        print("📊 Testing Groq Models:")
        for model in GROQ_MODELS:
            result = test_model(
                provider="Groq",
                model=model,
                prompt=TEST_PROMPT,
                api_key=groq_api_key,
                base_url="https://api.groq.com/openai/v1"
            )
            results.append(result)
            time.sleep(1)  # Rate limiting
        print()
    
    # Test OpenRouter models
    if openrouter_api_key:
        print("📊 Testing OpenRouter Models:")
        for model in OPENROUTER_MODELS:
            result = test_model(
                provider="OpenRouter",
                model=model,
                prompt=TEST_PROMPT,
                api_key=openrouter_api_key,
                base_url="https://openrouter.ai/api/v1"
            )
            results.append(result)
            time.sleep(1)  # Rate limiting
        print()
    
    # Test OpenAI models
    if openai_api_key:
        print("📊 Testing OpenAI Models:")
        for model in OPENAI_MODELS:
            result = test_model(
                provider="OpenAI",
                model=model,
                prompt=TEST_PROMPT,
                api_key=openai_api_key,
                base_url="https://api.openai.com/v1"
            )
            results.append(result)
            time.sleep(1)  # Rate limiting
        print()
    
    # Generate report
    print("=" * 60)
    print("Generating Report...")
    print("=" * 60)
    
    markdown_report = generate_markdown_report(results, TEST_PROMPT)
    
    # Save to file
    output_file = os.path.join(
        os.path.dirname(__file__),
        "benchmark_report.md"
    )
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown_report)
    
    print(f"\n✅ Report saved to: {output_file}")
    
    # Print summary
    successful = len([r for r in results if r['success']])
    failed = len([r for r in results if not r['success']])
    
    print(f"\n📊 Summary:")
    print(f"   Total Models Tested: {len(results)}")
    print(f"   Successful: {successful}")
    print(f"   Failed: {failed}")
    
    if successful > 0:
        fastest = min([r for r in results if r['success']], key=lambda x: x['ttft'])
        print(f"\n🏆 Fastest Model: {fastest['model']} ({fastest['provider']})")
        print(f"   TTFT: {fastest['ttft']:.0f}ms")
    
    print(f"\n✅ Benchmark completed!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Benchmark interrupted")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

