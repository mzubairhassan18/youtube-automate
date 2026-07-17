"""
Script Generator - Google Gemini Integration
Generates bedtime story scripts with image prompts for video creation.
Uses google-genai (new package) instead of deprecated google-generativeai.
"""

import json
import os
import random
from pathlib import Path
from typing import Optional, Dict, Any, List
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


# System prompt for bedtime story generation
SYSTEM_PROMPT = """You are a master storyteller creating bedtime stories for children.
Generate a complete story script with the following structure:

TOPIC: {topic}
AGE GROUP: {age_group}
DURATION: {duration} minutes
STYLE: {style} (calm, adventurous, moral, educational)

OUTPUT FORMAT (JSON only, no markdown):
{{
  "title": "Story title (compelling, SEO-friendly)",
  "description": "YouTube description (2-3 sentences, include keywords)",
  "tags": ["tag1", "tag2", ...],
  "thumbnail_prompt": "Detailed image prompt for the video thumbnail",
  "segments": [
    {{
      "segment_number": 1,
      "narration": "Voiceover text (30-60 seconds of speech when read aloud)",
      "image_prompt": "Detailed illustration prompt for this scene",
      "mood": "calm|exciting|reflective",
      "duration_seconds": 45
    }}
  ],
  "moral": "The moral of the story (1 sentence)",
  "age_appropriateness": "Why this is suitable for {age_group}"
}}

RULES:
1. Each narration segment should be 30-60 seconds when read aloud at a calm pace
2. Use simple, engaging language appropriate for {age_group}
3. Include sensory details (sounds, smells, feelings)
4. End with a calming conclusion suitable for bedtime
5. Total duration should be close to {duration} minutes
6. Use warm, comforting language
7. Include a clear beginning, middle, and end
8. Make sure the story has a positive message
9. Return ONLY valid JSON, no code blocks or extra text

CRITICAL IMAGE PROMPT RULES (very important):
- Every image_prompt MUST describe people with: "a young boy/girl with neatly combed dark brown hair, round curious eyes, warm brown skin, wearing a simple cream-colored tunic, happy gentle smile, natural human proportions with properly formed hands"
- ALWAYS include the full character description in EVERY segment prompt - do NOT skip it
- Describe the environment in detail: lighting, colors, weather, time of day
- Mention camera angle: "wide shot", "close-up portrait", "medium shot"
- Add quality tags: "beautiful illustration, sharp details, vibrant but soft colors, storybook art"
- NEVER use prompts that could cause distorted faces or broken anatomy
- Describe 1-2 characters maximum per scene for best quality
- Example good prompt: "A wide shot of a young boy with neatly combed dark brown hair, round curious eyes, warm brown skin, wearing a simple cream-colored tunic, standing in a sunlit green meadow with wildflowers, soft golden sunset light, butterflies nearby, beautiful children's storybook illustration, sharp details, vibrant soft colors"
"""


