"""
YouTube Automate - Main Orchestrator
Bedtime Stories Channel Automation
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.usage_tracker import UsageTracker
from src.script_generator import ScriptGenerator
from src.image_generator import ImageGenerator
from src.voiceover_generator import VoiceoverGenerator
from src.video_assembler import VideoAssembler
from src.shorts_creator import ShortsCreator


# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
    level="INFO"
)
logger.add(
    "./logs/app_{time:YYYY-MM-DD}.log",
    rotation="10 MB",
    retention="30 days",
    level="DEBUG"
)


class YouTubeAutomate:
    """Main orchestrator for bedtime stories automation."""
    
    def __init__(self):
        self.usage_tracker = UsageTracker()
        self.script_generator = ScriptGenerator()
        self.image_generator = ImageGenerator()
        self.voiceover_generator = VoiceoverGenerator()
        self.video_assembler = VideoAssembler()
        self.shorts_creator = ShortsCreator()
        
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from settings.yaml."""
        config_path = Path("./config/settings.yaml")
        
        if config_path.exists():
            try:
                import yaml
                with open(config_path, "r") as f:
                    return yaml.safe_load(f)
            except Exception as e:
                logger.warning(f"⚠️ Failed to load config: {e}")
        
        # Default config
        return {
            "video": {"fps": 30},
            "voice": {"voice": "bf_sage"},
        }
    
    def check_status(self):
        """Display current API usage status."""
        print(self.usage_tracker.get_status_display())
    
    def can_create_video(self) -> bool:
        """Check if we can create a new video."""
        can_create, reason = self.usage_tracker.can_create_video()
        
        if not can_create:
            print(f"\n❌ Cannot create video: {reason}")
            return False
        
        print(f"\n✅ Ready to create video!")
        return True
    
    def create_video(
        self,
        topic: str,
        age_group: str = "preschool",
        duration_minutes: int = 8,
        style: str = "calm",
    ) -> Optional[str]:
        """
        Create a complete bedtime story video.
        
        Args:
            topic: Story topic
            age_group: Target age group
            duration_minutes: Target duration
            style: Story style
            
        Returns:
            Path to created video or None if failed
        """
        start_time = time.time()
        
        print("\n" + "="*60)
        print(f"🎬 Creating Video: {topic}")
        print(f"   Age Group: {age_group}")
        print(f"   Duration: {duration_minutes} minutes")
        print("="*60)
        
        # Step 1: Generate Script
        print("\n📝 Step 1: Generating script...")
        script = self.script_generator.generate_script(
            topic=topic,
            age_group=age_group,
            duration_minutes=duration_minutes,
            style=style,
        )
        
        if not script:
            print("❌ Failed to generate script")
            return None
        
        print(f"   ✅ Script generated: {script.get('title', 'Untitled')}")
        print(f"   📊 Segments: {len(script.get('segments', []))}")
        
        # Step 2: Generate Images
        print("\n🎨 Step 2: Generating images...")
        segments = script.get("segments", [])
        
        image_paths = self.image_generator.generate_images(
            prompts=segments,
            output_prefix=f"story_{int(time.time())}",
        )
        
        if not image_paths:
            print("❌ Failed to generate images")
            return None
        
        print(f"   ✅ Generated {len(image_paths)} images")
        
        # Step 3: Generate Voiceover
        print("\n🎤 Step 3: Generating voiceover...")
        
        audio_paths = self.voiceover_generator.generate_voiceover(
            segments=segments,
            output_prefix=f"story_{int(time.time())}",
        )
        
        if not audio_paths:
            print("❌ Failed to generate voiceover")
            return None
        
        print(f"   ✅ Generated {len(audio_paths)} audio segments")
        
        # Step 4: Assemble Video
        print("\n🎬 Step 4: Assembling video...")
        
        # Create safe filename
        safe_topic = "".join(c if c.isalnum() else "_" for c in topic[:50])
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{safe_topic}_{timestamp}.mp4"
        
        video_path = self.video_assembler.assemble_video(
            image_paths=image_paths,
            audio_paths=audio_paths,
            output_filename=output_filename,
        )
        
        if not video_path:
            print("❌ Failed to assemble video")
            return None
        
        # Get video info
        video_info = self.video_assembler.get_video_info(video_path)
        duration = video_info.get("duration", 0)
        print(f"   ✅ Video assembled: {duration:.1f} seconds")
        
        # Step 5: Create Shorts
        print("\n📱 Step 5: Creating shorts...")
        
        shorts_paths = self.shorts_creator.create_shorts(
            video_path=video_path,
            script=script,
            output_prefix=f"short_{timestamp}",
        )
        
        print(f"   ✅ Created {len(shorts_paths)} shorts")
        
        # Record usage
        self.usage_tracker.record_video_created(len(shorts_paths))
        
        # Calculate time
        elapsed = time.time() - start_time
        print("\n" + "="*60)
        print(f"🎉 Video Creation Complete!")
        print(f"   ⏱️  Time: {elapsed:.1f} seconds")
        print(f"   📁 Video: {video_path}")
        print(f"   📱 Shorts: {len(shorts_paths)}")
        print("="*60)
        
        # Cleanup temporary files
        self.image_generator.cleanup_images()
        self.voiceover_generator.cleanup_audio()
        
        return video_path
    
    def create_video_from_script(self, script_path: str) -> Optional[str]:
        """Create video from an existing script file."""
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                script = json.load(f)
            
            topic = script.get("title", "Unknown Topic")
            return self.create_video(topic=topic, script=script)
            
        except Exception as e:
            logger.error(f"❌ Failed to load script: {e}")
            return None
    
    def run_interactive(self):
        """Run interactive mode for creating videos."""
        print("\n" + "="*60)
        print("🌙 YouTube Automate - Bedtime Stories")
        print("="*60)
        
        while True:
            self.check_status()
            
            print("\nOptions:")
            print("  [1] Create new video")
            print("  [2] Check API status")
            print("  [3] Exit")
            
            choice = input("\nEnter your choice (1-3): ").strip()
            
            if choice == "1":
                if not self.can_create_video():
                    continue
                
                # Get topic from user
                topic = input("\nEnter story topic: ").strip()
                if not topic:
                    print("❌ Topic cannot be empty")
                    continue
                
                # Get age group
                print("\nAge groups:")
                print("  1. Toddler (1-3 years)")
                print("  2. Preschool (3-5 years)")
                print("  3. School Age (5-8 years)")
                print("  4. Preteen (8-12 years)")
                
                age_choice = input("Select age group (1-4, default: 2): ").strip()
                age_groups = ["toddler", "preschool", "school_age", "preteen"]
                age_group = age_groups[int(age_choice) - 1] if age_choice in ["1","2","3","4"] else "preschool"
                
                # Get duration
                duration = input("Duration in minutes (default: 8): ").strip()
                duration = int(duration) if duration.isdigit() else 8
                
                # Create video
                self.create_video(
                    topic=topic,
                    age_group=age_group,
                    duration_minutes=duration,
                )
                
            elif choice == "2":
                self.check_status()
                input("\nPress Enter to continue...")
                
            elif choice == "3":
                print("\n👋 Goodbye!")
                break
                
            else:
                print("❌ Invalid choice")


def main():
    """Main entry point."""
    automator = YouTubeAutomate()
    
    if len(sys.argv) > 1:
        # Command line mode
        command = sys.argv[1]
        
        if command == "status":
            automator.check_status()
        
        elif command == "create":
            if len(sys.argv) < 3:
                print("Usage: python main.py create <topic> [age_group] [duration]")
                sys.exit(1)
            
            topic = sys.argv[2]
            age_group = sys.argv[3] if len(sys.argv) > 3 else "preschool"
            duration = int(sys.argv[4]) if len(sys.argv) > 4 else 8
            
            automator.create_video(topic, age_group, duration)
        
        elif command == "check":
            can, reason = automator.usage_tracker.can_create_video()
            print(f"Can create video: {can}")
            if not can:
                print(f"Reason: {reason}")
        
        else:
            print(f"Unknown command: {command}")
            print("Commands: status, create, check")
    
    else:
        # Interactive mode
        automator.run_interactive()


if __name__ == "__main__":
    main()
