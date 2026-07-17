"""
API Usage Tracker
Monitors and limits API calls to stay within free tier limits.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger


class UsageTracker:
    """Tracks API usage across all services and enforces limits."""
    
    def __init__(self, log_file: str = "./logs/usage.json"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.usage = self._load_usage()
        
        # Daily limits from settings
        self.limits = {
            "groq": {"daily": 14400, "warning": 0.8},  # 30 req/min free tier
            "gemini": {"daily": 1500, "warning": 0.8},
            "pollinations": {"daily": None, "rpm": 20},
            "youtube": {"daily": 10000, "warning": 0.8},
            "edge_tts": {"daily": None},  # Free, unlimited
            "ffmpeg": {"daily": None},
        }
    
    def _load_usage(self) -> Dict[str, Any]:
        """Load usage data from file."""
        if self.log_file.exists():
            try:
                with open(self.log_file, "r") as f:
                    data = json.load(f)
                    # Check if data is from today
                    if data.get("date") == datetime.now().strftime("%Y-%m-%d"):
                        return data
            except Exception as e:
                logger.error(f"Failed to load usage data: {e}")
        
        # Initialize new day
        return self._initialize_daily_usage()
    
    def _initialize_daily_usage(self) -> Dict[str, Any]:
        """Initialize usage for a new day."""
        usage = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "services": {
                "groq": {"calls": 0, "last_call": None},
                "gemini": {"calls": 0, "tokens": 0, "last_call": None},
                "pollinations": {"calls": 0, "last_call": None},
                "youtube": {"units": 0, "uploads": 0, "last_call": None},
                "edge_tts": {"calls": 0, "characters": 0, "last_call": None},
                "ffmpeg": {"calls": 0, "last_call": None},
            },
            "videos_created": 0,
            "shorts_created": 0,
        }
        self._save_usage(usage)
        return usage
    
    def _save_usage(self, usage: Optional[Dict] = None):
        """Save usage data to file."""
        if usage is None:
            usage = self.usage
        
        with open(self.log_file, "w") as f:
            json.dump(usage, f, indent=2)
    
    def can_use(self, service: str, amount: int = 1) -> bool:
        """
        Check if we can use a service without exceeding limits.
        
        Args:
            service: Service name (gemini, pollinations, youtube, etc.)
            amount: Number of calls/units to use
            
        Returns:
            True if usage is within limits, False otherwise
        """
        if service not in self.limits:
            logger.warning(f"Unknown service: {service}")
            return True
        
        limit_info = self.limits[service]
        daily_limit = limit_info.get("daily")
        
        # No limit (local services)
        if daily_limit is None:
            return True
        
        current_usage = self.usage["services"][service]
        
        # Get current count based on service type
        if service == "youtube":
            current_count = current_usage.get("units", 0)
        elif service == "kokoro":
            current_count = current_usage.get("characters", 0)
        else:
            current_count = current_usage.get("calls", 0)
        
        # Check if we'd exceed limit
        if current_count + amount > daily_limit:
            remaining = daily_limit - current_count
            logger.warning(
                f"⚠️ {service} limit reached! "
                f"Used: {current_count}/{daily_limit}, "
                f"Requested: {amount}, Remaining: {remaining}"
            )
            return False
        
        # Check warning threshold
        warning_threshold = limit_info.get("warning", 0.8)
        if current_count + amount > daily_limit * warning_threshold:
            usage_percent = ((current_count + amount) / daily_limit) * 100
            logger.warning(
                f"⚠️ {service} usage at {usage_percent:.1f}% - approaching limit!"
            )
        
        return True
    
    def record_usage(self, service: str, amount: int = 1, **kwargs):
        """
        Record API usage.
        
        Args:
            service: Service name
            amount: Number of calls/units used
            **kwargs: Additional data (tokens, characters, etc.)
        """
        if service not in self.usage["services"]:
            logger.warning(f"Unknown service: {service}")
            return
        
        now = datetime.now().isoformat()
        
        if service == "gemini":
            self.usage["services"][service]["calls"] += amount
            self.usage["services"][service]["tokens"] += kwargs.get("tokens", 0)
        elif service == "youtube":
            self.usage["services"][service]["units"] += amount
            if kwargs.get("upload"):
                self.usage["services"][service]["uploads"] += 1
        elif service == "kokoro":
            self.usage["services"][service]["calls"] += amount
            self.usage["services"][service]["characters"] += kwargs.get("characters", 0)
        else:
            self.usage["services"][service]["calls"] += amount
        
        self.usage["services"][service]["last_call"] = now
        self._save_usage()
        
        logger.debug(f"📊 Recorded {service} usage: +{amount}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current usage status for all services.
        
        Returns:
            Dictionary with usage status
        """
        status = {
            "date": self.usage["date"],
            "services": {},
            "videos_created": self.usage.get("videos_created", 0),
            "shorts_created": self.usage.get("shorts_created", 0),
        }
        
        for service, limit_info in self.limits.items():
            daily_limit = limit_info.get("daily")
            current = self.usage["services"].get(service, {})
            
            if service == "youtube":
                used = current.get("units", 0)
            elif service == "kokoro":
                used = current.get("characters", 0)
            else:
                used = current.get("calls", 0)
            
            if daily_limit is None:
                status["services"][service] = {
                    "used": used,
                    "limit": "unlimited",
                    "remaining": "unlimited",
                    "percent": 0,
                    "can_use": True,
                }
            else:
                remaining = max(0, daily_limit - used)
                percent = (used / daily_limit) * 100 if daily_limit > 0 else 0
                status["services"][service] = {
                    "used": used,
                    "limit": daily_limit,
                    "remaining": remaining,
                    "percent": round(percent, 1),
                    "can_use": remaining > 0,
                }
        
        return status
    
    def record_video_created(self, shorts_count: int = 0):
        """Record that a video was created."""
        self.usage["videos_created"] = self.usage.get("videos_created", 0) + 1
        self.usage["shorts_created"] = self.usage.get("shorts_created", 0) + shorts_count
        self._save_usage()
    
    def get_status_display(self) -> str:
        """
        Get a formatted status display for terminal output.
        
        Returns:
            Formatted string with usage status
        """
        status = self.get_status()
        
        lines = [
            "╔══════════════════════════════════════════════════════╗",
            "║           📊 API USAGE STATUS                       ║",
            "╠══════════════════════════════════════════════════════╣",
            f"║  Date: {status['date']:<43}║",
            f"║  Videos Created Today: {status['videos_created']:<30}║",
            f"║  Shorts Created Today: {status['shorts_created']:<30}║",
            "╠══════════════════════════════════════════════════════╣",
        ]
        
        for service, info in status["services"].items():
            if info["limit"] == "unlimited":
                lines.append(f"║  {service.upper():<12} ✅ {info['used']:>6} / unlimited         ║")
            else:
                emoji = "✅" if info["can_use"] else "❌"
                lines.append(
                    f"║  {service.upper():<12} {emoji} {info['used']:>6} / {info['limit']:<6} ({info['percent']}%)     ║"
                )
        
        lines.extend([
            "╠══════════════════════════════════════════════════════╣",
            "║  [r] Refresh  [q] Quit  [c] Create Video            ║",
            "╚══════════════════════════════════════════════════════╝",
        ])
        
        return "\n".join(lines)
    
    def can_create_video(self) -> tuple[bool, str]:
        """
        Check if we have enough API quota to create a video.
        
        Returns:
            Tuple of (can_create, reason)
        """
        # Check Gemini (needs ~2 calls for script)
        if not self.can_use("gemini", 2):
            return False, "Gemini API limit reached. Try again tomorrow."
        
        # YouTube upload check
        if not self.can_use("youtube", 100):
            return False, "YouTube API limit reached. Try again tomorrow."
        
        return True, "All APIs have sufficient quota."


def get_usage_tracker() -> UsageTracker:
    """Get or create usage tracker instance."""
    return UsageTracker()
