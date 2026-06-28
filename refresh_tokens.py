import os
import json
import requests
import yaml
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_alert(channel_name):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID or TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        print(f"Telegram credentials not configured. Skipping alert for {channel_name}.")
        return
    message = f"⚠️ Token {channel_name} scaduto — autorizzazione manuale richiesta"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        res = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        }, timeout=10)
        res.raise_for_status()
        print(f"Telegram alert sent successfully for: {channel_name}")
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")

def get_channel_title(creds):
    try:
        youtube = build('youtube', 'v3', credentials=creds)
        res = youtube.channels().list(part='snippet', mine=True).execute()
        items = res.get('items', [])
        if items:
            return items[0]['snippet'].get('title')
    except Exception:
        pass
    return None

def refresh_token_file(token_path, channel_label):
    if not os.path.exists(token_path):
        print(f"[-] {channel_label} token file not found at: {token_path}")
        send_telegram_alert(channel_label)
        return None
        
    try:
        creds = Credentials.from_authorized_user_file(token_path)
        if creds and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(token_path, 'w', encoding='utf-8') as f:
                    f.write(creds.to_json())
                channel_title = get_channel_title(creds)
                print(f"[+] Token rinnovato: {token_path} (Channel: {channel_title})")
                return creds
            except Exception as ref_err:
                print(f"[-] Refresh failed for {channel_label}: {ref_err}")
                send_telegram_alert(channel_label)
                return None
        else:
            print(f"[-] Missing refresh_token in {token_path}")
            send_telegram_alert(channel_label)
            return None
    except Exception as e:
        print(f"[-] Error parsing {token_path}: {e}")
        send_telegram_alert(channel_label)
        return None

def main():
    print("=== TUBEFLOW: REFRESHING YOUTUBE TOKENS ===")
    
    # 1. Refresh Military
    refresh_token_file("token_military.json", "military")
    
    # 2. Refresh Aviation
    refresh_token_file("token_aviation.json", "aviation")

if __name__ == "__main__":
    main()
