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

    def generate_script(self, topic: str) -> VideoScript:
        """
        Generates a structured YouTube Shorts script for the given topic
        using Gemini 2.5 Flash and Pydantic structured output.
        """
        if not self.client:
            raise ValueError("Gemini API key is not configured. Please set GEMINI_API_KEY in the .env file.")

        channel_cfg = self.config.get("channel", {})
        niche = channel_cfg.get("niche", "military aviation")
        tone = channel_cfg.get("tone", "dramatic, intense, epic")
        max_duration = self.config.get("video", {}).get("max_duration_seconds", 50)

        # Build prompt instructing Gemini to write a high-retention vertical script
        prompt = f"""
You are the lead scriptwriter for the YouTube Shorts channel '{channel_cfg.get('name', 'MilitaryDeepOps')}', specializing in '{niche}'.
Write a highly engaging, high-retention video script about the topic/title: "{topic}".

Your writing style must be: {tone}.

Key constraints for massive virality and monetization viability:
1. The total duration of all scenes combined MUST NOT exceed {max_duration} seconds (keep it between 35 and 45 seconds total).
2. The Hook (0:00 - 0:15): Start IMMEDIATELY by confirming the promise of the title in the very first sentence. NO intros, NO generic greetings like "Hey everyone". If the title talks about a specific secret, stat, or feature, the first sentence MUST state/address that immediately (e.g. if the title is "F-16 Viper: The ULTIMATE Budget Fighter Jet!", the first sentence must be: "This is the exact reason why the F-16 Viper rules the skies, despite costing a fraction of its competitors...").
3. The Pacing: Use short, punchy, high-impact sentences. Delete every single superfluous word. Each scene MUST have a duration of 4 to 6 seconds to keep the visual rhythm extremely fast.
4. The Open Loop: Around the middle of the script (around 20 seconds, usually in scene 3 or 4), insert an open loop—a mystery or a question that will be answered only at the end (e.g., "But there is a critical flaw that pilots fear most, and I'll show it to you in a moment.").
5. The Payoff: Deliver fully on the promise of the title by the end of the video. The open loop MUST be resolved, and the promise of the title must be completed truthfully without lying to the viewer.
6. Seamless Loop: The final sentence must end mid-thought or connect grammatically and thematically back to the very first sentence of the script, creating a seamless loop.
7. Scribe in standard English.
8. For each scene, specify an ultra-specific search query for stock footage. The query must be highly specific to the military/tactical niche, explicitly incorporating terms like 'military', 'navy', 'air force', 'fighter jet', or 'warfare' when relevant, and avoiding any generic words. For example, if a scene discusses a steam catapult, the query must be 'aircraft carrier flight deck, fighter jet taking off, steam catapult launch, military aviation' rather than just 'steam'.
"""

        print(f"Generating script for topic: '{topic}' using Gemini...")
        
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
