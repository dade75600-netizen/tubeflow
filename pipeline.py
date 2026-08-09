import sys
import os
import argparse
import yaml
from backend.pipeline import Pipeline

# Forzatura ambiente headless per prevenire hang
os.environ["HEADLESS"] = "1"
os.environ["PYTHONUNBUFFERED"] = "1"

# Blocca input interattivi globalmente (ffmpeg, auth, ecc.)
import builtins
def _no_input(*args, **kwargs):
    raise Exception("ERRORE CRITICO: Chiesto input() interattivo in ambiente headless!")
builtins.input = _no_input

def main():
    parser = argparse.ArgumentParser(description="TubeFlow Content Pipeline Runner")
    parser.add_argument("--channel", type=str, choices=["aviation", "military"], help="Override the active channel configuration")
    parser.add_argument("--force-publish", action="store_true", help="Force upload the video to YouTube (public)")
    parser.add_argument("--topic", type=str, help="Manual topic override to generate")
    
    args = parser.parse_args()
    
    # Instantiate and run pipeline
    pipeline = Pipeline()
    
    if args.channel:
        from backend.channel_config import CHANNEL_CONFIGS
        if args.channel == "aviation":
            pipeline.profile = CHANNEL_CONFIGS["aviation"]
            pipeline.queue_file = "topics_queue_aviation.txt"
            print("[Config] Overridden channel profile to: Aviation")
        else:
            pipeline.profile = CHANNEL_CONFIGS["military"]
            pipeline.queue_file = "topics_queue_military.txt"
            print("[Config] Overridden channel profile to: Military")
    
    # If force-publish, ensure status is public
    if args.force_publish:
        if "video" not in pipeline.config:
            pipeline.config["video"] = {}
        pipeline.config["video"]["privacy_status"] = "public"
        
    print(f"[*] Starting TubeFlow Pipeline (force-publish: {args.force_publish})")
    res = pipeline.run(manual_topic=args.topic, upload=args.force_publish)
    
    if res.get("success"):
        print("[+] Pipeline finished successfully.")
        sys.exit(0)
    else:
        print(f"[-] Pipeline failed: {res.get('error')}")
        sys.exit(1)

if __name__ == "__main__":
    main()
