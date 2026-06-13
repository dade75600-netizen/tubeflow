import os
import json
import time
import datetime
import yaml
import traceback
import random
from backend.pipeline import Pipeline

STATE_FILE = os.path.join("temp", "scheduler_state.json")

def load_state() -> set:
    """Loads the set of completed run slots from a JSON state file."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                completed = set()
                for item in data.get("completed", []):
                    try:
                        date_str, time_str = item.split("|")
                        y, m, d = map(int, date_str.split("-"))
                        completed.add((datetime.date(y, m, d), time_str))
                    except ValueError:
                        continue
                return completed
        except Exception as e:
            print(f"Error loading scheduler state: {e}")
    return set()

def save_state(completed_runs: set):
    """Saves the completed run slots set to a JSON state file."""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    try:
        data = {
            "completed": [f"{key[0].strftime('%Y-%m-%d')}|{key[1]}" for key in completed_runs]
        }
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving scheduler state: {e}")

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
    # Load completed runs from persistent JSON state file
    completed_runs = load_state()
    
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
            old_len = len(completed_runs)
            completed_runs = {key for key in completed_runs if key[0] >= current_date}
            if len(completed_runs) != old_len:
                save_state(completed_runs)
            
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
                
                # Construct target datetime for today
                target_dt = datetime.datetime.combine(current_date, datetime.time(target_hour, target_minute))
                
                # Check if current time is past target time, within a 2-hour grace period, and not yet run today
                is_due = (now >= target_dt) and (now <= target_dt + datetime.timedelta(hours=2))
                run_key = (current_date, t_str)
                
                if is_due and run_key not in completed_runs:
                    if now.weekday() in allowed_days:
                        # Mark this slot as completed immediately and save state
                        completed_runs.add(run_key)
                        save_state(completed_runs)
                        
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
