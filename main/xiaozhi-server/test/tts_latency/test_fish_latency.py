#!/usr/bin/env python3
"""
Fish Speech TTS Latency Comparison: HTTP vs WebSocket

This script compares the latency of Fish Speech TTS using:
1. HTTP streaming (session.tts)
2. WebSocket streaming (client.tts.stream_websocket)

Usage:
    python3 test_fish_latency.py
    
    # With custom API key
    FISH_API_KEY="your-key" python3 test_fish_latency.py
    
    # With custom voice
    FISH_REFERENCE_ID="voice-id" python3 test_fish_latency.py

Output:
    - Generates a markdown report in ./reports/
    - Prints summary to console

Requirements:
    pip install fish-audio-sdk
"""

import os
import sys
import time
import asyncio
import statistics
from datetime import datetime
from dataclasses import dataclass

# Check for required package
try:
    from fishaudio import AsyncFishAudio
    from fishaudio.types.tts import TTSConfig, FlushEvent
except ImportError:
    print("❌ Missing required packages. Install with:")
    print("   pip install fish-audio-sdk")
    sys.exit(1)


@dataclass
class LatencyResult:
    """Single test result"""
    method: str
    test_name: str
    text_length: int
    ttfb_ms: float  # Time to first byte
    total_ms: float  # Total time
    audio_bytes: int
    success: bool
    error: str = ""


@dataclass
class TestConfig:
    """Test configuration"""
    api_key: str
    reference_id: str
    sample_rate: int = 16000
    format: str = "pcm"
    latency_mode: str = "balanced"  # "balanced" or "normal"
    runs_per_test: int = 3


# LLM simulation - tokens arrive with delays
# Realistic LLM output with punctuation for sentence segmentation
LLM_SIMULATION = {
    "tokens": [
        "好", "的", "，", "今", "天", "天", "气", "非", "常", "不", "错", "。",
        "阳", "光", "明", "媚", "，", "温", "度", "适", "宜", "，", "非", "常", 
        "适", "合", "户", "外", "活", "动", "！", "你", "想", "去", "哪", "里", "玩", "呢", "？"
    ],
    "delay_ms": 30,  # Simulate ~30ms per token (typical LLM speed for Chinese)
}

# Punctuation sets for sentence segmentation (from base.py)
FIRST_SENTENCE_PUNCTUATIONS = ["，", ","]  # First sentence ends at comma
SENTENCE_PUNCTUATIONS = ["。", "！", "？", "；", ".", "!", "?", ";", "\n"]  # Full sentence ends
MIN_FIRST_SEGMENT_CHARS = 8  # Minimum chars for first segment


class TextSegmenter:
    """
    Simulates the text segmentation logic from base.py _get_segment_text()
    Collects tokens and yields segments when punctuation is encountered.
    """
    
    def __init__(self):
        self.buffer = ""
        self.is_first_sentence = True
    
    def reset(self):
        self.buffer = ""
        self.is_first_sentence = True
    
    def add_token(self, token: str) -> str | None:
        """
        Add a token and return a segment if ready, otherwise None.
        Mirrors the logic in base.py _get_segment_text()
        """
        self.buffer += token
        
        # Choose punctuation set based on whether it's the first sentence
        punctuations = FIRST_SENTENCE_PUNCTUATIONS if self.is_first_sentence else SENTENCE_PUNCTUATIONS
        
        # Find the last punctuation position
        last_punct_pos = -1
        for punct in punctuations:
            pos = self.buffer.rfind(punct)
            if pos != -1 and (last_punct_pos == -1 or pos < last_punct_pos):
                last_punct_pos = pos
        
        if last_punct_pos != -1:
            segment = self.buffer[:last_punct_pos + 1]
            
            # First segment minimum length check
            if self.is_first_sentence and len(segment) < MIN_FIRST_SEGMENT_CHARS:
                return None  # Wait for more text
            
            # Extract segment and update buffer
            self.buffer = self.buffer[last_punct_pos + 1:]
            
            if self.is_first_sentence:
                self.is_first_sentence = False
            
            return segment
        
        return None
    
    def flush(self) -> str | None:
        """Return any remaining text in buffer"""
        if self.buffer:
            remaining = self.buffer
            self.buffer = ""
            self.is_first_sentence = True
            return remaining
        return None


