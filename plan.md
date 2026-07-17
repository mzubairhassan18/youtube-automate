# YouTube Automate - Bedtime Stories Channel

## 🎯 Project Overview

Automated YouTube channel generating daily bedtime stories videos for children and families. Stories from Islamic history, Western history, motivational tales, and moral stories. Target: 8-15 minute videos with voiceover, images, and auto-generated shorts.

---

## 📋 API Keys Required

### 1. Google Gemini API (Script Generation)
- **Website:** https://aistudio.google.com/apikey
- **Free Tier:** 1,500 requests/day (Gemini 2.5 Flash)
- **Purpose:** Generate story scripts, image prompts, video descriptions
- **Cost:** $0 (no credit card required)

### 2. Pollinations.ai (Image Generation)
- **Website:** https://pollinations.ai
- **Free Tier:** Unlimited (rate-limited, no API key needed)
- **Purpose:** Generate story scene images
- **Cost:** $0

### 3. Kokoro TTS (Voice Over)
- **Website:** https://huggingface.co/hexgrad/Kokoro-82M
- **Free Tier:** Open source, Apache 2.0 license
- **Purpose:** Male voice narration for bedtime stories
- **Cost:** $0 (runs locally on CPU/GPU)
- **Alternative:** TTS.ai API (5,000 chars/day free)

### 4. YouTube Data API v3 (Upload)
- **Website:** https://console.cloud.google.com
- **Free Tier:** 10,000 units/day
- **Purpose:** Upload videos, manage playlists
- **Cost:** $0

### 5. FFmpeg (Video Processing)
- **Website:** https://ffmpeg.org
- **Free Tier:** Open source
- **Purpose:** Combine images + audio, add transitions, subtitles
- **Cost:** $0
- **GPU:** Use NVENC for fast encoding

---

## 🏗️ Project Structure

```
youtube-automate/
├── plan.md                    # This file - project documentation
├── .env.example               # API keys template
├── requirements.txt           # Python dependencies
├── main.py                    # Main orchestrator
├── config/
│   ├── settings.yaml          # App configuration
│   └── topics.json            # Story topics queue
├── src/
│   ├── __init__.py
│   ├── script_generator.py    # Gemini story script generation
│   ├── image_generator.py     # Pollinations/SDXL image generation
│   ├── voiceover_generator.py # Kokoro TTS voiceover
│   ├── video_assembler.py     # FFmpeg video composition
│   ├── shorts_creator.py      # Extract YouTube Shorts
│   ├── youtube_uploader.py    # YouTube API upload
│   ├── usage_tracker.py       # API usage monitoring
│   └── utils.py               # Helper functions
├── templates/
│   ├── intro.mp4              # Video intro template
│   ├── outro.mp4              # Video outro template
│   └── subtitles/             # Subtitle font styles
├── output/
│   ├── full_videos/           # Complete 8-15 min videos
│   ├── shorts/                # 15-60 sec shorts
│   ├── thumbnails/            # Auto-generated thumbnails
│   ├── audio/                 # Voiceover segments
│   └── scripts/               # Generated scripts (JSON)
└── logs/
    └── usage.log              # API usage tracking
```

---

## 🎬 Video Generation Pipeline

### Step 1: Script Generation (Gemini)
```
Input: Topic + Age Group + Duration
Output: JSON with segments, each containing:
  - narration_text (30-60 seconds)
  - image_prompt (for scene generation)
  - mood (calm, exciting, reflective)
  - duration_seconds
```

### Step 2: Image Generation (Pollinations)
```
Input: Image prompts from script
Output: 1024x576 (16:9) images for each segment
Style: Dreamy, soft, storybook illustration
Effects: Ken Burns (zoom/pan) in video
```

### Step 3: Voiceover Generation (Kokoro)
```
Input: Narration text segments
Output: WAV audio files (48kHz)
Voice: Male, calm, soothing (bedtime style)
Segments: 30-60 seconds each
```

### Step 4: Video Assembly (FFmpeg)
```
Input: Images + Audio + Transitions
Output: Complete MP4 video
Features:
  - Smooth crossfade transitions (1.5s)
  - Ken Burns effect on images
  - Soft background music (optional)
  - Subtitles overlay
  - Intro + Outro
```

### Step 5: Shorts Extraction
```
Input: Full video
Output: 3-5 shorts (15-60 seconds)
Selection: Best hooks, key moments, cliffhangers
```

---

## 📊 API Usage Limits & Tracking

### Free Tier Limits

| Service | Daily Limit | Our Usage/Video | Videos/Day | Status |
|---------|-------------|-----------------|------------|--------|
| Gemini Flash | 1,500 req | 1-2 requests | 750+ | ✅ Safe |
| Pollinations | Unlimited | 15-20 images | Unlimited | ✅ Safe |
| Kokoro TTS | Unlimited | 8-12 segments | Unlimited | ✅ Safe |
| YouTube API | 10,000 units | 100 units | 100 videos | ✅ Safe |
| FFmpeg | Unlimited | 1 render | Unlimited | ✅ Safe |

### Usage Tracker Implementation
- File: `src/usage_tracker.py`
- Tracks: Daily requests per service
- Warns: When approaching 80% of limit
- Blocks: When limit reached (shows wait time)
- Log: `logs/usage.log`

---

## 🎨 Story Categories & Topics

### Islamic Stories
1. Prophet Muhammad (PBUH) - bedtime stories for kids
2. Stories of the Prophets (AS)
3. Companions of the Prophet (RA)
4. Islamic Golden Age scientists
5. Stories from Quran (simplified for children)

### Western/Historical Stories
1. Greek myths (simplified for kids)
2. Famous inventors and discoveries
3. Historical heroes and heroines
4. Animal fables (Aesop, etc.)
5. Classic fairy tales (Cinderella, etc.)

