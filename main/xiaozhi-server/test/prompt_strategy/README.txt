System Prompt Strategy Testing Tool
====================================

This tool helps test and compare different system prompt organization strategies
to evaluate how each module (role, tone, guardrails, conversation strategy, etc.)
influences the agent's responses and behavior.

Directory Structure:
-------------------
test/
├── test_prompt_strategy.py    # Main test script
├── prompts/                    # Different prompt strategies
│   ├── unified.txt            # Baseline: all modules merged
│   ├── with_tts_emotion.txt   # Adds emotion markers for TTS
│   └── conversational.txt     # Natural speech with filler words & markers
├── scenarios/                  # Multi-turn conversation test cases
│   ├── scenario_01_normal.txt
│   ├── scenario_02_tone.txt
│   ├── scenario_03_guardrail.txt
│   ├── scenario_04_format.txt
│   ├── scenario_05_emotion.txt
│   └── scenario_06_conversational.txt
└── outputs/                    # Test results (auto-generated)

Quick Start:
-----------
1. Set your OpenAI API key:
   export OPENAI_API_KEY="sk-proj-your_key_here"

2. Run a test with a specific strategy and scenario:
   python3 test/prompt_strategy/test_prompt_strategy.py --strategy unified --scenario scenario_01_normal

3. Try interactive mode:
   python3 test/prompt_strategy/test_prompt_strategy.py --strategy unified --interactive

4. (Optional) Enable TTS playback:
   export FISH_API_KEY="your-fish-key"
   python3 test/prompt_strategy/test_prompt_strategy.py --strategy unified --scenario scenario_01_normal --tts

Usage Examples:
--------------
# Test unified strategy with normal conversation
python3 test/prompt_strategy/test_prompt_strategy.py --strategy unified --scenario scenario_01_normal

# Test another scenario
python3 test/prompt_strategy/test_prompt_strategy.py --strategy unified --scenario scenario_02_tone

# Interactive mode for manual testing
python3 test/prompt_strategy/test_prompt_strategy.py --strategy unified --interactive

# Use a different model
python3 test/prompt_strategy/test_prompt_strategy.py --strategy unified --scenario scenario_01_normal --model gpt-4o

# With TTS playback (requires Fish Audio SDK)
python3 test/prompt_strategy/test_prompt_strategy.py --strategy unified --scenario scenario_01_normal --tts

# With custom TTS voice
export FISH_REFERENCE_ID="your-voice-id"
python3 test/prompt_strategy/test_prompt_strategy.py --strategy unified --scenario scenario_01_normal --tts

Adding New Content:
------------------
1. Prompt Strategies:
   - Create a new .txt file in prompts/
   - Write your system prompt organization
   - Use it with --strategy <filename>

2. Scenarios:
   - Create a new .txt file in scenarios/
   - Add one user message per line
   - Lines starting with # are comments (ignored)
   - Use it with --scenario <filename>

Comparing Results:
-----------------
Results are saved in outputs/ directory with timestamp:
- File format: {strategy}_{scenario}_{timestamp}.json
- Contains: system prompt, conversation history, and performance metrics
- Compare different strategies by reviewing the JSON files

Evaluation Focus:
----------------
When reviewing results, pay attention to:
- Compliance: Does the model follow each module's instructions?
- Tone Consistency: Is the specified tone maintained?
- Guardrails: Are boundaries properly enforced?
- Format: Are responses formatted correctly for speech?
- Naturalness: Do responses sound conversational?
- Boundary Effects: How do different modules influence each other?

Prompt Strategies Explained:
----------------------------
1. unified.txt (Baseline)
   - All prompt modules in one cohesive prompt
   - No special speech markers or emotions
   - Good for comparing against enhanced versions

2. with_tts_emotion.txt (Emotion Enhanced)
   - Adds Fish Audio emotion markers: (happy), (empathetic), etc.
   - Teaches model to use emotions based on context
   - Best for expressive, emotionally aware responses
   - Test with: scenario_05_emotion

3. conversational.txt (Natural Speech)
   - Adds filler words: "Hmm", "Well...", "Let's see"
   - Uses natural pauses: "But... that's tricky"
   - Includes speech markers: "Right?", "You know?"
   - Best for human-like, natural conversation flow
   - Test with: scenario_06_conversational

Comparison Testing:
------------------
To compare strategies, run the same scenario with different prompts:

# Test baseline
python3 test/prompt_strategy/test_prompt_strategy.py \
  --strategy unified \
  --scenario scenario_06_conversational

# Test with natural speech markers
python3 test/prompt_strategy/test_prompt_strategy.py \
  --strategy conversational \
  --scenario scenario_06_conversational \
  --tts

# Test with emotions
python3 test/prompt_strategy/test_prompt_strategy.py \
  --strategy with_tts_emotion \
  --scenario scenario_05_emotion \
  --tts

Then compare the JSON files in outputs/ to see differences in:
- Response naturalness and flow
- Emotion usage appropriateness
- Speech marker placement
- Overall conversational quality

TTS Playback (Optional):
------------------------
The tool supports Fish Audio TTS playback for a more immersive testing experience.

Requirements:
- Fish Audio SDK: pip install fish-audio-sdk
- Fish Audio API key from https://fish.audio/

Setup:
1. Install Fish Audio SDK:
   pip install fish-audio-sdk

2. Set your API key:
   export FISH_API_KEY="your-fish-key"

3. (Optional) Set a custom voice:
   export FISH_REFERENCE_ID="your-voice-id"

4. Run with --tts flag:
   python3 test/prompt_strategy/test_prompt_strategy.py --strategy unified --scenario scenario_01_normal --tts

Notes:
- TTS audio files are saved to tmp/ directory (ignored by git)
- Audio playback uses 'afplay' on macOS
- If TTS fails, the test continues without audio playback

