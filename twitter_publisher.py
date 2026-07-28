import logging
import re
import time
import secrets
import hmac
import hashlib
import base64
import urllib.parse
import urllib.request
import json
from typing import Optional
from config import (
    TWITTER_API_KEY,
    TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_SECRET
)

logger = logging.getLogger("GamePulse.Twitter")

class TwitterPublisher:

    def __init__(self):
        self.api_key = TWITTER_API_KEY.strip()
        self.api_secret = TWITTER_API_SECRET.strip()
        self.access_token = TWITTER_ACCESS_TOKEN.strip()
        self.access_secret = TWITTER_ACCESS_SECRET.strip()

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_secret and self.access_token and self.access_secret)

    def clean_text_for_tweet(self, text: str) -> str:
        """Strips HTML tags like <b>, <code>, <i> for clean Twitter display and truncates to 275 chars."""
        if not text:
            return ""
        clean = re.sub(r'<[^>]+>', '', text)
        clean = clean.strip()
        if len(clean) > 275:
            clean = clean[:272] + "..."
        return clean

    def _generate_oauth_header(self, method: str, url: str, extra_params: Optional[dict] = None) -> str:
        """Generates standard OAuth 1.0a Authorization header without external dependencies."""
        oauth_params = {
            "oauth_consumer_key": self.api_key,
            "oauth_nonce": secrets.token_hex(16),
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": self.access_token,
            "oauth_version": "1.0"
        }

        all_params = oauth_params.copy()
        if extra_params:
            all_params.update(extra_params)

        param_pairs = sorted([(k, str(v)) for k, v in all_params.items()])
        param_str = "&".join([f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(v, safe='')}" for k, v in param_pairs])

        base_str = f"{method.upper()}&{urllib.parse.quote(url, safe='')}&{urllib.parse.quote(param_str, safe='')}"
        signing_key = f"{urllib.parse.quote(self.api_secret, safe='')}&{urllib.parse.quote(self.access_secret, safe='')}".encode("utf-8")

        hashed = hmac.new(signing_key, base_str.encode("utf-8"), hashlib.sha1)
        signature = base64.b64encode(hashed.digest()).decode("utf-8")

        oauth_params["oauth_signature"] = signature
        header_parts = [f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(v, safe="")}"' for k, v in sorted(oauth_params.items())]
        return "OAuth " + ", ".join(header_parts)

    def upload_media(self, image_url_or_path: str) -> Optional[str]:
        """Uploads image bytes to Twitter media/upload.json and returns media_id_string."""
        if not self.is_configured() or not image_url_or_path:
            return None

        try:
            # Get image bytes from URL or file
            if image_url_or_path.startswith("http://") or image_url_or_path.startswith("https://"):
                req = urllib.request.Request(image_url_or_path, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    img_data = resp.read()
            else:
                with open(image_url_or_path, "rb") as f:
                    img_data = f.read()

            upload_url = "https://upload.twitter.com/1.1/media/upload.json"
            boundary = f"----WebKitFormBoundary{secrets.token_hex(8)}"
            
            body = bytearray()
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(b'Content-Disposition: form-data; name="media"; filename="banner.png"\r\n')
            body.extend(b'Content-Type: image/png\r\n\r\n')
            body.extend(img_data)
            body.extend(b'\r\n')
            body.extend(f"--{boundary}--\r\n".encode("utf-8"))

            header = self._generate_oauth_header("POST", upload_url)
            req = urllib.request.Request(
                upload_url,
                data=bytes(body),
                headers={
                    "Authorization": header,
                    "Content-Type": f"multipart/form-data; boundary={boundary}"
                },
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=15) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                media_id = res_data.get("media_id_string")
                if media_id:
                    logger.info(f"Successfully uploaded media to Twitter. Media ID: {media_id}")
                    return str(media_id)
        except Exception as e:
            logger.error(f"Failed to upload media to Twitter: {e}")
            return None

    def publish_tweet(self, text: str, image_url: Optional[str] = None) -> bool:
        if not self.is_configured():
            logger.warning("Twitter API keys not configured. Skipping tweet.")
            return False

        clean_tweet = self.clean_text_for_tweet(text)
        if not clean_tweet:
            return False

        # Attempt to upload media if present (safely wrapped)
        media_id = None
        if image_url:
            try:
                media_id = self.upload_media(image_url)
            except Exception as e:
                logger.warning(f"Media upload failed, proceeding with text tweet: {e}")

        url = "https://api.twitter.com/2/tweets"
        header = self._generate_oauth_header("POST", url)

        payload = {"text": clean_tweet}
        if media_id:
            payload["media"] = {"media_ids": [media_id]}

        encoded_payload = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=encoded_payload,
            headers={
                "Authorization": header,
                "Content-Type": "application/json"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                logger.info(f"Tweet with image successfully posted to Twitter (X): {clean_tweet[:50]}...")
                return True
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            logger.error(f"Twitter API HTTP error {e.code}: {err_body}")
            # Fallback retry without media if media attachment was rejected by Twitter API v2
            if media_id and ("media" in err_body.lower() or "400" in str(e.code) or "403" in str(e.code)):
                logger.info("Retrying Tweet text-only fallback without media...")
                return self.publish_tweet(text, image_url=None)
            return False
        except Exception as e:
            logger.error(f"Failed to post Tweet: {e}")
            return False
