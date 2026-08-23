import os
import sys
import subprocess
from dotenv import load_dotenv

def check_env_vars():
    print("--- Controllo Variabili d'Ambiente (.env) ---")
    load_dotenv()
    
    keys_to_check = [
        "GEMINI_API_KEY",
        "PEXELS_API_KEY"
    ]
    
    all_ok = True
    for key in keys_to_check:
        val = os.getenv(key)
        if val:
            print(f"[OK] {key} è presente.")
        else:
            print(f"[ERROR] {key} MANCANTE o vuota.")
            all_ok = False
            
    # Check YouTube tokens
    yt_keys = ["YOUTUBE_TOKEN_JSON", "YOUTUBE_TOKEN_CIVIL_AVIATION", "YOUTUBE_TOKEN_MILITARY"]
    found_yt = [k for k in yt_keys if os.getenv(k)]
    if found_yt:
        print(f"[OK] Trovate variabili token YouTube: {', '.join(found_yt)}")
    else:
        print("[ERROR] Nessuna variabile token YouTube trovata (YOUTUBE_TOKEN_JSON, YOUTUBE_TOKEN_CIVIL_AVIATION, o YOUTUBE_TOKEN_MILITARY).")
        all_ok = False
        
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
        # Determine which environment variable to use for check
        target_env = "YOUTUBE_TOKEN_JSON"
        for k in ["YOUTUBE_TOKEN_MILITARY", "YOUTUBE_TOKEN_CIVIL_AVIATION", "YOUTUBE_TOKEN_JSON"]:
            if os.getenv(k):
                target_env = k
                break
        try:
            pub = YouTubePublisher(token_env_var=target_env)
            if pub.is_authorized():
                print(f"[OK] YouTubePublisher inizializzato correttamente (caricato da {target_env}).")
            else:
                print(f"[WARNING] YouTubePublisher inizializzato da {target_env} ma non è autorizzato.")
        except Exception as e:
            print(f"[WARNING] Inizializzazione YouTubePublisher fallita per {target_env}: {e}")
    except Exception as e:
        print(f"[ERROR] YouTubePublisher crash in import/struttura: {e}")
        
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
