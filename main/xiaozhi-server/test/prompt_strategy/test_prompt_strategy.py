"""
System Prompt Strategy Testing Tool

This script tests different system prompt organization strategies to evaluate:
- Compliance: How well the model follows different modules (role, tone, guardrails, etc.)
- Boundary: How each module influences the agent's responses and behavior

Usage:
    # Test with unified strategy and scenario file
    python3 test/prompt_strategy/test_prompt_strategy.py --strategy unified --scenario scenario_01_normal
    
    # Test with separated strategy (if you create one)
    python3 test/prompt_strategy/test_prompt_strategy.py --strategy separated --scenario scenario_02_tone
    
    # Interactive mode (manual input)
    python3 test/prompt_strategy/test_prompt_strategy.py --strategy unified --interactive
    
    # Custom model
    python3 test/prompt_strategy/test_prompt_strategy.py --strategy unified --scenario scenario_01_normal --model gpt-4o
    
    # With TTS playback
    python3 test/prompt_strategy/test_prompt_strategy.py --strategy unified --scenario scenario_01_normal --tts

Environment:
    OPENAI_API_KEY - Your OpenAI API key (required)
    OPENAI_MODEL - Default model name (optional, default: gpt-4o-mini)
    FISH_API_KEY - Your Fish.Audio API key (optional, for TTS playback)
    FISH_REFERENCE_ID - Voice reference ID (optional, default: Donald Trump voice)

Examples:
    export OPENAI_API_KEY="sk-proj-your_key_here"
    python3 test/prompt_strategy/test_prompt_strategy.py --strategy unified --scenario scenario_01_normal
    python3 test/prompt_strategy/test_prompt_strategy.py --strategy unified --interactive
    
    # With TTS playback
    export FISH_API_KEY="your-fish-key"
    python3 test/prompt_strategy/test_prompt_strategy.py --strategy unified --scenario scenario_01_normal --tts
"""

import sys
import os
import time
import json
import wave
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from io import BytesIO

# Check if OpenAI SDK is installed
try:
    from openai import OpenAI
except ImportError:
    print("❌ Error: openai package not installed")
    print("   Install with: pip install openai")
    sys.exit(1)

# Check if Fish Audio SDK is installed (optional for TTS)
TTS_AVAILABLE = False
try:
    from fish_audio_sdk import Session, TTSRequest
    import asyncio
    TTS_AVAILABLE = True
except ImportError:
    pass  # TTS is optional


# Get base directory for test resources
TEST_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = TEST_DIR / "prompts"
SCENARIOS_DIR = TEST_DIR / "scenarios"
OUTPUTS_DIR = TEST_DIR / "outputs"


def load_prompt_strategy(strategy_name: str) -> str:
    """
    Load system prompt from strategy file
    
    Args:
        strategy_name: Name of the strategy (e.g., 'unified', 'separated')
        
    Returns:
        System prompt text
    """
    prompt_file = PROMPTS_DIR / f"{strategy_name}.txt"
    
    if not prompt_file.exists():
        print(f"❌ Error: Strategy file not found: {prompt_file}")
        print(f"   Available strategies in {PROMPTS_DIR}:")
        for p in PROMPTS_DIR.glob("*.txt"):
            print(f"   - {p.stem}")
        sys.exit(1)
    
    print(f"📄 Loading prompt strategy: {strategy_name}")
    with open(prompt_file, "r", encoding="utf-8") as f:
        prompt = f.read()
    
    print(f"   ✓ Loaded ({len(prompt)} characters)")
    return prompt


def load_scenario(scenario_name: str) -> List[str]:
    """
    Load conversation scenario from file
    
    Args:
        scenario_name: Name of the scenario file (without extension)
        
    Returns:
        List of user messages for multi-turn conversation
    """
    scenario_file = SCENARIOS_DIR / f"{scenario_name}.txt"
    
    if not scenario_file.exists():
        print(f"❌ Error: Scenario file not found: {scenario_file}")
        print(f"   Available scenarios in {SCENARIOS_DIR}:")
        for p in SCENARIOS_DIR.glob("*.txt"):
            print(f"   - {p.stem}")
        sys.exit(1)
    
    print(f"📝 Loading scenario: {scenario_name}")
    with open(scenario_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip() and not line.strip().startswith("#")]
    
    print(f"   ✓ Loaded {len(lines)} turns")
    return lines


