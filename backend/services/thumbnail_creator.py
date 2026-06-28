import os
import requests
import random
import math
import re
import yaml
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

class ThumbnailCreator:
    def __init__(self, pexels_key: str = None, config_path: str = "config.yaml"):
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        self.pexels_key = pexels_key or os.getenv("PEXELS_API_KEY")
        self.config_path = config_path
        self.config = self.load_config()

    def load_config(self) -> dict:
        """Loads configuration from config.yaml."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Error reading configuration file: {e}")
        return {}

    def _detect_category(self, query: str) -> str:
        """
        Classifies the topic query into either 'military' or 'civil' aviation.
        """
        query_lower = query.lower()
        
        military_keywords = [
            "military", "army", "navy", "airforce", "air force", "combat", "fighter", 
            "bomber", "stealth", "weapon", "tank", "missile", "war", "soldier", 
            "carrier", "submarine", "tactical", "f-16", "f-22", "f-35", "su-57", 
            "mig-29", "su-27", "a-10", "warthog", "apache", "predator", "raptor", 
            "viper", "tomcat", "hornet", "flanker", "hind", "blackhawk", "destroyer", 
            "battleship", "gunship", "dogfight", "jet"
        ]
        
        civil_keywords = [
            "civil", "passenger", "airliner", "commercial", "boeing", "airbus", 
            "cessna", "concorde", "airport", "flight", "airline", "cargo", 
            "landing", "takeoff", "private jet", "glider", "travel", "turboprop", 
            "propeller", "fly", "pilots", "air traffic", "safety", "airways", 
            "aviation"
        ]
        
        military_score = sum(1 for kw in military_keywords if kw in query_lower)
        civil_score = sum(1 for kw in civil_keywords if kw in query_lower)
        
        if military_score > civil_score:
            return "military"
        elif civil_score > military_score:
            return "civil"
        else:
            niche = str(self.config.get("channel", {}).get("niche", "")).lower()
            if "civil" in niche or "commercial" in niche or "passenger" in niche:
                return "civil"
            return "military"

    def _generate_punchline(self, query: str, category: str, profile: dict = None) -> str:
        """
        Converts the topic query into a dramatic, high-impact punchline (MAX 3 WORDS in ALL CAPS).
        """
        is_military = False
        if profile and profile.get("thumbnail_palette") == "red_white":
            is_military = True
        elif category == "military":
            is_military = True

        if is_military:
            # Exclusive military hook pool
            military_pool = [
                "CLASSIFIED", "TOP SECRET", "NEVER TOLD", "THEY KNEW", 
                "BURIED TRUTH", "ZERO SURVIVORS", "LAST MISSION", "SILENT WAR"
            ]
        else:
            military_pool = [
                "MOST FEARED", "TOP SECRET", "BORN TO KILL", "LETHAL FORCE", 
                "NO ESCAPE", "PURE POWER", "DEADLY BEAST", "WAR MACHINE", 
                "TOTAL POWER", "PREDATOR", "FATAL BLOW", "AIR DOMINANCE", 
                "MAX SPEED", "ATTACK MODE", "FIREPOWER"
            ]
        
        civil_pool = [
            "CLOSE CALL", "NEAR DISASTER", "INSANE LANDING", "MEGA JET", 
            "SUPERSONIC", "JET AGE", "FLIGHT CRITICAL", "PILOT ERROR?", 
            "CRITICAL FAULT", "LOST CONTROL", "EXTREME WIND", "SKY BEAST", 
            "ENGINE FAIL", "SAVED LIVES"
        ]
        
        pool = military_pool if category == "military" else civil_pool
        # Deterministic stable choice
        index = sum(ord(c) for c in query) % len(pool)
        return pool[index]

    def create_thumbnail(
        self,
        query: str,
        output_path: str,
        add_arrow: bool = False,
        add_circle: bool = False,
        punchline: str = None,
        profile: dict = None
    ) -> bool:
        """
        Downloads a background stock photo from Pexels, crops/enhances it,
        applies dynamic-sized styled text, and overlays visual accents if requested.
        """
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        
        # 1. Detect Category & Determine Settings
        category = self._detect_category(query)
        
        # Resolve military configuration context
        is_military = False
        if profile and profile.get("thumbnail_palette") == "red_white":
            is_military = True
        elif not profile and category == "military":
            is_military = True
            
        # Default arrow option if military active
        if is_military:
            add_arrow = True

        punchline_text = punchline.upper() if punchline else self._generate_punchline(query, category, profile)
        print(f"Creating thumbnail: [Category: {category}] [Punchline: {punchline_text}] for '{query}'")
        
        # 2. Fetch Background from Pexels
        bg_downloaded = False
        temp_bg_path = output_path.replace(".jpg", "_raw.jpg")
        blacklist_suffix = " -commercial -passenger -airliner -vintage"
        
        if self.pexels_key:
            headers = {"Authorization": self.pexels_key}
            
            cleaned_query = re.sub(r'[^a-zA-Z0-9\s-]', '', query).strip()
            search_keywords = " ".join(cleaned_query.split()[:4])
            
            # Sfondo: preferire immagini scure/notturne per la nicchia militare
            if is_military:
                primary_search = f"{search_keywords} night{blacklist_suffix}"
            else:
                primary_search = f"{search_keywords}{blacklist_suffix}"
            
            try:
                url = f"https://api.pexels.com/v1/search?query={requests.utils.quote(primary_search)}&per_page=1&orientation=landscape"
                print(f"Searching Pexels: '{primary_search}'...")
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                data = response.json()
                photos = data.get("photos", [])
                
                if photos:
                    img_url = photos[0].get("src", {}).get("large2x") or photos[0].get("src", {}).get("large")
                    if img_url:
                        # Combine Pexels page URL, image asset URL, and alt description for comprehensive blacklist checks
                        page_url = photos[0].get("url", "")
                        alt_text = photos[0].get("alt", "")
                        check_metadata = f"{img_url} {page_url} {alt_text}".lower()
                        
                        blacklist_words = ["airline", "aeroflot", "airport", "passenger", "civil", "commercial"]
                        if any(w in check_metadata for w in blacklist_words):
                            print(f"Pexels image rejected due to blacklist match in metadata: {check_metadata}")
                        else:
                            print(f"Downloading Pexels image: {img_url}...")
                            img_data = requests.get(img_url, timeout=15)
                            img_data.raise_for_status()
                            with open(temp_bg_path, 'wb') as f:
                                f.write(img_data.content)
                            bg_downloaded = True
                else:
                    print("Pexels search returned no photos.")
            except Exception as e:
                print(f"Pexels API query or image download failed: {e}")
        else:
            print("No Pexels API key found.")

        try:
            # 3. Create or Load Image & Resize
            if bg_downloaded and os.path.exists(temp_bg_path):
                img = Image.open(temp_bg_path)
                img = img.resize((1280, 720), Image.Resampling.LANCZOS)
            else:
                print("Using fallback solid dark background RGB(12,18,28) with military texture...")
                img = Image.new("RGB", (1280, 720), color=(12, 18, 28))
                
                # Draw military green grid texture overlay
                overlay = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
                overlay_draw = ImageDraw.Draw(overlay)
                grid_size = 40
                
                # Thin military green lines (20, 40, 20) semi-transparent (alpha 80)
                for x in range(0, 1280, grid_size):
                    overlay_draw.line([(x, 0), (x, 720)], fill=(20, 40, 20, 80), width=1)
                for y in range(0, 720, grid_size):
                    overlay_draw.line([(0, y), (1280, y)], fill=(20, 40, 20, 80), width=1)
                
                img = img.convert("RGBA")
                img = Image.alpha_composite(img, overlay)
                img = img.convert("RGB")
            
            # 4. Boost Contrast and Saturation
            # Military contrast boost: 1.5, Civil contrast boost: 1.3
            contrast_val = 1.3
            if profile and "bg_contrast_boost" in profile:
                contrast_val = profile["bg_contrast_boost"]
            elif is_military:
                contrast_val = 1.5
                
            contrast_enhancer = ImageEnhance.Contrast(img)
            img = contrast_enhancer.enhance(contrast_val)
            
            saturation_enhancer = ImageEnhance.Color(img)
            img = saturation_enhancer.enhance(1.4)
            
            # 5. Apply Aggressive Bottom Vignette
            vignette = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
            vignette_draw = ImageDraw.Draw(vignette)
            for y in range(720):
                alpha = int(((y / 720) ** 1.6) * 200)
                vignette_draw.line([(0, y), (1280, y)], fill=(0, 0, 0, alpha))
            img = img.convert("RGBA")
            img = Image.alpha_composite(img, vignette)
            img = img.convert("RGB")
            
            draw = ImageDraw.Draw(img)
            
            # 6. Draw Red Circle & Arrow Visual Accents
            if add_circle:
                center_x, center_y = 850, 260
                r = 90
                draw.ellipse(
                    [center_x - r, center_y - r, center_x + r, center_y + r],
                    outline=(220, 30, 30),
                    width=12
                )
            
            if add_arrow:
                start_x, start_y = 1050, 100
                end_x, end_y = 920, 200
                
                # Draw arrow shaft
                draw.line([(start_x, start_y), (end_x, end_y)], fill=(220, 30, 30), width=12)
                
                # Draw arrowhead
                dx = end_x - start_x
                dy = end_y - start_y
                length = math.sqrt(dx**2 + dy**2)
                if length > 0:
                    ux = dx / length
                    uy = dy / length
                    px = -uy
                    py = ux
                    
                    arrow_size = 35
                    c1_x = end_x - ux * arrow_size + px * (arrow_size * 0.6)
                    c1_y = end_y - uy * arrow_size + py * (arrow_size * 0.6)
                    c2_x = end_x - ux * arrow_size - px * (arrow_size * 0.6)
                    c2_y = end_y - uy * arrow_size - py * (arrow_size * 0.6)
                    
                    draw.polygon(
                        [(end_x, end_y), (c1_x, c1_y), (c2_x, c2_y)],
                        fill=(220, 30, 30)
                    )
            
            # 7. Draw Topic Label in Top-Left (Truncated to 40 chars, Pill container)
            truncated_query = query[:40]
            if len(query) > 40:
                truncated_query = query[:37] + "..."
            
            label_font_path = "C:\\Windows\\Fonts\\arial.ttf"
            if not os.path.exists(label_font_path):
                label_font_path = "C:\\Windows\\Fonts\\arialbd.ttf"
            
            if os.path.exists(label_font_path):
                label_font = ImageFont.truetype(label_font_path, size=18)
            else:
                label_font = ImageFont.load_default()
            
            label_bbox = draw.textbbox((0, 0), truncated_query, font=label_font)
            l_w = label_bbox[2] - label_bbox[0]
            l_h = label_bbox[3] - label_bbox[1]
            
            pill_x1, pill_y1 = 20, 20
            pill_x2 = pill_x1 + l_w + 24
            pill_y2 = pill_y1 + l_h + 16
            
            pill_overlay = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
            pill_draw = ImageDraw.Draw(pill_overlay)
            pill_draw.rounded_rectangle(
                [pill_x1, pill_y1, pill_x2, pill_y2],
                radius=8,
                fill=(0, 0, 0, 128)
            )
            
            img = img.convert("RGBA")
            img = Image.alpha_composite(img, pill_overlay)
            img = img.convert("RGB")
            draw = ImageDraw.Draw(img)
            
            text_x = pill_x1 + 12 - label_bbox[0]
            text_y = pill_y1 + 8 - label_bbox[1]
            draw.text((text_x, text_y), truncated_query, font=label_font, fill=(180, 180, 180))
            
            # 8. Split Punchline text, select Dynamic Font Size and Fonts
            words = [w.upper() for w in punchline_text.split() if w]
            num_words = len(words)
            if num_words <= 2:
                font_size = 140
            elif num_words == 3:
                font_size = 115
            else:
                font_size = 95
            
            font_path = "C:\\Windows\\Fonts\\impact.ttf"
            if not os.path.exists(font_path):
                font_path = "C:\\Windows\\Fonts\\arialbd.ttf"
            
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, size=font_size)
            else:
                font = ImageFont.load_default()
            
            # Format punchline into max 2 lines
            if len(words) <= 1:
                lines = words
            elif len(words) == 2:
                lines = words
            elif len(words) == 3:
                lines = [" ".join(words[:2]), words[2]]
            else:
                mid = (len(words) + 1) // 2
                lines = [" ".join(words[:mid]), " ".join(words[mid:])]
            
            lines = lines[:2]
            
            # Measure layout lines
            line_bboxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
            line_widths = [bbox[2] - bbox[0] for bbox in line_bboxes]
            line_heights = [bbox[3] - bbox[1] for bbox in line_bboxes]
            
            line_spacing = 15
            total_text_height = sum(line_heights) + line_spacing * (len(lines) - 1)
            
            # Vertically center in bottom third (y >= 65% of 720 = 468)
            y_start = 468 + (720 - 468 - total_text_height) // 2
            
            # Bounds checking
            if y_start + total_text_height > 710:
                y_start = 710 - total_text_height
            if y_start < 468:
                y_start = 468
            
            # 9. Semi-transparent black rectangle backing
            max_width = max(line_widths) if line_widths else 0
            box_width = max_width + 60
            box_height = total_text_height + 40
            box_x = (1280 - box_width) // 2
            box_y = y_start - 20
            
            text_bg_overlay = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
            bg_draw = ImageDraw.Draw(text_bg_overlay)
            bg_draw.rounded_rectangle(
                [box_x, box_y, box_x + box_width, box_y + box_height],
                radius=15,
                fill=(0, 0, 0, 153) # 60% opacity black
            )
            
            img = img.convert("RGBA")
            img = Image.alpha_composite(img, text_bg_overlay)
            img = img.convert("RGB")
            draw = ImageDraw.Draw(img)
            
            # 10. Draw text with thick stroke and correct coloring (yelllow for 1st line, white for 2nd)
            running_y = y_start
            for i, line in enumerate(lines):
                line_w = line_widths[i]
                line_h = line_heights[i]
                line_bbox = line_bboxes[i]
                
                x = (1280 - line_w) // 2 - line_bbox[0]
                y = running_y - line_bbox[1]
                
                # Check palette selection (military uses red_white which has white-only text text_fill)
                if is_military:
                    text_fill = (255, 255, 255) # White only
                else:
                    text_fill = (255, 220, 0) if i == 0 else (255, 255, 255) # Yellow/White
                    
                stroke_width = 8
                
                try:
                    draw.text(
                        (x, y), line, font=font, fill=text_fill,
                        stroke_fill=(0, 0, 0), stroke_width=stroke_width
                    )
                except TypeError:
                    # Fallback for old Pillow versions
                    for ox in range(-stroke_width, stroke_width + 1):
                        for oy in range(-stroke_width, stroke_width + 1):
                            if ox != 0 or oy != 0:
                                draw.text((x + ox, y + oy), line, font=font, fill=(0, 0, 0))
                    draw.text((x, y), line, font=font, fill=text_fill)
                
                running_y += line_h + line_spacing
            
            # Save thumbnail
            img.save(output_path, "JPEG", quality=90)
            print(f"Saved completed thumbnail to: {output_path}")
            
            # Clean up raw download if it exists
            if os.path.exists(temp_bg_path):
                try:
                    os.remove(temp_bg_path)
                except:
                    pass
            return True
            
        except Exception as e:
            print(f"Error compiling final thumbnail: {e}")
            if os.path.exists(temp_bg_path):
                try:
                    os.remove(temp_bg_path)
                except:
                    pass
            return False

if __name__ == "__main__":
    # Standalone verification runner
    print("Running standalone tests for ThumbnailCreator...")
    
    # Instantiate with no key (uses environment or triggers fallback solid color)
    creator = ThumbnailCreator()
    
    # Import CHANNEL_CONFIGS to test profile-specific rules
    try:
        from backend.channel_config import CHANNEL_CONFIGS
        military_profile = CHANNEL_CONFIGS["military"]
        aviation_profile = CHANNEL_CONFIGS["aviation"]
    except ImportError:
        military_profile = None
        aviation_profile = None
    
    test_cases = [
        {
            "query": "F-35 Lightning II Stealth Fighter Mission",
            "output_path": "test_thumb_military_1.jpg",
            "profile": military_profile,
            "add_circle": True
        },
        {
            "query": "Nuclear Submarine vs Destroyer Warship Specs",
            "output_path": "test_thumb_military_2.jpg",
            "profile": military_profile,
            "add_circle": True,
            "punchline": "TOP SECRET"
        },
        {
            "query": "Boeing 747 Extreme Crosswind Landing in Storm",
            "output_path": "test_thumb_civil_1.jpg",
            "profile": aviation_profile,
            "add_arrow": True
        },
        {
            "query": "Airbus A380 Double Engine Failure Emergency Landing",
            "output_path": "test_thumb_civil_2.jpg",
            "profile": aviation_profile,
            "add_circle": True,
            "add_arrow": True
        }
    ]
    
    for idx, case in enumerate(test_cases, 1):
        print(f"\n--- Running Test Case {idx} ---")
        success = creator.create_thumbnail(
            query=case["query"],
            output_path=case["output_path"],
            add_arrow=case.get("add_arrow", False),
            add_circle=case.get("add_circle", False),
            punchline=case.get("punchline", None),
            profile=case.get("profile", None)
        )
        print(f"Test Case {idx} finished with status: {success}")
