"""
Image Generator - Pollinations.ai Integration
Generates high-quality story scene images for bedtime story videos.
"""

import os
import time
import requests
from pathlib import Path
from typing import Optional, List, Dict, Any
from loguru import logger
from urllib.parse import quote


# High-quality art style for children's storybook illustrations
ART_STYLE = (
    "masterpiece, best quality, highly detailed, "
    "beautiful children's storybook illustration, "
    "digital painting, vibrant colors, soft lighting, "
    "warm golden hour atmosphere, cinematic composition, "
    "sharp focus, professional art, no text, no watermark"
)

# Character consistency rules - appended to every prompt
CHARACTER_RULES = (
    "anatomically correct human proportions, "
    "properly formed hands with five fingers, "
    "natural facial features, "
    "consistent character design, "
    "clean linework, smooth shapes"
)

# Negative prompt to avoid common AI issues
NEGATIVE_PROMPT = (
    "text, words, letters, watermark, blurry, deformed, "
    "disfigured, bad anatomy, extra limbs, extra fingers, "
    "mutated hands, poorly drawn hands, poorly drawn face, "
    "mutation, ugly, duplicate, morbid, out of frame, "
    "low quality, worst quality, jpeg artifacts, "
    "dark, scary, violent, realistic photo, 3d render, "
    "split image, fragmented, broken, distorted"
)


class ImageGenerator:
    """Generates images using Pollinations.ai (free, unlimited)."""

    def __init__(
        self,
        style: str = ART_STYLE,
        negative_prompt: str = NEGATIVE_PROMPT,
        width: int = 1280,
        height: int = 720,
    ):
        self.style = style
        self.negative_prompt = negative_prompt
        self.width = width
        self.height = height
        self.output_dir = Path("./output/images")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 2.0  # seconds between requests

    def generate_images(
        self,
        prompts: List[Dict[str, Any]],
        output_prefix: str = "scene",
    ) -> List[str]:
        """Generate images for all story segments."""
        image_paths = []

        for i, segment in enumerate(prompts):
            prompt = segment.get("image_prompt", "")
            segment_num = segment.get("segment_number", i + 1)

            # Build high-quality prompt
            full_prompt = self._build_prompt(prompt)

            # Output path
            output_path = self.output_dir / f"{output_prefix}_{segment_num:03d}.png"

            # Generate with retries
            success = False
            for attempt in range(3):
                success = self._generate_with_pollinations(
                    prompt=full_prompt,
                    output_path=output_path,
                    seed=segment_num * 1000 + attempt,
                )
                if success:
                    # Verify image is valid (not too small = error page)
                    if output_path.exists() and output_path.stat().st_size > 10000:
                        break
                    else:
                        success = False
                        time.sleep(2)

            if success:
                image_paths.append(str(output_path))
                logger.info(
                    "Image %d/%d: %s (%dKB)",
                    segment_num, len(prompts), output_path.name,
                    output_path.stat().st_size // 1024,
                )
            else:
                logger.error("Failed image for segment %d", segment_num)
                placeholder = self._create_placeholder(output_path, segment_num)
                image_paths.append(str(placeholder))

        return image_paths

    def _build_prompt(self, base_prompt: str) -> str:
        """Build a high-quality prompt with style and character rules."""
        # Enhance the base prompt with character consistency and quality tags
        enhanced = (
            f"{base_prompt}, "
            f"{CHARACTER_RULES}, "
            f"{self.style}"
        )
        return enhanced

    def _generate_with_pollinations(
        self,
        prompt: str,
        output_path: Path,
        seed: Optional[int] = None,
    ) -> bool:
        """Generate image using Pollinations.ai."""
        try:
            self._wait_for_rate_limit()

            encoded_prompt = quote(prompt)

            params = {
                "model": "flux",
                "width": self.width,
                "height": self.height,
                "nologo": "true",
                "enhance": "true",
            }
            if seed is not None:
                params["seed"] = seed

            query = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?{query}"

            response = requests.get(url, timeout=90)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(response.content)

            self.last_request_time = time.time()
            return True

        except requests.Timeout:
            logger.error("Pollinations timeout")
            return False
        except requests.RequestException as e:
            logger.error("Pollinations failed: %s", e)
            return False

    def _create_placeholder(self, output_path: Path, segment_num: int) -> Path:
        """Create a gradient placeholder image."""
        try:
            from PIL import Image, ImageDraw, ImageFont

            img = Image.new("RGB", (self.width, self.height))
            draw = ImageDraw.Draw(img)

            for y in range(self.height):
                r = int(100 + (y / self.height) * 155)
                g = int(140 + (y / self.height) * 100)
                b = int(200 - (y / self.height) * 60)
                draw.line([(0, y), (self.width, y)], fill=(r, g, b))

            try:
                font = ImageFont.truetype("arial.ttf", 28)
            except Exception:
                font = ImageFont.load_default()

            text = "Scene %d" % segment_num
            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            draw.text(
                ((self.width - tw) // 2, (self.height - th) // 2),
                text, fill=(255, 255, 255), font=font,
            )

            img.save(output_path, quality=95)
            logger.info("Placeholder: %s", output_path.name)
            return output_path

        except Exception as e:
            logger.error("Placeholder failed: %s", e)
            return output_path

    def _wait_for_rate_limit(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)

    def cleanup_images(self, prefix: str = "scene"):
        for img in self.output_dir.glob(f"{prefix}_*.png"):
            img.unlink()
        logger.info("Cleaned images: %s", prefix)


def get_image_generator(**kwargs) -> ImageGenerator:
    return ImageGenerator(**kwargs)
