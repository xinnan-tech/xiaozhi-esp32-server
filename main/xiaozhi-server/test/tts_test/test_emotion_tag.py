#!/usr/bin/env python3
"""
Fish Speech Emotion Tag Test

This script tests whether Fish Speech TTS correctly handles emotion tags:
- Emotion tags like (happy), (sad) should NOT be read aloud
- Only the actual text content should be spoken

Method:
1. Generate TTS audio with emotion-tagged text
2. Transcribe the audio using Groq Whisper ASR
3. Compare transcript with expected text (without emotion tag)
4. Report whether the emotion tag was incorrectly read aloud

Usage:
    python3 test_emotion_tag.py
    
    # With API keys
    FISH_API_KEY="your-fish-key" GROQ_API_KEY="your-groq-key" python3 test_emotion_tag.py
    
    # With custom voice
    FISH_REFERENCE_ID="voice-id" python3 test_emotion_tag.py

Requirements:
    pip install fish-audio-sdk openai
"""

import os
import sys
import io
import wave
import asyncio
import tempfile
import argparse
from datetime import datetime
from dataclasses import dataclass, field

# Check for required packages
try:
    from fishaudio import AsyncFishAudio
    from fishaudio.types.tts import TTSConfig
except ImportError:
    print("❌ Missing fish-audio-sdk. Install with:")
    print("   pip install fish-audio-sdk")
    sys.exit(1)

try:
    from openai import OpenAI
except ImportError:
    print("❌ Missing openai. Install with:")
    print("   pip install openai")
    sys.exit(1)


# All emotion tags from role.md
EMOTION_TAGS = [
    "happy", "satisfied", "relaxed", "amused", "sincere", "conciliative",
    "calm", "confident", "curious", "keen", "confused", "worried",
    "frustrated", "sad", "unhappy", "impatient", "negative", "disapproving",
    "disdainful", "scornful", "sarcastic", "surprised"
]

# Voice reference IDs for different languages
VOICE_REFERENCES = {
    "zh": "aebaa2305aa2452fbdc8f41eec852a79",
    "en": "e58b0d7efca34eb38d5c4985e378abcb",
}

# Test texts in different languages (20 sentences each)
TEST_TEXTS = {
    "zh": [
        "今天天气真好",
        "我很高兴认识你",
        "这个问题有点复杂",
        "让我想一想",
        "你说得对",
        "我明白你的意思了",
        "这件事情很重要",
        "我们一起努力吧",
        "谢谢你的帮助",
        "请稍等一下",
        "我有一个想法",
        "这真是太棒了",
        "我需要更多时间",
        "你觉得怎么样",
        "让我们开始吧",
        "我不太确定",
        "这是个好主意",
        "我会尽力的",
        "请告诉我更多",
        "我们来看看",
    ],
    "en": [
        "The weather is nice today",
        "Nice to meet you",
        "This is a bit complicated",
        "Let me think about it",
        "You are right",
        "I understand what you mean",
        "This is very important",
        "Let us work together",
        "Thank you for your help",
        "Please wait a moment",
        "I have an idea",
        "This is amazing",
        "I need more time",
        "What do you think",
        "Let us get started",
        "I am not sure",
        "That is a good idea",
        "I will do my best",
        "Please tell me more",
        "Let us take a look",
    ],
}

# Default: test all emotion tags
DEFAULT_TEST_EMOTIONS = EMOTION_TAGS


@dataclass
class TestCase:
    """Single test case configuration"""
    emotion: str
    text: str
    lang: str
    input_text: str = field(init=False)
    
    def __post_init__(self):
        self.input_text = f"({self.emotion}) {self.text}"
        if self.lang == "en":
            self.input_text += "."
        else:
            self.input_text += "。"


@dataclass
class TestResult:
    """Single test result"""
    test_case: TestCase
    transcript: str
    tag_leaked: bool  # True if emotion tag was read aloud
    text_match: bool  # True if transcript matches expected text
    audio_duration_ms: float
    success: bool
    error: str = ""
    audio_file: str = ""  # Path to saved audio file (for failed cases)


