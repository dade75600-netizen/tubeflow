import os
import random

class AudioMixer:
    """
    Handles resolving background music and sound effects paths for the audio engine.
    Allows for dynamic selection of BGM tracks based on channel profile.
    """
    def __init__(self, base_dir="assets/audio"):
        self.base_dir = base_dir

    def get_bgm_path(self, channel_name: str) -> str:
        """
        Returns a random MP3 file path from the channel's BGM directory.
        """
        # Map profile names to directory names (e.g. 'Aviation' -> 'aviation')
        # We can handle generic lowercasing
        channel_slug = channel_name.lower().strip()
        # Edge cases for channel aliases
        if "military" in channel_slug:
            channel_slug = "military"
        elif "aviation" in channel_slug or "lords" in channel_slug:
            channel_slug = "aviation"
            
        dir_path = os.path.join(self.base_dir, channel_slug)
        
        if not os.path.exists(dir_path):
            print(f"BGM Directory not found: {dir_path}")
            return None
            
        files = [f for f in os.listdir(dir_path) if f.endswith(".mp3")]
        if not files:
            print(f"No MP3 files found in BGM Directory: {dir_path}")
            return None
            
        selected = random.choice(files)
        return os.path.join(dir_path, selected)

    def get_swoosh_path(self) -> str:
        """
        Returns the path to the swoosh sound effect.
        """
        path = os.path.join(self.base_dir, "sfx", "swoosh.mp3")
        return path if os.path.exists(path) else None

    def get_impact_path(self) -> str:
        """
        Returns the path to the impact (boom) sound effect.
        """
        path = os.path.join(self.base_dir, "sfx", "impact.mp3")
        return path if os.path.exists(path) else None
