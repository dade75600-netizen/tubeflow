import os
import sys
import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.readonly'
]

def main():
    import argparse
    parser = argparse.ArgumentParser(description="TubeFlow OAuth Token Generator")
    parser.add_argument("--env", type=str, default="YOUTUBE_TOKEN_CIVIL_AVIATION", help="Name of the environment variable to save under")
    args = parser.parse_args()
    target_env = args.env

    print("=" * 70)
    print(" TUBEFLOW OFFLINE YOUTUBE TOKEN GENERATOR ".center(70, "="))
    print("=" * 70)
    print(f"Target Environment Variable: {target_env}")

    secrets_file = os.getenv("YOUTUBE_SECRETS_FILE", "client_secrets.json")
    
    if not os.path.exists(secrets_file):
        print(f"\n[ERRORE CRITICO] File '{secrets_file}' non trovato!")
        print("Devi scaricare il file JSON con le credenziali OAuth 2.0")
        print("dalla Google Cloud Console (Tipo applicazione: Desktop)")
        print(f"e posizionarlo nella root come '{secrets_file}'.")
        sys.exit(1)

    print(f"\n[+] Inizializzazione del flusso OAuth da: {secrets_file}")
    
    try:
        # Configurazione Flow
        flow = InstalledAppFlow.from_client_secrets_file(secrets_file, SCOPES)
        
        # Avvio del server locale per l'autenticazione offline iniziale
        print("[+] Avvio del server locale per l'autenticazione. Controlla il browser.")
        print("[*] Verrà richiesto il consenso esplicito per ottenere il refresh_token permanente.")
        
        creds = flow.run_local_server(
            port=8080,
            prompt='consent',
            access_type='offline',
            open_browser=True
        )
        
        # Creazione del dizionario delle credenziali
        token_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes
        }
        
        # Salva direttamente nel file .env locale sotto la chiave target_env
        import re
        env_file = ".env"
        if os.path.exists(env_file):
            with open(env_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        else:
            lines = []
            
        key_found = False
        new_lines = []
        pattern = re.compile(r"^" + re.escape(target_env) + r"=")
        escaped_val = json.dumps(token_data).replace("'", "'\\''")
        new_line = f"{target_env}='{escaped_val}'\n"
        
        for line in lines:
            if pattern.match(line):
                new_lines.append(new_line)
                key_found = True
            else:
                new_lines.append(line)
                
        if not key_found:
            if new_lines and not new_lines[-1].endswith("\n"):
                new_lines.append("\n")
            new_lines.append(new_line)
            
        with open(env_file, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
            
        print(f"\n[+] SUCCESS: Token generato con successo e salvato in {env_file} sotto la chiave {target_env}.")
        
        print("\n" + "=" * 70)
        print("\nCOPIA QUESTO TESTO E INCOLLALO NEI GITHUB SECRETS:\n")
        print(json.dumps(token_data))
        print("\n" + "=" * 70 + "\n")
        
    except Exception as e:
        print(f"\n[ERRORE CRITICO] Generazione del token fallita: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
