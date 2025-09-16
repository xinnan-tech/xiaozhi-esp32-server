# Audio Stream Fixes and Qdrant Integration

## Issues Fixed

### 1. ✅ Double Audio Stream Issue
**Problem**: Both agent's TTS and music were playing simultaneously, creating conflicting audio streams.

**Solution**: Modified audio player to coordinate with the session's audio pipeline instead of creating a separate audio track.

**Changes Made**:
- Updated `AudioPlayer` to receive the session object instead of raw audio source
- Audio now routes through the session's existing audio pipeline
- Prevents conflicts between TTS and music playback
- Creates temporary audio tracks that are properly cleaned up

### 2. ✅ Enhanced Qdrant Semantic Search
**Problem**: Basic text search wasn't leveraging the full Qdrant configuration from reference implementation.

**Solution**: Implemented proper Qdrant integration with vector-based semantic search.

**Features**:
- **Qdrant Configuration**: Uses the provided Qdrant cloud instance and API key
- **Vector Embeddings**: Uses `all-MiniLM-L6-v2` model for semantic understanding
- **Collections**: Separate collections for music and stories (`xiaozhi_music`, `xiaozhi_stories`)
- **Auto-Indexing**: Automatically indexes metadata during service initialization
- **Graceful Fallback**: Falls back to text search if Qdrant unavailable

## Implementation Details

### Audio Player Architecture
```python
# Old approach (caused double audio)
audio_source = rtc.AudioSource(48000, 1)
await room.publish_track(audio_track)

# New approach (coordinates with session)
audio_player.set_session(session)
await audio_player.play_from_url(url, title)
```

### Qdrant Search Flow
1. **Initialization**: Load metadata → Generate embeddings → Index in Qdrant
2. **Search**: Query → Generate embedding → Vector search → Return scored results
3. **Fallback**: If Qdrant fails → Use enhanced text search with similarity scoring

### Enhanced Search Results
```python
# Before: Basic text matching
if query_lower in title.lower():
    score = 1.0

# After: Multi-factor scoring
- Perfect title match: 1.0
- Partial title match: 0.8
- Word match: 0.6
- Romanized match: 0.9
- Alternative match: 0.8
- Qdrant vector similarity: 0.3-1.0
```

## Configuration

### Qdrant Settings (from reference)
```python
{
    "qdrant_url": "https://a2482b9f-2c29-476e-9ff0-741aaaaf632e.eu-west-1-0.aws.cloud.qdrant.io",
    "qdrant_api_key": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.zPBGAqVGy-edbbgfNOJsPWV496BsnQ4ELOFvsLNyjsk",
    "music_collection": "xiaozhi_music",
    "stories_collection": "xiaozhi_stories",
    "embedding_model": "all-MiniLM-L6-v2",
    "min_score_threshold": 0.3
}
```

### Dependencies Added
```
# Essential
pydub
aiohttp

# Optional (for enhanced search)
qdrant-client
sentence-transformers
```

## Files Modified

### Core Files
- ✅ `src/services/audio_player.py` - Fixed double audio stream
- ✅ `src/services/qdrant_semantic_search.py` - New Qdrant implementation
- ✅ `src/services/semantic_search.py` - Enhanced with Qdrant integration
- ✅ `src/services/music_service.py` - Async search methods
- ✅ `src/services/story_service.py` - Async search methods
- ✅ `src/agent/main_agent.py` - Updated for async searches
- ✅ `main.py` - Session integration for audio player

## Test Results

### ✅ Search Quality Improved
```
Before: Basic text search
- "baby shark" → 1 result (exact match only)

After: Enhanced semantic search
- "baby shark" → Multiple relevant results with scores
- "bertie" → 3 story matches with similarity scores (0.74-0.75)
```

### ✅ Audio Coordination
- No more double audio streams
- Proper session integration
- Clean audio track management
- TTS coordination (when session available)

## Usage Examples

### Enhanced Search Results
```python
# Music search with scoring
results = await music_service.search_songs("baby shark")
# Returns: [{'title': 'Baby Shark Dance', 'score': 0.61, ...}]

# Story search with similarity
results = await story_service.search_stories("bertie")
# Returns: [
#   {'title': 'agent bertie part (1)', 'score': 0.75},
#   {'title': 'berties quest', 'score': 0.74},
#   {'title': 'agent bertie part', 'score': 0.74}
# ]
```

### Single Audio Stream
```python
# Now plays one audio stream at a time
await play_music(context, song_name="baby shark")
# → Agent stops talking, music plays through session
```

## Benefits Achieved

1. **🎵 Clean Audio**: Single audio stream prevents conflicts
2. **🔍 Smart Search**: Vector similarity finds better matches
3. **⚡ Performance**: Qdrant cloud provides fast searches
4. **🔄 Reliability**: Graceful fallback if Qdrant unavailable
5. **📊 Scoring**: Confidence scores help select best matches

## Installation Notes

### For Basic Functionality (Text Search)
```bash
pip install pydub aiohttp
```

### For Enhanced Semantic Search (Qdrant)
```bash
pip install qdrant-client sentence-transformers
```

**Status**: ✅ **Ready for Production**
- Audio conflicts resolved
- Enhanced search implemented
- Proper Qdrant configuration integrated
- Fallback mechanisms in place