@dataclass
class TestConfig:
    """Test configuration"""
    api_key: str
    groq_api_key: str
    voice_references: dict  # {lang: reference_id}
    sample_rate: int = 16000
    format: str = "pcm"
    whisper_model: str = "whisper-large-v3"  # Groq whisper model
    emotions: list = field(default_factory=lambda: DEFAULT_TEST_EMOTIONS)
    languages: list = field(default_factory=lambda: ["zh", "en"])
    
    def get_reference_id(self, lang: str) -> str:
        """Get voice reference ID for a specific language"""
        return self.voice_references.get(lang, "")


class EmotionTagTester:
    """Emotion tag testing class"""
    
    # Groq API base URL (OpenAI compatible)
    GROQ_BASE_URL = "https://api.groq.com/openai/v1"
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.client = AsyncFishAudio(api_key=config.api_key)
        self.groq_client = OpenAI(
            api_key=config.groq_api_key,
            base_url=self.GROQ_BASE_URL
        )
        
        # Create tmp directory for failed audio files
        self.tmp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp")
        os.makedirs(self.tmp_dir, exist_ok=True)
    
    def _pcm_to_wav(self, pcm_data: bytes) -> bytes:
        """Convert PCM to WAV format for ASR"""
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self.config.sample_rate)
            wav_file.writeframes(pcm_data)
        return wav_buffer.getvalue()
    
    def _save_failed_audio(self, test_case: TestCase, audio_data: bytes) -> str:
        """Save failed audio to tmp directory"""
        # Generate filename: {emotion}_{lang}_{text_hash}.wav
        text_hash = hash(test_case.text) & 0xFFFFFF  # 6 hex chars
        filename = f"{test_case.emotion}_{test_case.lang}_{text_hash:06x}.wav"
        filepath = os.path.join(self.tmp_dir, filename)
        
        wav_data = self._pcm_to_wav(audio_data)
        with open(filepath, "wb") as f:
            f.write(wav_data)
        
        return filepath
    
    def _transcribe(self, audio_data: bytes, lang: str) -> str:
        """Transcribe audio using Groq Whisper API"""
        # Save to temp file (API needs file)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_data = self._pcm_to_wav(audio_data)
            f.write(wav_data)
            temp_path = f.name
        
        try:
            with open(temp_path, "rb") as audio_file:
                response = self.groq_client.audio.transcriptions.create(
                    model=self.config.whisper_model,
                    file=audio_file,
                    language=lang if lang != "zh" else "zh",
                )
            return response.text.strip()
        finally:
            os.unlink(temp_path)
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        # Remove punctuation and convert to lowercase
        import re
        text = re.sub(r'[^\w\s]', '', text)
        return text.lower().strip()
    
    def _check_tag_leaked(self, transcript: str, emotion: str) -> bool:
        """Check if emotion tag was read aloud"""
        normalized = self._normalize_text(transcript)
        emotion_lower = emotion.lower()
        
        # Check for exact emotion word
        if emotion_lower in normalized.split():
            return True
        
        # Check for common mispronunciations/variations
        variations = {
            "happy": ["happy", "hapi", "happie"],
            "sad": ["sad", "sæd"],
            "calm": ["calm", "kam", "come"],
            "surprised": ["surprised", "surprise"],
            "curious": ["curious", "curios"],
            "worried": ["worried", "worry"],
            "frustrated": ["frustrated", "frustrate"],
            "confident": ["confident", "confidence"],
            "sincere": ["sincere", "sincer"],
            "sarcastic": ["sarcastic", "sarcasm"],
        }
        
        for var in variations.get(emotion_lower, [emotion_lower]):
            if var in normalized:
                return True
        
        return False
    
    def _check_text_match(self, transcript: str, expected: str) -> bool:
        """Check if transcript matches expected text (fuzzy)"""
        norm_transcript = self._normalize_text(transcript)
        norm_expected = self._normalize_text(expected)
        
        # Simple word overlap ratio
        transcript_words = set(norm_transcript.split())
        expected_words = set(norm_expected.split())
        
        if not expected_words:
            return True
        
        overlap = len(transcript_words & expected_words)
        ratio = overlap / len(expected_words)
        
        return ratio >= 0.5  # At least 50% word match
    
    async def run_test(self, test_case: TestCase) -> TestResult:
        """Run a single test case"""
        try:
            tts_config = TTSConfig(
                format=self.config.format,
                model="s1",
                sample_rate=self.config.sample_rate,
                normalize=True,
                latency="balanced",
            )
            
            # Get voice reference ID for this language
            reference_id = self.config.get_reference_id(test_case.lang)
            if not reference_id:
                return TestResult(
                    test_case=test_case,
                    transcript="",
                    tag_leaked=False,
                    text_match=False,
                    audio_duration_ms=0,
                    success=False,
                    error=f"No voice reference ID configured for language: {test_case.lang}"
                )
            
            # Generate TTS audio
            audio_data = b''
            audio_stream = await self.client.tts.stream(
                text=test_case.input_text,
                reference_id=reference_id,
                model="s1",
                config=tts_config,
            )
            
            async for chunk in audio_stream:
                if chunk:
                    audio_data += chunk
            
            if not audio_data:
                return TestResult(
                    test_case=test_case,
                    transcript="",
                    tag_leaked=False,
                    text_match=False,
                    audio_duration_ms=0,
                    success=False,
                    error="No audio data received"
                )
            
            # Calculate audio duration
            audio_duration_ms = len(audio_data) / (self.config.sample_rate * 2) * 1000
            
            # Transcribe
            transcript = self._transcribe(audio_data, test_case.lang)
            
            # Check results
            tag_leaked = self._check_tag_leaked(transcript, test_case.emotion)
            text_match = self._check_text_match(transcript, test_case.text)
            
            # Save audio if tag leaked
            audio_file = ""
            if tag_leaked:
                audio_file = self._save_failed_audio(test_case, audio_data)
            
            return TestResult(
                test_case=test_case,
                transcript=transcript,
                tag_leaked=tag_leaked,
                text_match=text_match,
                audio_duration_ms=audio_duration_ms,
                success=True,
                audio_file=audio_file
            )
            
        except Exception as e:
            return TestResult(
                test_case=test_case,
                transcript="",
                tag_leaked=False,
                text_match=False,
                audio_duration_ms=0,
                success=False,
                error=str(e)
            )
    
    async def run_all_tests(self) -> list[TestResult]:
        """Run all test cases"""
        results = []
        
        # Generate test cases: organized by language -> emotion -> texts
        test_cases = []
        for lang in self.config.languages:
            texts = TEST_TEXTS.get(lang, [])
            for emotion in self.config.emotions:
                for text in texts:
                    test_cases.append(TestCase(emotion=emotion, text=text, lang=lang))
        
        total = len(test_cases)
        num_emotions = len(self.config.emotions)
        num_texts = len(TEST_TEXTS.get(self.config.languages[0], []))
        
        print(f"\n🧪 Test Plan:")
        print(f"   Languages: {self.config.languages}")
        print(f"   Emotion Tags: {num_emotions}")
        print(f"   Sentences per Tag: {num_texts}")
        print(f"   Total Test Cases: {total}")
        
        leaked_count = 0
        current_lang = None
        current_emotion = None
        
        for i, tc in enumerate(test_cases, 1):
            # Print progress header when language or emotion changes
            if tc.lang != current_lang:
                current_lang = tc.lang
                print(f"\n{'='*60}")
                print(f"📍 Language: {current_lang.upper()}")
                print(f"{'='*60}")
            
            if tc.emotion != current_emotion:
                current_emotion = tc.emotion
                print(f"\n🏷️  Testing emotion: {current_emotion}")
            
            # Run test
            result = await self.run_test(tc)
            results.append(result)
            
            # Compact progress output
            if result.success:
                if result.tag_leaked:
                    leaked_count += 1
                    print(f"   ❌ [{i}/{total}] LEAKED: \"{tc.text[:20]}...\" → \"{result.transcript[:30]}...\"")
                    if result.audio_file:
                        print(f"      📁 Saved: {os.path.basename(result.audio_file)}")
                else:
                    # Only show dot for success to keep output clean
                    print(f"   ✓ [{i}/{total}] OK", end="\r")
            else:
                print(f"   ⚠️ [{i}/{total}] ERROR: {result.error[:50]}")
            
            # Small delay between requests
            await asyncio.sleep(0.2)
        
        # Final summary
        print(f"\n\n{'='*60}")
        print(f"📊 Test Complete: {total} tests, {leaked_count} leaks")
        print(f"{'='*60}")
        
        return results


