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
    narration: str = Field(description="The exact English voiceover text to be spoken in this scene. Must be high energy and engaging.")
    duration: float = Field(description="Estimated duration in seconds for this narration. Rule of thumb: words count divided by 2.5.")
    search_query: str = Field(description="A specific, 2-3 word English search query to find relevant stock videos on Pexels (e.g., 'fighter jet flight', 'aircraft carrier launch', 'military pilot cockpit').")

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
Write a highly engaging, high-retention video script about the topic: "{topic}".

Your writing style must be: {tone}.

Key constraints for massive virality and monetization viability:
1. The total duration of all scenes combined MUST NOT exceed {max_duration} seconds (keep it between 35 and 45 seconds total).
2. Start with a massive psychological hook in the first 3 seconds to stop the scroll (e.g., start with shocking questions, classified/unknown secrets, or high-stakes statements like 'This is the terrifying reason...', 'What the military hid about...', or 'Most pilots don't survive this...').
3. Keep the narration fast-paced, dramatic, and punchy. Use short, high-impact sentences.
4. Bait viewer interaction: Include a subtle debate, mystery, or direct question near the middle or end to drive massive comment section discussion (e.g., 'Would you fly this?', 'Was it a design flaw or sabotage? Comment below').
5. Seamless loop: The final sentence (outro) must end mid-thought or connect grammatically/thematically back to the first sentence of the script, creating a seamless loop that tricks viewers into watching the video 2-3 times.
6. Scribe in standard English.
7. For each scene, specify a concrete search query for stock footage. It must be highly relevant and descriptive, optimized for Pexels search.
"""

        print(f"Generating script for topic: '{topic}' using Gemini...")
        
        # Call the Gemini API with structured schema configuration
        response = self.client.models.generate_content(
            model='gemini-3.5-flash',
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
