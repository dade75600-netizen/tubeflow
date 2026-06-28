import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Required scopes for YouTube uploads and comment posting
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.force-ssl'
]

# OAuth file paths (configured relative to project root)
SECRETS_FILE = os.getenv('YOUTUBE_SECRETS_FILE', 'client_secrets.json')
TOKEN_FILE = os.getenv('YOUTUBE_TOKEN_FILE', 'token.json')

class YouTubePublisher:
    code_verifier = None

    def __init__(self, secrets_file=SECRETS_FILE, token_file=TOKEN_FILE):
        self.secrets_file = secrets_file
        self.token_file = token_file
        self.credentials = None
        self.load_credentials()

    def load_credentials(self):
        """Loads cached OAuth credentials if they exist."""
        if os.path.exists(self.token_file):
            try:
                self.credentials = Credentials.from_authorized_user_file(self.token_file, SCOPES)
            except Exception as e:
                print(f"Error loading credentials from {self.token_file}: {e}")
                self.credentials = None

    def is_authorized(self) -> bool:
        """Returns True if valid credentials exist or can be refreshed."""
        if not self.credentials:
            return False
        if self.credentials.expired:
            if self.credentials.refresh_token:
                try:
                    self.credentials.refresh(Request())
                    self.save_credentials()
                    return True
                except Exception as e:
                    print(f"Failed to refresh YouTube OAuth credentials: {e}")
                    return False
            return False
        return True

    def save_credentials(self):
        """Saves current credentials to token_file."""
        if self.credentials:
            with open(self.token_file, 'w') as f:
                f.write(self.credentials.to_json())

    def get_flow(self, redirect_uri: str) -> Flow:
        """Creates the OAuth2 flow object using the client secrets file."""
        if not os.path.exists(self.secrets_file):
            raise FileNotFoundError(
                f"Google OAuth client_secrets.json was not found at: {os.path.abspath(self.secrets_file)}.\n"
                "Please download it from Google Cloud Console (Desktop application type) and place it here."
            )
        return Flow.from_client_secrets_file(
            self.secrets_file,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )

    def get_auth_url(self, redirect_uri: str) -> tuple:
        """Generates the authorization URL and state."""
        flow = self.get_flow(redirect_uri)
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        # Store the code_verifier for the callback
        YouTubePublisher.code_verifier = getattr(flow, 'code_verifier', None)
        return auth_url, state

    def fetch_token(self, redirect_uri: str, authorization_response: str):
        """Exchanges authorization code for credentials and saves it."""
        flow = self.get_flow(redirect_uri)
        # Restore the code_verifier from the class-level storage
        if YouTubePublisher.code_verifier:
            flow.code_verifier = YouTubePublisher.code_verifier
        flow.fetch_token(authorization_response=authorization_response)
        self.credentials = flow.credentials
        self.save_credentials()

    def get_service(self):
        """Returns the authorized YouTube API service object."""
        if not self.is_authorized():
            raise Exception("YouTube channel is not authorized. Please complete the OAuth2 login flow.")
        return build('youtube', 'v3', credentials=self.credentials)

    def upload_video(self, file_path: str, title: str, description: str, tags: list, privacy_status: str = "public") -> str:
        """
        Uploads a video to YouTube.
        Returns the video ID on success.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Video file not found at: {file_path}")

        youtube = self.get_service()

        body = {
            'snippet': {
                'title': title[:100],  # YouTube titles have a 100 character limit
                'description': description,
                'tags': tags,
                'categoryId': '22'  # 'People & Blogs' or change as desired. 20 is Gaming, 28 is Science/Tech
            },
            'status': {
                'privacyStatus': privacy_status, # "private", "public", "unlisted"
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
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"Uploaded {int(status.progress() * 100)}%...")

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