# Rich fallback templates for when Gemini is unavailable
FALLBACK_STORIES = {
    "islamic_history": {
        "intros": [
            "In the blessed city of Makkah, many years ago, there lived a person whose heart shone brighter than the morning sun.",
            "Long, long ago, in a land of golden sands and endless skies, a wonderful story began to unfold.",
            "Every night, when the stars filled the sky like scattered diamonds, wise people would gather to hear tales of faith and courage.",
        ],
        "middles": [
            "And so, with patience and faith, the story continued to unfold like a beautiful flower opening to the morning sun.",
            "Through every challenge and every moment of difficulty, the heart remained strong and the spirit stayed bright.",
            "The days passed like gentle waves on a calm sea, each one bringing new lessons of kindness, courage, and love.",
            "In the quiet moments between prayers and rest, beautiful lessons were learned that would last forever.",
        ],
        "outros": [
            "And so, dear child, remember that with faith in your heart and kindness in your actions, you can face any day with a smile. Close your eyes now, drift into peaceful dreams, and know that you are loved. Goodnight.",
            "Remember, little one, that every good deed is like a shining star in the night sky. Be kind, be brave, and be loving. Now rest your sleepy head and dream wonderful dreams. Goodnight.",
        ],
    },
    "moral_stories": {
        "intros": [
            "Once upon a time, in a meadow filled with wildflowers and singing birds, there lived a little creature with the biggest heart.",
            "In a quiet village where everyone knew each other's name, there began a story that would teach a very important lesson.",
            "High up in the hills, where the clouds kissed the mountaintops, there lived someone special who was about to learn something wonderful.",
        ],
        "middles": [
            "Day by day, the little one learned that being kind was more important than being fast, and being helpful was better than being first.",
            "Through meadows of soft green grass and forests of whispering trees, the adventure continued, teaching lessons of heart and soul.",
            "With each passing moment, the lesson became clearer: true happiness comes from helping others and sharing what we have.",
            "The wind carried whispers of wisdom through the leaves, and the little one listened with an open heart.",
        ],
        "outros": [
            "And that, dear child, is why we always try our best to be kind to everyone we meet. Now close your eyes, feel the warmth of love around you, and drift into the most beautiful dreams. Goodnight.",
            "Remember, sweet one, that the kindest hearts are the happiest hearts. Be gentle, be caring, and be you. Now rest, and dream of all the wonderful things tomorrow will bring. Goodnight.",
        ],
    },
    "animal_fables": {
        "intros": [
            "In a forest where the trees danced with the wind and the streams sang lullabies, there lived the most curious little rabbit.",
            "Deep in the enchanted woodland, where fireflies lit the path like tiny lanterns, a wonderful adventure was about to begin.",
            "On the banks of a sparkling river, where frogs croaked their evening songs, there lived a clever little fox with the kindest eyes.",
        ],
        "middles": [
            "Hop, hop, hopped the little rabbit through fields of clover and beds of soft moss, discovering that every friend has something special to share.",
            "The forest animals gathered around, each one adding their own special gift to the adventure, showing that together we are stronger.",
            "Through the dappled sunlight and moonlit paths, the animals learned that working together makes every task easier and every joy brighter.",
            "With gentle paws and warm hearts, the little creatures showed that even the smallest among us can make the biggest difference.",
        ],
        "outros": [
            "And so, dear child, just like the little rabbit learned, being kind and helpful makes the world a more beautiful place. Now snuggle into your warm bed, close your sleepy eyes, and dream of all the wonderful friends waiting for you in dreamland. Goodnight.",
            "Remember, little one, that like the forest animals, we are all special in our own way. Be brave, be kind, and always share your smile. Now rest your head and let the sweet dreams come. Goodnight.",
        ],
    },
    "fairy_tales": {
        "intros": [
            "Once upon a time, in a kingdom where the castles touched the clouds and the gardens bloomed with magical flowers, there lived a kind young soul.",
            "Far, far away, beyond the rainbow and past the twinkling stars, there was a land where dreams came true and every wish found its way home.",
            "In a cottage at the edge of an enchanted forest, where the moonlight painted silver paths, a wonderful tale was about to unfold.",
        ],
        "middles": [
            "And so the adventure continued, through gardens of glittering dew and paths of soft, warm starlight, each step bringing something magical.",
            "The enchanted world sparkled with wonder at every turn, teaching that beauty can be found in the most unexpected places.",
            "Through meadows of dancing flowers and streams of crystal water, the journey went on, filled with moments of pure magic.",
            "Every day brought a new wonder, a new friend, and a new reason to believe in the magic that lives in every heart.",
        ],
        "outros": [
            "And so, dear child, remember that magic is real - it lives in your kindness, your dreams, and your imagination. Now close your eyes, let the fairy lights guide you to dreamland, and sleep peacefully. Goodnight.",
            "Remember, sweet one, that every star in the sky is a wish waiting to come true. Dream big, love deeply, and sleep soundly. Goodnight, little dreamer.",
        ],
    },
    "courage_bravery": {
        "intros": [
            "In a world where mountains touched the sky and rivers raced to the sea, there lived a brave little heart who was about to discover something amazing about themselves.",
            "On a morning filled with golden sunshine and the sweet songs of birds, a courageous young soul set out on an adventure that would change everything.",
            "High on a hill overlooking a valley of dreams, there lived someone who didn't know yet just how brave they truly were.",
        ],
        "middles": [
            "Step by step, through thick forests and across bubbling streams, the brave little heart discovered that courage grows stronger every time we use it.",
            "With each challenge faced and each fear overcome, the young adventurer grew taller inside, their heart filling with warm, golden courage.",
            "Through storms and sunshine, through laughter and tears, the brave one learned that being scared is okay - what matters is that we keep going.",
            "The wind cheered them on, the sun warmed their path, and every step forward made them a little braver than before.",
        ],
        "outros": [
            "And so, dear child, remember that you are braver than you know, stronger than you think, and more loved than you can imagine. Now close your eyes, feel the warmth of courage in your heart, and sleep peacefully. Tomorrow is waiting for your bravery. Goodnight.",
            "Remember, little brave one, that every hero was once someone who was afraid but chose to keep going. You are that hero. Now rest your tired eyes and dream of all the adventures tomorrow will bring. Goodnight.",
        ],
    },
}