def generate_and_play_tts(text: str, fish_session: Optional[Session] = None, reference_id: Optional[str] = None) -> bool:
    """
    Generate and play TTS audio using Fish Audio
    
    Args:
        text: Text to synthesize
        fish_session: Fish Audio session (optional)
        reference_id: Voice reference ID (optional)
        
    Returns:
        True if successful, False otherwise
    """
    if not TTS_AVAILABLE:
        print("   ⚠️  Fish Audio SDK not installed (TTS skipped)")
        return False
    
    if not fish_session:
        return False
    
    try:
        # Prepare TTS request
        tts_request = TTSRequest(
            text=text,
            # reference_id=reference_id or "5196af35f6ff4a0dbf541793fc9f2157",  # Default: Donald Trump voice
            reference_id="aebaa2305aa2452fbdc8f41eec852a79",
            format="pcm",
            normalize=True,
            sample_rate=16000,
        )
        
        # Generate audio
        audio_stream = fish_session.tts(tts_request, backend="s1")
        audio_bytes = b''.join(chunk for chunk in audio_stream if chunk)
        
        # Convert to WAV format
        wav_buffer = BytesIO()
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(1)       # Mono
            wf.setsampwidth(2)       # 16-bit
            wf.setframerate(16000)   # 16kHz
            wf.writeframes(audio_bytes)
        
        # Save and play
        output_dir = TEST_DIR / "tmp"
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / "tts_playback.wav"
        
        with open(output_file, 'wb') as f:
            f.write(wav_buffer.getvalue())
        
        # Play audio (macOS)
        os.system(f"afplay '{output_file}' 2>/dev/null")
        
        return True
        
    except Exception as e:
        print(f"   ⚠️  TTS error: {e}")
        return False