def generate_report(results: list[TestResult], config: TestConfig) -> str:
    """Generate markdown report"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Statistics
    total = len(results)
    successful = sum(1 for r in results if r.success)
    leaked = sum(1 for r in results if r.success and r.tag_leaked)
    matched = sum(1 for r in results if r.success and r.text_match)
    
    # Build voice references string
    voice_refs_str = ", ".join([f"{lang.upper()}: `{config.voice_references.get(lang, 'N/A')}`" for lang in config.languages])
    
    # Calculate sentences per tag
    num_sentences = len(TEST_TEXTS.get(config.languages[0], []))
    
    report = f"""# Fish Speech Emotion Tag Test Report

**Generated:** {now}  
**Voice References:** {voice_refs_str}  
**ASR Model:** Groq {config.whisper_model}  
**Languages:** {', '.join(config.languages)}  
**Emotion Tags:** {len(config.emotions)}  
**Sentences per Tag:** {num_sentences}  
**Total Tests:** {total}

---

## Summary

| Metric | Count | Percentage |
|--------|-------|------------|
| Total Tests | {total} | 100% |
| Successful | {successful} | {successful/total*100:.1f}% |
| **Tag Leaked** | **{leaked}** | **{leaked/successful*100:.1f}%** |
| Text Matched | {matched} | {matched/successful*100:.1f}% |

