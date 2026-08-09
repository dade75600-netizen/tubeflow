import os
import requests

class TikTokPublisher:
    def __init__(self):
        self.client_key = os.getenv("TIKTOK_CLIENT_KEY")
        self.access_token = os.getenv("TIKTOK_ACCESS_TOKEN")

    def is_authorized(self) -> bool:
        """Returns True if required credentials exist."""
        return bool(self.client_key and self.access_token)

    def upload_video(self, file_path: str, title: str, description: str, tags: list) -> str:
        """
        Uploads a video to TikTok via Content Posting API.
        Returns the TikTok publish_id on success, None on failure/timeout.
        """
        if not self.is_authorized():
            print("TikTok API credentials are not set. Skipping TikTok upload.")
            return None
            
        if not os.path.exists(file_path):
            print(f"[TikTok] Video file not found: {file_path} — skipping.")
            return None

        import threading
        result_box = [None]
        error_box = [None]

        def _do_tiktok_upload():
            try:
                result_box[0] = self._upload_internal(file_path, title, description, tags)
            except Exception as e:
                error_box[0] = e

        t = threading.Thread(target=_do_tiktok_upload, daemon=True)
        t.start()
        t.join(timeout=120)  # max 2 minuti

        if t.is_alive():
            print("[TIMEOUT] Upload TikTok bloccato dopo 2 minuti — saltato.", flush=True)
            return None
        if error_box[0]:
            print(f"[TikTok] Errore di rete TikTok, passo oltre: {error_box[0]}", flush=True)
            return None
        return result_box[0]

    def _upload_internal(self, file_path: str, title: str, description: str, tags: list) -> str:
        """Internal upload logic wrapped by upload_video with timeout."""
        print(f"Starting TikTok upload for {file_path}...")
        
        # Format caption with tags
        caption = description
        if tags:
            tag_str = " ".join([f"#{t.replace(' ', '')}" for t in tags])
            caption = f"{caption}\n\n{tag_str}"
            
        file_size = os.path.getsize(file_path)
        
        # Step 1: Initialize upload
        init_url = "https://open.tiktokapis.com/v2/post/publish/video/init/"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json; charset=UTF-8"
        }
        init_data = {
            "post_info": {
                "title": caption[:2200],
                "privacy_level": "PUBLIC",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
                "video_cover_timestamp_ms": 1000
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": file_size,
                "chunk_size": file_size,
                "total_chunk_count": 1
            }
        }

        try:
            init_response = requests.post(init_url, headers=headers, json=init_data, timeout=30)
            init_response.raise_for_status()
            init_json = init_response.json()
            
            if init_json.get("error", {}).get("code") != "ok":
                raise Exception(f"TikTok Init Error: {init_json.get('error')}")
                
            upload_url = init_json["data"]["upload_url"]
            publish_id = init_json["data"]["publish_id"]
            
            # Step 2: Upload the actual video file
            with open(file_path, "rb") as f:
                video_bytes = f.read()
                
            upload_headers = {
                "Content-Type": "video/mp4",
                "Content-Range": f"bytes 0-{file_size-1}/{file_size}"
            }
            upload_response = requests.put(upload_url, headers=upload_headers, data=video_bytes, timeout=60)
            upload_response.raise_for_status()
            
            print(f"TikTok upload completed successfully! Publish ID: {publish_id}")
            return publish_id
            
        except Exception as e:
            print(f"Failed to upload to TikTok: {e}")
            return None
