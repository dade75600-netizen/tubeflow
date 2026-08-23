import sys
import os
import argparse
import builtins

# Headless / Interactive input blocker
os.environ["HEADLESS"] = "1"
os.environ["PYTHONUNBUFFERED"] = "1"

def _no_input(*args, **kwargs):
    raise Exception("ERRORE CRITICO: Chiesto input() interattivo in ambiente headless!")
builtins.input = _no_input

from backend.pipeline import Pipeline

def main():
    parser = argparse.ArgumentParser(description="TubeFlow Dynamic Channel Runner")
    parser.add_argument("--config", type=str, required=True, help="Path to channel configuration JSON")
    parser.add_argument("--topic", type=str, help="Manual topic override to generate")
    parser.add_argument("--force-publish", action="store_true", help="Force upload the video to YouTube")
    parser.add_argument("--dry-run", action="store_true", help="Generate video locally without publishing")
    
    args = parser.parse_args()
    
    print(f"[*] Starting TubeFlow Pipeline with config: {args.config}")
    
    # Initialize pipeline with dynamic channel configuration
    pipeline = Pipeline(channel_config_path=args.config)
    
    # If force-publish, ensure status is public
    if args.force_publish:
        if "video" not in pipeline.config:
            pipeline.config["video"] = {}
        pipeline.config["video"]["privacy_status"] = "public"
        
    res = pipeline.run(manual_topic=args.topic, upload=not args.dry_run)
    
    if res.get("success"):
        print("[+] Pipeline finished successfully.")
        sys.exit(0)
    else:
        print(f"[-] Pipeline failed: {res.get('error')}")
        sys.exit(1)

if __name__ == "__main__":
    main()