class HTTPTester:
    """HTTP streaming TTS tester"""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.client = AsyncFishAudio(api_key=config.api_key)
    
    async def test_llm_stream(self, test_name: str) -> LatencyResult:
        """
        Test TTS with simulated LLM streaming output via HTTP.
        
        Flow (matches current implementation):
        1. LLM outputs tokens with delays
        2. TextSegmenter collects tokens and waits for punctuation
        3. When a segment is ready, immediately call HTTP TTS for that segment
        4. Continue receiving LLM tokens while TTS processes
        
        Key limitation: HTTP cannot start TTS until a complete segment is available.
        """
        tokens = LLM_SIMULATION["tokens"]
        delay_ms = LLM_SIMULATION["delay_ms"]
        
        # Start timing from when LLM starts generating
        start_time = time.perf_counter()
        first_chunk_time = None
        audio_bytes = b''
        full_text = "".join(tokens)
        
        try:
            segmenter = TextSegmenter()
            tts_config = TTSConfig(
                format=self.config.format,
                model="s1",
                sample_rate=self.config.sample_rate,
                normalize=True,
                latency=self.config.latency_mode,
            )
            
            # Process tokens and immediately send segments to TTS when ready
            for token in tokens:
                await asyncio.sleep(delay_ms / 1000)  # Simulate LLM generation delay
                segment = segmenter.add_token(token)
                
                # When a segment is ready, immediately call HTTP TTS
                if segment:
                    audio_stream = await self.client.tts.stream(
                        text=segment,
                        reference_id=self.config.reference_id,
                        model="s1",
                        config=tts_config,
                    )
                    
                    async for chunk in audio_stream:
                        if chunk:
                            if first_chunk_time is None:
                                first_chunk_time = time.perf_counter()
                            audio_bytes += chunk
            
            # Flush any remaining text
            remaining = segmenter.flush()
            if remaining:
                audio_stream = await self.client.tts.stream(
                    text=remaining,
                    reference_id=self.config.reference_id,
                    model="s1",
                    config=tts_config,
                )
                
                async for chunk in audio_stream:
                    if chunk:
                        if first_chunk_time is None:
                            first_chunk_time = time.perf_counter()
                        audio_bytes += chunk
            
            end_time = time.perf_counter()
            
            if first_chunk_time is None:
                first_chunk_time = end_time
            
            return LatencyResult(
                method="HTTP-LLM",
                test_name=test_name,
                text_length=len(full_text),
                ttfb_ms=(first_chunk_time - start_time) * 1000,  # From LLM start to first audio
                total_ms=(end_time - start_time) * 1000,
                audio_bytes=len(audio_bytes),
                success=True,
            )
        except Exception as e:
            return LatencyResult(
                method="HTTP-LLM",
                test_name=test_name,
                text_length=len(full_text),
                ttfb_ms=0,
                total_ms=0,
                audio_bytes=0,
                success=False,
                error=str(e),
            )


