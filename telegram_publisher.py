import json
import logging
import urllib.request
import urllib.parse
import os
import time
from typing import Optional, Tuple, List
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ES, TELEGRAM_CHANNEL_EN

logger = logging.getLogger("GamePulse.Telegram")

class TelegramPublisher:

    def __init__(self, bot_token: Optional[str] = None):
        self.bot_token = bot_token or TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.bot_token != "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ")

    def _post(self, method: str, data: dict) -> dict:
        if not self.base_url:
            logger.warning("Telegram Bot token not configured. Skipping post.")
            return {"ok": False, "description": "No bot token"}

        url = f"{self.base_url}/{method}"
        encoded_data = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=encoded_data, headers={"Content-Type": "application/json"})

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            logger.error(f"Telegram API HTTP error {e.code}: {err_body}")
            if e.code == 429:
                time.sleep(3)
                return self._post(method, data)
            return {"ok": False, "description": err_body}
        except Exception as e:
            logger.error(f"Telegram publish error: {e}")
            return {"ok": False, "description": str(e)}

    def publish_text(self, chat_id: str, text: str) -> bool:
        if not chat_id:
            logger.warning("No chat_id specified.")
            return False

        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        res = self._post("sendMessage", data)
        return res.get("ok", False)

    def publish_photo_file(self, chat_id: str, photo_path: str, caption: str) -> bool:
        if not self.base_url or not chat_id:
            return False

        safe_caption = caption
        if len(safe_caption) > 1024:
            safe_caption = safe_caption[:1020] + "..."

        boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
        body = []

        body.append(f'--{boundary}\r\nContent-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'.encode('utf-8'))
        body.append(f'--{boundary}\r\nContent-Disposition: form-data; name="parse_mode"\r\n\r\nHTML\r\n'.encode('utf-8'))
        body.append(f'--{boundary}\r\nContent-Disposition: form-data; name="caption"\r\n\r\n{safe_caption}\r\n'.encode('utf-8'))

        filename = os.path.basename(photo_path)
        body.append(f'--{boundary}\r\nContent-Disposition: form-data; name="photo"; filename="{filename}"\r\nContent-Type: image/png\r\n\r\n'.encode('utf-8'))
        with open(photo_path, 'rb') as f:
            body.append(f.read())
        body.append(f'\r\n--{boundary}--\r\n'.encode('utf-8'))

        payload = b''.join(body)
        url = f'{self.base_url}/sendPhoto'
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if data.get('ok', False):
                    return True
                logger.warning(f"Telegram photo upload rejected: {data.get('description')}")
        except Exception as e:
            logger.error(f"Error publishing local photo file: {e}")
        
        # Fallback: publish text message if photo upload fails
        return self.publish_text(chat_id, caption)

    def publish_photo(self, chat_id: str, photo_input: str, caption: str) -> bool:
        if not chat_id:
            logger.warning("No chat_id specified.")
            return False

        # If caption fits within Telegram's 1024 character photo caption limit
        if len(caption) <= 1024:
            if os.path.exists(photo_input):
                return self.publish_photo_file(chat_id, photo_input, caption)

            data = {
                "chat_id": chat_id,
                "photo": photo_input,
                "caption": caption,
                "parse_mode": "HTML"
            }
            res = self._post("sendPhoto", data)
            if res.get("ok", False):
                return True
            logger.warning(f"sendPhoto failed: {res.get('description')}. Falling back to publish_text.")
            return self.publish_text(chat_id, caption)

        # If caption exceeds 1024 characters: send photo with top header, then send complete untruncated text!
        header_lines = caption.strip().split("\n")
        header_caption = "\n".join(header_lines[:2]) if len(header_lines) >= 2 else header_lines[0]

        if os.path.exists(photo_input):
            self.publish_photo_file(chat_id, photo_input, header_caption)
        else:
            data = {"chat_id": chat_id, "photo": photo_input, "caption": header_caption, "parse_mode": "HTML"}
            self._post("sendPhoto", data)

        time.sleep(1)
        return self.publish_text(chat_id, caption)

    def publish_poll(self, chat_id: str, question: str, options: List[str], is_anonymous: bool = True) -> bool:
        if not chat_id:
            logger.warning("No chat_id specified for poll.")
            return False

        data = {
            "chat_id": chat_id,
            "question": question,
            "options": options,
            "is_anonymous": is_anonymous
        }
        res = self._post("sendPoll", data)
        return res.get("ok", False)

    def publish_bilingual(self, msg_es: str, msg_en: str, image_url: Optional[str] = None,
                          channel_es: Optional[str] = None, channel_en: Optional[str] = None) -> Tuple[bool, bool]:
        target_en = channel_en or TELEGRAM_CHANNEL_EN

        res_es = False
        res_en = False

        # Publish to English Channel (@GamePulseUS) & Auto-Tweet to Twitter (X)
        if target_en:
            if image_url:
                res_en = self.publish_photo(target_en, image_url, msg_en)
            else:
                res_en = self.publish_text(target_en, msg_en)

            # Auto-Tweet to Twitter / X natively
            try:
                from twitter_publisher import TwitterPublisher
                tw = TwitterPublisher()
                tw.publish_tweet(msg_en, image_url)
            except Exception as e:
                logger.error(f"Error auto-posting to Twitter: {e}")
        else:
            logger.info("English Channel ID not configured.")

        return res_es, res_en

    def publish_bilingual_poll(self, question_es: str, question_en: str,
                               options_es: List[str], options_en: List[str],
                               channel_es: Optional[str] = None, channel_en: Optional[str] = None) -> Tuple[bool, bool]:
        target_es = channel_es or TELEGRAM_CHANNEL_ES
        target_en = channel_en or TELEGRAM_CHANNEL_EN

        res_es = False
        res_en = False

        if target_es:
            res_es = self.publish_poll(target_es, question_es, options_es)
        if target_en:
            res_en = self.publish_poll(target_en, question_en, options_en)

        return res_es, res_en
