import os
import sys
import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.force-ssl'
]

SECRETS_FILE = 'client_secrets.json'
TOKEN_FILE = 'nuovo_token_youtube.json'

def main():
    print("=" * 70)
    print(" YOUTUBE ULTIMATE TOKEN GENERATOR ".center(70, "="))
    print("=" * 70)

    # 1. Verifica presenza di client_secrets.json
    if not os.path.exists(SECRETS_FILE):
        print(f"\n[ERRORE CRITICO] File '{SECRETS_FILE}' non trovato!")
        print("Devi scaricare il file JSON con le credenziali OAuth 2.0")
        print("dalla Google Cloud Console (Tipo applicazione: Desktop)")
        print("e posizionarlo nella cartella principale del progetto.")
        sys.exit(1)

    print("\n[+] Inizializzazione del flusso OAuth...")
    
    try:
        # 2. Configurazione Flow
        flow = InstalledAppFlow.from_client_secrets_file(SECRETS_FILE, SCOPES)
        
        # 3. Avvio server locale forzando il prompt di consenso per ottenere SEMPRE il refresh_token
        print("[+] Avvio del server locale per l'autenticazione. Controlla il browser.")
        creds = flow.run_local_server(
            port=8080,
            prompt='consent',
            access_type='offline',
            open_browser=False
        )
        
        # 4. Salvataggio del nuovo token
        with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
            f.write(creds.to_json())
            
        print(f"\n[+] SUCCESS: Token generato con successo e salvato come '{TOKEN_FILE}'")
        
        # 5. Stampa a schermo per copia-incolla facile
        print("\n" + "🔥" * 35)
        print("\nCOPIA QUESTO TESTO E INCOLLALO NEI GITHUB SECRETS:\n")
        
        # Rilegge il file e lo stampa su una singola riga compatta
        with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
            token_data = json.load(f)
            # dumps senza indentazione per creare una stringa su singola riga
            print(json.dumps(token_data))
            
        print("\n" + "🔥" * 35 + "\n")
        
    except Exception as e:
        print(f"\n[ERRORE CRITICO] Qualcosa è andato storto durante la generazione: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
