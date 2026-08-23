import os
import json
import yaml
import sys
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from backend.services.notifier import Notifier

# Required scopes for YouTube uploads and comment posting
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.force-ssl'
]

class YouTubePublisher:
    def __init__(self, token_env_var: str = None):
        if not token_env_var:
            if os.getenv("YOUTUBE_TOKEN_CIVIL_AVIATION"):
                token_env_var = "YOUTUBE_TOKEN_CIVIL_AVIATION"
            elif os.getenv("YOUTUBE_TOKEN_MILITARY"):
                token_env_var = "YOUTUBE_TOKEN_MILITARY"
            else:
                token_env_var = "YOUTUBE_TOKEN_JSON"
        self.token_env_var = token_env_var
        self.credentials = None
        self.client = None
        self.load_credentials()

    def load_credentials(self):
        """Loads OAuth credentials from the designated environment variable and auto-refreshes if expired."""
        token_json_str = os.getenv(self.token_env_var)
        if not token_json_str and self.token_env_var != "YOUTUBE_TOKEN_JSON":
            token_json_str = os.getenv("YOUTUBE_TOKEN_JSON")
            if token_json_str:
                print(f"[YouTubePublisher] {self.token_env_var} not found. Falling back to YOUTUBE_TOKEN_JSON.")
        
        if not token_json_str:
            print(f"[YouTubePublisher] WARNING: {self.token_env_var} environment variable is not set. Channel uploads will be disabled.")
            self.credentials = None
            return
            
        try:
            token_dict = json.loads(token_json_str)
        except Exception as e:
            print(f"[YouTubePublisher] ERROR: Parsing JSON Token from {self.token_env_var} failed: {e}")
            Notifier().send_alert(f"🚨 <b>ERRORE CRITICO</b>: Parsing JSON Token da {self.token_env_var} fallito. Controlla il formato! Errore: {e}")
            self.credentials = None
            return

        try:
            token = token_dict.get('token')
            refresh_token = token_dict.get('refresh_token')
            token_uri = token_dict.get('token_uri')
            client_id = token_dict.get('client_id')
            client_secret = token_dict.get('client_secret')
            scopes = token_dict.get('scopes')

            self.credentials = Credentials(
                token=token,
                refresh_token=refresh_token,
                token_uri=token_uri,
                client_id=client_id,
                client_secret=client_secret,
                scopes=scopes
            )
        except Exception as e:
            print(f"[YouTubePublisher] ERROR: Instantiating Credentials failed: {e}")
            Notifier().send_alert(f"🚨 <b>ERRORE CRITICO</b>: Creazione credentials fallito. Errore: {e}")
            self.credentials = None
            return

        # If token is expired but we have a refresh_token, refresh automatically
        if not self.credentials.valid:
            if self.credentials.expired and self.credentials.refresh_token:
                print(f"[YouTubePublisher] Silent token refresh for {self.token_env_var}...")
                try:
                    from google.auth.transport.requests import Request
                    self.credentials.refresh(Request())
                    print("[YouTubePublisher] Silent token refresh completed successfully.")
                except Exception as e:
                    print(f"[YouTubePublisher] ERROR: Silent token refresh failed: {e}")
                    Notifier().send_alert(f"🚨 <b>ERRORE CRITICO: Token YouTube Scaduto/Revocato.</b> Refresh fallito per {self.token_env_var}: {e}")
                    self.credentials = None
            else:
                print(f"[YouTubePublisher] ERROR: Token for {self.token_env_var} is invalid/expired without a refresh token.")
                Notifier().send_alert(f"🚨 <b>ERRORE CRITICO: Token YouTube Invalido/Scaduto senza refresh per {self.token_env_var}.</b>")
                self.credentials = None

        if self.is_authorized():
            try:
                import socket
                socket.setdefaulttimeout(120)  # 2 min timeout on each socket operation
                self.client = build('youtube', 'v3', credentials=self.credentials)
            except Exception as e:
                print(f"[YouTubePublisher] ERROR: Building YouTube client failed: {e}")
                self.credentials = None
                self.client = None

    def is_authorized(self) -> bool:
        """Returns True if valid credentials exist."""
        return self.credentials is not None and self.credentials.valid

    def get_service(self):
        """Returns the authorized YouTube API service object."""
        if not self.is_authorized() or self.client is None:
            Notifier().send_alert(f"🚨 <b>ERRORE CRITICO: Client YouTube non autorizzato o mancante.</b> Rinnovare il token per {self.token_env_var}!")
            raise Exception(f"ERRORE CRITICO: Il token in {self.token_env_var} e' scaduto, non valido o revocato.")
        return self.client

    def upload_video(self, file_path: str, title: str, description: str, tags: list, privacy_status: str = "public") -> str:
        """
        Uploads a video to YouTube as a Short.
        #Shorts is injected into description (first line) and tags to ensure
        the YouTube algorithm classifies the video as a Short.
        Returns the video ID on success.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Video file not found at: {file_path}")

        youtube = self.get_service()

        # ── Inject #Shorts ────────────────────────────────────────────────────
        # Description: #Shorts must appear on the first line for algorithm pickup
        if not description.strip().startswith("#Shorts"):
            description = f"#Shorts\n\n{description}"
        # Always append #Shorts at the end of description as well (belt + braces)
        if "#Shorts" not in description[-60:]:
            description = f"{description}\n\n#Shorts #YouTubeShorts"

        # Tags: 'Shorts' and 'YouTubeShorts' must be first two entries
        shorts_tags = ["Shorts", "YouTubeShorts"]
        clean_tags  = [t for t in tags if t not in shorts_tags]
        final_tags  = shorts_tags + clean_tags

        body = {
            'snippet': {
                'title': title[:100],  # YouTube titles limited to 100 characters
                'description': description,
                'tags': final_tags,
                'categoryId': '22'  # People & Blogs — optimal for viral Shorts
            },
            'status': {
                'privacyStatus': privacy_status,  # "private", "public", "unlisted"
                'selfDeclaredMadeForKids': False
            }
        }

        # MediaFileUpload object for streaming upload
        media = MediaFileUpload(
            file_path,
            mimetype='video/mp4',
            resumable=True,
            chunksize=1024 * 1024  # 1MB chunks
        )

        # Ensure 'id' is included in the part parameter to guarantee the video ID is returned in the response
        parts = list(body.keys())
        if 'id' not in parts:
            parts.append('id')

        request = youtube.videos().insert(
            part=','.join(parts),
            body=body,
            media_body=media
        )

        print(f"Starting upload of {file_path} to YouTube...")
        response = None
        import threading
        upload_error = [None]
        
        def do_upload():
            nonlocal response
            try:
                while response is None:
                    status, response = request.next_chunk()
                    if status:
                        print(f"Uploaded {int(status.progress() * 100)}%...", flush=True)
            except Exception as e:
                upload_error[0] = e

        upload_thread = threading.Thread(target=do_upload, daemon=True)
        upload_thread.start()
        upload_thread.join(timeout=600)  # max 10 minuti
        
        if upload_thread.is_alive():
            print("[TIMEOUT] Upload YouTube bloccato dopo 10 minuti — annullato.", flush=True)
            Notifier().send_alert("🚨 <b>TIMEOUT: Upload YouTube</b> bloccato dopo 10 minuti. Pipeline continua.")
            raise Exception("Upload YouTube timeout dopo 10 minuti.")
        
        if upload_error[0]:
            err = upload_error[0]
            print(f"ERRORE CRITICO: Upload YouTube fallito: {err}")
            Notifier().send_alert(f"🚨 <b>ERRORE CRITICO: Upload YouTube Fallito!</b>\nDettagli: {err}")
            raise upload_error[0]

        video_id = response.get('id')
        print(f"Upload completed successfully! Video ID: {video_id}")
        return video_id

    def post_comment(self, video_id: str, text: str) -> str:
        """
        Posts a top-level comment (pinned/affiliate comment) on the uploaded video.
        Returns the comment ID on success, None otherwise.
        """
        try:
            youtube = self.get_service()
            
            body = {
                'snippet': {
                    'videoId': video_id,
                    'topLevelComment': {
                        'snippet': {
                            'textOriginal': text
                        }
                    }
                }
            }
            
            request = youtube.commentThreads().insert(
                part='snippet',
                body=body
            )
            
            print(f"Posting affiliate comment to video {video_id}...")
            response = request.execute()
            comment_id = response.get('id')
            print(f"Comment posted successfully! Comment ID: {comment_id}")
            return comment_id
        except Exception as e:
            print(f"Failed to post YouTube comment: {e}")
            print("Verify that the YouTube channel is authorized with the correct scopes (force-ssl).")
            return None