class ScriptGenerator:
    """Generates bedtime story scripts using Groq (Llama 3) or Gemini, with fallback templates."""

    def __init__(self, api_key: Optional[str] = None, provider: str = "groq"):
        self.provider = provider
        self.groq_client = None
        self.gemini_client = None
        self.groq_model = "llama-3.3-70b-versatile"
        self.gemini_model = "gemini-2.0-flash"
        self._initialize_clients()

    def _initialize_clients(self):
        """Initialize available AI clients."""
        # Groq (primary - works worldwide, fast)
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            try:
                import groq
                self.groq_client = groq.Client(api_key=groq_key)
                logger.info("✅ Groq API client initialized (Llama 3.3)")
            except ImportError:
                logger.warning("⚠️ groq not installed. Run: pip install groq")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Groq client: {e}")

        # Gemini (secondary - may have region restrictions)
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=gemini_key)
                logger.info("✅ Gemini API client initialized")
            except Exception:
                pass

    def generate_script(
        self,
        topic: str,
        age_group: str = "preschool",
        duration_minutes: int = 8,
        style: str = "calm",
        num_segments: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate a complete bedtime story script. Tries Groq -> Gemini -> Fallback."""

        # Try Groq first (fast, worldwide, generous free tier)
        if self.groq_client:
            script = self._generate_with_groq(
                topic, age_group, duration_minutes, style, num_segments
            )
            if script:
                return script

        # Try Gemini second
        if self.gemini_client:
            script = self._generate_with_gemini(
                topic, age_group, duration_minutes, style, num_segments
            )
            if script:
                return script

        # Fallback to templates
        logger.info("📝 Using template-based script generation")
        return self._generate_fallback_script(
            topic, age_group, duration_minutes, num_segments
        )

    def _generate_with_groq(
        self,
        topic: str,
        age_group: str,
        duration_minutes: int,
        style: str,
        num_segments: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Generate script using Groq API (Llama 3.3 - fast & free)."""
        try:
            from .usage_tracker import UsageTracker
            tracker = UsageTracker()

            if not tracker.can_use("groq", 1):
                logger.warning("⚠️ Groq API limit reached.")
                return None

            prompt = SYSTEM_PROMPT.format(
                topic=topic,
                age_group=age_group,
                duration=duration_minutes,
                style=style,
            )
            if num_segments:
                prompt += f"\n\nGenerate exactly {num_segments} segments."

            logger.info(f"📝 Generating script with Groq (Llama 3.3) for: {topic}")

            response = self.groq_client.chat.completions.create(
                model=self.groq_model,
                messages=[
                    {"role": "system", "content": "You are an expert bedtime story writer. Always respond with valid JSON only, no extra text or markdown."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.8,
                max_tokens=8192,
                top_p=0.95,
            )

            tracker.record_usage("groq", 1)

            response_text = response.choices[0].message.content
            script = self._parse_response(response_text)

            if script:
                self._save_script(script, topic)
                return script
            else:
                logger.warning("⚠️ Failed to parse Groq response.")
                return None

        except Exception as e:
            logger.error(f"❌ Groq generation failed: {e}")
            return None

    def _generate_with_gemini(
        self,
        topic: str,
        age_group: str,
        duration_minutes: int,
        style: str,
        num_segments: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Generate script using Gemini API."""
        try:
            from .usage_tracker import UsageTracker
            tracker = UsageTracker()

            if not tracker.can_use("gemini", 2):
                return None

            prompt = SYSTEM_PROMPT.format(
                topic=topic,
                age_group=age_group,
                duration=duration_minutes,
                style=style,
            )
            if num_segments:
                prompt += f"\n\nGenerate exactly {num_segments} segments."

            logger.info(f"📝 Generating script with Gemini for: {topic}")
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=prompt,
            )

            tracker.record_usage("gemini", 2)
            script = self._parse_response(response.text)

            if script:
                self._save_script(script, topic)
                return script
            return None

        except Exception as e:
            logger.error(f"❌ Gemini generation failed: {e}")
            return None

    def _parse_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse AI response into structured script."""
        try:
            text = response_text.strip()

            # Remove code block markers
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]

            # Find JSON in response
            json_start = text.find("{")
            json_end = text.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                text = text[json_start:json_end]

            script = json.loads(text.strip())

            required_fields = ["title", "description", "segments"]
            for field in required_fields:
                if field not in script:
                    logger.warning(f"⚠️ Missing field: {field}")
                    return None

            for i, segment in enumerate(script["segments"]):
                if "narration" not in segment or "image_prompt" not in segment:
                    logger.warning(f"⚠️ Invalid segment {i+1}")
                    return None

            return script

        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parse error: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Parse error: {e}")
            return None

    def _generate_fallback_script(
        self,
        topic: str,
        age_group: str,
        duration_minutes: int,
        num_segments: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate a rich fallback script from templates."""
        logger.info(f"📝 Generating rich fallback script for: {topic}")

        # Calculate segments
        if num_segments is None:
            num_segments = max(6, min(15, duration_minutes * 2))

        # Determine category from topic keywords
        category = self._detect_category(topic)

        # Get templates for this category
        templates = FALLBACK_STORIES.get(category, FALLBACK_STORIES["moral_stories"])

        # Age-appropriate vocabulary
        age_descriptions = {
            "toddler": "a little one just learning about the world",
            "preschool": "a curious young child",
            "school_age": "a bright and eager child",
            "preteen": "a thoughtful young person",
        }

        # Build segments
        segments = []

        # Opening segment (2 segments)
        intro = random.choice(templates["intros"])
        segments.append({
            "segment_number": 1,
            "narration": (
                f"Once upon a time, there was a story meant just for you. "
                f"{intro} "
                f"Tonight, we're going to discover something beautiful together. "
                f"Are you comfortable? Are your eyes getting sleepy? "
                f"Let our story begin..."
            ),
            "image_prompt": (
                f"Enchanted landscape at twilight, soft golden light, {topic} theme, "
                f"dreamy watercolor storybook illustration, warm colors, magical atmosphere, "
                f"gentle clouds, twinkling stars beginning to appear"
            ),
            "mood": "calm",
            "duration_seconds": 40,
        })

        segments.append({
            "segment_number": 2,
            "narration": (
                f"In this gentle story, we meet our hero - {age_descriptions.get(age_group, 'a young child')} "
                f"who lived in a place filled with wonder and beauty. "
                f"The air smelled of wildflowers and honey, and everywhere you looked, "
                f"there was something magical to discover. "
                f"Our story takes us on a journey through this wonderful world..."
            ),
            "image_prompt": (
                f"Beautiful storybook village scene, {topic} theme, warm sunset colors, "
                f"children's book art style, soft watercolor, cozy houses, "
                f"flowing river, wildflowers, dreamy atmosphere"
            ),
            "mood": "calm",
            "duration_seconds": 45,
        })

        # Middle segments (varies by duration)
        middle_count = num_segments - 4  # Minus intro (2) and outro (2)
        for i in range(middle_count):
            middle_text = random.choice(templates["middles"])
            segment_num = i + 3

            # Vary the narration slightly
            if i % 3 == 0:
                narration = (
                    f"{middle_text} "
                    f"And as the story unfolded, beautiful things began to happen, "
                    f"like morning dew sparkling on a rose petal."
                )
            elif i % 3 == 1:
                narration = (
                    f"{middle_text} "
                    f"The gentle breeze carried the story forward, "
                    f"like a lullaby floating through the evening air."
                )
            else:
                narration = (
                    f"{middle_text} "
                    f"And the stars above twinkled a little brighter, "
                    f"as if they too were listening to our tale."
                )

            # Vary image prompts
            image_styles = [
                f"Soft watercolor storybook scene, {topic} theme, golden hour lighting, "
                f"dreamy atmosphere, children's book illustration, warm colors, gentle details",

                f"Magical storybook illustration, {topic} theme, twilight colors, "
                f"soft brushstrokes, whimsical atmosphere, cozy and warm feeling",

                f"Gentle watercolor painting, {topic} theme, moonlit scene, "
                f"soft shadows, dreamy quality, children's book art, soothing colors",
            ]

            segments.append({
                "segment_number": segment_num,
                "narration": narration,
                "image_prompt": random.choice(image_styles),
                "mood": random.choice(["calm", "reflective"]),
                "duration_seconds": random.randint(35, 50),
            })

        # Closing segments (2 segments)
        outro1 = random.choice(templates["outros"])

        segments.append({
            "segment_number": num_segments - 1,
            "narration": (
                f"And so, our story gently comes to its end, "
                f"like a candle flickering softly in the night. "
                f"The lesson of our tale is simple and beautiful: "
                f"when we are kind, when we are brave, and when we love, "
                f"the whole world becomes a more wonderful place. "
                f"Remember this as you drift into your dreams tonight..."
            ),
            "image_prompt": (
                f"Peaceful nighttime scene, {topic} theme, soft moonlight, "
                f"gentle stars, warm cozy atmosphere, lullaby feeling, "
                f"dreamy watercolor, children's book illustration"
            ),
            "mood": "calm",
            "duration_seconds": 40,
        })

        segments.append({
            "segment_number": num_segments,
            "narration": outro1,
            "image_prompt": (
                f"Magical starry night sky, {topic} theme, soft glowing moon, "
                f"peaceful clouds, dreamy watercolor illustration, "
                f"cozy bedroom feeling, warm golden stars, lullaby atmosphere"
            ),
            "mood": "calm",
            "duration_seconds": 45,
        })

        # Build script
        script = {
            "title": f"The Story of {topic.title()} - A Bedtime Tale",
            "description": (
                f"Join us for a wonderful bedtime story about {topic}. "
                f"Perfect for {age_group} children. A calming tale to help little ones "
                f"drift off to sleep. Sweet dreams await! "
                f"#bedtimestories #children #sleep #storytelling"
            ),
            "tags": [
                topic.lower(), "bedtime stories", "children", age_group,
                "storytelling", "sleep", "calm", "fairy tale",
                "kids story", "lullaby", "moral story",
            ],
            "thumbnail_prompt": (
                f"Magical scene depicting {topic}, soft watercolor style, "
                f"warm golden lighting, dreamy atmosphere, children's book illustration, "
                f"eye-catching, vibrant but soothing colors"
            ),
            "segments": segments,
            "moral": f"Every story teaches us something beautiful. Be kind, be brave, and always share your love.",
            "age_appropriateness": f"This story is designed for {age_group} children with age-appropriate themes, gentle language, and a calming tone perfect for bedtime.",
            "total_estimated_duration_seconds": sum(s["duration_seconds"] for s in segments),
        }

        self._save_script(script, topic)
        return script

    def _detect_category(self, topic: str) -> str:
        """Detect story category from topic text."""
        topic_lower = topic.lower()

        if any(kw in topic_lower for kw in ["prophet", "sahaba", "companion", "quran", "hadith", "islamic"]):
            return "islamic_history"
        elif any(kw in topic_lower for kw in ["brave", "courage", "fear", "hero"]):
            return "courage_bravery"
        elif any(kw in topic_lower for kw in ["animal", "rabbit", "fox", "lion", "bird", "fish"]):
            return "animal_fables"
        elif any(kw in topic_lower for kw in ["magic", "fairy", "enchanted", "kingdom"]):
            return "fairy_tales"
        else:
            return "moral_stories"

    def _save_script(self, script: Dict[str, Any], topic: str):
        """Save generated script to file."""
        output_dir = Path("./output/scripts")
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = topic.lower().replace(" ", "_")[:50]
        filepath = output_dir / f"{filename}.json"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(script, f, indent=2, ensure_ascii=False)

        logger.info(f"💾 Script saved to: {filepath}")

    def get_script_status(self) -> Dict[str, Any]:
        """Get status of generated scripts."""
        scripts_dir = Path("./output/scripts")
        if not scripts_dir.exists():
            return {"total": 0, "scripts": []}

        scripts = list(scripts_dir.glob("*.json"))
        return {
            "total": len(scripts),
            "scripts": [s.name for s in scripts[-10:]],
        }


def get_script_generator(api_key: Optional[str] = None) -> ScriptGenerator:
    """Get or create script generator instance."""
    return ScriptGenerator(api_key)
