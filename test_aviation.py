from backend.pipeline import Pipeline
from backend.channel_config import CHANNEL_CONFIGS

p = Pipeline()
p.profile = CHANNEL_CONFIGS["aviation"]
p.queue_file = "topics_queue_aviation.txt"
print("Running aviation pipeline test (dry-run, upload=False)...")
res = p.run(upload=False)
if res.get("success"):
    print(f"\nSUCCESS! Video generated at: {res.get('video_path')}")
else:
    print("\nFAILED:", res.get("error"))
