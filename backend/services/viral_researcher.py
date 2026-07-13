"""
viral_researcher.py
────────────────────────────────────────────────────────────────────────────
TubeFlow Growth-Hacking Module

Workflow:
  1. YouTube Data API  → find high-engagement recent videos per niche keyword
  2. Engagement filter → keep only videos above median view/like thresholds
  3. Gemini LLM        → extract viral psychology, rewrite 3 original titles
                         + 3 fresh concept angles (zero plagiarism)
  4. Queue writer      → append ready-to-use topics to the channel queue files

Usage (standalone):
    python -m backend.services.viral_researcher --channel all
    python -m backend.services.viral_researcher --channel military
    python -m backend.services.viral_researcher --channel aviation
    python -m backend.services.viral_researcher --dry-run
"""

import os
import sys
import json
import datetime
import argparse
from typing import List, Dict, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

# ─── Scopes (read-only is enough for search/videos list) ─────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

# ─── Per-channel seed keywords ────────────────────────────────────────────────
CHANNEL_KEYWORDS: Dict[str, List[str]] = {
    "military": [
        "military history secrets",
        "classified military operations",
        "cold war nuclear secrets",
        "special forces secret missions",
        "fighter jets classified programs",
        "military pilot secrets",
        "navy seal secret operation",
        "stealth aircraft classified",
        "black ops history",
        "nuclear bomb secrets history",
    ],
    "aviation": [
        "aviation secrets pilots",
        "plane crash investigation secrets",
        "pilot emergency landing",
        "aviation mysteries unexplained",
        "commercial aircraft secrets",
        "airline hidden facts",
        "cockpit secrets pilots",
        "air traffic control secrets",
        "flight attendant secrets",
        "aviation disaster investigation",
    ],
}

# Queue file paths per channel
QUEUE_FILES: Dict[str, str] = {
    "military": "topics_queue_military.txt",
    "aviation": "topics_queue_aviation.txt",
}

# Engagement thresholds — discard below these
MIN_VIEWS = 100_000
MIN_ENGAGEMENT_RATIO = 0.005   # (likes + comments) / views ≥ 0.5%

# How far back to search (days)
LOOKBACK_DAYS = 120

# Results to fetch per keyword from YouTube Search API
SEARCH_RESULTS_PER_KW = 8

# ─── Pydantic model for Gemini structured output ─────────────────────────────
class ViralConcept(BaseModel):
    title: str = Field(
        description=(
            "A viral YouTube Shorts title. Under 60 characters. "
            "1 emoji at the end. High click-bait but factually grounded. "
            "No hashtags."
        )
    )
    concept: str = Field(
        description=(
            "A 1-2 sentence script concept / angle for this title. "
            "Describe the unique psychological hook and the core narrative arc. "
            "Different angle from any source material (zero plagiarism)."
        )
    )

class ViralResearchOutput(BaseModel):
    channel: str = Field(description="The niche channel: 'military' or 'aviation'.")
    keyword: str = Field(description="The seed keyword that triggered this analysis.")
    psychology: str = Field(
        description=(
            "1-2 sentences explaining WHY the winning videos went viral. "
            "Reference the specific psychological triggers: fear, curiosity, "
            "authority, forbidden knowledge, social proof, etc."
        )
    )
    new_titles: List[ViralConcept] = Field(
        description="Exactly 3 brand-new original viral concepts inspired by (but different from) the winning videos.",
        min_length=3,
        max_length=3,
    )


# ─── Helper: load credentials from environment ────────────────────────────────
def _load_yt_credentials() -> Optional[Credentials]:
    token_str = os.getenv("YOUTUBE_TOKEN_JSON")
    if not token_str:
        print("[ViralResearcher] YOUTUBE_TOKEN_JSON not set. Skipping YouTube API calls.")
        return None
    try:
        token_dict = json.loads(token_str)
        creds = Credentials.from_authorized_user_info(token_dict, SCOPES)
        return creds
    except Exception as e:
        print(f"[ViralResearcher] Could not parse YOUTUBE_TOKEN_JSON: {e}")
        return None