### Interpretation

- **Tag Leaked = 0**: ✅ Fish Speech correctly handles emotion tags (not read aloud)
- **Tag Leaked > 0**: ⚠️ Fish Speech may be reading emotion tags as text

---

## Leak Rate by Emotion Tag & Language

This is the main summary table showing leak rate for each emotion tag across languages.

"""
    
    # Build main summary table: Emotion x Language
    report += "| Emotion Tag |"
    for lang in config.languages:
        report += f" {lang.upper()} |"
    report += " Overall |\n"
    
    report += "|-------------|"
    for _ in config.languages:
        report += "--------|"
    report += "---------|\n"
    
    for emotion in config.emotions:
        report += f"| {emotion} |"
        
        total_leaked = 0
        total_count = 0
        
        for lang in config.languages:
            lang_emo_results = [
                r for r in results 
                if r.test_case.emotion == emotion 
                and r.test_case.lang == lang 
                and r.success
            ]
            lang_leaked = sum(1 for r in lang_emo_results if r.tag_leaked)
            lang_count = len(lang_emo_results)
            
            total_leaked += lang_leaked
            total_count += lang_count
            
            if lang_count > 0:
                rate = lang_leaked / lang_count * 100
                status = "✅" if lang_leaked == 0 else "⚠️"
                report += f" {lang_leaked}/{lang_count} ({rate:.0f}%) {status} |"
            else:
                report += " N/A |"
        
        # Overall for this emotion
        if total_count > 0:
            overall_rate = total_leaked / total_count * 100
            overall_status = "✅" if total_leaked == 0 else "⚠️"
            report += f" {total_leaked}/{total_count} ({overall_rate:.0f}%) {overall_status} |\n"
        else:
            report += " N/A |\n"
    
    # Language summary row
    report += "| **Total** |"
    grand_total_leaked = 0
    grand_total_count = 0
    
    for lang in config.languages:
        lang_results = [r for r in results if r.test_case.lang == lang and r.success]
        lang_leaked = sum(1 for r in lang_results if r.tag_leaked)
        lang_count = len(lang_results)
        
        grand_total_leaked += lang_leaked
        grand_total_count += lang_count
        
        if lang_count > 0:
            rate = lang_leaked / lang_count * 100
            report += f" **{lang_leaked}/{lang_count} ({rate:.0f}%)** |"
        else:
            report += " N/A |"
    
    if grand_total_count > 0:
        overall_rate = grand_total_leaked / grand_total_count * 100
        report += f" **{grand_total_leaked}/{grand_total_count} ({overall_rate:.0f}%)** |\n"
    else:
        report += " N/A |\n"
    
    report += "\n---\n\n"
    
    # Detailed failures
    failures = [r for r in results if r.success and r.tag_leaked]
    if failures:
        report += "## ⚠️ Failed Cases (Tag Leaked)\n\n"
        report += "Audio files saved in `tmp/` directory.\n\n"
        
        # Group by emotion
        from collections import defaultdict
        failures_by_emotion = defaultdict(list)
        for r in failures:
            failures_by_emotion[r.test_case.emotion].append(r)
        
        for emotion in sorted(failures_by_emotion.keys()):
            report += f"### {emotion}\n\n"
            report += "| Language | Input Text | Transcript | Audio File |\n"
            report += "|----------|------------|------------|------------|\n"
            
            for r in failures_by_emotion[emotion]:
                input_short = r.test_case.input_text[:40] + "..." if len(r.test_case.input_text) > 40 else r.test_case.input_text
                trans_short = r.transcript[:40] + "..." if len(r.transcript) > 40 else r.transcript
                audio_name = os.path.basename(r.audio_file) if r.audio_file else "N/A"
                report += f"| {r.test_case.lang.upper()} | {input_short} | {trans_short} | `{audio_name}` |\n"
            
            report += "\n"
    
    # Errors
    errors = [r for r in results if not r.success]
    if errors:
        report += "---\n\n## Errors\n\n"
        for r in errors:
            report += f"- [{r.test_case.lang.upper()}] {r.test_case.emotion}: {r.error}\n"
        report += "\n"
    
    report += """---

