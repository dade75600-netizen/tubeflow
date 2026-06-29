import os
import subprocess

def create_directory(path):
    os.makedirs(path, exist_ok=True)
    print(f"Created directory: {path}")

def generate_silence_mp3(filepath, duration=1.0):
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        print(f"Generating placeholder MP3: {filepath}")
        try:
            ffmpeg_path = os.path.join(os.path.dirname(__file__), "bin", "ffmpeg.exe")
            if not os.path.exists(ffmpeg_path):
                ffmpeg_path = "ffmpeg"
                
            # Generate a silent mp3 file using ffmpeg
            subprocess.run([
                ffmpeg_path, "-y", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo", 
                "-t", str(duration), "-q:a", "9", "-acodec", "libmp3lame", filepath
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"Failed to generate {filepath} via ffmpeg: {e}")
            # Fallback to an empty file if ffmpeg fails (though it shouldn't)
            open(filepath, 'a').close()

def main():
    base_dir = os.path.join(os.path.dirname(__file__), "assets", "audio")
    
    dirs = [
        os.path.join(base_dir, "military"),
        os.path.join(base_dir, "aviation"),
        os.path.join(base_dir, "sfx")
    ]
    
    for d in dirs:
        create_directory(d)
        
    # Generate placeholder background music
    generate_silence_mp3(os.path.join(base_dir, "military", "placeholder_bgm.mp3"), 10.0)
    generate_silence_mp3(os.path.join(base_dir, "aviation", "placeholder_bgm.mp3"), 10.0)
    
    # Generate placeholder SFX
    generate_silence_mp3(os.path.join(base_dir, "sfx", "swoosh.mp3"), 1.0)
    generate_silence_mp3(os.path.join(base_dir, "sfx", "impact.mp3"), 1.0)

    print("\n--- Audio Assets Setup Complete ---")
    print("Folders generated successfully. Placeholder 'silence' mp3s have been inserted.")
    print("Please replace them with your actual sound files.")
    
if __name__ == "__main__":
    main()