class WebSocketTester:
    """WebSocket streaming TTS tester using fishaudio SDK"""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.client = AsyncFishAudio(api_key=config.api_key)
    
    async def test_llm_stream(self, test_name: str) -> LatencyResult:
        """
        Test TTS with simulated LLM streaming output via WebSocket.
        
        Optimizations:
        1. Pre-connect: Yield empty string before LLM delay to establish connection early
        2. FlushEvent: Use TextSegmenter + FlushEvent to force audio generation at sentence boundaries
        
        This mirrors HTTP's chunking strategy but with WebSocket's streaming advantage.
        """
        tokens = LLM_SIMULATION["tokens"]
        delay_ms = LLM_SIMULATION["delay_ms"]
        full_text = "".join(tokens)

        tts_config = TTSConfig(
            format=self.config.format,
            sample_rate=self.config.sample_rate,
            normalize=True,
            latency=self.config.latency_mode,
        )

        # Optimization 1: Pre-connect - yield empty string to establish connection
        # before the first LLM token delay

        async def init_websocket():
            yield ""
        
        self.client.tts.stream_websocket(
            init_websocket(),
            reference_id=self.config.reference_id,
            config=tts_config,
        )

        start_time = time.perf_counter()
        first_chunk_time = None
        audio_bytes = b''
        
        try:
            
            async def llm_token_gen():
                """
                Simulate LLM streaming with FlushEvent optimization.
                - Pre-connect by yielding empty string immediately
                - Use TextSegmenter to detect sentence boundaries  
                - Yield FlushEvent after each complete segment to force immediate audio generation
                """
                segmenter = TextSegmenter()
                
                for token in tokens:
                    await asyncio.sleep(delay_ms / 1000)  # Simulate LLM generation delay
                    
                    # Accumulate token and check for segment completion
                    segment = segmenter.add_token(token)
                    
                    if segment:
                        # Optimization 2: When segment is complete, yield it + FlushEvent
                        # to force immediate audio generation
                        yield segment
                        yield FlushEvent()
                    # Note: Don't yield individual tokens - TextSegmenter handles buffering
                    # The segment already contains all accumulated tokens
                
                # Flush any remaining text
                remaining = segmenter.flush()
                if remaining:
                    yield remaining
                    yield FlushEvent()
            
            audio_stream = self.client.tts.stream_websocket(
                llm_token_gen(),
                reference_id=self.config.reference_id,
                config=tts_config,
            )
            
            async for chunk in audio_stream:
                if chunk:
                    if first_chunk_time is None:
                        first_chunk_time = time.perf_counter()
                    audio_bytes += chunk
            
            end_time = time.perf_counter()
            
            if first_chunk_time is None:
                first_chunk_time = end_time
            
            return LatencyResult(
                method="WebSocket-LLM",
                test_name=test_name,
                text_length=len(full_text),
                ttfb_ms=(first_chunk_time - start_time) * 1000,
                total_ms=(end_time - start_time) * 1000,
                audio_bytes=len(audio_bytes),
                success=True,
            )
        except Exception as e:
            return LatencyResult(
                method="WebSocket-LLM",
                test_name=test_name,
                text_length=len(full_text),
                ttfb_ms=0,
                total_ms=0,
                audio_bytes=0,
                success=False,
                error=str(e),
            )


def generate_report(results: list[LatencyResult], config: TestConfig) -> str:
    """Generate markdown report"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = f"""# Fish Speech TTS Latency Comparison Report

**Generated:** {now}  
**Reference ID:** {config.reference_id}  
**Sample Rate:** {config.sample_rate} Hz  
**Format:** {config.format}  
**WebSocket Latency Mode:** {config.latency_mode}  
**Runs per Test:** {config.runs_per_test}

---

## Summary

| Method | Test | Avg TTFB (ms) | Avg Total (ms) | Avg Audio (bytes) |
|--------|------|---------------|----------------|-------------------|
"""
    
    # Group results by method and test
    grouped = {}
    for r in results:
        if not r.success:
            continue
        key = (r.method, r.test_name)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(r)
    
    for (method, test_name), runs in sorted(grouped.items()):
        avg_ttfb = statistics.mean(r.ttfb_ms for r in runs)
        avg_total = statistics.mean(r.total_ms for r in runs)
        avg_audio = statistics.mean(r.audio_bytes for r in runs)
        report += f"| {method} | {test_name} | {avg_ttfb:.1f} | {avg_total:.1f} | {avg_audio:.0f} |\n"
    
    report += """
---

## Detailed Results