## Conclusion

"""
    
    if leaked == 0:
        report += "✅ **All emotion tags were correctly handled** - Fish Speech does not read emotion tags aloud.\n"
    else:
        leak_rate = leaked / successful * 100 if successful > 0 else 0
        report += f"⚠️ **{leaked} out of {successful} tests had tag leaks ({leak_rate:.1f}%)**\n\n"
        
        # Find problematic emotions
        problematic = []
        for emotion in config.emotions:
            emo_results = [r for r in results if r.test_case.emotion == emotion and r.success]
            emo_leaked = sum(1 for r in emo_results if r.tag_leaked)
            if emo_leaked > 0:
                rate = emo_leaked / len(emo_results) * 100
                problematic.append((emotion, rate))
        
        if problematic:
            problematic.sort(key=lambda x: -x[1])
            report += "**Most problematic emotion tags:**\n"
            for emotion, rate in problematic[:5]:
                report += f"- `{emotion}`: {rate:.0f}% leak rate\n"
    
    report += "\n---\n\n*Generated by Fish Speech Emotion Tag Tester*\n"
    
    return report


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Fish Speech Emotion Tag Test - Test if emotion tags are correctly handled",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test a single emotion tag
  python test_emotion_tag.py --tag happy
  
  # Test multiple tags
  python test_emotion_tag.py --tag happy --tag sad --tag calm
  
  # Run all tests
  python test_emotion_tag.py
  
  # List all available emotion tags
  python test_emotion_tag.py --list-tags

Environment Variables:
  FISH_API_KEY       Fish Audio API key (required)
  GROQ_API_KEY       Groq API key for ASR (required)
"""
    )
    
    parser.add_argument(
        "--tag", "-t",
        action="append",
        dest="tags",
        metavar="EMOTION",
        help="Emotion tag(s) to test (can be specified multiple times). Default: all tags"
    )
    
    parser.add_argument(
        "--list-tags",
        action="store_true",
        help="List all available emotion tags and exit"
    )
    
    return parser.parse_args()


