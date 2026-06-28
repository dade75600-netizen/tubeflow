"""
analytics_engine.py
===================
Fetches performance metrics (Views, Likes, Comments) for recent YouTube Shorts
using the YouTube Data API v3. 
"""

import os
from googleapiclient.discovery import build
from backend.services.youtube_publisher import YouTubePublisher

class AnalyticsEngine:
    def __init__(self):
        self.publisher = YouTubePublisher()

    def fetch_recent_metrics(self, max_results: int = 15) -> list:
        """
        Fetches the latest videos uploaded to the authorized channel
        and their basic performance statistics.
        Returns a list of dictionaries with video metadata and stats.
        """
        if not self.publisher.is_authorized():
            raise PermissionError("YouTube channel is not authorized. Cannot fetch analytics.")
            
        youtube = build('youtube', 'v3', credentials=self.publisher.credentials)
        
        # 1. Get the channel's uploaded videos playlist ID
        channel_response = youtube.channels().list(
            mine=True,
            part="contentDetails"
        ).execute()
        
        if not channel_response.get("items"):
            print("No YouTube channel found for the authorized user.")
            return []
            
        uploads_playlist_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        
        # 2. Fetch recent videos from the uploads playlist
        playlist_response = youtube.playlistItems().list(
            playlistId=uploads_playlist_id,
            part="snippet",
            maxResults=max_results
        ).execute()
        
        video_items = playlist_response.get("items", [])
        if not video_items:
            print("No videos found in the uploads playlist.")
            return []
            
        video_ids = [item["snippet"]["resourceId"]["videoId"] for item in video_items]
        
        # 3. Fetch statistics for these videos
        stats_response = youtube.videos().list(
            id=",".join(video_ids),
            part="snippet,statistics"
        ).execute()
        
        dataset = []
        for item in stats_response.get("items", []):
            stats = item.get("statistics", {})
            snippet = item.get("snippet", {})
            
            # Safely parse numeric strings
            view_count = int(stats.get("viewCount", 0))
            like_count = int(stats.get("likeCount", 0))
            comment_count = int(stats.get("commentCount", 0))
            
            # Calculate Engagement Rate
            engagement_rate = round((like_count / view_count * 100), 2) if view_count > 0 else 0.0
            
            dataset.append({
                "video_id": item["id"],
                "title": snippet.get("title", "Unknown Title"),
                "published_at": snippet.get("publishedAt", ""),
                "view_count": view_count,
                "like_count": like_count,
                "comment_count": comment_count,
                "engagement_rate_percent": engagement_rate
            })
            
        return dataset
