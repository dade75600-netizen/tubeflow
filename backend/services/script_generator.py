import os
import yaml
import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List

# Define structured output models for Gemini
class ScriptScene(BaseModel):
    scene_number: int = Field(description="The sequential number of the scene starting from 1")
    narration: str = Field(description="The exact English voiceover text to be spoken in this scene. Must be high energy, engaging, and under 10-15 words.")
    duration: float = Field(description="Estimated duration in seconds for this narration. MUST be strictly between 4.0 and 6.0 seconds.")
    search_query: str = Field(description="An ultra-specific military search query of 3-5 words for Pexels. MUST be highly specific to military aviation and tactics. Avoid generic terms (e.g. if the scene is about carrier takeoff, use 'aircraft carrier flight deck, fighter jet taking off, steam catapult launch, military aviation' instead of just 'steam' or 'takeoff').")

class VideoScript(BaseModel):
    title: str = Field(description="An extremely engaging, click-worthy YouTube Shorts title in English. (Keep under 100 chars, use emojis).")
    description: str = Field(description="SEO optimized video description in English including brief summary, timestamps, and hashtags (e.g., #military #aviation).")
    tags: List[str] = Field(description="List of 8-12 relevant tags/keywords for YouTube SEO.")
    voiceover_text: str = Field(description="The complete, concatenated narration text of all scenes (clean, no directions, just the words to speak).")
    scenes: List[ScriptScene] = Field(description="List of chronological scenes that make up the video.")

