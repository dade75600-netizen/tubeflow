import os
import requests
import asyncio
# pyrefly: ignore [missing-import]
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

    def _detect_military_pool(self, text: str) -> list:
        """
        Returns military search keywords matching target sub-niche (cold war, special ops, modern).
        """
        text_lower = text.lower()
        cold_war_keywords = [
            "cold war", "soviet", "nuclear", "missile", "silo", "bunker", "submarine", 
            "periscope", "radar", "doomsday", "spy", "kgb", "cia", "berlin", "cuba", 
            "1962", "1950", "1960", "1970", "1980"
        ]
        special_ops_keywords = [
            "special forces", "seal", "sas", "night vision", "parachute", "sniper", 
            "hostage", "raid", "training", "mission", "green beret", "commando", "ranger"
        ]
        
        is_cold_war = any(k in text_lower for k in cold_war_keywords)
        is_special_ops = any(k in text_lower for k in special_ops_keywords)
        
        if is_cold_war:
            return [
                "nuclear missile silo", "cold war bunker", "submarine periscope", "military radar station",
                "submarine underwater dark", "military submarine periscope ocean", "nuclear submarine navy", "cold war military bunker dark"
            ]
        elif is_special_ops:
            return ["soldier night vision", "special forces training", "military parachute jump", "sniper position"]
        else:
            # Modern warfare (default)
            return ["military drone strike", "special forces night operation", "tank battlefield smoke", "military helicopter combat"]

    def _detect_aviation_pool(self, text: str) -> list:
        """
        Returns aviation-specific Pexels search fallback queries based on content context.
        Pools: crash/emergency, cockpit/technical, atmosphere/flight, investigation.
        """
        text_lower = text.lower()
        crash_keywords = [
            "crash", "killed", "disaster", "explosion", "fire", "wreckage", "dead",
            "fatal", "impact", "collide", "collision", "survivors", "emergency",
            "accident", "minutes", "seconds", "fell", "lost", "vanish"
        ]
        cockpit_keywords = [
            "cockpit", "pilot", "engine", "hydraulic", "sensor", "instrument",
            "control", "autopilot", "stall", "altitude", "captain", "crew",
            "mayday", "takeoff", "cvr", "fdr", "black box"
        ]
        investigation_keywords = [
            "investigate", "investigator", "ntsb", "safety board", "report",
            "finding", "cause", "reason", "why", "explained", "regulation"
        ]

        is_crash = any(k in text_lower for k in crash_keywords)
        is_cockpit = any(k in text_lower for k in cockpit_keywords)
        is_investigation = any(k in text_lower for k in investigation_keywords)

        if is_crash:
            return [
                "airplane emergency landing", "aircraft wreckage dramatic",
                "plane fire runway", "aviation rescue emergency"
            ]
        elif is_cockpit:
            return [
                "airplane cockpit instruments", "pilot controls dramatic",
                "aircraft engine close up", "aviation radar display"
            ]
        elif is_investigation:
            return [
                "investigators wreckage site", "black box flight recorder",
                "aviation safety inspection", "aircraft maintenance hangar"
            ]
        else:
            # atmosphere/flight fallback
            return [
                "airplane turbulence storm clouds", "aircraft night flight dramatic",
                "jet contrail dark sky", "airport runway night"
            ]

    def fetch_stock_video(self, query: str, output_path: str, duration_needed: float, profile: dict = None, title: str = None) -> bool:
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
        
        # Determine channel profile context and blacklists
        is_military = False
        is_aviation = False
        if profile and profile.get("bg_pool") == "military_combat":
            is_military = True
        elif profile and profile.get("bg_pool") == "aviation_dramatic":
            is_aviation = True
        elif not profile:
            channel_cfg = self.config.get("channel", {})
            niche = str(channel_cfg.get("niche", "")).lower()
            if "military" in niche or "combat" in niche or "stealth" in niche:
                is_military = True
            elif "aviation" in niche or "civil" in niche or "flight" in niche:
                is_aviation = True

        # Blacklist logic — aviation uses its own stricter exclusion list
        if is_military:
            blacklist_operators = ' -civilian -commercial -protest -vintage -antique -parade'
        elif is_aviation:
            blacklist_operators = ' -vacation -tourism -happy -celebration -luxury -business'
        else:
            blacklist_operators = ' -commercial -passenger -airliner -airport_terminal -vintage -antique'

        # Clean query (strip and replace commas to avoid Pexels API issues)
        clean_query = query.replace(',', ' ').replace('.', ' ').strip()
        
        # Force context if missing and generic
        if is_military:
            military_keywords = ['military', 'navy', 'air force', 'fighter jet', 'warfare', 'soldier', 'combat', 'stealth', 'aircraft carrier']
            has_military_context = any(k in query.lower() for k in military_keywords)
            if not has_military_context:
                clean_query = f"{clean_query} military fighter jet"
        
        processed_query = f"{clean_query}{blacklist_operators}"
        
        # We search specifically for portrait (vertical) videos, increase per_page to give more randomized options
        url = f"https://api.pexels.com/videos/search?query={requests.utils.quote(processed_query)}&per_page=15&orientation=portrait"
        
        try:
            print(f"Searching Pexels for '{processed_query}' (vertical)...")
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            videos = data.get("videos", [])
            if not videos:
                # Sourcing pool fallback — route to correct pool based on channel profile
                check_text = title if title else query
                if is_military:
                    fallbacks = self._detect_military_pool(check_text)
                elif is_aviation:
                    fallbacks = self._detect_aviation_pool(check_text)
                else:
                    fallbacks = ["military jet", "fighter jet", "stealth aircraft", "aircraft carrier launch", "military aircraft cockpit"]
                
                chosen_fallback = random.choice(fallbacks)
                processed_fallback = f"{chosen_fallback}{blacklist_operators}"
                print(f"No videos found on Pexels for: '{processed_query}'. Trying fallback '{processed_fallback}'...")
                fallback_url = f"https://api.pexels.com/videos/search?query={requests.utils.quote(processed_fallback)}&per_page=10&orientation=portrait"
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
