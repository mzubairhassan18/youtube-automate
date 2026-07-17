"""
Voiceover Generator - Edge TTS Integration
Generates male voiceover narration for bedtime stories using Microsoft Edge neural TTS.
"""

import os
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
from loguru import logger

# Edge TTS voice options for bedtime stories (male)
VOICE_OPTIONS = {
    "male_calm": "en-US-GuyNeural",
    "male_deep": "en-US-ChristopherNeural",
    "male_warm": "en-US-AndrewNeural",
    "male_british": "en-GB-RyanNeural",
    "female_calm": "en-US-AvaNeural",
}

DEFAULT_VOICE = "male_calm"

# FFmpeg paths
FFMPEG_DIRS = [
    r"C:\Users\hp\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin",
    r"C:\Users\hp\AppData\Local\Microsoft\WinGet\Links",
]


class VoiceoverGenerator:
    """Generates voiceover audio using Edge TTS (Microsoft Neural TTS)."""

    def __init__(
        self,
        voice: str = DEFAULT_VOICE,
        rate: str = "-15%",
        volume: str = "+0%",
        pitch: str = "-2Hz",
    ):
        self.voice_name = voice
        self.voice = VOICE_OPTIONS.get(voice, voice)
        self.rate = rate
        self.volume = volume
        self.pitch = pitch
        self.output_dir = Path("./output/audio")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Ensure FFmpeg is in PATH
        for d in FFMPEG_DIRS:
            if os.path.exists(d) and d not in os.environ.get("PATH", ""):
                os.environ["PATH"] = d + ";" + os.environ.get("PATH", "")

        logger.info(f"Using Edge TTS voice: {self.voice}")

    def generate_voiceover(
        self,
        segments: List[Dict[str, Any]],
        output_prefix: str = "story",
    ) -> List[str]:
        """Generate voiceover audio for all story segments."""
        audio_paths = []

        for i, segment in enumerate(segments):
            narration = segment.get("narration", "")
            segment_num = segment.get("segment_number", i + 1)
            output_path = self.output_dir / f"{output_prefix}_{segment_num:03d}.wav"

            success = self._generate_audio(narration, output_path)

            if success:
                audio_paths.append(str(output_path))
                logger.info(
                    f"Audio {segment_num}/{len(segments)}: {output_path.name}"
                )
            else:
                logger.error(f"Failed audio for segment {segment_num}")
                silent_path = self._create_silent_audio(
                    output_path, segment.get("duration_seconds", 30)
                )
                audio_paths.append(str(silent_path))

        return audio_paths

    def _generate_audio(self, text: str, output_path: Path) -> bool:
        """Generate audio using edge-tts, output as WAV for compatibility."""
        try:
            mp3_path = output_path.with_suffix(".mp3")
            asyncio.run(self._edge_tts_generate(text, str(mp3_path)))

            if not mp3_path.exists() or mp3_path.stat().st_size == 0:
                logger.error(f"Edge TTS produced empty/missing file: {mp3_path}")
                return False

            logger.debug(f"Edge TTS MP3 created: {mp3_path.stat().st_size} bytes")

            # Convert MP3 to WAV for universal compatibility
            if output_path.suffix == ".wav":
                result = subprocess.run(
                    [
                        "ffmpeg", "-y",
                        "-i", str(mp3_path),
                        "-ar", "44100",
                        "-ac", "1",
                        str(output_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode != 0:
                    logger.error(f"FFmpeg conversion failed: {result.stderr[-300:]}")
                    # Try to use the MP3 directly as fallback
                    import shutil
                    shutil.copy2(str(mp3_path), str(output_path.with_suffix(".mp3")))
                    return False

                mp3_path.unlink(missing_ok=True)

            return output_path.exists() and output_path.stat().st_size > 0

        except Exception as e:
            logger.error(f"Edge TTS failed: {e}")
            return False

    async def _edge_tts_generate(self, text: str, output_path: str):
        """Async edge-tts generation."""
        import edge_tts

        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=self.rate,
            volume=self.volume,
            pitch=self.pitch,
        )
        await communicate.save(output_path)

    def _create_silent_audio(self, output_path: Path, duration: int = 30) -> Path:
        """Create silent audio using FFmpeg as fallback."""
        try:
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"anullsrc=r=44100:cl=mono",
                "-t", str(duration),
                str(output_path),
            ]
            subprocess.run(cmd, capture_output=True, check=True, timeout=10)
            logger.info(f"Silent audio: {output_path.name} ({duration}s)")
            return output_path
        except Exception as e:
            logger.error(f"Failed to create silent audio: {e}")
            return output_path

    def cleanup_audio(self, prefix: str = "story"):
        """Remove generated audio files."""
        for ext in ("*.mp3", "*.wav"):
            for audio in self.output_dir.glob(f"{prefix}_{ext}"):
                audio.unlink()
        logger.info(f"Cleaned up audio with prefix: {prefix}")


def get_voiceover_generator(**kwargs) -> VoiceoverGenerator:
    return VoiceoverGenerator(**kwargs)
