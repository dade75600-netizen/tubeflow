"""
first_frame_engineer.py — TubeFlow Viral Shorts Hook Frame Generator
======================================================================
Generates a 1080x1920 (9:16) hyper-saturated hook image injected as the
first 1.5 seconds of every Short, accompanied by a programmatically
generated "swoosh/boom" SFX WAV file.

The hook frame is designed to stop the scroll in the first 1.5 seconds
by displaying the video's punchline in enormous, high-contrast text
against a vibrant, color-graded background.

Visual design:
  - Background: Pexels vertical photo (portrait orientation) with
    saturation ×2.0, contrast ×1.8, and a centered crop to 1080x1920.
    Falls back to dark navy + green grid if no valid photo found.
  - Punchline text: Impact / Arial Black, 160px, centered vertically,
    white fill with 10px black stroke.
  - Red accent bar: full-width 8px bar above and below the text box.
  - Yellow flash highlights: 2 diagonal accent lines at top-right corner.
  - Channel badge: top-left pill with channel handle in small caps.
"""

import os
import re
import math
import wave
import struct
import random
import requests
import yaml
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

# ── Pexels blacklist: reject civilian aviation assets on military frames ──────
BLACKLIST_WORDS = [
    "airline", "aeroflot", "airport", "passenger",
    "civil", "commercial", "terminal"
]

# ── Military punchline pool ───────────────────────────────────────────────────
MILITARY_POOL = [
    "CLASSIFIED", "TOP SECRET", "NEVER TOLD",
    "THEY KNEW", "BURIED TRUTH", "ZERO SURVIVORS",
    "LAST MISSION", "SILENT WAR", "FORBIDDEN",
    "CODE BLACK", "OPERATION X"
]

# ── Aviation punchline pool ───────────────────────────────────────────────────
AVIATION_POOL = [
    "CLOSE CALL", "ENGINE FAIL", "NEAR DISASTER",
    "PILOT ERROR?", "CRITICAL FAULT", "LOST CONTROL",
    "EXTREME WIND", "MAYDAY", "DEADSTICK",
    "EMERGENCY!", "NO SURVIVORS"
]


