"""
YouTube Uploader - OAuth 2.0 with YouTube Data API v3
Handles authentication, video upload, thumbnails, and metadata.
Channel: Dreamland Narrations (@DreamlandNarrations)
"""

import os
import json
import time
import pickle
from pathlib import Path
from typing import Optional, Dict, Any, List
from loguru import logger

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# Scopes needed for YouTube upload
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# Paths
CONFIG_DIR = Path(__file__).parent.parent / "config"
CLIENT_SECRET_PATH = CONFIG_DIR / "client_secret.json"
TOKEN_PATH = Path(__file__).parent.parent / "token.json"

# Channel info
CHANNEL_NAME = "Dreamland Narrations"
CHANNEL_HANDLE = "@DreamlandNarrations"

# YouTube category for kids content
CATEGORY_ID = "22"  # People & Blogs (best for kids stories)

# Default metadata
DEFAULT_TAGS = [
    "bedtime story", "kids story", "children story", "sleep story",
    "bedtime stories for kids", "story for kids", "read aloud",
    "fairy tale", "moral story", "Islamic story", "children bedtime",
    "kids bedtime story", "animated story", "story time",
    "toddler story", "preschool story", "bedtime tales",
    "sleep stories for children", "relaxing story", "dreamland narrations",
]

DEFAULT_DESCRIPTION_TEMPLATE = """
{description}

About this story:
{moral}

Channel: Dreamland Narrations
Subscribe for daily bedtime stories for kids!

#bedtimestory #kidsstory #childrenstory #sleepstory #dreamlandnarrations #storytime #fairy tale #moralstory
""".strip()


