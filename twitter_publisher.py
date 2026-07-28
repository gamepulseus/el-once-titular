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

    def _generate_oauth_header(self, method: str, url: str) -> str:
        """Generates standard OAuth 1.0a Authorization header without external dependencies."""
        oauth_params = {
            "oauth_consumer_key": self.api_key,
            "oauth_nonce": secrets.token_hex(16),
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": self.access_token,
            "oauth_version": "1.0"
        }

        # Parameter string
        param_pairs = sorted([(k, v) for k, v in oauth_params.items()])
        param_str = "&".join([f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(v, safe='')}" for k, v in param_pairs])

        # Base string
        base_str = f"{method.upper()}&{urllib.parse.quote(url, safe='')}&{urllib.parse.quote(param_str, safe='')}"

        # Signing key
        signing_key = f"{urllib.parse.quote(self.api_secret, safe='')}&{urllib.parse.quote(self.access_secret, safe='')}".encode("utf-8")

        # Signature
        hashed = hmac.new(signing_key, base_str.encode("utf-8"), hashlib.sha1)
        signature = base64.b64encode(hashed.digest()).decode("utf-8")

        oauth_params["oauth_signature"] = signature

        header_parts = [f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(v, safe="")}"' for k, v in sorted(oauth_params.items())]
        return "OAuth " + ", ".join(header_parts)

    def publish_tweet(self, text: str) -> bool:
        if not self.is_configured():
            logger.warning("Twitter API keys not configured. Skipping tweet.")
            return False

        clean_tweet = self.clean_text_for_tweet(text)
        if not clean_tweet:
            return False

        url = "https://api.twitter.com/2/tweets"
        header = self._generate_oauth_header("POST", url)

        payload = json.dumps({"text": clean_tweet}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": header,
                "Content-Type": "application/json"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                logger.info(f"Tweet successfully posted to Twitter (X): {clean_tweet[:50]}...")
                return True
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            logger.error(f"Twitter API HTTP error {e.code}: {err_body}")
            return False
        except Exception as e:
            logger.error(f"Failed to post Tweet: {e}")
            return False
