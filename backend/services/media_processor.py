import os
import requests
import asyncio
import edge_tts
import yaml
import random

class MediaProcessor:
    def __init__(self, pexels_key: str = None, config_path: str = "config.yaml"):
        self.pexels_key = pexels_key or os.getenv("PEXELS_API_KEY")
        self.config_path = config_path
        self.config = self.load_config()

    def load_config(self) -> dict:
        """Loads configuration from config.yaml."""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        return {}

    def generate_voiceover_sync(self, text: str, output_path: str):
        """Synchronous wrapper for generating voiceover."""
        asyncio.run(self.generate_voiceover(text, output_path))

    async def generate_voiceover(self, text: str, output_path: str):
        """Generates voiceover using edge-tts neural voices."""
        voice_cfg = self.config.get("voice", {})
        voice_name = voice_cfg.get("name", "en-US-GuyNeural")
        rate = voice_cfg.get("rate", "+5%")
        pitch = voice_cfg.get("pitch", "+0Hz")

        print(f"Generating voiceover with voice: {voice_name} (rate: {rate}, pitch: {pitch})...")
        
        # Build edge-tts communicator
        communicate = edge_tts.Communicate(text, voice_name, rate=rate, pitch=pitch)
        
        # Save to file
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        await communicate.save(output_path)
        print(f"Voiceover saved to {output_path}")

    def fetch_stock_video(self, query: str, output_path: str, duration_needed: float) -> bool:
        """
        Queries Pexels for a vertical video clip matching the query and downloads it.
        Ensures that the same video clip is never reused across different video pipeline runs.
        """
        if not self.pexels_key:
            print("Pexels API key not found. Skipping stock video download.")
            return False

        headers = {
            "Authorization": self.pexels_key
        }
        
        # Load video history to avoid duplication
        history_file = "video_history.txt"
        used_video_ids = set()
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r', encoding='utf-8') as h_f:
                    used_video_ids = {line.strip() for line in h_f.readlines() if line.strip()}
            except Exception as h_err:
                print(f"Error reading video history: {h_err}")
        
        # We search specifically for portrait (vertical) videos, increase per_page to give more randomized options
        url = f"https://api.pexels.com/videos/search?query={requests.utils.quote(query)}&per_page=15&orientation=portrait"
        
        try:
            print(f"Searching Pexels for '{query}' (vertical)...")
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            videos = data.get("videos", [])
            if not videos:
                # Randomized fallbacks to prevent asset duplication across different videos
                fallbacks = ["military jet", "fighter jet", "stealth aircraft", "aircraft carrier launch", "military aircraft cockpit"]
                chosen_fallback = random.choice(fallbacks)
                print(f"No videos found on Pexels for: '{query}'. Trying fallback '{chosen_fallback}'...")
                fallback_url = f"https://api.pexels.com/videos/search?query={requests.utils.quote(chosen_fallback)}&per_page=10&orientation=portrait"
                response = requests.get(fallback_url, headers=headers, timeout=15)
                data = response.json()
                videos = data.get("videos", [])
                
            if not videos:
                print("No videos found even with fallback. Sourcing failed.")
                return False

            # Filter out already used video IDs
            available_videos = [v for v in videos if str(v.get("id")) not in used_video_ids]
            if not available_videos:
                print("All search results have been used in previous videos. Resetting video pool for this query...")
                available_videos = videos
            
            # Shuffle available videos to ensure we don't always pick the same video first
            random.shuffle(available_videos)
            
            # Find a suitable vertical file link (usually we prefer HD resolution around 720x1280 or 1080x1920)
            best_link = None
            selected_video = None
            for video in available_videos:
                video_files = video.get("video_files", [])
                for f in video_files:
                    # Check if it has vertical orientation
                    w = f.get("width", 0)
                    h = f.get("height", 0)
                    if h > w: # Vertical orientation confirmed
                        # Prefer HD resolution around 720p or 1080p
                        if 720 <= w <= 1080:
                            best_link = f.get("link")
                            selected_video = video
                            break
                if best_link:
                    break
            
            # Fallback if no ideal vertical resolution matches
            if not best_link:
                # Grab the first available file link from any shuffled video
                for video in available_videos:
                    video_files = video.get("video_files", [])
                    if video_files:
                        best_link = video_files[0].get("link")
                        selected_video = video
                        break

            if not best_link or not selected_video:
                print("Failed to resolve a downloadable video link.")
                return False

            # Download the video file
            print(f"Downloading clip: {best_link} -> {output_path}")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            video_data = requests.get(best_link, stream=True, timeout=30)
            video_data.raise_for_status()
            
            with open(output_path, 'wb') as out_f:
                for chunk in video_data.iter_content(chunk_size=8192):
                    if chunk:
                        out_f.write(chunk)
            
            print(f"Clip successfully downloaded to: {output_path}")
            
            # Record the selected video ID to history file to prevent future reuse
            try:
                with open(history_file, 'a', encoding='utf-8') as h_f:
                    h_f.write(f"{selected_video.get('id')}\n")
            except Exception as h_err:
                print(f"Error writing to video history: {h_err}")
                
            return True

        except Exception as e:
            print(f"Error downloading stock video from Pexels: {e}")
            return False