class YouTubeUploader:
    """Handles YouTube OAuth and video uploads."""

    def __init__(self):
        self.youtube = None
        self._authenticated = False

    def authenticate(self) -> bool:
        """Authenticate with YouTube via OAuth 2.0. Opens browser for first-time auth."""
        try:
            creds = None

            # Load existing token
            if TOKEN_PATH.exists():
                creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

            # If no valid credentials, do OAuth flow
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    logger.info("Refreshing expired YouTube token...")
                    creds.refresh(Request())
                else:
                    if not CLIENT_SECRET_PATH.exists():
                        logger.error("client_secret.json not found at %s", CLIENT_SECRET_PATH)
                        return False

                    logger.info("Opening browser for YouTube OAuth...")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(CLIENT_SECRET_PATH), SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                # Save token for next time
                with open(TOKEN_PATH, "w") as f:
                    f.write(creds.to_json())
                logger.info("YouTube token saved to %s", TOKEN_PATH)

            self.youtube = build("youtube", "v3", credentials=creds)
            self._authenticated = True
            logger.info("YouTube authenticated successfully")
            return True

        except Exception as e:
            logger.error("YouTube authentication failed: %s", e)
            return False

    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        category_id: str = CATEGORY_ID,
        privacy_status: str = "private",
        thumbnail_path: Optional[str] = None,
        made_for_kids: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Upload a video to YouTube with full metadata.

        Args:
            video_path: Path to the video file
            title: Video title
            description: Video description
            tags: List of tags/keywords
            category_id: YouTube category ID (22 = People & Blogs)
            privacy_status: "private", "unlisted", or "public"
            thumbnail_path: Path to thumbnail image (optional)
            made_for_kids: COPPA compliance flag

        Returns:
            Dict with video_id, url, etc. or None on failure
        """
        if not self._authenticated:
            if not self.authenticate():
                return None

        if not os.path.exists(video_path):
            logger.error("Video file not found: %s", video_path)
            return None

        # Build metadata
        if tags is None:
            tags = DEFAULT_TAGS

        body = {
            "snippet": {
                "title": title[:100],  # YouTube max 100 chars
                "description": description[:5000],  # YouTube max 5000 chars
                "tags": tags[:30],  # YouTube max 30 tags
                "categoryId": category_id,
                "defaultLanguage": "en",
                "defaultAudioLanguage": "en",
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": made_for_kids,
                "embeddable": True,
                "publicStatsViewable": True,
            },
        }

        file_size = os.path.getsize(video_path)
        logger.info(
            "Uploading '%s' (%.1f MB) as '%s'...",
            Path(video_path).name,
            file_size / 1024 / 1024,
            privacy_status,
        )

        try:
            media = MediaFileUpload(
                video_path,
                mimetype="video/mp4",
                resumable=True,
                chunksize=10 * 1024 * 1024,  # 10MB chunks
            )

            request = self.youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )

            # Upload with progress
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    pct = int(status.progress() * 100)
                    logger.info("Upload progress: %d%%", pct)

            video_id = response["id"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            logger.info("Video uploaded: %s", video_url)

            # Set thumbnail if provided
            thumbnail_set = False
            if thumbnail_path and os.path.exists(thumbnail_path):
                thumbnail_set = self._set_thumbnail(video_id, thumbnail_path)

            return {
                "video_id": video_id,
                "url": video_url,
                "title": title,
                "privacy": privacy_status,
                "thumbnail_set": thumbnail_set,
            }

        except HttpError as e:
            logger.error("YouTube upload failed: %s", e)
            return None
        except Exception as e:
            logger.error("Upload error: %s", e)
            return None

    def _set_thumbnail(self, video_id: str, thumbnail_path: str) -> bool:
        """Set a custom thumbnail for a video."""
        try:
            self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path, mimetype="image/jpeg"),
            ).execute()
            logger.info("Thumbnail set for video %s", video_id)
            return True
        except HttpError as e:
            logger.warning("Thumbnail upload failed: %s", e)
            return False

    def update_video_metadata(
        self,
        video_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """Update metadata for an existing video."""
        if not self._authenticated:
            if not self.authenticate():
                return False

        try:
            # Get current video details
            video_response = self.youtube.videos().list(
                part="snippet", id=video_id
            ).execute()

            if not video_response["items"]:
                logger.error("Video not found: %s", video_id)
                return False

            snippet = video_response["items"][0]["snippet"]
            if title:
                snippet["title"] = title[:100]
            if description:
                snippet["description"] = description[:5000]
            if tags:
                snippet["tags"] = tags[:30]

            self.youtube.videos().update(
                part="snippet", body={"id": video_id, "snippet": snippet}
            ).execute()

            logger.info("Video metadata updated: %s", video_id)
            return True

        except HttpError as e:
            logger.error("Update failed: %s", e)
            return False

    def build_metadata_from_script(
        self, script: Dict[str, Any], privacy: str = "private"
    ) -> Dict[str, Any]:
        """Build upload metadata from a story script."""
        title = script.get("title", "Bedtime Story")
        description = script.get("description", "")
        tags = script.get("tags", [])
        moral = script.get("moral", "")

        # Ensure channel branding in description
        full_description = DEFAULT_DESCRIPTION_TEMPLATE.format(
            description=description,
            moral=moral,
        )

        # Merge tags
        all_tags = list(set(tags + DEFAULT_TAGS))[:30]

        return {
            "title": title,
            "description": full_description,
            "tags": all_tags,
            "privacy_status": privacy,
            "category_id": CATEGORY_ID,
            "made_for_kids": True,
        }

    def get_channel_info(self) -> Optional[Dict[str, Any]]:
        """Get info about the authenticated channel."""
        if not self._authenticated:
            if not self.authenticate():
                return None

        try:
            response = self.youtube.channels().list(
                part="snippet,statistics,contentDetails",
                mine=True,
            ).execute()

            if response["items"]:
                channel = response["items"][0]
                return {
                    "id": channel["id"],
                    "title": channel["snippet"]["title"],
                    "description": channel["snippet"].get("description", ""),
                    "subscribers": channel["statistics"].get("subscriberCount", "0"),
                    "videos": channel["statistics"].get("videoCount", "0"),
                }
            return None

        except HttpError as e:
            logger.error("Failed to get channel info: %s", e)
            return None