async def main():
    args = parse_args()
    
    # Handle --list-tags
    if args.list_tags:
        print("Available emotion tags:")
        for i, tag in enumerate(EMOTION_TAGS, 1):
            print(f"  {i:2}. {tag}")
        print(f"\nTotal: {len(EMOTION_TAGS)} tags")
        sys.exit(0)
    
    print("🏷️  Fish Speech Emotion Tag Test")
    print("=" * 50)
    
    # Get configuration from environment
    api_key = os.environ.get("FISH_API_KEY")
    if not api_key:
        print("\n❌ Error: FISH_API_KEY not set")
        print("   export FISH_API_KEY='your-key'")
        print("\n💡 Get your API key from: https://fish.audio/")
        sys.exit(1)
    
    groq_api_key = os.environ.get("GROQ_API_KEY")
    if not groq_api_key:
        print("\n❌ Error: GROQ_API_KEY not set")
        print("   export GROQ_API_KEY='your-key'")
        print("\n💡 Get your API key from: https://console.groq.com/")
        sys.exit(1)
    
    # Voice references from fixed config
    voice_references = VOICE_REFERENCES.copy()
    whisper_model = "whisper-large-v3"
    
    # Emotions: CLI --tag or all
    if args.tags:
        # Validate tags
        invalid_tags = [t for t in args.tags if t not in EMOTION_TAGS]
        if invalid_tags:
            print(f"\n❌ Invalid emotion tag(s): {invalid_tags}")
            print(f"   Use --list-tags to see available tags")
            sys.exit(1)
        emotions = args.tags
    else:
        emotions = DEFAULT_TEST_EMOTIONS
    
    # Languages: always test both
    languages = ["zh", "en"]
    
    # Calculate sentence count
    all_texts = TEST_TEXTS.get(languages[0], [])
    num_sentences = len(all_texts)
    
    # Validate voice references for selected languages
    missing_voices = [lang for lang in languages if not voice_references.get(lang)]
    if missing_voices:
        print(f"\n❌ Error: Missing voice reference ID for language(s): {missing_voices}")
        print("   Please configure VOICE_REFERENCES in test_emotion_tag.py")
        sys.exit(1)
    
    config = TestConfig(
        api_key=api_key,
        groq_api_key=groq_api_key,
        voice_references=voice_references,
        whisper_model=whisper_model,
        emotions=emotions,
        languages=languages,
    )
    
    print(f"\n📋 Configuration:")
    print(f"   Groq ASR Model: {whisper_model}")
    print(f"   Languages & Voices:")
    for lang in languages:
        ref_id = voice_references.get(lang, "N/A")
        print(f"      {lang.upper()}: {ref_id}")
    print(f"   Emotion Tags: {len(emotions)} ({', '.join(emotions[:5])}{'...' if len(emotions) > 5 else ''})")
    print(f"   Sentences per Tag: {num_sentences}")
    print(f"   Estimated Tests: {len(emotions) * len(languages) * num_sentences}")
    
    # Run tests
    tester = EmotionTagTester(config)
    results = await tester.run_all_tests()
    
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
    report_file = os.path.join(reports_dir, f"emotion_tag_report_{timestamp}.md")
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"\n✅ Report saved to: {report_file}")
    
    # Print summary
    print("\n" + "=" * 50)
    print("📈 Quick Summary")
    print("=" * 50)
    
    total = len(results)
    successful = sum(1 for r in results if r.success)
    leaked = sum(1 for r in results if r.success and r.tag_leaked)
    saved_audio = sum(1 for r in results if r.audio_file)
    
    print(f"\n   Total Tests: {total}")
    print(f"   Successful: {successful}")
    print(f"   Tag Leaked: {leaked}")
    
    if leaked == 0:
        print("\n✅ All emotion tags handled correctly!")
    else:
        print(f"\n⚠️  {leaked} emotion tags were incorrectly read aloud!")
        if saved_audio > 0:
            print(f"📁 {saved_audio} audio files saved to: {tester.tmp_dir}")
    
    print("\n✅ Test completed!")


if __name__ == "__main__":
    asyncio.run(main())