# ─── Core class ──────────────────────────────────────────────────────────────
class ViralResearcher:
    def __init__(self):
        self.gemini_client = None
        self.yt_service = None

        # Init Gemini
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            self.gemini_client = genai.Client(api_key=gemini_key)
        else:
            raise EnvironmentError(
                "GEMINI_API_KEY is not set. "
                "Add it to your .env file or GitHub Secrets."
            )

        # Init YouTube Data API (read-only, uses OAuth token)
        creds = _load_yt_credentials()
        if creds:
            self.yt_service = build("youtube", "v3", credentials=creds)
        else:
            print(
                "[ViralResearcher] WARNING: No YouTube credentials — "
                "will skip trend data and use keyword-only Gemini research."
            )

    # ─── Step 1: Search YouTube for high-performing recent videos ────────────
    def _search_videos(self, keyword: str) -> List[Dict]:
        """
        Calls YouTube Search.list with order=viewCount for the last
        LOOKBACK_DAYS days. Returns a list of {video_id, title, description}.
        """
        if not self.yt_service:
            return []

        published_after = (
            datetime.datetime.utcnow()
            - datetime.timedelta(days=LOOKBACK_DAYS)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        try:
            response = self.yt_service.search().list(
                part="snippet",
                q=keyword,
                type="video",
                videoDuration="short",        # Shorts = short content
                order="viewCount",
                publishedAfter=published_after,
                maxResults=SEARCH_RESULTS_PER_KW,
                relevanceLanguage="en",
                regionCode="US",
            ).execute()

            results = []
            for item in response.get("items", []):
                vid_id = item["id"].get("videoId")
                if not vid_id:
                    continue
                snippet = item.get("snippet", {})
                results.append({
                    "video_id": vid_id,
                    "title": snippet.get("title", ""),
                    "description": snippet.get("description", ""),
                    "channel": snippet.get("channelTitle", ""),
                })
            return results

        except Exception as e:
            print(f"[ViralResearcher] YouTube search failed for '{keyword}': {e}")
            return []

    # ─── Step 2: Fetch statistics and filter by engagement ───────────────────
    def _filter_by_engagement(self, candidates: List[Dict]) -> List[Dict]:
        """
        Calls Videos.list to get viewCount, likeCount, commentCount.
        Discards videos below MIN_VIEWS or below MIN_ENGAGEMENT_RATIO.
        Returns sorted list (highest views first).
        """
        if not candidates or not self.yt_service:
            return candidates  # pass-through when no API

        ids = [c["video_id"] for c in candidates if c.get("video_id")]
        if not ids:
            return []

        try:
            response = self.yt_service.videos().list(
                part="statistics",
                id=",".join(ids),
            ).execute()

            stats_map: Dict[str, Dict] = {}
            for item in response.get("items", []):
                vid_id = item["id"]
                stats = item.get("statistics", {})
                views   = int(stats.get("viewCount",   0))
                likes   = int(stats.get("likeCount",   0))
                comments= int(stats.get("commentCount", 0))
                stats_map[vid_id] = {
                    "views": views,
                    "likes": likes,
                    "comments": comments,
                    "engagement_ratio": (likes + comments) / max(views, 1),
                }
        except Exception as e:
            print(f"[ViralResearcher] Videos.list stats call failed: {e}")
            return candidates   # fall back to unfiltered

        enriched = []
        for c in candidates:
            vid_id = c.get("video_id")
            s = stats_map.get(vid_id)
            if not s:
                continue
            if s["views"] < MIN_VIEWS:
                continue
            if s["engagement_ratio"] < MIN_ENGAGEMENT_RATIO:
                continue
            enriched.append({**c, **s})

        enriched.sort(key=lambda x: x["views"], reverse=True)
        return enriched

    # ─── Step 3: Gemini rewrite ───────────────────────────────────────────────
    def _gemini_rewrite(
        self, channel: str, keyword: str, winning_videos: List[Dict]
    ) -> ViralResearchOutput:
        """
        Sends winning video titles + metadata to Gemini and asks for
        3 brand-new viral concepts in the same niche.
        Works even with an empty winning_videos list (falls back to
        keyword-only mode).
        """
        niche_desc = (
            "classified military history, secret operations, cold war secrets, fighter jets, "
            "black ops"
            if channel == "military"
            else
            "commercial aviation emergencies, pilot secrets, air crash investigations, "
            "airline industry hidden facts"
        )

        if winning_videos:
            video_block = "\n".join(
                f'- Title: "{v["title"]}" | '
                f'Views: {v.get("views", "N/A"):,} | '
                f'Engagement: {v.get("engagement_ratio", 0):.2%}'
                for v in winning_videos[:5]
            )
            source_context = (
                f"The following YouTube Shorts recently went viral in this niche "
                f"(keyword: '{keyword}'):\n{video_block}"
            )
        else:
            source_context = (
                f"No live trend data is available right now. "
                f"Work purely from your knowledge of what makes '{keyword}' "
                f"content go viral on YouTube Shorts."
            )

        prompt = f"""You are a Senior YouTube Growth Hacker and viral content strategist 
specializing in the {niche_desc} niche.

{source_context}

YOUR TASK:
1. Analyse the psychology behind this content's virality (forbidden knowledge, fear, 
   authority bias, social proof, curiosity gap, etc.).
2. Generate exactly 3 brand-new, original YouTube Shorts titles + concept angles 
   that exploit the SAME psychological triggers but cover a COMPLETELY DIFFERENT 
   specific story, event, or fact. 
   - Zero plagiarism: do not copy any title word-for-word.
   - Each title must be under 60 characters with exactly 1 emoji.
   - Each concept must describe the unique narrative angle in 1-2 sentences.
   - Concepts must be factually plausible (no invented events).
   - Target: 500k+ views potential for a YouTube Short.

Channel niche: {niche_desc}
Seed keyword: {keyword}

Return a ViralResearchOutput JSON object."""

        response = self.gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ViralResearchOutput,
                temperature=1.0,
            ),
        )
        data = json.loads(response.text)
        return ViralResearchOutput(**data)

    # ─── Step 4: Write results to queue file ─────────────────────────────────
    def _append_to_queue(
        self, channel: str, results: List[ViralResearchOutput], dry_run: bool = False
    ) -> List[str]:
        """
        Appends the generated titles to the channel queue file.
        Returns the list of titles written.
        """
        queue_file = QUEUE_FILES.get(channel)
        if not queue_file:
            print(f"[ViralResearcher] No queue file configured for channel '{channel}'.")
            return []

        titles_written = []
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        header = f"\n# --- VIRAL RESEARCH AUTO-FILL [{timestamp}] ---\n"
        lines = [header]

        for res in results:
            for concept in res.new_titles:
                lines.append(f"{concept.title}\n")
                titles_written.append(concept.title)

        if dry_run:
            print(f"\n[DRY RUN] Would write to {queue_file}:")
            print("".join(lines))
        else:
            with open(queue_file, "a", encoding="utf-8") as f:
                f.writelines(lines)
            print(f"[ViralResearcher] Appended {len(titles_written)} topics to {queue_file}.")

        return titles_written

    # ─── Main entry point ─────────────────────────────────────────────────────
    def run(
        self,
        channels: List[str] = None,
        dry_run: bool = False,
        keywords_per_channel: int = 3,
    ) -> Dict[str, List[str]]:
        """
        Full research loop. Returns a dict: {channel: [new_titles]}.
        
        Args:
            channels:              List of 'military'/'aviation'. Defaults to both.
            dry_run:               If True, prints results without writing queue files.
            keywords_per_channel:  How many seed keywords to process per channel.
        """
        channels = channels or ["military", "aviation"]
        report: Dict[str, List[str]] = {}

        for channel in channels:
            print(f"\n{'='*60}")
            print(f"[ViralResearcher] Starting research for channel: {channel.upper()}")
            print(f"{'='*60}")

            keywords = CHANNEL_KEYWORDS.get(channel, [])[:keywords_per_channel]
            channel_results: List[ViralResearchOutput] = []

            for kw in keywords:
                print(f"\n[ViralResearcher] Keyword: '{kw}'")

                # 1. Search YouTube
                candidates = self._search_videos(kw)
                print(f"  Found {len(candidates)} candidates from YouTube Search.")

                # 2. Filter by engagement
                winners = self._filter_by_engagement(candidates)
                print(f"  {len(winners)} passed engagement filter (>{MIN_VIEWS:,} views, >{MIN_ENGAGEMENT_RATIO:.1%} ratio).")

                if winners:
                    for w in winners[:3]:
                        print(f"    ✓ [{w.get('views',0):>9,} views] {w['title']}")
                else:
                    print("  No winners from YouTube — falling back to keyword-only Gemini mode.")

                # 3. Gemini rewrite
                try:
                    output = self._gemini_rewrite(channel, kw, winners)
                    print(f"\n  [Gemini] Viral psychology: {output.psychology}")
                    print(f"  [Gemini] Generated {len(output.new_titles)} new titles:")
                    for t in output.new_titles:
                        print(f"    → {t.title}")
                        print(f"      Concept: {t.concept}")
                    channel_results.append(output)
                except Exception as e:
                    print(f"  [ViralResearcher] Gemini rewrite failed for '{kw}': {e}")

            # 4. Write to queue
            written = self._append_to_queue(channel, channel_results, dry_run=dry_run)
            report[channel] = written

        print(f"\n{'='*60}")
        print("[ViralResearcher] Research complete!")
        for ch, titles in report.items():
            print(f"  {ch}: {len(titles)} new topics added to queue.")
        print(f"{'='*60}\n")

        return report


# ─── CLI entry point ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TubeFlow Viral Researcher")
    parser.add_argument(
        "--channel",
        type=str,
        default="all",
        choices=["all", "military", "aviation"],
        help="Which channel to research (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print results without writing to queue files",
    )
    parser.add_argument(
        "--keywords",
        type=int,
        default=3,
        help="Number of seed keywords to process per channel (default: 3)",
    )
    args = parser.parse_args()

    channels = ["military", "aviation"] if args.channel == "all" else [args.channel]

    researcher = ViralResearcher()
    researcher.run(
        channels=channels,
        dry_run=args.dry_run,
        keywords_per_channel=args.keywords,
    )
