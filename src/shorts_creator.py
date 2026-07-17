"""
Shorts Creator - Extract YouTube Shorts from main videos
Creates vertical (9:16) shorts from horizontal (16:9) bedtime story videos.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
from loguru import logger


class ShortsCreator:
    """Creates YouTube Shorts from main video content."""
    
    def __init__(
        self,
        short_width: int = 1080,
        short_height: int = 1920,
        min_duration: int = 15,
        max_duration: int = 60,
        shorts_per_video: int = 3,
    ):
        self.short_width = short_width
        self.short_height = short_height
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.shorts_per_video = shorts_per_video
        self.output_dir = Path("./output/shorts")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Ensure FFmpeg is in PATH
        for d in [
            r"C:\Users\hp\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin",
            r"C:\Users\hp\AppData\Local\Microsoft\WinGet\Links",
        ]:
            if os.path.exists(d) and d not in os.environ.get("PATH", ""):
                os.environ["PATH"] = d + ";" + os.environ.get("PATH", "")
    
    def create_shorts(
        self,
        video_path: str,
        script: Dict[str, Any],
        output_prefix: str = "short",
    ) -> List[str]:
        """
        Create YouTube Shorts from main video.
        
        Args:
            video_path: Path to main video
            script: Story script with segments info
            output_prefix: Prefix for output filenames
            
        Returns:
            List of created short video paths
        """
        shorts_paths = []
        
        try:
            # Get video duration
            duration = self._get_video_duration(video_path)
            if duration <= 0:
                logger.error("❌ Could not determine video duration")
                return []
            
            # Find good moments to extract
            moments = self._find_key_moments(script, duration)
            
            # Create shorts from each moment
            for i, moment in enumerate(moments[:self.shorts_per_video]):
                output_path = self.output_dir / f"{output_prefix}_{i+1:03d}.mp4"
                
                success = self._extract_short(
                    video_path=video_path,
                    start_time=moment["start"],
                    duration=moment["duration"],
                    output_path=output_path,
                    title=moment.get("title", f"Short {i+1}"),
                )
                
                if success:
                    shorts_paths.append(str(output_path))
                    logger.info(
                        f"📱 Created short {i+1}/{len(moments)}: "
                        f"{output_path.name} ({moment['duration']}s)"
                    )
                else:
                    logger.warning(f"⚠️ Failed to create short {i+1}")
            
            return shorts_paths
            
        except Exception as e:
            logger.error(f"❌ Failed to create shorts: {e}")
            return []
    
    def _find_key_moments(
        self, 
        script: Dict[str, Any], 
        total_duration: float
    ) -> List[Dict[str, Any]]:
        """
        Find key moments in the script to extract as shorts.
        
        Returns moments with start time, duration, and title.
        """
        moments = []
        segments = script.get("segments", [])
        
        if not segments:
            # No segments info, create random moments
            return self._create_random_moments(total_duration)
        
        # Strategy 1: Extract from beginning (hook)
        if segments:
            first_segment = segments[0]
            moments.append({
                "start": 0,
                "duration": min(self.max_duration, first_segment.get("duration_seconds", 30)),
                "title": "Opening Hook",
            })
        
        # Strategy 2: Extract from middle (key lesson)
        if len(segments) >= 3:
            mid_index = len(segments) // 2
            mid_segment = segments[mid_index]
            
            # Calculate start time from segments before
            start_time = sum(
                seg.get("duration_seconds", 30) 
                for seg in segments[:mid_index]
            )
            
            moments.append({
                "start": start_time,
                "duration": min(self.max_duration, mid_segment.get("duration_seconds", 30)),
                "title": "Key Moment",
            })
        
        # Strategy 3: Extract from end (climax/conclusion)
        if len(segments) >= 2:
            last_segment = segments[-1]
            
            start_time = sum(
                seg.get("duration_seconds", 30) 
                for seg in segments[:-1]
            )
            
            moments.append({
                "start": start_time,
                "duration": min(self.max_duration, last_segment.get("duration_seconds", 30)),
                "title": "Conclusion",
            })
        
        return moments
    
    def _create_random_moments(self, total_duration: float) -> List[Dict[str, Any]]:
        """Create evenly spaced moments when no script info available."""
        moments = []
        
        # Divide video into thirds
        segment_duration = total_duration / 3
        
        for i in range(self.shorts_per_video):
            start = i * segment_duration
            duration = min(self.max_duration, segment_duration)
            
            moments.append({
                "start": start,
                "duration": duration,
                "title": f"Moment {i+1}",
            })
        
        return moments
    
    def _extract_short(
        self,
        video_path: str,
        start_time: float,
        duration: float,
        output_path: Path,
        title: str,
    ) -> bool:
        """
        Extract and convert a segment to vertical short format.
        
        Args:
            video_path: Source video path
            start_time: Start time in seconds
            duration: Duration in seconds
            output_path: Output file path
            title: Short title (for metadata)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Build FFmpeg command for vertical video
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(start_time),
                "-i", video_path,
                "-t", str(duration),
                "-vf", (
                    f"crop=ih*9/16:ih,"  # Crop to 9:16 aspect
                    f"scale={self.short_width}:{self.short_height}:force_original_aspect_ratio=decrease,"
                    f"pad={self.short_width}:{self.short_height}:(ow-iw)/2:(oh-ih)/2"
                ),
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "192k",
                "-r", "30",
                "-movflags", "+faststart",
                str(output_path)
            ]
            
            # Execute FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ FFmpeg error creating short: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to create short: {e}")
            return False
    
    def _get_video_duration(self, video_path: str) -> float:
        """Get duration of video file in seconds."""
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            return float(result.stdout.strip())
            
        except Exception as e:
            logger.error(f"❌ Could not get video duration: {e}")
            return 0.0
    
    def create_thumbnail_for_short(
        self,
        video_path: str,
        timestamp: float = 0,
        output_path: Optional[Path] = None,
    ) -> Optional[str]:
        """
        Extract a frame from video for short thumbnail.
        
        Args:
            video_path: Source video path
            timestamp: Time to extract frame (seconds)
            output_path: Output path for thumbnail
            
        Returns:
            Path to thumbnail or None if failed
        """
        if output_path is None:
            output_path = self.output_dir / "thumbnail.jpg"
        
        try:
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(timestamp),
                "-i", video_path,
                "-vframes", "1",
                "-vf", f"scale={self.short_width}:{self.short_height}",
                "-q:v", "2",
                str(output_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info(f"📸 Extracted thumbnail: {output_path.name}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"❌ Failed to extract thumbnail: {e}")
            return None
    
    def get_created_shorts(self, prefix: str = "short") -> List[str]:
        """Get list of all created short videos."""
        shorts = sorted(self.output_dir.glob(f"{prefix}_*.mp4"))
        return [str(short) for short in shorts]
    
    def cleanup_shorts(self, prefix: str = "short"):
        """Remove created short videos."""
        for short in self.output_dir.glob(f"{prefix}_*.mp4"):
            short.unlink()
        logger.info(f"🗑️ Cleaned up shorts with prefix: {prefix}")


def get_shorts_creator(**kwargs) -> ShortsCreator:
    """Get or create shorts creator instance."""
    return ShortsCreator(**kwargs)
