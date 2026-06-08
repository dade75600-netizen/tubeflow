import os
import requests
import html

class Notifier:
    def __init__(self, bot_token: str = None, chat_id: str = None):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.enabled = bool(self.bot_token and self.chat_id and self.bot_token != "your_telegram_bot_token_here")

    def send_notification(self, title: str, video_id: str, thumbnail_path: str = None) -> bool:
        """Sends a notification to the user's Telegram chat with the upload details."""
        if not self.enabled:
            print("Telegram notification details are not configured or are placeholder. Skipping notification.")
            return False

        youtube_url = f"https://youtu.be/{video_id}"
        escaped_title = html.escape(title)
        escaped_url = html.escape(youtube_url)
        
        message = (
            f"🚀 <b>TubeFlow Upload Alert!</b>\n\n"
            f"🎬 <b>Title</b>: {escaped_title}\n"
            f"🔗 <b>Link</b>: {escaped_url}\n"
            f"✅ Status: Uploaded to YouTube (Draft/Scheduled)."
        )

        try:
            # If thumbnail is provided, send it as a photo
            if thumbnail_path and os.path.exists(thumbnail_path):
                print("Sending Telegram notification with thumbnail...")
                url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
                with open(thumbnail_path, 'rb') as photo:
                    files = {'photo': photo}
                    data = {
                        'chat_id': self.chat_id,
                        'caption': message,
                        'parse_mode': 'HTML'
                    }
                    response = requests.post(url, data=data, files=files, timeout=15)
            else:
                # Send text-only message
                print("Sending Telegram text notification...")
                url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
                data = {
                    'chat_id': self.chat_id,
                    'text': message,
                    'parse_mode': 'HTML'
                }
                response = requests.post(url, data=data, timeout=15)
            
            if response.status_code != 200:
                print(f"Telegram API response: {response.text}")
            response.raise_for_status()
            print("Telegram notification sent successfully!")
            return True
            
        except Exception as e:
            if 'response' in locals() and hasattr(response, 'text'):
                print(f"Telegram API error response: {response.text}")
            print(f"Error sending Telegram notification: {e}")
            return False
