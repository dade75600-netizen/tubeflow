import os
import subprocess
import yaml
import re

class VideoEditor:
    def __init__(self, ffmpeg_path: str = None, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self.load_config()
        # Resolve ffmpeg executable
        self.ffmpeg = ffmpeg_path or self.resolve_ffmpeg()

    def load_config(self) -> dict:
        """Loads configuration from config.yaml."""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        return {}

    def resolve_ffmpeg(self) -> str:
        """Checks local bin/ first, then falls back to system path."""
        import sys
        if sys.platform.startswith("win"):
            local_ffmpeg = os.path.join("bin", "ffmpeg.exe")
            if os.path.exists(local_ffmpeg):
                return os.path.abspath(local_ffmpeg)
        return "ffmpeg" # Assume it is on system PATH

    def generate_ass_subtitles(self, script, ass_path: str):
        """
        Generates a stylized ASS subtitle file.
        Splits each scene's text into chunks of 2-3 words and estimates timings linearly.
        """
        sub_cfg = self.config.get("video", {}).get("subtitles", {})
        font_name = sub_cfg.get("font_name", "Impact")
        font_size = sub_cfg.get("font_size", 70)
        primary_color = sub_cfg.get("color", "#FFFF00") # Hex e.g. #FFFF00
        stroke_color = sub_cfg.get("stroke_color", "#000000")
        stroke_width = sub_cfg.get("stroke_width", 5)
        words_per_line = sub_cfg.get("words_per_line", 2)

        # Convert hex color to ASS format (&H00BBGGRR)
        def to_ass_color(hex_color):
            hex_color = hex_color.lstrip('#')
            if len(hex_color) == 6:
                r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
                return f"&H00{b}{g}{r}"
            return "&H0000FFFF" # Default yellow

        ass_primary = to_ass_color(primary_color)
        ass_stroke = to_ass_color(stroke_color)

        header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{ass_primary},&H000000FF,{ass_stroke},&H00000000,-1,0,0,0,100,100,0,0,1,{stroke_width},0,5,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        lines = []
        current_time = 0.0

        for scene in script.scenes:
            scene_text = scene.narration.strip()
            scene_duration = scene.duration
            
            # Split text into words
            words = [w for w in re.split(r'\s+', scene_text) if w]
            if not words:
                current_time += scene_duration
                continue

            num_words = len(words)
            words_per_sec = num_words / scene_duration if scene_duration > 0 else 2.5
            
            # Group words into chunks of words_per_line
            chunks = []
            for i in range(0, num_words, words_per_line):
                chunks.append(words[i:i + words_per_line])

            # Generate timing for each chunk
            import random
            for i, chunk in enumerate(chunks):
                words_in_chunk = [w.upper() for w in chunk]
                if len(words_in_chunk) > 1 and random.random() < 0.65:
                    # Choose a random word to highlight
                    hl_idx = random.randint(0, len(words_in_chunk) - 1)
                    hl_color = random.choice(["&H99D334&", "&H00FFFF&"]) # Green or Yellow in ASS BGR hex format
                    words_in_chunk[hl_idx] = f"{{\\c{hl_color}}}{words_in_chunk[hl_idx]}{{\\c{ass_primary}&}}"
                
                chunk_text = " ".join(words_in_chunk)
                chunk_word_count = len(chunk)
                
                start_offset = (i * words_per_line) / words_per_sec
                end_offset = start_offset + (chunk_word_count / words_per_sec)
                
                # Make sure the last chunk ends exactly at the scene's end boundary
                if i == len(chunks) - 1:
                    end_offset = scene_duration

                start_sec = current_time + start_offset
                end_sec = current_time + end_offset

                # Format seconds to HH:MM:SS.cs (centiseconds)
                def format_time(seconds):
                    hrs = int(seconds // 3600)
                    mins = int((seconds % 3600) // 60)
                    secs = int(seconds % 60)
                    csecs = int(round((seconds - int(seconds)) * 100))
                    if csecs == 100:
                        secs += 1
                        csecs = 0
                    return f"{hrs:d}:{mins:02d}:{secs:02d}.{csecs:02d}"

                start_str = format_time(start_sec)
                end_str = format_time(end_sec)
                
                lines.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{chunk_text}")

            current_time += scene_duration

        os.makedirs(os.path.dirname(ass_path), exist_ok=True)
        with open(ass_path, 'w', encoding='utf-8') as f:
            f.write(header)
            f.write("\n".join(lines))
            f.write("\n")
        print(f"ASS subtitle file written to {ass_path}")

    def compile_video(self, script, clips_paths: list, voiceover_path: str, background_path: str, output_path: str) -> bool:
        """
        Uses FFmpeg to crop, scale, trim, concatenate video clips, mix audio tracks,
        and burn in ASS subtitles.
        """
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Temp paths for build files
        ass_subs_path = output_path.replace(".mp4", ".ass")
        self.generate_ass_subtitles(script, ass_subs_path)

        # Build FFmpeg command inputs
        # -y: overwrite output
        # Inputs:
        # 0..N: Video clips
        # N+1: Voiceover audio
        # N+2: Background music
        cmd = [self.ffmpeg, "-y"]
        for path in clips_paths:
            cmd.extend(["-i", path])
            
        cmd.extend(["-i", voiceover_path])
        
        # If background music exists, add it as input
        bg_enabled = os.path.exists(background_path)
        if bg_enabled:
            cmd.extend(["-stream_loop", "-1", "-i", background_path]) # Loop background music indefinitely

        # Construct filter_complex
        filter_complex = []
        
        # 1. Scale, Crop, and Trim each input video clip to fit 1080x1920 and matching scene duration
        # We also force frame rate to 30fps and format to yuv420p for compatibility.
        v_idx = 0
        for i, scene in enumerate(script.scenes):
            duration = scene.duration
            # Scale, crop, color enhance (contrast and saturation), add vignette, and trim to duration
            filter_complex.append(
                f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase,"
                f"crop=1080:1920,eq=contrast=1.08:saturation=1.12:brightness=0.01,vignette=PI/5,"
                f"trim=0:{duration},setpts=PTS-STARTPTS,fps=30[v{i}]"
            )
            v_idx += 1

        # 2. Concatenate all vertical video tracks
        concat_videos = "".join([f"[v{i}]" for i in range(v_idx)])
        filter_complex.append(f"{concat_videos}concat=n={v_idx}:v=1:a=0[v_concated]")

        # 3. Burn the subtitles into the concatenated video track
        # Important: For the subtitles filter on Windows, backslashes must be escaped or forward slashes used.
        escaped_ass_path = ass_subs_path.replace("\\", "/").replace(":", "\\:")
        filter_complex.append(f"[v_concated]subtitles='{escaped_ass_path}'[v_final]")

        # 4. Mix voiceover and background audio
        voice_input_idx = len(clips_paths)
        bg_volume = self.config.get("music", {}).get("background_volume", 0.12)
        
        if bg_enabled:
            bg_input_idx = voice_input_idx + 1
            # Lower volume of background music, and mix it with voiceover.
            # We truncate the audio duration to the length of the voiceover track (duration=first)
            filter_complex.append(
                f"[{bg_input_idx}:a]volume={bg_volume}[bg_music]; "
                f"[{voice_input_idx}:a][bg_music]amix=inputs=2:duration=first[a_final]"
            )
        else:
            # No background music, just pass through voiceover audio
            filter_complex.append(f"[{voice_input_idx}:a]anull[a_final]")

        # Assemble filter complex parameter
        cmd.extend(["-filter_complex", "; ".join(filter_complex)])
        
        # Map output tracks
        cmd.extend(["-map", "[v_final]", "-map", "[a_final]"])
        
        # Encoding parameters for standard MP4 (H.264 + AAC)
        # faststart enables streaming play, crf 23 is standard high quality
        cmd.extend([
            "-c:v", "libx264",
            "-profile:v", "high",
            "-level:v", "4.2",
            "-pix_fmt", "yuv420p",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest", # stop rendering when shortest mapped track ends
            output_path
        ])

        print(f"Compiling video to {output_path}...")
        try:
            # Run FFmpeg process
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            print("Video compile successful!")
            # Clean up subtitle file after successful compile
            if os.path.exists(ass_subs_path):
                try:
                    os.remove(ass_subs_path)
                except:
                    pass
            return True
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg compilation failed with error code: {e.returncode}")
            print(f"FFmpeg stdout:\n{e.stdout}")
            print(f"FFmpeg stderr:\n{e.stderr}")
            return False
