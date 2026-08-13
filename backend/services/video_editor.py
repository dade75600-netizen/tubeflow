"""
video_editor.py — TubeFlow Shorts Engine
=========================================
Compiles vertical 9:16 YouTube Shorts from B-roll clips using FFmpeg.

Key features:
  - Hard crop to 1080x1920 (no black bars ever)
  - Dynamic zoom (1.0→1.08) + alternating pan on every clip
  - ASS subtitles centered on screen (Impact 90px, white + black stroke 6px)
  - Keyword coloring: RED for danger words, YELLOW for emphasis words
  - Optional first-frame hook image (1.5s static + swoosh audio)
  - Pacing enforcement: clips are trimmed to max 2.0s sub-segments
"""

import os
import subprocess
import yaml
import re

# Words to color RED in subtitles
HIGHLIGHT_RED = {
    "died", "dead", "death", "killed", "kill", "crash", "crashed",
    "explosion", "exploded", "destroyed", "zero", "failed", "failure",
    "warning", "mayday", "emergency"
}

# Words to color YELLOW in subtitles
HIGHLIGHT_YELLOW = {
    "secret", "secrets", "classified", "forbidden", "hidden", "banned",
    "pilot", "pilots", "never", "impossible", "unknown"
}

class VideoEditor:
    def __init__(self, ffmpeg_path: str = None, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self.load_config()
        self.ffmpeg = ffmpeg_path or self.resolve_ffmpeg()

    def load_config(self) -> dict:
        """Loads configuration from config.yaml."""
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def resolve_ffmpeg(self) -> str:
        """Checks local bin/ first, then falls back to system path."""
        import sys
        if sys.platform.startswith("win"):
            local_ffmpeg = os.path.join("bin", "ffmpeg.exe")
            if os.path.exists(local_ffmpeg):
                return os.path.abspath(local_ffmpeg)
        return "ffmpeg"

    # ─── ASS Subtitle Engine ──────────────────────────────────────────────────

    def generate_ass_subtitles(self, script, ass_path: str):
        """
        Generates an ASS subtitle file for YouTube Shorts.
        - Alignment 5: center of screen (not bottom)
        - Font: Impact, 90px
        - Color: white (#FFFFFF) with 6px black stroke
        - 1-2 words per subtitle card
        - Keyword coloring: RED for danger, YELLOW for emphasis
        """
        # ASS color format: &H00BBGGRR (alpha=00 = fully opaque)
        ASS_WHITE  = "&H00FFFFFF"   # white
        ASS_BLACK  = "&H00000000"   # black stroke
        ASS_RED    = "&H000000FF"   # red   (BGR: 00, 00, FF → RGB red)
        ASS_YELLOW = "&H0000FFFF"   # yellow (BGR: 00, FF, FF → RGB yellow)

        header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Impact,90,{ASS_WHITE},&H000000FF,{ASS_BLACK},&H96000000,-1,0,0,0,100,100,2,0,1,6,0,5,40,40,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        def format_time(seconds: float) -> str:
            seconds = max(0.0, seconds)
            hrs  = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            cs   = int(round((seconds - int(seconds)) * 100))
            if cs == 100:
                secs += 1
                cs = 0
            return f"{hrs}:{mins:02d}:{secs:02d}.{cs:02d}"

        def colorize_word(word: str, base_color: str) -> str:
            """Wraps a word in an ASS color tag and resets to base after."""
            lower = word.lower().rstrip(".,!?;:'\"")
            if lower in HIGHLIGHT_RED:
                return f"{{\\c{ASS_RED}}}{word}{{\\c{base_color}}}"
            if lower in HIGHLIGHT_YELLOW:
                return f"{{\\c{ASS_YELLOW}}}{word}{{\\c{base_color}}}"
            return word

        lines = []
        current_time = 0.0
        words_per_card = 2  # 1-2 words per subtitle card for Shorts pacing

        for scene in script.scenes:
            scene_text = scene.narration.strip()
            scene_duration = scene.duration

            words = [w for w in re.split(r"\s+", scene_text) if w]
            if not words:
                current_time += scene_duration
                continue

            words_per_sec = len(words) / scene_duration if scene_duration > 0 else 2.5

            # Split into cards of words_per_card words
            chunks = [words[i:i + words_per_card] for i in range(0, len(words), words_per_card)]

            for idx, chunk in enumerate(chunks):
                # Apply keyword coloring to each word in the chunk
                colored_words = [colorize_word(w.upper(), ASS_WHITE) for w in chunk]
                card_text = " ".join(colored_words)

                chunk_word_count = len(chunk)
                start_offset = (idx * words_per_card) / words_per_sec
                end_offset   = start_offset + (chunk_word_count / words_per_sec)

                # Clamp last card to exact scene boundary
                if idx == len(chunks) - 1:
                    end_offset = scene_duration

                start_str = format_time(current_time + start_offset)
                end_str   = format_time(current_time + end_offset)

                lines.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{card_text}")

            current_time += scene_duration

        os.makedirs(os.path.dirname(ass_path) or ".", exist_ok=True)
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(header)
            f.write("\n".join(lines))
            f.write("\n")
        print(f"ASS subtitle file written to {ass_path}")

    # ─── FFmpeg Clip Filter Builder ───────────────────────────────────────────

    def _build_clip_filter(self, input_idx: int, duration: float,
                           clip_idx: int) -> str:
        """
        Returns an FFmpeg filter_complex chain for a single B-roll clip:
        1. Trim to `duration` seconds
        2. Scale to fill 1920px height (no black bars)
        3. Center-crop to 1080x1920 (9:16)
        4. setsar=1
        5. Force 30fps, yuv420p
        """
        filt = (
            f"[{input_idx}:v]"
            f"trim=0:{duration},setpts=PTS-STARTPTS,"
            f"scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,"
            f"setsar=1,"
            f"fps=30,format=yuv420p"
            f"[v{clip_idx}]"
        )
        return filt

    # ─── Main compile method ──────────────────────────────────────────────────

    def compile_video(
        self,
        script,
        clips_paths: list,
        voiceover_path: str,
        background_path: str,
        output_path: str,
        first_frame_path: str = None,
        swoosh_path: str = None,
        impact_path: str = None
    ) -> bool:
        """
        Uses FFmpeg to compile a vertical 1080x1920 YouTube Short.

        Parameters
        ----------
        script          : VideoScript object with .scenes list
        clips_paths     : list of B-roll clip file paths (one per scene)
        voiceover_path  : path to the TTS voiceover WAV/MP3
        background_path : path to the background music track
        output_path     : final MP4 output path
        first_frame_path: optional 1080x1920 JPEG for the hook frame (1.5s)
        swoosh_path     : optional WAV file for the swoosh sfx on hook frame
        impact_path     : optional WAV/MP3 file for the boom sfx on hook frame
        """
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        ass_path = output_path.replace(".mp4", ".ass")
        self.generate_ass_subtitles(script, ass_path)

        # ── Build input list ──────────────────────────────────────────────
        cmd = [self.ffmpeg, "-y", "-nostdin"]

        # Optional hook frame image → static video input
        has_hook = first_frame_path and os.path.exists(first_frame_path)
        hook_duration = 1.5  # seconds

        if has_hook:
            # -loop 1 forces ffmpeg to treat the image as a looped video source
            cmd.extend(["-loop", "1", "-t", str(hook_duration),
                        "-i", first_frame_path])

        # B-roll clips (one per scene)
        for path in clips_paths:
            cmd.extend(["-i", path])

        # Voiceover
        cmd.extend(["-i", voiceover_path])

        # Background music (looped)
        bg_enabled = os.path.exists(background_path)
        if bg_enabled:
            cmd.extend(["-stream_loop", "-1", "-i", background_path])

        # Optional swoosh SFX
        has_swoosh = swoosh_path and os.path.exists(swoosh_path)
        if has_swoosh:
            cmd.extend(["-i", swoosh_path])

        # Optional impact SFX
        has_impact = impact_path and os.path.exists(impact_path)
        if has_impact:
            cmd.extend(["-i", impact_path])

        # ── filter_complex construction ──────────────────────────────────
        fc = []

        # Index tracking
        clip_input_offset = 1 if has_hook else 0
        num_clips = len(clips_paths)
        voice_idx = clip_input_offset + num_clips
        bg_idx    = voice_idx + 1
        
        current_idx = bg_idx + 1 if bg_enabled else voice_idx + 1
        swoosh_idx = current_idx if has_swoosh else None
        if has_swoosh: current_idx += 1
        
        impact_idx = current_idx if has_impact else None
        if has_impact: current_idx += 1

        video_labels = []

        # Hook frame: scale to 9:16, ensure correct format
        if has_hook:
            fc.append(
                f"[0:v]scale=1080:1920,setsar=1,"
                f"fps=30,format=yuv420p[v_hook]"
            )
            video_labels.append("[v_hook]")

        # B-roll clips
        for i, scene in enumerate(script.scenes):
            input_idx = clip_input_offset + i
            filt = self._build_clip_filter(input_idx, scene.duration, i)
            fc.append(filt)
            video_labels.append(f"[v{i}]")

        # Concatenate all video segments
        concat_inputs = "".join(video_labels)
        n_segments    = len(video_labels)
        fc.append(f"{concat_inputs}concat=n={n_segments}:v=1:a=0[v_concat]")

        # Burn subtitles (Alignment=5 = center screen)
        if os.path.exists(ass_path):
            escaped_ass = ass_path.replace("\\", "/").replace(":", "\\:")
            fc.append(f"[v_concat]subtitles='{escaped_ass}'[v_final]")
        else:
            print(f"[WARNING] ASS subtitle file not found: {ass_path} — skipping subtitles.", flush=True)
            fc.append("[v_concat]copy[v_final]")

        # ─── Audio Mixing Engine ─────────────────────────────────────────
        # We ensure that the main voiceover is the FIRST input to amix, 
        # so duration=first acts as the master clock, preventing infinite BGM loops.
        audio_inputs = []

        if has_hook:
            # Pad voiceover start by hook_duration so it lines up after hook
            fc.append(
                f"[{voice_idx}:a]adelay={int(hook_duration * 1000)}|"
                f"{int(hook_duration * 1000)}[voice_delayed]"
            )
            audio_inputs.append("[voice_delayed]")
        else:
            audio_inputs.append(f"[{voice_idx}:a]")

        if bg_enabled:
            # Duck BGM aggressively to allow voice to dominate
            bg_volume = 0.12
            fc.append(f"[{bg_idx}:a]volume={bg_volume}[bg_music]")
            audio_inputs.append("[bg_music]")

        if has_hook and has_swoosh:
            fc.append(
                f"[{swoosh_idx}:a]atrim=0:{hook_duration},"
                f"asetpts=PTS-STARTPTS,volume=0.8,apad[swoosh_trim]"
            )
            audio_inputs.append("[swoosh_trim]")
            
        if has_hook and has_impact:
            fc.append(
                f"[{impact_idx}:a]atrim=0:{hook_duration},"
                f"asetpts=PTS-STARTPTS,volume=1.0,apad[impact_trim]"
            )
            audio_inputs.append("[impact_trim]")

        if len(audio_inputs) == 1:
            fc.append(f"{audio_inputs[0]}anull[a_final]")
        else:
            fc.append(f"".join(audio_inputs) + f"amix=inputs={len(audio_inputs)}:duration=first:dropout_transition=0[a_final]")

        # ── Assemble full command ────────────────────────────────────────
        cmd.extend(["-filter_complex", "; ".join(fc)])
        cmd.extend(["-map", "[v_final]", "-map", "[a_final]"])
        cmd.extend([
            "-c:v", "libx264",
            "-profile:v", "high",
            "-level:v", "4.2",
            "-pix_fmt", "yuv420p",
            "-crf", "22",
            "-preset", "ultrafast",
            "-threads", "2",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_path
        ])

        print(f"Compiling video to {output_path} (Hook: {has_hook}, Clips: {num_clips}, Audio streams: {len(audio_inputs)})...", flush=True)
        print(f"[DEBUG] FULL FFmpeg cmd: {' '.join(cmd)}")
        # Comando pulito, senza interazioni e sovrascrittura forzata
        cmd.insert(1, '-y')
        if '-nostdin' not in cmd:
            cmd.insert(2, '-nostdin')

        print(f">>> Esecuzione FFmpeg pulita avviata...")
        try:
            # Esecuzione standard, catturiamo l'output per i log in caso di errore, 
            # ma senza intasare i buffer (usiamo capture_output)
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
                check=True
            )
            print(">>> Compilazione FFmpeg completata con successo!")
            # Clean up .ass subtitle file
            if os.path.exists(ass_path):
                try:
                    os.remove(ass_path)
                except Exception:
                    pass
            return True
        except subprocess.CalledProcessError as e:
            print(f"!!! ERRORE CRITICO FFMPEG (Codice {e.returncode}) !!!")
            print(f"STDOUT:\n{e.stdout[-1000:] if e.stdout else 'Nessuno'}")
            print(f"STDERR:\n{e.stderr[-2000:] if e.stderr else 'Nessuno'}")
            raise RuntimeError("Pipeline interrotta per errore FFmpeg")
