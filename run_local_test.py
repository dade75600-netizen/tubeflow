import os
import sys
from dotenv import load_dotenv

# Set console encoding to UTF-8 on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from backend.pipeline import Pipeline

def main():
    load_dotenv()
    
    # 1. Get the first topic from the queue (without popping/deleting it)
    queue_path = "topics_queue.txt"
    test_topic = None
    
    if os.path.exists(queue_path):
        with open(queue_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    test_topic = stripped
                    break
                    
    if not test_topic:
        test_topic = "F-16 Viper: The ULTIMATE Budget Fighter Jet! 🦅 (Why it Rules the World's Skies!)"
        print(f"[*] Queue empty or missing. Using default test topic: '{test_topic}'")
    else:
        print(f"[+] Loaded first topic from queue for local test: '{test_topic}'")
        print("[*] Note: The topic will NOT be deleted from the queue so it can still run on your scheduled GitHub Action.")
        
    print("\nStarting local-only test run (uploads disabled)...")
    
    try:
        pipeline = Pipeline()
        res = pipeline.run(manual_topic=test_topic, upload=False)
        
        if res.get("success"):
            print("\n" + "="*50)
            print("🎉 LOCAL TEST GENERATION SUCCESSFUL!")
            print("="*50)
            print(f"Video Title: {res.get('title')}")
            print(f"Video Saved To: {os.path.abspath(res.get('video_path'))}")
            print(f"Thumbnail Saved To: {os.path.abspath(res.get('thumbnail_path')) if res.get('thumbnail_path') else 'N/A'}")
            print("\n[+] This video was generated locally for your eyes only. No uploads were performed.")
            print("="*50)
        else:
            print(f"\n[-] Local generation failed: {res.get('error')}")
            
    except Exception as e:
        print(f"\n[-] An error occurred: {e}")

if __name__ == "__main__":
    main()
