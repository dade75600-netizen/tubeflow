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
        description="Ordered list of scenes composing the Short."
    )
    on_screen_hook: str = Field(
        default="",
        description="Visual hook text shown on screen."
    )
    loop_bridge: str = Field(
        default="",
        description="Transition phrase looping back to start."
    )
    pexels_search_queries: List[str] = Field(
        default=[],
        description="List of Pexels search queries."
    )

class StrictScriptSegment(BaseModel):
    text: str = Field(description="The voiceover text/narration for this transition segment (8-14 words).")
    visual_keyword: str = Field(description="A specific, high-conversion visual search query keyword for Pexels (3-6 words).")

class StrictVideoScript(BaseModel):
    title: str = Field(description="SEO-optimized click-worthy YouTube Short title.")
    description: str = Field(description="SEO-optimized description starting with #Shorts.")
    tags: List[str] = Field(description="SEO tags starting with 'Shorts' and 'YouTubeShorts'.")
    segments: List[StrictScriptSegment] = Field(description="Chronological segments of the script (10-11 total).")

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

    def _dynamic_prompt(self, topic: str, profile: dict) -> str:
        channel_name = profile.get("channel_id") or profile.get("channel_handle") or "wealth_engine"
        niche = profile.get("niche") or "personal finance and wealth psychology"
        target_audience = profile.get("target_audience") or "high CPM viewers interested in wealth creation"
        pexels_queries = ", ".join(profile.get("pexels_queries", ["luxury lifestyle", "wealth", "finance"]))
        
        # Timeline rules from config
        hook_rule = "0-3s: Hook (date, shocking number, or question to grab attention)"
        core_rule = "3-40s: Core story (highly educational, dark psychological facts, money principles)"
        loop_rule = "40-50s: Seamless Loop (the last sentence is incomplete and flows perfectly into the first word of the video)"
        
        rules = f"""- Hook: {hook_rule}
- Core: {core_rule}
- Loop: {loop_rule}"""

        prompt = f"""You are the lead scriptwriter for the YouTube Shorts channel '{channel_name}' focusing on the niche: '{niche}'.
Target Audience: {target_audience}
Topic: "{topic}"

YOUR MISSION: Write a loop-able, highly engaging YouTube Short script.

═══════════ ABSOLUTE HARD RULES ═══════════
1. SCRIPTING TIMELINE & RULES:
{rules}
2. SEGMENT PACING: Split the script into segments. Each segment narration is 8-14 words max.
   Each segment duration MUST correspond to 3-5 seconds of voiceover (approx. 2-3 words per second).
3. NO INTRO / NO OUTRO: Start with the hook immediately. Do not write "Welcome", "Subscribe", or any fillers.
4. STOCK FOOTAGE: Each segment needs a specific, high-conversion visual keyword search query for Pexels (3-6 words).
   Focus on these visual motifs: [{pexels_queries}]. Do not use generic keywords.
5. LANGUAGE: English only.

═══════════ OUTPUT FORMAT ═══════════
Return a StrictVideoScript JSON object containing:
- title: Click-worthy title under 60 characters with 1 emoji, NO hashtags.
- description: SEO-optimized description starting with #Shorts.
- tags: List of 8-12 tags starting with 'Shorts' and 'YouTubeShorts'.
- segments: List of chronological segments with 'text' and 'visual_keyword'.
"""
        return prompt

    def generate_script(self, topic: str, profile: dict = None) -> VideoScript:
        """
        Generates a structured Shorts script (max 140 words, 50-55s) with
        a seamless loop ending. Uses Gemini 2.5 Flash.
        If profile is dynamic, uses StrictVideoScript schema and maps it.
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

        is_dynamic = profile and ("channel_id" in profile or "niche" in profile)

        if is_dynamic:
            prompt = self._dynamic_prompt(topic, profile)
            print(f"Generating dynamic Shorts script for: '{topic}' using niche: '{profile.get('niche')}'...")
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=StrictVideoScript,
                    temperature=0.85,
                ),
            )
            
            try:
                strict_data = json.loads(response.text)
                strict_script = StrictVideoScript(**strict_data)
                
                # Convert StrictVideoScript to standard VideoScript format
                scenes = []
                voiceover_text = " ".join(seg.text for seg in strict_script.segments)
                
                # Average duration per scene
                avg_duration = round(target_duration / max(len(strict_script.segments), 1), 1)
                for idx, seg in enumerate(strict_script.segments):
                    scenes.append(ScriptScene(
                        scene_number=idx + 1,
                        narration=seg.text,
                        duration=avg_duration,
                        search_query=seg.visual_keyword
                    ))
                
                return VideoScript(
                    title=strict_script.title,
                    description=strict_script.description,
                    tags=strict_script.tags,
                    voiceover_text=voiceover_text,
                    scenes=scenes
                )
            except Exception as e:
                print(f"Error parsing Gemini response: {e}")
                print(f"Raw response: {response.text}")
                raise e

        tone = (profile or {}).get("script_tone", "classified_documentary")

        if tone == "military_micro":
            prompt = self._military_micro_prompt(topic, channel_name)
            num_scenes = 2
            target_duration = 9
        elif tone == "classified_documentary":
            prompt = self._military_prompt(topic, channel_name, num_scenes, target_duration)
        elif tone == "aviation_documentary":
            prompt = self._aviation_prompt(topic, channel_name, num_scenes, target_duration)
        else:
            prompt = self._military_prompt(topic, channel_name, num_scenes, target_duration)

        print(
            f"Generating Shorts script for: '{topic}' "
            f"(Target: {target_duration}s, {num_scenes} scenes)..."
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

    def _military_micro_prompt(self, topic: str, channel_name: str) -> str:
        return f"""You are the lead scriptwriter for '{channel_name}', a viral micro-documentary channel.
Write a loop-able, highly educational, anti-reused content YouTube Short script about classified military technology or historical secrets.

TOPIC: "{topic}"

YOUR MISSION: Write a micro-documentary script (8-10 seconds total) designed for high retention loops.

═══════════ ABSOLUTE HARD RULES ═══════════
1. TOTAL NARRATION: Must be exactly 20-25 words total across the entire video.
2. SEAMLESS LOOP: The last sentence must cut off mid-thought and flow perfectly back to the first word of the video.
3. SCENES: Generate exactly 2 scenes:
   - Scene 1 (Duration: 4.5s): Hook / shocking fact.
   - Scene 2 (Duration: 4.5s): Explanation ending in loop_bridge.
4. FOCUS AREAS: Focus on nuclear submarines, stealth aircraft (SR-71 Blackbird, B-2 Spirit, F-22 Raptor), declassified Cold War files, or naval/air military records.

═══════════ JSON OUTPUT FORMAT ═══════════
Return a VideoScript JSON object conforming to this schema:
- title: click-worthy title under 60 characters with 1 emoji, NO hashtags.
- description: SEO-optimized description starting with #Shorts.
- tags: list of tags starting with 'Shorts', 'YouTubeShorts'.
- on_screen_hook: the shocking visual hook text to display on screen (3-5 words).
- loop_bridge: the final phrase connecting back to the start.
- voiceover_text: the combined narration text of Scene 1 + Scene 2.
- pexels_search_queries: list of exactly 2 military search queries in English.
- scenes: exactly 2 scenes:
  * Scene 1: scene_number=1, narration=Scene 1 hook text, duration=4.5, search_query=pexels_search_queries[0]
  * Scene 2: scene_number=2, narration=Scene 2 text ending in loop_bridge, duration=4.5, search_query=pexels_search_queries[1]
"""

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
