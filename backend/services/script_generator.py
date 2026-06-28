import os
import yaml
import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List

# ─── Keyword list for highlight coloring in video subtitles ─────────────────
HIGHLIGHT_KEYWORDS = {
    "died", "dead", "death", "killed", "kill", "secret", "secrets",
    "explosion", "exploded", "classified", "pilot", "pilots", "banned",
    "zero", "warning", "crash", "crashed", "failed", "failure",
    "forbidden", "hidden", "never", "impossible", "destroyed"
}

# ─── Structured output models ────────────────────────────────────────────────
class ScriptScene(BaseModel):
    scene_number: int = Field(
        description="Sequential scene number starting from 1."
    )
    narration: str = Field(
        description=(
            "The exact English voiceover text for this scene. "
            "MUST be 8-14 words max. Ultra-punchy, no filler words. "
            "Each sentence is a standalone shock statement."
        )
    )
    duration: float = Field(
        description=(
            "Estimated duration in seconds for this narration. "
            "MUST be strictly between 4.0 and 6.0 seconds."
        )
    )
    search_query: str = Field(
        description=(
            "A hyper-specific 3-6 word Pexels stock footage search query "
            "matching the exact visual needed for this scene. "
            "Include niche-specific terms (military, cockpit, fighter jet, "
            "submarine, etc). Never use generic terms like 'man' or 'people'."
        )
    )

class VideoScript(BaseModel):
    title: str = Field(
        description=(
            "Extremely click-worthy YouTube Shorts title in English. "
            "Under 60 characters. 1 relevant emoji at the end. "
            "No hashtags in the title."
        )
    )
    description: str = Field(
        description=(
            "SEO-optimized YouTube video description. "
            "Start with #Shorts on the first line. "
            "Then a 2-sentence hook summary. "
            "Then relevant hashtags: #Shorts #Military #Aviation etc."
        )
    )
    tags: List[str] = Field(
        description=(
            "List of 8-12 relevant YouTube SEO tags. "
            "MUST include 'Shorts' and 'YouTubeShorts' as the first two tags."
        )
    )
    voiceover_text: str = Field(
        description=(
            "The complete concatenated narration text of all scenes. "
            "Plain text only — no stage directions, no scene numbers."
        )
    )
    scenes: List[ScriptScene] = Field(
        description="Ordered list of scenes (10-11 total) composing the Short."
    )

