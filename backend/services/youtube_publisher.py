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
    def __init__(self):
        self.credentials = None
        self.load_credentials()

    def load_credentials(self):
        """Loads OAuth credentials from environment variable and auto-refreshes if expired."""
        token_json_str = os.getenv('YOUTUBE_TOKEN_JSON')
        
        if not token_json_str:
            raise Exception("ERRORE CRITICO: Variabile d'ambiente YOUTUBE_TOKEN_JSON non impostata o vuota.")
            
        try:
            token_dict = json.loads(token_json_str)
            self.credentials = Credentials.from_authorized_user_info(token_dict, SCOPES)
        except Exception as e:
            Notifier().send_alert(f"🚨 <b>ERRORE CRITICO</b>: Parsing JSON Token fallito. Controlla il formato! Errore: {e}")
            raise Exception(f"ERRORE CRITICO: Impossibile fare il parsing del JSON fornito: {e}")

        # If token is expired but we have a refresh_token, refresh automatically
        if not self.credentials.valid:
            if self.credentials.expired and self.credentials.refresh_token:
                print("[Auth] Access token scaduto — eseguo il refresh automatico con refresh_token...")
                try:
                    from google.auth.transport.requests import Request
                    self.credentials.refresh(Request())
                    print("[Auth] Token rinnovato con successo!")
                except Exception as e:
                    Notifier().send_alert("🚨 <b>ERRORE CRITICO: Token YouTube Scaduto.</b> Rinnovare immediatamente con generate_ultimate_token.py!")
                    raise Exception(f"ERRORE CRITICO: Refresh del token fallito: {e}")
            else:
                Notifier().send_alert("🚨 <b>ERRORE CRITICO: Token YouTube Invalido/Scaduto senza refresh.</b> Rinnovare immediatamente!")
                raise Exception("ERRORE CRITICO: Il token e' incompleto o non valido e non ha un refresh_token.")

    def is_authorized(self) -> bool:
        """Returns True if valid credentials exist."""
        return self.credentials and self.credentials.valid

    def get_service(self):
        """Returns the authorized YouTube API service object with socket timeout."""
        import socket
        socket.setdefaulttimeout(120)  # 2 min timeout su ogni operazione socket
        if not self.is_authorized():
            Notifier().send_alert("🚨 <b>ERRORE CRITICO: Token YouTube Scaduto.</b> Rinnovare immediatamente!")
            raise Exception("ERRORE CRITICO: Il token nei GitHub Secrets e' scaduto o non valido.")
        return build('youtube', 'v3', credentials=self.credentials)

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
