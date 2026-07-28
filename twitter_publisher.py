import logging
import re
import time
import secrets
import urllib.parse
import json
from typing import Optional
import tweepy
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

        if self.is_configured():
            try:
                self.client = tweepy.Client(
                    consumer_key=self.api_key,
                    consumer_secret=self.api_secret,
                    access_token=self.access_token,
                    access_token_secret=self.access_secret
                )
            except Exception as e:
                logger.error(f"Error initializing Tweepy client: {e}")
                self.client = None
        else:
            self.client = None

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_secret and self.access_token and self.access_secret)

    def clean_text_for_tweet(self, text: str) -> str:
        clean = re.sub(r'<[^>]+>', '', text)
        clean = clean.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        clean = clean.strip()
        if len(clean) > 275:
            clean = clean[:272] + "..."
        return clean

    def publish_tweet(self, text: str, image_url: Optional[str] = None) -> bool:
        if not self.is_configured() or not self.client:
            logger.warning("Twitter API keys not configured. Skipping tweet.")
            return False

        clean_tweet = self.clean_text_for_tweet(text)
        if not clean_tweet:
            return False

        try:
            response = self.client.create_tweet(text=clean_tweet)
            if response and response.data:
                logger.info(f"Tweet successfully posted to Twitter (X): {clean_tweet[:50]}...")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to post Tweet via Tweepy: {e}")
            return False
