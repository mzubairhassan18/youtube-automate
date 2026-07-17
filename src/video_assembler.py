"""
Video Assembler - FFmpeg Pipeline
Combines images and audio into final video with transitions and effects.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
from loguru import logger


class VideoAssembler:
    """Assembles video from images and audio using FFmpeg."""
    
    def __init__(
        self,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        transition_duration: float = 1.5,
        ken_burns: bool = True,
    ):
        self.width = width
        self.height = height
        self.fps = fps
        self.transition_duration = transition_duration
        self.ken_burns = ken_burns
        self.output_dir = Path("./output/full_videos")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Check FFmpeg availability
        self.ffmpeg_available = self._check_ffmpeg()
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is installed and available."""
        # Ensure FFmpeg is in PATH
        ffmpeg_dirs = [
            r"C:\Users\hp\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin",
            r"C:\Users\hp\AppData\Local\Microsoft\WinGet\Links",
        ]
        for d in ffmpeg_dirs:
            if os.path.exists(d) and d not in os.environ.get("PATH", ""):
                os.environ["PATH"] = d + ";" + os.environ.get("PATH", "")

        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info("✅ FFmpeg is available")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error(
                "❌ FFmpeg not found. Please install FFmpeg: "
                "https://ffmpeg.org/download.html"
            )
            return False
    
    def assemble_video(
        self,
        image_paths: List[str],
        audio_paths: List[str],
        output_filename: str = "output.mp4",
        intro_path: Optional[str] = None,
        outro_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        Assemble final video from images and audio.
        
        Args:
            image_paths: List of image file paths
            audio_paths: List of audio file paths
            output_filename: Name of output video file
            intro_path: Optional intro video path
            outro_path: Optional outro video path
            
        Returns:
            Path to assembled video or None if failed
        """
        if not self.ffmpeg_available:
            logger.error("❌ Cannot assemble video: FFmpeg not available")
            return None
        
        if len(image_paths) != len(audio_paths):
            logger.error(
                f"❌ Mismatch: {len(image_paths)} images vs {len(audio_paths)} audio files"
            )
            return None
        
        output_path = self.output_dir / output_filename
        
        try:
            # Create individual segment videos
            segment_videos = []
            
            for i, (img_path, audio_path) in enumerate(zip(image_paths, audio_paths)):
                segment_path = self._create_segment_video(
                    img_path, audio_path, i + 1
                )
                if segment_path:
                    segment_videos.append(segment_path)
                else:
                    logger.warning(f"⚠️ Failed to create segment {i+1}, skipping")
            
            if not segment_videos:
                logger.error("❌ No segments were created successfully")
                return None
            
            # Concatenate all segments
            final_video = self._concatenate_segments(
                segment_videos, output_path
            )
            
            if final_video:
                # Clean up segment videos
                for seg in segment_videos:
                    try:
                        Path(seg).unlink()
                    except:
                        pass
                
                logger.info(f"🎬 Video assembled: {output_path}")
                return str(output_path)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Video assembly failed: {e}")
            return None
    
    def _create_segment_video(
        self,
        image_path: str,
        audio_path: str,
        segment_num: int,
    ) -> Optional[str]:
        """
        Create a video segment from one image and one audio file.
        
        Args:
            image_path: Path to image file
            audio_path: Path to audio file
            segment_num: Segment number for filename
            
        Returns:
            Path to segment video or None if failed
        """
        try:
            # Get audio duration
            duration = self._get_audio_duration(audio_path)
            if duration <= 0:
                duration = 30  # Default 30 seconds
            
            # Add padding for transitions
            total_duration = duration + self.transition_duration
            
            # Create segment video
            segment_path = f"./output/segment_{segment_num:03d}.mp4"
            
            # Build FFmpeg command
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", image_path,
                "-i", audio_path,
                "-c:v", "libx264",
                "-tune", "stillimage",
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-vf", f"scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2",
                "-t", str(total_duration),
                "-r", str(self.fps),
                segment_path
            ]
            
            # Add Ken Burns effect if enabled
            if self.ken_burns:
                cmd = self._add_ken_burns_effect(cmd, duration)
            
            # Execute FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.debug(f"📊 Segment {segment_num} created: {duration:.1f}s")
            return segment_path
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ FFmpeg error for segment {segment_num}: {e.stderr}")
            return None
        except Exception as e:
            logger.error(f"❌ Failed to create segment {segment_num}: {e}")
            return None
    
    def _add_ken_burns_effect(self, cmd: List[str], duration: float) -> List[str]:
        """
        Add Ken Burns (zoom/pan) effect to FFmpeg command.
        
        This creates a gentle zoom effect on still images.
        """
        # Ken Burns: slow zoom in
        zoom_duration = duration
        zoom_filter = (
            f"zoompan=z='min(zoom+0.0015,1.15)'"
            f":d={int(zoom_duration * self.fps)}"
            f":s={self.width}x{self.height}"
            f":fps={self.fps}"
        )
        
        # Insert zoom filter before scale
        cmd = cmd.copy()
        for i, arg in enumerate(cmd):
            if arg == "-vf":
                cmd[i + 1] = f"{zoom_filter},{cmd[i + 1]}"
                break
        
        return cmd
    
    def _concatenate_segments(
        self, 
        segment_videos: List[str], 
        output_path: Path
    ) -> Optional[str]:
        """
        Concatenate multiple video segments into one.
        
        Args:
            segment_videos: List of segment video paths
            output_path: Output file path
            
        Returns:
            Path to concatenated video or None if failed
        """
        try:
            # Create concat file in same dir as segments to use relative paths
            concat_file = "./output/concat_list.txt"
            with open(concat_file, "w") as f:
                for seg in segment_videos:
                    # Use just the filename since concat file is in the same dir
                    seg_name = os.path.basename(seg).replace("\\", "/")
                    f.write(f"file '{seg_name}'\n")
            
            # FFmpeg concat command
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "192k",
                str(output_path)
            ]
            
            # Execute
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Clean up concat file
            try:
                os.remove(concat_file)
            except:
                pass
            
            return str(output_path)
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ FFmpeg concat failed: {e.stderr}")
            return None
        except Exception as e:
            logger.error(f"❌ Concatenation failed: {e}")
            return None
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """
        Get duration of audio file in seconds.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Duration in seconds
        """
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            return float(result.stdout.strip())
            
        except Exception as e:
            logger.warning(f"⚠️ Could not get audio duration: {e}")
            return 0.0
    
    def add_subtitles(
        self,
        video_path: str,
        subtitles_path: str,
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        Add subtitles to video.
        
        Args:
            video_path: Path to input video
            subtitles_path: Path to SRT/ASS subtitles file
            output_path: Optional output path
            
        Returns:
            Path to video with subtitles or None if failed
        """
        if output_path is None:
            output_path = video_path.replace(".mp4", "_subtitled.mp4")
        
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-vf", f"subtitles={subtitles_path}",
                "-c:a", "copy",
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info(f"📝 Added subtitles: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Failed to add subtitles: {e}")
            return None
    
    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """
        Get information about a video file.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dictionary with video information
        """
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                video_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            import json
            info = json.loads(result.stdout)
            
            # Extract useful info
            duration = float(info.get("format", {}).get("duration", 0))
            size = int(info.get("format", {}).get("size", 0))
            
            # Get video stream info
            video_stream = None
            audio_stream = None
            for stream in info.get("streams", []):
                if stream.get("codec_type") == "video":
                    video_stream = stream
                elif stream.get("codec_type") == "audio":
                    audio_stream = stream
            
            return {
                "duration": duration,
                "size_mb": size / (1024 * 1024),
                "width": int(video_stream.get("width", 0)) if video_stream else 0,
                "height": int(video_stream.get("height", 0)) if video_stream else 0,
                "fps": eval(video_stream.get("r_frame_rate", "0/1")) if video_stream else 0,
                "codec": video_stream.get("codec_name", "unknown") if video_stream else "unknown",
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get video info: {e}")
            return {}


def get_video_assembler(**kwargs) -> VideoAssembler:
    """Get or create video assembler instance."""
    return VideoAssembler(**kwargs)
