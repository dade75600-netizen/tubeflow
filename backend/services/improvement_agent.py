"""
improvement_agent.py
====================
Analyzes YouTube performance metrics using Gemini 3.1 Pro and automatically 
generates new high-performing topics to append to the content queues.
"""

import os
import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List

class OptimizationReport(BaseModel):
    analysis: str = Field(description="A brief paragraph summarizing what worked and what didn't based on the metrics.")
    new_topics: List[str] = Field(description="A list of 5-10 new Shorts topics inspired by the top performing videos. Maximum 55 characters each. Include 1 emoji.")

class ImprovementAgent:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")
        
        # Use a faster/less restrictive model for analytics to prevent quota issues
        self.client = genai.Client(api_key=self.api_key)
        self.model_id = 'gemini-2.5-flash'

    def analyze_and_improve(self, dataset: list, queue_file: str, profile: dict) -> OptimizationReport:
        """
        Takes the performance dataset, sends it to Gemini for analysis,
        and appends the generated optimized topics to the queue file.
        """
        if not dataset:
            print("No dataset provided to ImprovementAgent. Skipping analysis.")
            return None

        # Filter out videos with less than 50 views (too little data)
        # unless all videos have low views, in which case we take the top ones anyway
        dataset.sort(key=lambda x: x["view_count"], reverse=True)
        top_performers = dataset[:5]
        low_performers = dataset[-5:] if len(dataset) > 5 else []

        prompt = f"""
You are an expert YouTube Shorts Algorithm Strategist.
Your goal is to analyze the performance of a channel ({profile.get('channel_name', 'Unknown')}) and generate NEW highly-optimized video topics to fill the content pipeline.

Here is the data from the most recent videos uploaded:

TOP PERFORMERS:
{json.dumps(top_performers, indent=2)}

LOWEST PERFORMERS:
{json.dumps(low_performers, indent=2)}

INSTRUCTIONS:
1. Analyze the engagement rate (likes/views) and view counts. Identify which keywords, subjects, or hooks drove the most views.
2. Generate a brief analysis.
3. Based on the analysis, brainstorm 5 to 10 NEW topics for the channel that closely mimic the structure or subject of the top performers, but are distinct. 
4. The topics MUST fit the channel niche: {profile.get('persona_prompt', '')}.
5. Each topic MUST be under 55 characters and end with exactly 1 relevant emoji.
"""

        print("Sending performance data to Gemini for optimization analysis...")
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=OptimizationReport,
                temperature=0.7,
            ),
        )

        try:
            report_data = json.loads(response.text)
            report = OptimizationReport(**report_data)
            
            print(f"--- OPTIMIZATION ANALYSIS ---\n{report.analysis}\n-----------------------------")
            
            if report.new_topics:
                self._append_to_queue(report.new_topics, queue_file)
                print(f"Appended {len(report.new_topics)} new optimized topics to {queue_file}!")
                
            return report
        except Exception as e:
            print(f"Failed to parse ImprovementAgent output: {e}")
            return None

    def _append_to_queue(self, topics: List[str], queue_file: str):
        """Appends new topics to the specified queue file."""
        os.makedirs(os.path.dirname(queue_file) or ".", exist_ok=True)
        with open(queue_file, "a", encoding="utf-8") as f:
            f.write("\n# --- AI AUTO-OPTIMIZED TOPICS ---\n")
            for t in topics:
                f.write(f"{t}\n")