# ─── Generator class ─────────────────────────────────────────────────────────
class ScriptGenerator:
    def __init__(self, api_key: str = None, config_path: str = "config.yaml"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.config_path = config_path
        self.config = self.load_config()

        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    def load_config(self) -> dict:
        """Loads configuration from config.yaml."""
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def generate_script(self, topic: str, profile: dict = None) -> VideoScript:
        """
        Generates a structured Shorts script (max 140 words, 50-55s) with
        a seamless loop ending. Uses Gemini 2.5 Flash with structured JSON output.
        """
        if not self.client:
            raise ValueError(
                "Gemini API key is not configured. "
                "Please set GEMINI_API_KEY in the .env file."
            )

        channel_cfg = self.config.get("channel", {})
        channel_name = channel_cfg.get("name", "MilitaryDeepOps")

        # Shorts: fixed 10 scenes × ~5s = ~50s, max 140 words total
        num_scenes = 10
        target_duration = 52  # seconds

        tone = (profile or {}).get("script_tone", "classified_documentary")

        if tone == "classified_documentary":
            prompt = self._military_prompt(topic, channel_name, num_scenes, target_duration)
        elif tone == "aviation_documentary":
            prompt = self._aviation_prompt(topic, channel_name, num_scenes, target_duration)
        else:
            prompt = self._military_prompt(topic, channel_name, num_scenes, target_duration)

        print(
            f"Generating Shorts script for: '{topic}' "
            f"(Target: {target_duration}s, {num_scenes} scenes, max 140 words)..."
        )

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=VideoScript,
                temperature=0.85,
            ),
        )

        try:
            script_data = json.loads(response.text)
            return VideoScript(**script_data)
        except Exception as e:
            print(f"Error parsing Gemini response: {e}")
            print(f"Raw response: {response.text}")
            raise e

    # ─── Prompt builders ─────────────────────────────────────────────────────

    def _military_prompt(self, topic: str, channel_name: str,
                         num_scenes: int, target_duration: int) -> str:
        return f"""You are the lead scriptwriter for '{channel_name}', a viral YouTube Shorts channel about classified military operations and secret government history.

TOPIC: "{topic}"

YOUR MISSION: Write a YouTube Short script that is a loop-able, frantic, classified-document reveal.

═══════════ ABSOLUTE HARD RULES ═══════════

1. TOTAL WORD COUNT: The sum of ALL narration across ALL {num_scenes} scenes MUST NOT exceed 140 words. Count carefully.

2. SCENE COUNT: Generate exactly {num_scenes} scenes. Each scene narration is 8-14 words. Each scene duration is 4.0-6.0 seconds.

3. NO INTRO / NO OUTRO: Do NOT write "In this video", "Welcome", "Subscribe", "Like and comment", or any conventional YouTube phrases. Start with the shock fact. End mid-sentence.

4. THREE-PART STRUCTURE:
   - SHOCK HOOK (Scene 1, ~3-4s): Start with a DATE, NAME, or NUMBER. Immediately shocking. Example: "1972. A US spy plane vanished over Soviet airspace."
   - RAPID ESCALATION (Scenes 2-9): Each scene raises stakes. Short declarative sentences. No padding.
   - SEAMLESS LOOP (Scene 10): The LAST SENTENCE must be syntactically INCOMPLETE — it must cut off mid-thought and connect back PERFECTLY to the first word of Scene 1, creating an infinite loop. Example: If Scene 1 starts with "1972.", Scene 10 might end with "...and everything began in"

5. TONE: Ex-CIA analyst revealing classified secrets under duress. Cold. Precise. Terrifying. No emotion words like "amazingly" or "incredibly".

6. HIGHLIGHT WORDS: Use at least 3 of these words naturally in the script (they will be colored RED/YELLOW in the video): died, killed, secret, classified, explosion, banned, zero, warning, destroyed, forbidden, crashed, hidden.

7. STOCK FOOTAGE: Each scene needs a hyper-specific visual query (3-6 words). Use terms like: military aircraft carrier, cold war nuclear silo, fighter jet cockpit, navy submarine interior, special forces raid, classified documents folder.

8. LANGUAGE: English only.

═══════════ OUTPUT FORMAT ═══════════
Return a VideoScript JSON object with exactly {num_scenes} scenes.
The description field MUST start with "#Shorts" on the first line.
Tags MUST include "Shorts" and "YouTubeShorts" as the first two entries.
Title MUST be under 60 characters with 1 emoji, NO hashtags.
"""

    def _aviation_prompt(self, topic: str, channel_name: str,
                         num_scenes: int, target_duration: int) -> str:
        return f"""You are the lead scriptwriter for '{channel_name}', a viral YouTube Shorts channel about commercial aviation emergencies, flight engineering secrets, and pilot decisions under pressure.

TOPIC: "{topic}"

YOUR MISSION: Write a YouTube Short script structured like a black-box flight recorder being played back — terse, technical, terrifying.

═══════════ ABSOLUTE HARD RULES ═══════════

1. TOTAL WORD COUNT: The sum of ALL narration across ALL {num_scenes} scenes MUST NOT exceed 140 words. Count carefully.

2. SCENE COUNT: Generate exactly {num_scenes} scenes. Each scene narration is 8-14 words. Each scene duration is 4.0-6.0 seconds.

3. NO INTRO / NO OUTRO: Do NOT write "In this video", "Hey guys", "Subscribe", "Like and comment". Start immediately with the flight context. End mid-sentence.

4. THREE-PART STRUCTURE:
   - SHOCK HOOK (Scene 1, ~3-4s): Start with flight number, altitude, or a direct emergency fact. Example: "Flight 232. 37,000 feet. The hydraulic system just failed — completely."
   - RAPID ESCALATION (Scenes 2-9): Each scene adds a new technical failure or pilot decision. Short declarative sentences. Use aviation terminology (MAYDAY, PAN-PAN, TCAS, V1, rotate, deadstick).
   - SEAMLESS LOOP (Scene 10): The LAST SENTENCE must be syntactically INCOMPLETE — it connects back to the first word of Scene 1, creating an infinite loop. Example: If Scene 1 starts with "Flight 232", Scene 10 might end with "...and it all started on"

5. TONE: Professional captain playing back the CVR. Cold, clinical, precise. The terror comes from the facts, not from dramatic language.

6. HIGHLIGHT WORDS: Use at least 3 of these words naturally (they will be colored RED/YELLOW): died, killed, secret, crashed, explosion, failed, warning, zero, pilot, forbidden, hidden, classified.

7. STOCK FOOTAGE: Each scene needs a hyper-specific visual query (3-6 words). Use: cockpit instruments close-up, flight deck emergency alert, aircraft engine fire, runway emergency vehicles, air traffic control radar, passenger oxygen mask drop.

8. LANGUAGE: English only.

═══════════ OUTPUT FORMAT ═══════════
Return a VideoScript JSON object with exactly {num_scenes} scenes.
The description field MUST start with "#Shorts" on the first line.
Tags MUST include "Shorts" and "YouTubeShorts" as the first two entries.
Title MUST be under 60 characters with 1 emoji, NO hashtags.
"""