### Motivational Stories
1. Never give up stories
2. Kindness and generosity tales
3. Friendship stories
4. Courage and bravery tales
5. Learning from mistakes

### Age Groups
- **Toddlers (1-3):** Very simple, 3-5 minutes
- **Preschool (3-5):** Simple morals, 5-8 minutes
- **School Age (5-8):** Detailed stories, 8-12 minutes
- **Pre-Teen (8-12):** Complex narratives, 10-15 minutes

---

## 🛠️ Tech Stack

```
Language:      Python 3.11+
AI:            google-generativeai (Gemini)
Images:        requests + Pollinations API
TTS:           kokoro (local) / requests (API)
Video:         ffmpeg-python, moviepy, pillow
YouTube:       google-api-python-client, google-auth-oauthlib
Config:        python-dotenv, pyyaml
Logging:       loguru, rich
Scheduler:     schedule, APScheduler (optional)
```

---

## 🚀 Implementation Phases

### Phase 1: Core Pipeline (Current)
- [x] Project structure
- [x] Plan documentation
- [ ] Config files
- [ ] Script generator (Gemini)
- [ ] Image generator (Pollinations)
- [ ] Voiceover generator (Kokoro)
- [ ] Video assembler (FFmpeg)
- [ ] Usage tracker

### Phase 2: YouTube Integration
- [ ] YouTube OAuth setup
- [ ] Auto-upload functionality
- [ ] Thumbnail generator
- [ ] Shorts extractor

### Phase 3: Automation
- [ ] Daily scheduler
- [ ] Topic queue management
- [ ] Error handling & retry
- [ ] Dashboard/status page

### Phase 4: Optimization
- [ ] GPU acceleration
- [ ] Batch processing
- [ ] Quality presets
- [ ] Analytics tracking

---

## 📝 Script Generation Prompt Template

```python
SYSTEM_PROMPT = """
You are a master storyteller creating bedtime stories for children.
Generate a complete story script with the following structure:

TOPIC: {topic}
AGE GROUP: {age_group}
DURATION: {duration} minutes
STYLE: {style} (calm, adventurous, moral, educational)

OUTPUT FORMAT (JSON):
{
  "title": "Story title",
  "description": "YouTube description (SEO optimized)",
  "tags": ["tag1", "tag2", ...],
  "thumbnail_prompt": "Image prompt for thumbnail",
  "segments": [
    {
      "segment_number": 1,
      "narration": "Voiceover text (30-60 seconds of speech)",
      "image_prompt": "Detailed image prompt for this scene",
      "mood": "calm|exciting|reflective",
      "duration_seconds": 45
    },
    ...
  ],
  "moral": "The moral of the story",
  "age_appropriateness": "Why this is suitable for {age_group}"
}

RULES:
1. Each narration segment should be 30-60 seconds when read aloud
2. Use simple, engaging language appropriate for {age_group}
3. Include sensory details (sounds, smells, feelings)
4. End with a calming conclusion suitable for bedtime
5. Image prompts should be detailed and consistent in style
6. Total duration should be close to {duration} minutes
"""
```

---

## 🎨 Image Style Guide

### Consistent Art Style
```
Style: "Soft watercolor storybook illustration, warm tones, 
gentle lighting, dreamy atmosphere, children's book art style, 
no text, cinematic composition, 16:9 aspect ratio"
```

### Prompt Template for Each Scene
```
{scene_description}, soft watercolor storybook illustration, 
warm golden lighting, dreamy atmosphere, gentle colors, 
children's book art style, no text, cinematic, 16:9
```

---

## 🎤 Voice Configuration

### Kokoro TTS Settings
```python
VOICE_CONFIG = {
    "voice": "af_heart",      # Male voice (warm, calm)
    "speed": 0.85,            # Slightly slower for bedtime
    "pitch": -2,              # Slightly deeper
    "format": "wav",
    "sample_rate": 48000
}
```

### Alternative Male Voices
- `af_heart` - Warm and calming
- `bf_sage` - Deep and soothing  
- `cf_bella` - Gentle (if female acceptable)

---

## 📈 Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Videos/Day | 1 | 0 |
| Avg. Duration | 8-12 min | - |
| Shorts/Video | 3-5 | 0 |
| Daily API Calls | <500 | 0 |
| Video Quality | 1080p | - |
| Upload Time | <1 hour | - |

---

## 🔧 Environment Variables (.env)

```bash
# Google Gemini
GEMINI_API_KEY=your_gemini_api_key_here

# YouTube (OAuth)
YOUTUBE_CLIENT_ID=your_client_id
YOUTUBE_CLIENT_SECRET=your_client_secret

# Optional: Alternative TTS
TTS_API_KEY=your_tts_api_key_here

# Settings
DEFAULT_AGE_GROUP=preschool
DEFAULT_DURATION=10
DEFAULT_VOICE=af_heart
```

---

## ⚠️ Important Notes

1. **API Limits:** Usage tracker MUST check limits before each API call
2. **Fallback:** If Gemini fails, use cached/template scripts
3. **Quality:** All images must be 1024x576 minimum (16:9)
4. **Audio:** Voiceover must be clear, no background noise
5. **Copyright:** All content must be original or public domain
6. **YouTube TOS:** Follow YouTube's automated content policies

---

## 📚 References

- [Gemini API Docs](https://ai.google.dev/docs)
- [Pollinations.ai](https://pollinations.ai)
- [Kokoro TTS](https://huggingface.co/hexgrad/Kokoro-82M)
- [FFmpeg Wiki](https://trac.ffmpeg.org)
- [YouTube API](https://developers.google.com/youtube)

---

*Last Updated: 2026-07-17*
*Status: Phase 1 - In Progress*