class ScriptGenerator:
    def __init__(self, api_key: str = None, config_path: str = "config.yaml"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.config_path = config_path
        self.config = self.load_config()
        
        if self.api_key:
            # Initialize the new Google GenAI client
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    def load_config(self) -> dict:
        """Loads configuration from config.yaml."""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        return {}

    def generate_script(self, topic: str, profile: dict = None) -> VideoScript:
        """
        Generates a structured YouTube Shorts script for the given topic
        using Gemini 2.5 Flash and Pydantic structured output.
        """
        if not self.client:
            raise ValueError("Gemini API key is not configured. Please set GEMINI_API_KEY in the .env file.")

        channel_cfg = self.config.get("channel", {})
        niche = channel_cfg.get("niche", "military aviation")
        tone = channel_cfg.get("tone", "dramatic, intense, epic")
        
        # Calculate target duration and scenes based on the channel profile
        if profile:
            target_duration = profile.get("video_duration_target", 50)
            tone = profile.get("script_tone", tone)
        else:
            target_duration = self.config.get("video", {}).get("max_duration_seconds", 50)
        
        # Each scene averages 5 seconds
        num_scenes = max(6, int(target_duration / 5.0))

        # Check script tone profile to apply custom hook/narrative constraints
        if profile and profile.get("script_tone") == "classified_documentary":
            prompt = f"""
You are the lead scriptwriter for the YouTube Shorts channel '{channel_cfg.get('name', 'MilitaryDeepOps')}', specializing in '{niche}'.
Write a highly engaging, high-retention video script about the topic/title: "{topic}".

Your writing style must be: Classified documentary style. Sound like an authoritative ex-CIA intelligence analyst revealing top-secret secrets. The tone is intense, dramatic, precise, and suspenseful.

Key constraints for massive virality and high retention:
1. Generate exactly {num_scenes} sequential scenes to hit a target duration of approximately {target_duration} seconds.
2. Hook (First 15 seconds): Start IMMEDIATELY with a specific, shocking fact (such as a date, real name, statistic, or number). NEVER start with intros like "In this video...", "Welcome back...", or "Have you ever wondered...". Get straight to the shock fact.
3. 4-Act Narrative Structure:
   - Act 1: Shock Hook (0-15 seconds) - Startle the viewer with a shocking reveal.
   - Act 2: Context (approx 30 seconds) - Lay out the background history or details.
   - Act 3: Dramatic Escalation - Build up tension or raise the stakes.
   - Act 4: Final Revelation with a Twist - Deliver a dramatic payoff or unexpected twist.
4. Open Loop: In the exact middle of the script (around scene {num_scenes // 2}), plant a compelling unresolved mystery or question that will only be solved at the very end to prevent drops in retention (e.g., "But the radar screens showed something impossible. You will see what it was in a moment.").
5. Pacing: Short, punchy, high-impact sentences. Keep visual rhythm very fast. Every single scene narration must be under 10-15 words and have an estimated duration between 4.0 and 6.0 seconds.
6. CTA for Comments: The very last sentence of the script must end with a provocative open question that forces viewers to leave comments (e.g., "What would have happened if that pilot had pulled the trigger?").
7. Seamless Loop: The last word of the script must loop back cleanly into the first word of the video for endless play loops.
8. Language: English.
9. Stock footage queries: For each scene, specify an ultra-specific search query of 3-5 words. Use terms like 'military', 'navy', 'air force', 'fighter jet', or 'warfare' when relevant. Avoid generic queries.
"""
        elif profile and profile.get("script_tone") == "aviation_documentary":
            prompt = f"""
You are the lead scriptwriter for the YouTube Shorts channel '{channel_cfg.get('name', 'CivilAviationLords')}', specializing in '{niche}'.
Write a highly engaging, high-retention video script about the topic/title: "{topic}".

Your writing style must be: Technical aviation documentary style. Sound like a professional captain analyzing flight recorder logs or cockpit emergencies. The tone is suspenseful, technical, and educational.

Key constraints:
1. Generate exactly {num_scenes} sequential scenes to hit a target duration of approximately {target_duration} seconds.
2. Hook (First 15 seconds): Start immediately with the flight context and emergency (e.g. "Boeing 737 flight 243 was climbing through 24,000 feet when the cabin roof peeled open..."). No introductory fluff.
3. Narrative Structure: Introduce flight parameters -> build technical issue -> pilot decision point -> final resolution and safety lesson.
4. Open Loop: Plant a question in the middle of the script (around scene {num_scenes // 2}) about whether the plane will survive, to be resolved at the end.
5. Pacing: Every scene narration must be short, under 10-15 words, with duration between 4.0 and 6.0 seconds.
6. Language: English.
7. Stock footage queries: Specify queries related to commercial airplanes, passenger aviation, flight deck, cockpit instrumentation, or runway landings.
"""
        else:
            # Fallback to the original prompt
            prompt = f"""
You are the lead scriptwriter for the YouTube Shorts channel '{channel_cfg.get('name', 'MilitaryDeepOps')}', specializing in '{niche}'.
Write a highly engaging, high-retention video script about the topic/title: "{topic}".

Your writing style must be: {tone}.

Key constraints for massive virality and monetization viability:
1. The total duration of all scenes combined MUST NOT exceed {target_duration} seconds (keep it between 35 and 45 seconds total, generating exactly {num_scenes} scenes).
2. The Hook (0:00 - 0:15): Start IMMEDIATELY by confirming the promise of the title in the very first sentence. NO intros, NO generic greetings.
3. The Pacing: Use short, punchy, high-impact sentences. Each scene MUST have a duration of 4 to 6 seconds.
4. The Open Loop: Around the middle of the script, insert an open loop—a mystery or a question that will be answered only at the end.
5. The Payoff: Deliver fully on the promise of the title by the end of the video.
6. Seamless Loop: The final sentence must connect grammatically and thematically back to the very first sentence of the script.
7. Scribe in standard English.
8. For each scene, specify an ultra-specific search query for stock footage. Incorporate niche-specific terms like 'military', 'navy', 'air force', 'fighter jet', or 'warfare' when relevant.
"""

        print(f"Generating script for topic: '{topic}' using Gemini (Target Duration: {target_duration}s, Scenes: {num_scenes})...")
        
        # Call the Gemini API with structured schema configuration
        response = self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=VideoScript,
                temperature=0.8,
            ),
        )

        # The SDK returns the parsed object automatically under .parsed if schema is provided
        # Or we can load the JSON text
        try:
            script_data = json.loads(response.text)
            return VideoScript(**script_data)
        except Exception as e:
            print(f"Error parsing Gemini response: {e}")
            print(f"Raw response: {response.text}")
            raise e