"""
    
    for (method, test_name), runs in sorted(grouped.items()):
        report += f"### {method} - {test_name}\n\n"
        report += "| Run | TTFB (ms) | Total (ms) | Audio (bytes) | Text Length |\n"
        report += "|-----|-----------|------------|---------------|-------------|\n"
        
        for i, r in enumerate(runs, 1):
            report += f"| {i} | {r.ttfb_ms:.1f} | {r.total_ms:.1f} | {r.audio_bytes} | {r.text_length} |\n"
        
        if len(runs) > 1:
            ttfb_std = statistics.stdev(r.ttfb_ms for r in runs)
            total_std = statistics.stdev(r.total_ms for r in runs)
            report += f"\n**TTFB Std Dev:** {ttfb_std:.1f} ms | **Total Std Dev:** {total_std:.1f} ms\n"
        
        report += "\n"
    
    # Error summary
    errors = [r for r in results if not r.success]
    if errors:
        report += "## Errors\n\n"
        for r in errors:
            report += f"- **{r.method}** - {r.test_name}: {r.error}\n"
        report += "\n"
    
    # Analysis
    report += """---

## Analysis

### Key Findings: LLM Streaming Simulation

This is the critical comparison for multi-turn conversations.

**Test Setup:**
- Simulated LLM output: {} tokens, {}ms per token
- Full text: "{}"

**HTTP-LLM Flow (Current Implementation):**
1. LLM outputs tokens → TextSegmenter collects
2. Wait for punctuation (e.g., comma for first sentence)
3. Segment ready → HTTP TTS request
4. Repeat for each segment

**WebSocket-LLM Flow (Proposed):**
1. LLM outputs tokens → Stream directly to WebSocket
2. Fish Audio server buffers and generates audio
3. Audio chunks return as soon as server is ready
4. No client-side segmentation needed!

""".format(len(LLM_SIMULATION["tokens"]), LLM_SIMULATION["delay_ms"], "".join(LLM_SIMULATION["tokens"])[:50] + "...")
    
    http_llm_runs = grouped.get(("HTTP-LLM", "llm_simulation"), [])
    ws_llm_runs = grouped.get(("WebSocket-LLM", "llm_simulation"), [])
    
    if http_llm_runs and ws_llm_runs:
        http_ttfb = statistics.mean(r.ttfb_ms for r in http_llm_runs)
        ws_ttfb = statistics.mean(r.ttfb_ms for r in ws_llm_runs)
        http_total = statistics.mean(r.total_ms for r in http_llm_runs)
        ws_total = statistics.mean(r.total_ms for r in ws_llm_runs)
        
        ttfb_diff = http_ttfb - ws_ttfb
        total_diff = http_total - ws_total
        ttfb_pct = (ttfb_diff / http_ttfb * 100) if http_ttfb > 0 else 0
        total_pct = (total_diff / http_total * 100) if http_total > 0 else 0
        
        report += f"| Metric | HTTP-LLM | WebSocket-LLM | Difference |\n"
        report += f"|--------|----------|---------------|------------|\n"
        report += f"| TTFB | {http_ttfb:.0f}ms | {ws_ttfb:.0f}ms | **{ttfb_diff:.0f}ms** ({ttfb_pct:.1f}%) |\n"
        report += f"| Total | {http_total:.0f}ms | {ws_total:.0f}ms | **{total_diff:.0f}ms** ({total_pct:.1f}%) |\n"
        
        if ttfb_diff > 100:
            report += f"\n🎯 **WebSocket provides {ttfb_diff:.0f}ms faster first audio** in LLM streaming scenarios!\n"
    
    report += """
### Recommendations

1. **For single requests:** Compare TTFB values above to determine the best method
2. **For LLM streaming:** WebSocket allows sending tokens as they arrive, reducing perceived latency
3. **Consider `latency="balanced"` for real-time applications**
4. **For multi-turn conversations:** WebSocket streaming is recommended for lower latency

---