def run_conversation_test(
    system_prompt: str,
    user_messages: List[str],
    model: str = None,
    interactive: bool = False,
    enable_tts: bool = False
) -> Tuple[List[Dict], Dict]:
    """
    Run a multi-turn conversation test
    
    Args:
        system_prompt: System prompt to use
        user_messages: List of user messages (ignored if interactive=True)
        model: Model name (optional)
        interactive: If True, use interactive mode
        enable_tts: If True, play TTS audio after each response
        
    Returns:
        Tuple of (conversation_history, metrics)
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("❌ Error: GROQ_API_KEY not set")
        print("   export GROQ_API_KEY='sk-proj-your_key_here'")
        print("\n💡 Get your API key from: https://console.groq.com/keys")
        sys.exit(1)
    
    if model is None:
        model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
    
    # Initialize Fish Audio session if TTS is enabled
    fish_session = None
    fish_reference_id = None
    if enable_tts:
        if not TTS_AVAILABLE:
            print("⚠️  Warning: Fish Audio SDK not installed, TTS will be disabled")
            print("   Install with: pip install fish-audio-sdk")
            enable_tts = False
        else:
            fish_api_key = os.environ.get("FISH_API_KEY")
            if not fish_api_key:
                print("⚠️  Warning: FISH_API_KEY not set, TTS will be disabled")
                print("   export FISH_API_KEY='your-key'")
                enable_tts = False
            else:
                fish_session = Session(fish_api_key)
                fish_reference_id = os.environ.get("FISH_REFERENCE_ID")
                if fish_reference_id:
                    print(f"🔊 TTS enabled with voice ID: {fish_reference_id}")
                else:
                    print(f"🔊 TTS enabled with default voice")
    
    print(f"\n🤖 Running Conversation Test")
    print(f"   Model: {model}")
    print(f"   Mode: {'Interactive' if interactive else 'Scripted'}")
    print(f"   TTS: {'Enabled' if enable_tts else 'Disabled'}")
    print(f"   Turns: {len(user_messages) if not interactive else 'Manual input'}\n")
    
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
    
    # Initialize conversation with system prompt
    messages = [{"role": "system", "content": system_prompt}]
    conversation_history = []
    metrics = {
        "turns": 0,
        "total_latency_ms": 0,
        "total_tokens": 0,
        "ttfts": []
    }
    
    try:
        if interactive:
            print("=" * 60)
            print("Interactive mode - Type your messages (Ctrl+C or 'quit' to exit)")
            print("=" * 60 + "\n")
            
            turn_num = 0
            while True:
                user_input = input(f"\n[Turn {turn_num + 1}] You: ").strip()
                
                if not user_input or user_input.lower() in ['quit', 'exit', 'q']:
                    break
                
                turn_num += 1
                turn_result = _process_turn(client, messages, user_input, model, turn_num, fish_session, fish_reference_id)
                conversation_history.append(turn_result)
                
                # Update metrics
                metrics["turns"] = turn_num
                metrics["total_latency_ms"] += turn_result["latency_ms"]
                metrics["total_tokens"] += turn_result["token_count"]
                metrics["ttfts"].append(turn_result["ttft_ms"])
        else:
            print("=" * 60)
            print("Starting scripted conversation")
            print("=" * 60 + "\n")
            
            for turn_num, user_msg in enumerate(user_messages, start=1):
                print(f"\n[Turn {turn_num}] User: {user_msg}")
                
                turn_result = _process_turn(client, messages, user_msg, model, turn_num, fish_session, fish_reference_id)
                conversation_history.append(turn_result)
                
                # Update metrics
                metrics["turns"] = turn_num
                metrics["total_latency_ms"] += turn_result["latency_ms"]
                metrics["total_tokens"] += turn_result["token_count"]
                metrics["ttfts"].append(turn_result["ttft_ms"])
                
                # Small pause between turns for readability
                time.sleep(0.5)
        
        print("\n" + "=" * 60)
        return conversation_history, metrics
        
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted")
        return conversation_history, metrics


def _process_turn(
    client: OpenAI,
    messages: List[Dict],
    user_msg: str,
    model: str,
    turn_num: int,
    fish_session: Optional[Session] = None,
    fish_reference_id: Optional[str] = None
) -> Dict:
    """
    Process a single conversation turn
    
    Args:
        client: OpenAI client
        messages: Conversation history (will be mutated)
        user_msg: User message
        model: Model name
        turn_num: Current turn number
        fish_session: Fish Audio session for TTS (optional)
        fish_reference_id: Voice reference ID for TTS (optional)
        
    Returns:
        Dictionary with turn results
    """
    # Add user message
    messages.append({"role": "user", "content": user_msg})
    
    # Generate response
    start_time = time.time()
    ttft = None
    full_response = ""
    token_count = 0
    
    print(f"[Turn {turn_num}] Assistant: ", end="", flush=True)
    
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        max_tokens=1024,
        temperature=0.7
    )
    
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
    
    print()  # New line after response
    
    # Play TTS if enabled
    if fish_session:
        print("   🔊 Playing TTS audio...", end="", flush=True)
        tts_success = generate_and_play_tts(full_response, fish_session, fish_reference_id)
        if tts_success:
            print(" ✓")
        else:
            print()
    
    # Add assistant response to conversation
    messages.append({"role": "assistant", "content": full_response})
    
    return {
        "turn": turn_num,
        "user": user_msg,
        "assistant": full_response,
        "ttft_ms": ttft,
        "latency_ms": total_latency,
        "token_count": token_count
    }


def save_results(
    strategy_name: str,
    scenario_name: str,
    system_prompt: str,
    conversation: List[Dict],
    metrics: Dict,
    model: str
):
    """
    Save test results to JSON file
    
    Args:
        strategy_name: Name of the prompt strategy
        scenario_name: Name of the scenario
        system_prompt: System prompt used
        conversation: Conversation history
        metrics: Performance metrics
        model: Model name used
    """
    # Create output directory if it doesn't exist
    OUTPUTS_DIR.mkdir(exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{strategy_name}_{scenario_name}_{timestamp}.json"
    output_file = OUTPUTS_DIR / filename
    
    # Prepare output data
    output_data = {
        "metadata": {
            "strategy": strategy_name,
            "scenario": scenario_name,
            "model": model,
            "timestamp": datetime.now().isoformat()
        },
        "system_prompt": system_prompt,
        "conversation": conversation,
        "metrics": {
            "total_turns": metrics["turns"],
            "total_latency_ms": metrics["total_latency_ms"],
            "avg_latency_ms": metrics["total_latency_ms"] / metrics["turns"] if metrics["turns"] > 0 else 0,
            "total_tokens": metrics["total_tokens"],
            "avg_ttft_ms": sum(metrics["ttfts"]) / len(metrics["ttfts"]) if metrics["ttfts"] else 0
        }
    }
    
    # Save to file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")


def print_metrics(metrics: Dict):
    """Print performance metrics summary"""
    if metrics["turns"] == 0:
        return
    
    print(f"\n📊 Performance Metrics:")
    print(f"   🔢 Total Turns: {metrics['turns']}")
    print(f"   ⏱️  Total Latency: {metrics['total_latency_ms']:.0f} ms ({metrics['total_latency_ms']/1000:.2f}s)")
    print(f"   📊 Avg Latency per Turn: {metrics['total_latency_ms']/metrics['turns']:.0f} ms")
    print(f"   🔢 Total Token Chunks: {metrics['total_tokens']}")
    
    if metrics["ttfts"]:
        avg_ttft = sum(metrics["ttfts"]) / len(metrics["ttfts"])
        print(f"   ⚡ Avg TTFT: {avg_ttft:.0f} ms")


def main():
    """Main entry point"""
    # Parse command line arguments
    strategy = None
    scenario = None
    model = None
    interactive = False
    enable_tts = False
    
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--strategy" and i + 1 < len(args):
            strategy = args[i + 1]
            i += 2
        elif args[i] == "--scenario" and i + 1 < len(args):
            scenario = args[i + 1]
            i += 2
        elif args[i] == "--model" and i + 1 < len(args):
            model = args[i + 1]
            i += 2
        elif args[i] == "--interactive":
            interactive = True
            i += 1
        elif args[i] == "--tts":
            enable_tts = True
            i += 1
        else:
            i += 1
    
    # Validate required arguments
    if not strategy:
        print("❌ Error: --strategy is required")
        print("\nUsage:")
        print("  python3 test/prompt_strategy/test_prompt_strategy.py --strategy unified --scenario scenario_01_normal")
        print("  python3 test/prompt_strategy/test_prompt_strategy.py --strategy unified --interactive")
        sys.exit(1)
    
    if not interactive and not scenario:
        print("❌ Error: Either --scenario or --interactive is required")
        print("\nUsage:")
        print("  python3 test/prompt_strategy/test_prompt_strategy.py --strategy unified --scenario scenario_01_normal")
        print("  python3 test/prompt_strategy/test_prompt_strategy.py --strategy unified --interactive")
        sys.exit(1)
    
    print("=" * 60)
    print("🧪 System Prompt Strategy Testing Tool")
    print("=" * 60)
    
    # Load prompt strategy
    system_prompt = load_prompt_strategy(strategy)
    
    # Load scenario (if not interactive)
    user_messages = []
    if not interactive:
        user_messages = load_scenario(scenario)
    
    # Run conversation test
    try:
        conversation, metrics = run_conversation_test(
            system_prompt=system_prompt,
            user_messages=user_messages,
            model=model,
            interactive=interactive,
            enable_tts=enable_tts
        )
        
        # Print metrics
        print_metrics(metrics)
        
        # Save results
        if conversation:
            scenario_name = scenario if scenario else "interactive"
            save_results(strategy, scenario_name, system_prompt, conversation, metrics, model or "gpt-4o-mini")
        
        print("\n✅ Test completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

