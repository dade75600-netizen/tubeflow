import os
import time
import datetime
import yaml
import traceback
import random
from backend.pipeline import Pipeline

def load_scheduler_config(config_path="config.yaml") -> dict:
    """Loads the scheduler section from config.yaml."""
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                cfg = yaml.safe_load(f)
                return cfg.get("scheduler", {})
        except Exception as e:
            print(f"Error loading scheduler config: {e}")
    return {}

def start_scheduler():
    print("=" * 60)
    print("TUBEFLOW AUTOMATED BACKGROUND SCHEDULER STARTED")
    print("=" * 60)
    
    pipeline = Pipeline()
    # Track completed runs as a set of (date, time_str)
    completed_runs = set()
    
    while True:
        try:
            # 1. Load config dynamically
            sched_cfg = load_scheduler_config()
            
            if not sched_cfg.get("enabled", False):
                # Scheduler disabled, wait and check again later
                time.sleep(60)
                continue
                
            # 2. Get current time
            now = datetime.datetime.now()
            current_date = now.date()
            
            # 3. Clean up older dates from completed_runs to prevent memory leak
            completed_runs = {key for key in completed_runs if key[0] >= current_date}
            
            # 4. Get target times (default to 12:00 and 18:00)
            target_times = sched_cfg.get("times", ["12:00", "18:00"])
            
            # 5. Check if current day of week is allowed (0=Monday, 6=Sunday)
            allowed_days = sched_cfg.get("days", [0, 1, 2, 3, 4, 5, 6])
            
            for t_str in target_times:
                try:
                    target_hour, target_minute = map(int, t_str.split(":"))
                except ValueError:
                    print(f"Invalid time format in config: '{t_str}'. Skipping.")
                    continue
                
                # Check if current time matches this target slot, and we haven't run it today
                run_key = (current_date, t_str)
                if now.hour == target_hour and now.minute == target_minute and run_key not in completed_runs:
                    
                    if now.weekday() in allowed_days:
                        # Mark this slot as completed immediately to prevent double trigger during delay sleep
                        completed_runs.add(run_key)
                        
                        # Generate human-like random delay (between 1 and 25 minutes)
                        delay_seconds = random.randint(60, 1500)
                        trigger_time = now.strftime('%Y-%m-%d %H:%M:%S')
                        run_time = (now + datetime.timedelta(seconds=delay_seconds)).strftime('%Y-%m-%d %H:%M:%S')
                        
                        print(f"\n[{trigger_time}] Scheduler Triggered for slot {t_str}!")
                        print(f"Adding a human-like random delay of {delay_seconds // 60}m {delay_seconds % 60}s to stagger upload.")
                        print(f"The video pipeline will start at approximately: {run_time}")
                        
                        time.sleep(delay_seconds)
                        
                        # Run the pipeline
                        result = pipeline.run()
                        
                        if result.get("success"):
                            print(f"Scheduler job complete for slot {t_str}. Video uploaded/compiled successfully.")
                        else:
                            print(f"Scheduler job for slot {t_str} encountered an error: {result.get('error')}")
            
            # Sleep 30 seconds before checking time again
            time.sleep(30)
            
        except KeyboardInterrupt:
            print("\nScheduler stopped by user.")
            break
        except Exception as e:
            print(f"Error in scheduler loop: {e}")
            traceback.print_exc()
            time.sleep(60) # Wait a minute before retrying after error

if __name__ == "__main__":
    start_scheduler()
