import os
import sys
import subprocess
from dotenv import load_dotenv

def check_env_vars():
    print("--- Controllo Variabili d'Ambiente (.env) ---")
    load_dotenv()
    
    keys_to_check = [
        "GEMINI_API_KEY",
        "PEXELS_API_KEY",
        "YOUTUBE_TOKEN_JSON"
    ]
    
    all_ok = True
    for key in keys_to_check:
        val = os.getenv(key)
        if val:
            print(f"[OK] {key} è presente.")
        else:
            print(f"[ERROR] {key} MANCANTE o vuota.")
            all_ok = False
            
    # Check discrepancy between .env template and youtube_publisher
    if os.getenv("YOUTUBE_TOKEN_FILE") and not os.getenv("YOUTUBE_TOKEN_JSON"):
        print("[WARNING] Trovato YOUTUBE_TOKEN_FILE ma manca YOUTUBE_TOKEN_JSON. youtube_publisher.py richiede YOUTUBE_TOKEN_JSON.")
        
    return all_ok

def check_ffmpeg():
    print("\n--- Controllo FFmpeg ---")
    # First check local bin
    local_ffmpeg = os.path.join("bin", "ffmpeg.exe") if sys.platform.startswith("win") else "bin/ffmpeg"
    ffmpeg_cmd = local_ffmpeg if os.path.exists(local_ffmpeg) else "ffmpeg"
    
    try:
        result = subprocess.run([ffmpeg_cmd, "-version"], capture_output=True, text=True)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"[OK] FFmpeg accessibile: {version_line}")
            return True
        else:
            print("[ERROR] FFmpeg ha restituito un errore.")
            return False
    except FileNotFoundError:
        print("[ERROR] FFmpeg non trovato nel sistema o in bin/.")
        return False

def check_directories():
    print("\n--- Controllo Cartelle ---")
    dirs = ["assets", "temp", "outputs"]
    for d in dirs:
        if not os.path.exists(d):
            print(f"[INFO] Creazione cartella mancante: {d}")
            os.makedirs(d, exist_ok=True)
        else:
            print(f"[OK] Cartella {d} esiste.")

def check_class_initialization():
    print("\n--- Controllo Inizializzazione Classi ---")
    
    try:
        from backend.services.video_editor import VideoEditor
        editor = VideoEditor()
        print("[OK] VideoEditor inizializzato correttamente.")
    except Exception as e:
        print(f"[ERROR] VideoEditor crash in inizializzazione: {e}")

    try:
        from backend.services.youtube_publisher import YouTubePublisher
        try:
            # It will sys.exit(1) if YOUTUBE_TOKEN_JSON is missing/invalid.
            # We catch SystemExit to not break the health check.
            pub = YouTubePublisher()
            print("[OK] YouTubePublisher inizializzato correttamente.")
        except SystemExit as e:
            print(f"[WARNING] YouTubePublisher ha interrotto l'esecuzione (codice {e}). Questo accade se il token manca o è scaduto, come previsto dall'approccio statico.")
    except Exception as e:
        print(f"[ERROR] YouTubePublisher crash in inizializzazione: {e}")
        
    try:
        from backend.services.script_generator import ScriptGenerator
        gen = ScriptGenerator()
        print("[OK] ScriptGenerator inizializzato correttamente.")
    except Exception as e:
        print(f"[ERROR] ScriptGenerator crash in inizializzazione: {e}")

def main():
    print("Iniziando TubeFlow Health Check...\n")
    check_env_vars()
    check_ffmpeg()
    check_directories()
    check_class_initialization()
    print("\nHealth Check completato.")

if __name__ == "__main__":
    main()