class FirstFrameEngineer:
    """
    Generates a 1080×1920 hook image and a swoosh SFX WAV.
    Designed to be the first 1.5 seconds of every YouTube Short.
    """

    W, H = 1080, 1920  # Shorts resolution

    def __init__(self, pexels_key: str = None, config_path: str = "config.yaml"):
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        self.pexels_key = pexels_key or os.getenv("PEXELS_API_KEY")
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> dict:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                pass
        return {}

    # ── Punchline selection ───────────────────────────────────────────────────

    def _select_punchline(self, topic: str, profile: dict = None) -> str:
        tone = (profile or {}).get("script_tone", "classified_documentary")
        pool = AVIATION_POOL if tone == "aviation_documentary" else MILITARY_POOL
        idx = sum(ord(c) for c in topic) % len(pool)
        return pool[idx]

    # ── Pexels background fetcher (portrait / vertical) ───────────────────────

    def _fetch_pexels_background(self, topic: str, is_military: bool) -> Image.Image | None:
        if not self.pexels_key:
            return None

        cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", topic).strip()
        keywords = " ".join(cleaned.split()[:4])
        suffix   = " night dark" if is_military else ""
        query    = f"{keywords}{suffix}"

        try:
            url = (
                f"https://api.pexels.com/v1/search"
                f"?query={requests.utils.quote(query)}"
                f"&per_page=3&orientation=portrait"
            )
            headers  = {"Authorization": self.pexels_key}
            response = requests.get(url, headers=headers, timeout=12)
            response.raise_for_status()
            photos = response.json().get("photos", [])

            for photo in photos:
                img_url   = photo.get("src", {}).get("portrait") or \
                            photo.get("src", {}).get("large2x")
                page_url  = photo.get("url", "")
                alt_text  = photo.get("alt", "")
                meta      = f"{img_url} {page_url} {alt_text}".lower()

                if any(w in meta for w in BLACKLIST_WORDS):
                    print(f"[FirstFrame] Pexels photo blacklisted: {page_url}")
                    continue

                img_data = requests.get(img_url, timeout=12)
                img_data.raise_for_status()

                from io import BytesIO
                img = Image.open(BytesIO(img_data.content)).convert("RGB")
                print(f"[FirstFrame] Pexels photo downloaded: {img_url}")
                return img

        except Exception as e:
            print(f"[FirstFrame] Pexels fetch failed: {e}")
        return None

    # ── Fallback background generator ────────────────────────────────────────

    def _make_fallback_bg(self) -> Image.Image:
        """Dark navy background with military green radar grid."""
        img     = Image.new("RGB", (self.W, self.H), (12, 18, 28))
        overlay = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        draw    = ImageDraw.Draw(overlay)
        step    = 60
        for x in range(0, self.W, step):
            draw.line([(x, 0), (x, self.H)], fill=(20, 40, 20, 60), width=1)
        for y in range(0, self.H, step):
            draw.line([(0, y), (self.W, y)], fill=(20, 40, 20, 60), width=1)
        img = Image.alpha_composite(img.convert("RGBA"), overlay)
        return img.convert("RGB")

    # ── Background processing ─────────────────────────────────────────────────

    def _process_background(self, raw_img: Image.Image) -> Image.Image:
        """Center-crop to 1080x1920, boost saturation ×2.0 and contrast ×1.8."""
        # Scale to fill height
        ratio  = self.H / raw_img.height
        new_w  = int(raw_img.width * ratio)
        resized = raw_img.resize((max(new_w, self.W), self.H),
                                 Image.Resampling.LANCZOS)
        # Center crop width
        left  = (resized.width - self.W) // 2
        img   = resized.crop((left, 0, left + self.W, self.H))

        img = ImageEnhance.Color(img).enhance(2.0)
        img = ImageEnhance.Contrast(img).enhance(1.8)
        img = ImageEnhance.Brightness(img).enhance(0.85)
        return img

    # ── Visual overlay layers ─────────────────────────────────────────────────

    def _apply_dark_vignette(self, img: Image.Image) -> Image.Image:
        """Radial dark vignette to focus on center text."""
        vignette = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        draw     = ImageDraw.Draw(vignette)
        cx, cy   = self.W // 2, self.H // 2
        max_r    = math.sqrt(cx**2 + cy**2)
        for r in range(int(max_r), 0, -8):
            alpha = int(180 * (r / max_r) ** 1.5)
            alpha = max(0, 180 - alpha)
            draw.ellipse(
                [cx - r, cy - r, cx + r, cy + r],
                fill=(0, 0, 0, alpha)
            )
        return Image.alpha_composite(img.convert("RGBA"), vignette).convert("RGB")

    def _draw_red_accent_bars(self, draw: ImageDraw.Draw,
                               box_top: int, box_bottom: int):
        """Full-width red accent bars above and below the text box."""
        bar_h = 8
        draw.rectangle([(0, box_top - bar_h - 4), (self.W, box_top - 4)],
                        fill=(220, 30, 30))
        draw.rectangle([(0, box_bottom + 4), (self.W, box_bottom + bar_h + 4)],
                        fill=(220, 30, 30))

    def _draw_yellow_corner_accents(self, draw: ImageDraw.Draw):
        """Two diagonal yellow accent lines at top-right corner."""
        for i in range(2):
            offset = i * 20
            draw.line(
                [(self.W - 60 + offset, 60), (self.W - 10 + offset, 120)],
                fill=(255, 220, 0),
                width=5
            )

    def _draw_channel_badge(self, draw: ImageDraw.Draw,
                             channel_handle: str, font_path: str):
        """Small channel handle pill at top-left."""
        try:
            badge_font = ImageFont.truetype(font_path, size=28)
        except Exception:
            badge_font = ImageFont.load_default()

        text  = channel_handle.upper()
        bbox  = draw.textbbox((0, 0), text, font=badge_font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pad   = 14
        rx1, ry1 = 24, 32
        rx2, ry2 = rx1 + tw + pad * 2, ry1 + th + pad

        # Semi-transparent black pill
        pill_overlay = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        pd = ImageDraw.Draw(pill_overlay)
        pd.rounded_rectangle([rx1, ry1, rx2, ry2], radius=10, fill=(0, 0, 0, 160))
        return pill_overlay, badge_font, text, (rx1 + pad - bbox[0], ry1 + pad // 2 - bbox[1])

    # ── Punchline text renderer ───────────────────────────────────────────────

    def _draw_punchline(self, img: Image.Image, punchline: str,
                         is_military: bool, font_path: str) -> Image.Image:
        """
        Renders the punchline in enormous Impact text, centered vertically,
        with white fill + 10px black stroke, on a semi-transparent backing.
        """
        words     = punchline.upper().split()
        font_size = 160 if len(words) <= 2 else (130 if len(words) == 3 else 110)

        try:
            font = ImageFont.truetype(font_path, size=font_size)
        except Exception:
            font = ImageFont.load_default()

        draw = ImageDraw.Draw(img)

        # Split into max 2 lines
        if len(words) <= 2:
            lines = words
        elif len(words) == 3:
            lines = [" ".join(words[:2]), words[2]]
        else:
            mid   = (len(words) + 1) // 2
            lines = [" ".join(words[:mid]), " ".join(words[mid:])]
        lines = lines[:2]

        # Measure
        bboxes    = [draw.textbbox((0, 0), l, font=font) for l in lines]
        widths    = [b[2] - b[0] for b in bboxes]
        heights   = [b[3] - b[1] for b in bboxes]
        spacing   = 20
        total_h   = sum(heights) + spacing * (len(lines) - 1)

        # Center vertically in the middle band (40%–65% of height)
        band_top    = int(self.H * 0.38)
        band_bottom = int(self.H * 0.68)
        y_start     = band_top + (band_bottom - band_top - total_h) // 2

        # Background box
        max_w    = max(widths)
        box_pad  = 40
        box_x1   = (self.W - max_w) // 2 - box_pad
        box_y1   = y_start - box_pad
        box_x2   = (self.W + max_w) // 2 + box_pad
        box_y2   = y_start + total_h + box_pad

        bg_overlay = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        bg_draw    = ImageDraw.Draw(bg_overlay)
        bg_draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2],
                                   radius=20, fill=(0, 0, 0, 180))
        img = Image.alpha_composite(img.convert("RGBA"), bg_overlay).convert("RGB")

        draw = ImageDraw.Draw(img)

        # Red accent bars
        self._draw_red_accent_bars(draw, box_y1, box_y2)
        self._draw_yellow_corner_accents(draw)

        # Text rendering
        running_y = y_start
        for i, (line, bbox, w, h) in enumerate(zip(lines, bboxes, widths, heights)):
            x = (self.W - w) // 2 - bbox[0]
            y = running_y - bbox[1]
            fill = (255, 255, 255) if is_military else \
                   ((255, 220, 0) if i == 0 else (255, 255, 255))
            try:
                draw.text((x, y), line, font=font, fill=fill,
                           stroke_fill=(0, 0, 0), stroke_width=10)
            except TypeError:
                for ox in range(-10, 11):
                    for oy in range(-10, 11):
                        if ox != 0 or oy != 0:
                            draw.text((x + ox, y + oy), line, font=font,
                                       fill=(0, 0, 0))
                draw.text((x, y), line, font=font, fill=fill)
            running_y += h + spacing

        return img, box_y1, box_y2

    # ── Public API ────────────────────────────────────────────────────────────

    def create_hook_frame(
        self,
        topic: str,
        output_path: str,
        profile: dict = None,
        punchline: str = None,
    ) -> bool:
        """
        Generates the 1080x1920 hook image and saves it to output_path.

        Returns True on success, False on failure.
        """
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        tone        = (profile or {}).get("script_tone", "classified_documentary")
        is_military = tone != "aviation_documentary"
        channel_handle = (profile or {}).get("channel_handle", "@TubeFlow")
        punch_text  = (punchline or self._select_punchline(topic, profile)).upper()

        print(f"[FirstFrame] Generating hook frame: [Punchline: {punch_text}] for '{topic}'")

        # 1. Background
        raw = self._fetch_pexels_background(topic, is_military)
        if raw:
            bg = self._process_background(raw)
        else:
            print("[FirstFrame] Using fallback dark background + grid.")
            bg = self._make_fallback_bg()

        # 2. Vignette
        bg = self._apply_dark_vignette(bg)

        # 3. Font resolution
        font_candidates = [
            "C:\\Windows\\Fonts\\impact.ttf",
            "C:\\Windows\\Fonts\\arialbd.ttf",
            "/usr/share/fonts/truetype/msttcorefonts/Impact.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        ]
        font_path = next((f for f in font_candidates if os.path.exists(f)), None)
        if not font_path:
            font_path = ""  # will use default

        # 4. Punchline text
        img, box_y1, box_y2 = self._draw_punchline(bg, punch_text, is_military, font_path)

        # 5. Channel badge
        draw = ImageDraw.Draw(img)
        if font_path:
            pill_overlay, badge_font, badge_text, (tx, ty) = \
                self._draw_channel_badge(draw, channel_handle, font_path)
            img = Image.alpha_composite(img.convert("RGBA"), pill_overlay).convert("RGB")
            draw = ImageDraw.Draw(img)
            draw.text((tx, ty), badge_text, font=badge_font, fill=(200, 200, 200))

        # 6. Save
        img.save(output_path, "JPEG", quality=92)
        print(f"[FirstFrame] Hook frame saved to: {output_path}")
        return True

    def create_swoosh_wav(self, output_path: str, duration_ms: int = 800) -> bool:
        """
        Programmatically generates a synthetic "swoosh/boom" SFX WAV file.
        The sound is a frequency-swept sine wave (600Hz→80Hz) with an
        exponential amplitude decay — a classic cinematic "impact" sound.
        """
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        sample_rate = 44100
        n_samples   = int(sample_rate * duration_ms / 1000)
        frames      = []

        for i in range(n_samples):
            t       = i / sample_rate
            progress = i / n_samples  # 0.0 → 1.0

            # Frequency sweep: 600Hz → 80Hz (exponential descent)
            freq    = 600.0 * math.exp(-progress * 2.0) + 80.0
            # Amplitude envelope: fast attack, exponential decay
            amp     = 0.7 * math.exp(-progress * 4.5)
            # White noise layer for the "swoosh" texture
            noise   = random.uniform(-0.15, 0.15)
            # Combine
            sample  = math.sin(2 * math.pi * freq * t) * amp + noise * (1.0 - progress)
            # Clamp and convert to 16-bit int
            value   = max(-1.0, min(1.0, sample))
            frames.append(struct.pack("<h", int(value * 32767)))

        try:
            with wave.open(output_path, "w") as wf:
                wf.setnchannels(1)        # mono
                wf.setsampwidth(2)        # 16-bit
                wf.setframerate(sample_rate)
                wf.writeframes(b"".join(frames))
            print(f"[FirstFrame] Swoosh WAV saved to: {output_path}")
            return True
        except Exception as e:
            print(f"[FirstFrame] Failed to write swoosh WAV: {e}")
            return False


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    eng = FirstFrameEngineer()

    success = eng.create_hook_frame(
        topic="The Soviet Submarine That Almost Started WW3",
        output_path="test_hook_military.jpg",
        punchline="TOP SECRET"
    )
    print(f"Hook frame generated: {success}")

    success = eng.create_swoosh_wav("test_swoosh.wav")
    print(f"Swoosh WAV generated: {success}")
