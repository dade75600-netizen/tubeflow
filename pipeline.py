import sys
import os
import argparse
import yaml
from backend.pipeline import Pipeline

def set_channel_in_config(channel_name):
    config_path = "config.yaml"
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        
        if "channel" not in config:
            config["channel"] = {}
        
        config["channel"]["name"] = channel_name
        
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f)
        print(f"[Config] Updated active channel in config.yaml to: '{channel_name}'")

def main():
    parser = argparse.ArgumentParser(description="TubeFlow Content Pipeline Runner")
    parser.add_argument("--channel", type=str, choices=["aviation", "military"], help="Override the active channel configuration")
    parser.add_argument("--force-publish", action="store_true", help="Force upload the video to YouTube (public)")
    parser.add_argument("--topic", type=str, help="Manual topic override to generate")
    
    args = parser.parse_args()
    
    if args.channel:
        if args.channel == "aviation":
            set_channel_in_config("CivilAviationLords")
        else:
            set_channel_in_config("MilitaryDeepOps")
            
    # Instantiate and run pipeline
    pipeline = Pipeline()
    
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
