import os
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import yaml

class ThumbnailCreator:
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

    def create_thumbnail(self, query: str, output_path: str) -> bool:
        """
        Downloads a landscape stock photo from Pexels, crops it to 1280x720,
        and overlays stylized high-impact text in the center.
        """
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 1. Download Background Image
        bg_downloaded = False
        temp_bg_path = output_path.replace(".jpg", "_raw.jpg")

        if self.pexels_key:
            headers = {
                "Authorization": self.pexels_key
            }
            # Search Pexels for horizontal landscape image
            url = f"https://api.pexels.com/v1/search?query={requests.utils.quote(query)}&per_page=1&orientation=landscape"
            try:
                print(f"Searching Pexels for thumbnail image: '{query}'...")
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                data = response.json()
                
                photos = data.get("photos", [])
                if not photos:
                    # Fallback query
                    fallback_url = "https://api.pexels.com/v1/search?query=military+jet+cockpit&per_page=1&orientation=landscape"
                    response = requests.get(fallback_url, headers=headers, timeout=15)
                    data = response.json()
                    photos = data.get("photos", [])

                if photos:
                    # Get the large image URL
                    img_url = photos[0].get("src", {}).get("large2x") or photos[0].get("src", {}).get("large")
                    if img_url:
                        print(f"Downloading background image: {img_url}...")
                        img_data = requests.get(img_url, timeout=15)
                        img_data.raise_for_status()
                        with open(temp_bg_path, 'wb') as f:
                            f.write(img_data.content)
                        bg_downloaded = True
            except Exception as e:
                print(f"Pexels thumbnail search failed: {e}")

        # 2. If download failed, create a fallback dark gradient background
        try:
            if bg_downloaded and os.path.exists(temp_bg_path):
                img = Image.open(temp_bg_path)
            else:
                print("Using fallback solid dark background for thumbnail...")
                # Solid dark military-green/gray background
                img = Image.new("RGB", (1280, 720), color=(15, 23, 42)) # Slate dark
            
            # Crop & Resize image to exactly 1280x720 (standard YT thumbnail resolution)
            img = img.resize((1280, 720), Image.Resampling.LANCZOS)
            
            # 3. Apply a Vignette / Dark Overlay to make the image stand out
            overlay = Image.new("RGBA", (1280, 720), (0, 0, 0, 80)) # Subtle overall vignette/darkening
            img = img.convert("RGBA")
            img = Image.alpha_composite(img, overlay)
            img = img.convert("RGB")

            # 4. Draw stylized text
            draw = ImageDraw.Draw(img)
            
            # Load font (try Impact or default Arial)
            font_path = "C:\\Windows\\Fonts\\impact.ttf" # Standard path on Windows
            if not os.path.exists(font_path):
                font_path = "C:\\Windows\\Fonts\\arialbd.ttf" # Arial Bold fallback
            
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, size=85)
            else:
                font = ImageFont.load_default() # Base fallback

            # Format the text (wrap it to 2-3 words per line, uppercase)
            words = [w.upper() for w in query.split() if w]
            lines = []
            current_line = []
            for w in words:
                current_line.append(w)
                if len(current_line) >= 2: # 2 words per line
                    lines.append(" ".join(current_line))
                    current_line = []
            if current_line:
                lines.append(" ".join(current_line))
            
            # Only keep top 3 lines maximum
            lines = lines[:3]
            
            # Calculate text drawing positions for vertical centering
            sample_bbox = draw.textbbox((0, 0), "TEST", font=font)
            line_height = sample_bbox[3] - sample_bbox[1]
            line_spacing = 20
            total_text_height = (line_height * len(lines)) + (line_spacing * (len(lines) - 1))
            
            y_start = (720 - total_text_height) // 2
            
            # Draw a dedicated semi-transparent rounded rectangle under the text for readability
            max_line_width = 0
            for line in lines:
                line_bbox = draw.textbbox((0, 0), line, font=font)
                w = line_bbox[2] - line_bbox[0]
                if w > max_line_width:
                    max_line_width = w
            
            box_width = max_line_width + 80
            box_height = total_text_height + 60
            box_x = (1280 - box_width) // 2
            box_y = y_start - 30
            
            # Create a transparent overlay layer for the box
            box_overlay = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
            box_draw = ImageDraw.Draw(box_overlay)
            # Rounded rectangle with black fill at 60% opacity (153)
            box_draw.rounded_rectangle(
                [box_x, box_y, box_x + box_width, box_y + box_height],
                radius=20,
                fill=(0, 0, 0, 153)
            )
            
            img = img.convert("RGBA")
            img = Image.alpha_composite(img, box_overlay)
            img = img.convert("RGB")
            draw = ImageDraw.Draw(img) # Re-obtain drawing context on composited image
            
            # Draw each line centered with a thick outline
            for i, line in enumerate(lines):
                # Calculate width of this line
                line_bbox = draw.textbbox((0, 0), line, font=font)
                line_width = line_bbox[2] - line_bbox[0]
                x = (1280 - line_width) // 2
                y = y_start + i * (line_height + line_spacing)
                
                # Dynamic Alternating Colors: White/Yellow/White
                # If only one line, draw it in Yellow. If multiple, draw the middle line in Yellow and others in White.
                if len(lines) == 1:
                    text_fill = (255, 255, 0) # Yellow
                else:
                    if i == 1:
                        text_fill = (255, 255, 0) # Yellow
                    else:
                        text_fill = (255, 255, 255) # White
                
                # Draw thick black outline (stroke)
                stroke_width = 8
                try:
                    draw.text((x, y), line, font=font, fill=text_fill, stroke_fill=(0, 0, 0), stroke_width=stroke_width)
                except TypeError:
                    # Fallback for older Pillow versions without stroke support
                    for offset_x in range(-stroke_width, stroke_width + 1):
                        for offset_y in range(-stroke_width, stroke_width + 1):
                            draw.text((x + offset_x, y + offset_y), line, font=font, fill=(0, 0, 0))
                    draw.text((x, y), line, font=font, fill=text_fill)

            # Save the final thumbnail
            img.save(output_path, "JPEG", quality=90)
            print(f"Thumbnail successfully generated and saved to: {output_path}")
            
            # Clean up temp file
            if os.path.exists(temp_bg_path):
                try:
                    os.remove(temp_bg_path)
                except:
                    pass
            return True

        except Exception as e:
            print(f"Error drawing thumbnail: {e}")
            if os.path.exists(temp_bg_path):
                try:
                    os.remove(temp_bg_path)
                except:
                    pass
            return False
