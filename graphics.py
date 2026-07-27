import os
import urllib.request
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import logging
from typing import Optional

logger = logging.getLogger("GamePulse.Graphics")

BANNER_DIR = Path(__file__).resolve().parent / "cache" / "banners"
BANNER_DIR.mkdir(parents=True, exist_ok=True)

REPO_ROOT = Path(__file__).resolve().parent
GAMEPULSE_LOGO_PATH = REPO_ROOT / "static" / "images" / "gamepulse_logo.png"
if not GAMEPULSE_LOGO_PATH.exists():
    LOCAL_FALLBACK = Path(r"C:\Users\Sergio Amorelli\Downloads\photo_5994478025761820201_y-Photoroom.png")
    if LOCAL_FALLBACK.exists():
        GAMEPULSE_LOGO_PATH = LOCAL_FALLBACK

class MatchupGraphics:

    @staticmethod
    def _fetch_image(url: str) -> Optional[Image.Image]:
        if not url:
            return None
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                return Image.open(BytesIO(resp.read())).convert("RGBA")
        except Exception as e:
            logger.warning(f"Failed to fetch image {url}: {e}")
            return None

    @classmethod
    def generate_matchup_banner(cls, home_team: dict, away_team: dict, event_id: str) -> Optional[str]:
        """
        Generates a clean, HD broadcast match banner:
        - Solid dark navy/slate background
        - Center GamePulse official logo (No 'VS' circle)
        - Left & Right team logos with large bold team names underneath.
        """
        output_path = BANNER_DIR / f"match_novs_{event_id}.png"
        if output_path.exists():
            return str(output_path)

        width, height = 1200, 630

        # 1. Solid Dark Slate Background (RGB 12, 18, 32)
        banner = Image.new("RGBA", (width, height), (12, 18, 32, 255))
        draw = ImageDraw.Draw(banner)

        # Load fonts
        try:
            font_name = ImageFont.truetype("arialbd.ttf", 32)
        except Exception:
            try:
                font_name = ImageFont.truetype("arial.ttf", 32)
            except Exception:
                font_name = None

        # 2. Center GamePulse Logo (Centered vertically & horizontally)
        if os.path.exists(GAMEPULSE_LOGO_PATH):
            try:
                gp_logo = Image.open(GAMEPULSE_LOGO_PATH).convert("RGBA")
                gp_logo.thumbnail((260, 260))
                gw, gh = gp_logo.size
                banner.paste(gp_logo, (width // 2 - gw // 2, height // 2 - gh // 2 - 20), gp_logo)
            except Exception as e:
                logger.warning(f"Error pasting GamePulse logo: {e}")

        # 3. Fetch and draw team logos
        home_logo_url = home_team.get("logo")
        away_logo_url = away_team.get("logo")
        home_img = cls._fetch_image(home_logo_url)
        away_img = cls._fetch_image(away_logo_url)

        home_name = home_team.get("short_name", home_team.get("name", "Local")).upper()
        away_name = away_team.get("short_name", away_team.get("name", "Visitante")).upper()

        # Home Logo Left (Center X ~ 250, Center Y ~ 280)
        if home_img:
            home_img.thumbnail((300, 300))
            hw, hh = home_img.size
            banner.paste(home_img, (250 - hw // 2, 280 - hh // 2), home_img)

        # Away Logo Right (Center X ~ 950, Center Y ~ 280)
        if away_img:
            away_img.thumbnail((300, 300))
            aw, ah = away_img.size
            banner.paste(away_img, (950 - aw // 2, 280 - ah // 2), away_img)

        # 4. Team Names underneath (Large, Bold, Centered)
        if font_name:
            bbox_h = font_name.getbbox(home_name)
            w_h = bbox_h[2] - bbox_h[0]
            draw.text((250 - w_h // 2, 490), home_name, fill=(147, 197, 253, 255), font=font_name)

            bbox_a = font_name.getbbox(away_name)
            w_a = bbox_a[2] - bbox_a[0]
            draw.text((950 - w_a // 2, 490), away_name, fill=(248, 113, 113, 255), font=font_name)
        else:
            draw.text((250 - len(home_name) * 6, 490), home_name, fill=(147, 197, 253, 255))
            draw.text((950 - len(away_name) * 6, 490), away_name, fill=(248, 113, 113, 255))

        try:
            banner.save(output_path, "PNG")
            return str(output_path)
        except Exception as e:
            logger.error(f"Error saving match banner: {e}")
            return None

    @classmethod
    def watermark_news_image(cls, img_url: str, news_id: str) -> Optional[str]:
        """
        For news or other articles: keeps the default image and overlays the official GamePulse logo as watermark.
        """
        if not img_url:
            return None

        output_path = BANNER_DIR / f"news_branded_{news_id}.png"
        if output_path.exists():
            return str(output_path)

        base_img = cls._fetch_image(img_url)
        if not base_img:
            return img_url

        bw, bh = base_img.size

        if os.path.exists(GAMEPULSE_LOGO_PATH):
            try:
                logo = Image.open(GAMEPULSE_LOGO_PATH).convert("RGBA")
                logo_w = int(bw * 0.20)
                logo_h = int(logo_w * (logo.size[1] / logo.size[0]))
                logo = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
                
                margin = int(bw * 0.03)
                pos = (bw - logo_w - margin, margin)
                base_img.paste(logo, pos, logo)
            except Exception as e:
                logger.warning(f"Error watermarking news image: {e}")

        try:
            base_img.save(output_path, "PNG")
            return str(output_path)
        except Exception as e:
            logger.error(f"Error saving watermarked news image: {e}")
            return img_url
