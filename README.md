# 🌙 Bedtime Stories Automator

Automated YouTube channel for bedtime stories using AI.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup Environment
```bash
# Copy .env.example to .env (already done)
# Edit .env and add your Gemini API key
```

### 3. Run the App

#### Option A: Web GUI (Recommended)
```bash
streamlit run app.py
```
This opens a browser window with the interface.

#### Option B: Command Line
```bash
# Interactive mode
python main.py

# Direct creation
python main.py create "The Story of Prophet Yusuf" preschool 8

# Check status
python main.py status
```

## 📊 API Limits (Free Tier)

| Service | Daily Limit | Our Usage |
|---------|-------------|-----------|
| Gemini | 1,500 req | ~2/video |
| Pollinations | Unlimited | 15-20 images |
| Kokoro TTS | Unlimited | 10-12 segments |
| YouTube | 10,000 units | ~100/upload |

## 🎬 Video Creation Pipeline

1. **Script** → Gemini generates story + image prompts
2. **Images** → Pollinations generates storybook illustrations
3. **Voice** → Kokoro TTS generates male voiceover
4. **Video** → FFmpeg assembles with Ken Burns effect
5. **Shorts** → Extracts 3-5 vertical shorts

## 📁 Project Structure

```
youtube-automate/
├── app.py              # Web GUI (Streamlit)
├── main.py             # CLI interface
├── .env                # API keys
├── plan.md             # Full documentation
├── config/
│   ├── settings.yaml   # Configuration
│   └── topics.json     # 50 story topics
└── src/
    ├── script_generator.py
    ├── image_generator.py
    ├── voiceover_generator.py
    ├── video_assembler.py
    ├── shorts_creator.py
    └── usage_tracker.py
```

## 🎤 Voice Options

- **bf_sage** - Deep & Soothing (Male) - Default
- **am_adam** - Clear & Friendly (Male)
- **af_heart** - Warm & Calm (Female)

## 📱 Story Categories

- Islamic History
- Western History
- Motivational Stories
- Moral Stories
- Animal Fables
- Fairy Tales
- Prophet Stories
- Companion Stories

## ⚠️ Requirements

1. **Python 3.8+**
2. **FFmpeg** - Install from https://ffmpeg.org/download.html
3. **Gemini API Key** - Get from https://aistudio.google.com/apikey

## 🐛 Troubleshooting

### FFmpeg not found
```bash
# Windows (winget)
winget install FFmpeg

# Or download manually and add to PATH
```

### Gemini API errors
- Check your API key in `.env`
- Verify you haven't exceeded 1,500 daily requests
- Check https://aistudio.google.com for usage

### TTS not working
- Kokoro requires installation: `pip install kokoro`
- Fallback: TTS.ai API (5,000 chars/day free)

## 📝 License

MIT License - Free to use and modify.
