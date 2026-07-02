import os
import sys
import time
import yaml
import shutil
from dotenv import load_dotenv

# Reconfigure stdout/stderr to UTF-8 to prevent charmap/encoding issues on Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Import services
from backend.services.youtube_publisher import YouTubePublisher
from backend.services.tiktok_publisher import TikTokPublisher
from backend.services.script_generator import ScriptGenerator
from backend.services.media_processor import MediaProcessor
from backend.services.video_editor import VideoEditor
from backend.services.first_frame_engineer import FirstFrameEngineer
from backend.services.notifier import Notifier
from backend.services.analytics_engine import AnalyticsEngine
from backend.services.improvement_agent import ImprovementAgent
from backend.services.audio_mixer import AudioMixer
from backend.channel_config import CHANNEL_CONFIGS

# Load environment variables from .env
load_dotenv()

class Pipeline:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self.load_config()

        # Resolve active channel profile from configuration channel name
        channel_name = self.config.get("channel", {}).get("name", "").lower()
        if "aviation" in channel_name or "civil" in channel_name or "lords" in channel_name:
            self.profile = CHANNEL_CONFIGS["aviation"]
            self.queue_file = "topics_queue_aviation.txt"
        else:
            self.profile = CHANNEL_CONFIGS["military"]
            self.queue_file = "topics_queue_military.txt"
        print(f"[Pipeline] Resolved active channel profile: {self.profile.get('channel_handle')}")
        print(f"[Pipeline] Using queue file: {self.queue_file}")

    def load_config(self) -> dict:
        """Loads configuration from yaml."""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        return {}

    def get_next_topic(self) -> str:
        """
        Reads the topics queue file, pops the first non-comment topic,
        rewrites the queue file without it, and returns the topic.
        """
        if not os.path.exists(self.queue_file):
            print(f"Queue file {self.queue_file} not found. Creating a blank one.")
            with open(self.queue_file, 'w') as f:
                f.write("# Add your video topics here, one per line.\n")
            return None

        with open(self.queue_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        topic = None
        new_lines = []
        
        # Parse lines
        for line in lines:
            stripped = line.strip()
            if not topic and stripped and not stripped.startswith("#"):
                topic = stripped
                # Log this topic as done in a done file
                self.log_completed_topic(topic)
            else:
                new_lines.append(line)

        # Rewrite queue file
        with open(self.queue_file, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

        return topic

    def log_completed_topic(self, topic: str):
        """Appends completed topic to a history file."""
        history_file = "topics_done.txt"
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(history_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {topic}\n")

    def run(self, manual_topic: str = None, upload: bool = True) -> dict:
        """
        Runs the complete automated YouTube video production and publishing pipeline.
        Returns a status dictionary with results.
        """
        start_time = time.time()
        print("\n" + "="*50)
        print("TUBEFLOW: STARTING CONTENT PIPELINE RUN")
        print("="*50)

        # Initialize publisher early
        publisher = YouTubePublisher()



        # Check YouTube authorization if running from queue (automated mode)
        if upload and manual_topic is None and not publisher.is_authorized():
            msg = "YouTube channel is NOT authorized. Please run the local dashboard to log in and update GitHub secrets."
            print(msg)
            return {"success": False, "error": msg}

        # 1. Resolve Topic
        topic = manual_topic or self.get_next_topic()
        if not topic:
            msg = "No topics found in queue. Add topics to topics_queue.txt to proceed."
            print(msg)
            return {"success": False, "error": msg}

        print(f"Processing Topic: '{topic}'")

        # Create temporary working directory for this run
        run_id = f"video_{int(time.time())}"
        temp_dir = os.path.join("temp", run_id)
        os.makedirs(temp_dir, exist_ok=True)
        os.makedirs("outputs", exist_ok=True)

        final_video_path = os.path.join("outputs", f"{run_id}.mp4")
        final_thumbnail_path = os.path.join("outputs", f"{run_id}.jpg")

        # Instantiate Services
        script_gen      = ScriptGenerator(config_path=self.config_path)
        media_proc      = MediaProcessor(config_path=self.config_path)
        video_edit      = VideoEditor(config_path=self.config_path)
        first_frame_eng = FirstFrameEngineer(config_path=self.config_path)
        # publisher is already initialized at the start of the method
        tiktok_publisher = TikTokPublisher()
        notifier        = Notifier()

        try:
            # Step 1: Generate Script
            max_retries = 5
            retry_delay = 15
            script = None
            
            for attempt in range(1, max_retries + 1):
                try:
                    script = script_gen.generate_script(topic, profile=self.profile)
                    break
                except Exception as e:
                    print(f"Attempt {attempt} to generate script failed: {e}")
                    if attempt < max_retries:
                        print(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        raise Exception(f"Failed to generate script after {max_retries} attempts. Last error: {e}")

            print(f"Script generated successfully. Title: '{script.title}'")
            print(f"Narration Length: {len(script.scenes)} scenes, total length approx. {sum(s.duration for s in script.scenes):.1f}s.")

            # Step 2: Generate Voiceover Audio
            voiceover_path = os.path.join(temp_dir, "voiceover.mp3")
            media_proc.generate_voiceover_sync(script.voiceover_text, voiceover_path)

            # Step 3: Fetch Stock Video Clips
            clips_paths = []
            for scene in script.scenes:
                clip_filename = f"scene_{scene.scene_number}.mp4"
                clip_path = os.path.join(temp_dir, clip_filename)
                
                # Sourcing video matching the search query
                success = media_proc.fetch_stock_video(scene.search_query, clip_path, scene.duration, profile=self.profile, title=topic)
                
                # If search fails, retry with a broader query or fallback
                if not success:
                    fallback_query = "military aviation"
                    print(f"Retrying scene {scene.scene_number} with fallback: '{fallback_query}'")
                    success = media_proc.fetch_stock_video(fallback_query, clip_path, scene.duration, profile=self.profile, title=topic)
                
                if success and os.path.exists(clip_path):
                    clips_paths.append(clip_path)
                else:
                    raise Exception(f"Failed to source a video clip for scene {scene.scene_number}: '{scene.search_query}'")

            # Step 4: Resolve Audio Assets via AudioMixer
            print("[Pipeline] Resolving audio assets (BGM, SFX)...")
            mixer = AudioMixer()
            channel_name = self.config.get("channel", {}).get("name", "")
            bgm_path = mixer.get_bgm_path(channel_name)
            swoosh_path = mixer.get_swoosh_path()
            impact_path = mixer.get_impact_path()
            
            if bgm_path:
                print(f"[Pipeline] Selected BGM: {bgm_path}")

            # Step 4b: Generate hook frame (first 1.5s of Short)
            hook_frame_path = os.path.join(temp_dir, "hook_frame.jpg")
            hook_ok = first_frame_eng.create_hook_frame(
                topic=topic,
                output_path=hook_frame_path,
                profile=self.profile
            )
            hook_frame_path = hook_frame_path if hook_ok else None

            # Step 4c: Compile Final Video (Audio + Video + Subtitles)
            render_success = video_edit.compile_video(
                script=script,
                clips_paths=clips_paths,
                voiceover_path=voiceover_path,
                background_path=bgm_path if bgm_path else "",
                output_path=final_video_path,
                first_frame_path=hook_frame_path,
                swoosh_path=swoosh_path,
                impact_path=impact_path
            )

            if not render_success or not os.path.exists(final_video_path):
                raise Exception("FFmpeg failed to compile the final video.")

            print(f"Video compiled successfully! Saved to {final_video_path}")

            # Step 5: Save hook frame as the upload thumbnail
            # The hook frame is already 1080x1920 — upload it as YouTube thumbnail
            if hook_ok and os.path.exists(hook_frame_path):
                import shutil as _shutil
                _shutil.copy2(hook_frame_path, final_thumbnail_path)
                print(f"Hook frame copied as thumbnail to: {final_thumbnail_path}")
            else:
                print("Warning: Hook frame unavailable. Thumbnail upload will be skipped.")
                final_thumbnail_path = None

            # Step 6: Publish to YouTube
            video_id = None
            uploaded = False
            
            if upload and publisher.is_authorized():
                print("YouTube channel authorized. Starting upload...")
                
                # Format description with affiliate links at the very top (first 3 lines)
                affiliate_links = self.config.get("affiliate", {}).get("links", [])
                affiliate_desc = ""
                if affiliate_links:
                    affiliate_desc = "🔥 Special Offers & Gear:\n"
                    for item in affiliate_links:
                        label = item.get("label", "Check out")
                        url = item.get("url", "")
                        affiliate_desc += f"👉 {label}: {url}\n"
                    affiliate_desc += "\n"
                
                description = affiliate_desc + script.description
                tags = script.tags
                
                # Upload video (read privacy status from config, fallback to public)
                privacy = self.config.get("video", {}).get("privacy_status", "public")
                video_id = publisher.upload_video(
                    file_path=final_video_path,
                    title=script.title,
                    description=description,
                    tags=tags,
                    privacy_status=privacy
                )
                uploaded = bool(video_id)
                print(f"Video uploaded to YouTube. Video ID: {video_id}")
                
                # Post affiliate links as the first comment
                if video_id and affiliate_links:
                    affiliate_comment = "🔥 Get the ultimate military gear and models here:\n"
                    for item in affiliate_links:
                        label = item.get("label", "Click here")
                        url = item.get("url", "")
                        affiliate_comment += f"👉 {label}: {url}\n"
                    
                    try:
                        print("Posting affiliate links comment...")
                        publisher.post_comment(video_id, affiliate_comment)
                    except Exception as c_err:
                        print(f"Could not post affiliate comment: {c_err}")
            else:
                print("YouTube channel is NOT authorized. Video saved locally in outputs/ folder. Upload skipped.")

            # Step 6.1: Publish to TikTok
            if upload and self.config.get("tiktok", {}).get("enabled", True):
                print("TikTok publishing is enabled.")
                tiktok_publisher.upload_video(
                    file_path=final_video_path,
                    title=script.title,
                    description=script.description,
                    tags=script.tags
                )
                
            # Step 7: Send Notification
            if notifier.enabled:
                title_alert = script.title
                # If upload failed/skipped, notify local save
                notif_video_id = video_id if uploaded else "LOCAL_ONLY"
                notifier.send_notification(
                    title=title_alert,
                    video_id=notif_video_id,
                    thumbnail_path=final_thumbnail_path
                )

            # Cleanup temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"Temporary folder {temp_dir} cleaned up.")
            
            duration_taken = time.time() - start_time
            print(f"Pipeline completed successfully in {duration_taken:.1f}s.")
            
            return {
                "success": True,
                "topic": topic,
                "title": script.title,
                "video_path": final_video_path,
                "thumbnail_path": final_thumbnail_path,
                "uploaded": uploaded,
                "video_id": video_id,
                "duration_seconds": duration_taken
            }

        except Exception as e:
            print(f"Pipeline run encountered an error: {e}")
            # Cleanup temp folder even on failure
            shutil.rmtree(temp_dir, ignore_errors=True)
            return {
                "success": False,
                "topic": topic,
                "error": str(e)
            }

    def run_analysis(self) -> dict:
        """
        Runs the performance analysis and feedback loop.
        Fetches metrics using AnalyticsEngine and optimizes queue with ImprovementAgent.
        """
        print("\n" + "="*50)
        print(f"TUBEFLOW: RUNNING PERFORMANCE ANALYSIS FOR {self.profile.get('channel_handle')}")
        print("="*50)
        
        try:
            analytics = AnalyticsEngine()
            print("Fetching recent video metrics from YouTube...")
            dataset = analytics.fetch_recent_metrics(max_results=20)
            
            if not dataset:
                print("No data available for analysis.")
                return {"success": False, "error": "No dataset"}
                
            agent = ImprovementAgent(config_path=self.config_path)
            report = agent.analyze_and_improve(
                dataset=dataset,
                queue_file=self.queue_file,
                profile=self.profile
            )
            
            return {
                "success": True,
                "report": report.model_dump() if report else None,
                "dataset_size": len(dataset)
            }
        except Exception as e:
            print(f"Analysis failed: {e}")
            return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="TubeFlow Content Pipeline")
    parser.add_argument("--analyze", action="store_true", help="Run the performance analysis and feedback loop")
    parser.add_argument("--channel", type=str, help="Force channel profile (military/aviation)")
    parser.add_argument("--force-publish", action="store_true", help="Force publish ignoring config")
    
    args = parser.parse_args()
    
    p = Pipeline()
    if args.channel:
        from backend.channel_config import CHANNEL_CONFIGS
        if args.channel.lower() in ["aviation", "civil", "lords"]:
            p.profile = CHANNEL_CONFIGS["aviation"]
            p.queue_file = "topics_queue_aviation.txt"
        else:
            p.profile = CHANNEL_CONFIGS["military"]
            p.queue_file = "topics_queue_military.txt"
            
    if args.analyze:
        res = p.run_analysis()
        sys.exit(0 if res.get("success") else 1)
    else:
        res = p.run(upload=args.force_publish)
        sys.exit(0 if res.get("success") else 1)

