# 🚀 Guida di Configurazione TubeFlow su GitHub Cloud

Questa guida ti spiega come impostare il progetto per funzionare **100% in automatico nel cloud gratis**, permettendoti di spegnere il tuo PC!

---

## Passo 1: Crea un Repository Privato su GitHub
1. Vai su [github.com](https://github.com) ed esegui l'accesso.
2. Crea un **nuovo repository** (New repository).
3. **MOLTO IMPORTANTE**: Imposta la visibilità su **Private** (perché contiene i tuoi video e la coda degli argomenti).
4. Carica/inizializza tutti i file del progetto in questo repository.

---

## Passo 2: Aggiungi i Segreti su GitHub
Poiché non dobbiamo inserire le tue chiavi e password direttamente nel codice (per sicurezza), le inseriremo nei **Repository Secrets** di GitHub:

1. Nel tuo repository su GitHub, vai in **Settings** (la scheda in alto a destra).
2. Nel menu a sinistra, clicca su **Secrets and variables** -> **Actions**.
3. Clicca sul pulsante verde **New repository secret**.
4. Aggiungi i seguenti segreti (uno alla volta):

### 🔑 Segreti API Generali
* **`GEMINI_API_KEY`**: Copia il valore presente in `.env` (inizia con `AIza...`).
* **`PEXELS_API_KEY`**: Copia il valore presente in `.env`.
* **`TELEGRAM_BOT_TOKEN`**: Copia il valore presente in `.env`.
* **`TELEGRAM_CHAT_ID`**: Copia il valore presente in `.env`.

### 🔑 Segreti YouTube (Molto Importante)
Per consentire a GitHub di caricare i video sul tuo canale, incolla i contenuti completi dei file di autenticazione:
* **`YOUTUBE_CLIENT_SECRETS_JSON`**: Apri il file `client_secrets.json` nel tuo computer, copia tutto il testo ed incollalo qui.
* **`YOUTUBE_TOKEN_JSON`**: Apri il file `token.json` nel tuo computer, copia tutto il testo ed incollalo qui.

### 🔑 Segreti TikTok (Opzionali - Quando decidi di attivarlo)
* **`TIKTOK_CLIENT_KEY`**: Copia il valore dal tuo `.env`.
* **`TIKTOK_CLIENT_SECRET`**: Copia il valore dal tuo `.env`.
* **`TIKTOK_ACCESS_TOKEN`**: Copia il valore dal tuo `.env` (dopo aver effettuato il login sul dashboard).
* **`TIKTOK_OPENID`**: Copia il valore dal tuo `.env`.

---

## Passo 3: Come Funziona la Coda e la Pubblicazione?
* **Orari di Pubblicazione**: GitHub Actions eseguirà automaticamente la pipeline ogni giorno alle **12:00** e alle **18:00** (ora italiana).
* **Gestione della Coda**: Puoi aggiungere nuovi argomenti per i tuoi video modificando direttamente il file `topics_queue.txt` su GitHub! 
* **Aggiornamento Automatico**: Quando GitHub Actions pubblica un video, rimuove la riga da `topics_queue.txt`, la aggiunge a `topics_done.txt` e salva le modifiche nel tuo repository in automatico.

---

### Passo 4: Avviare un Video Manualmente (Facoltativo)
Se vuoi generare un video immediatamente nel cloud senza aspettare gli orari programmati:
1. Nel tuo repository GitHub, vai nella scheda **Actions**.
2. Clicca su **TubeFlow Cloud Scheduler** nel menu a sinistra.
3. Clicca sul menu a tendina **Run workflow** sulla destra e premi il pulsante verde **Run workflow**.

---

## Passo 5: Evitare i Ritardi di GitHub Actions (Consigliato per precisione al minuto)
I cron-job nativi di GitHub Actions subiscono ritardi variabili (da 15 a 90+ minuti) a causa delle code dei server condivisi. Se desideri che i video vengano generati e pubblicati all'orario esatto, puoi attivare il workflow tramite un servizio esterno gratuito come **[cron-job.org](https://cron-job.org)**:

1. **Crea un Personal Access Token su GitHub** (se non l'hai gia creato per `deploy_to_github.bat`):
   - Vai su [github.com/settings/tokens](https://github.com/settings/tokens) e clicca su **Generate new token (classic)**.
   - Spunta i permessi per `repo` e `workflow`.
   - Copia il token generato (inizia con `ghp_...`).
2. **Crea un Cronjob su cron-job.org**:
   - Registrati gratis su [cron-job.org](https://cron-job.org) e clicca su **Create Cronjob**.
   - **Title**: `TubeFlow 12:00` (creane uno anche per le `18:00`).
   - **Address**: `https://api.github.com/repos/TUO_USERNAME/tubeflow/actions/workflows/scheduler.yml/dispatches` (sostituisci **TUO_USERNAME** con il tuo vero username di GitHub).
   - **Request Method**: `POST`
   - **Schedule**: Seleziona gli orari italiani esatti (es. alle 12:00 e alle 18:00).
3. **Configura le Intestazioni (Headers) e il Corpo (Body)**:
   - Nella scheda **Headers**, aggiungi queste due righe:
     * `Authorization`: `Bearer ghp_tuotokengenerato...` (sostituisci con il tuo token copiato al punto 1).
     * `Accept`: `application/vnd.github.v3+json`
     * `User-Agent`: `TubeFlow-Cron`
   - Nella scheda **Body**, imposta il tipo su **Raw (application/json)** e scrivi questo testo esatto:
     ```json
     {
       "ref": "main"
     }
     ```
4. **Salva**: Clicca su **Create**. Ora, quando scocchera l'ora, il servizio esterno inviera una richiesta diretta a GitHub che avviera il video istantaneamente senza ritardi.