*Generated by Fish Speech TTS Latency Tester*
"""
    
    return report


async def main():
    print("🐟 Fish Speech TTS Latency Comparison Test")
    print("=" * 50)
    
    # Get configuration from environment
    api_key = os.environ.get("FISH_API_KEY")
    if not api_key:
        print("\n❌ Error: FISH_API_KEY not set")
        print("   export FISH_API_KEY='your-key'")
        print("\n💡 Get your API key from: https://fish.audio/")
        sys.exit(1)
    
    reference_id = os.environ.get("FISH_REFERENCE_ID", "5196af35f6ff4a0dbf541793fc9f2157")
    runs = int(os.environ.get("TEST_RUNS", "3"))
    
    config = TestConfig(
        api_key=api_key,
        reference_id=reference_id,
        runs_per_test=runs,
    )
    
    print(f"\n📋 Configuration:")
    print(f"   Reference ID: {reference_id}")
    print(f"   Sample Rate: {config.sample_rate} Hz")
    print(f"   Format: {config.format}")
    print(f"   Runs per test: {runs}")
    
    # Initialize testers
    http_tester = HTTPTester(config)
    ws_tester = WebSocketTester(config)
    
    results: list[LatencyResult] = []
    
    # Run HTTP LLM simulation test
    print("\n" + "=" * 50)
    print("🔄 Testing HTTP with LLM Simulation...")
    print("   (HTTP must wait for segment completion before starting TTS)")
    print("=" * 50)
    
    print(f"\n📝 Simulating LLM output ({len(LLM_SIMULATION['tokens'])} tokens, {LLM_SIMULATION['delay_ms']}ms/token)")
    for run in range(runs):
        result = await http_tester.test_llm_stream("llm_simulation")
        results.append(result)
        if result.success:
            print(f"   Run {run + 1}: TTFB={result.ttfb_ms:.0f}ms, Total={result.total_ms:.0f}ms")
        else:
            print(f"   Run {run + 1}: ❌ {result.error}")
        await asyncio.sleep(0.5)
    
    # Run WebSocket LLM simulation test
    print("\n" + "=" * 50)
    print("🔄 Testing WebSocket with LLM Simulation...")
    print("=" * 50)
    
    print(f"\n📝 Simulating LLM output ({len(LLM_SIMULATION['tokens'])} tokens, {LLM_SIMULATION['delay_ms']}ms/token)")
    for run in range(runs):
        result = await ws_tester.test_llm_stream("llm_simulation")
        results.append(result)
        if result.success:
            print(f"   Run {run + 1}: TTFB={result.ttfb_ms:.0f}ms, Total={result.total_ms:.0f}ms")
        else:
            print(f"   Run {run + 1}: ❌ {result.error}")
        await asyncio.sleep(0.5)
    
    # Generate report
    print("\n" + "=" * 50)
    print("📊 Generating Report...")
    print("=" * 50)
    
    report = generate_report(results, config)
    
    # Save report
    script_dir = os.path.dirname(os.path.abspath(__file__))
    reports_dir = os.path.join(script_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(reports_dir, f"latency_report_{timestamp}.md")
    
    with open(report_file, "w") as f:
        f.write(report)
    
    print(f"\n✅ Report saved to: {report_file}")
    
    # Print summary
    print("\n" + "=" * 50)
    print("📈 Quick Summary")
    print("=" * 50)
    
    # Group and average results
    grouped = {}
    for r in results:
        if not r.success:
            continue
        key = (r.method, r.test_name)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(r)
    
    print(f"\n{'Method':<15} {'Test':<20} {'Avg TTFB (ms)':<15} {'Avg Total (ms)':<15}")
    print("-" * 65)
    
    for (method, test_name), runs_list in sorted(grouped.items()):
        avg_ttfb = statistics.mean(r.ttfb_ms for r in runs_list)
        avg_total = statistics.mean(r.total_ms for r in runs_list)
        print(f"{method:<15} {test_name:<20} {avg_ttfb:<15.0f} {avg_total:<15.0f}")
    
    print("\n✅ Test completed!")


if __name__ == "__main__":
    asyncio.run(main())

