import os
import re
import string
import random
import hashlib
import base64
import requests
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
import yaml
from string import Template
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from dotenv import load_dotenv

# Import our custom services
from backend.services.youtube_publisher import YouTubePublisher
from backend.pipeline import Pipeline

# Load environment variables
load_dotenv()

app = FastAPI(title="TubeFlow YouTube Automation Engine")

# HTML Template using $variable placeholders (safe with CSS curly braces)
DASHBOARD_HTML = Template("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TubeFlow Dashboard - MilitaryDeepOps</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-gradient: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
            --glass-bg: rgba(30, 41, 59, 0.45);
            --glass-border: rgba(255, 255, 255, 0.08);
            --accent-purple: #818cf8;
            --accent-green: #34d399;
            --accent-red: #f87171;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Outfit', sans-serif;
        }

        body {
            background: var(--bg-gradient);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 2rem;
            display: flex;
            justify-content: center;
        }

        .container {
            width: 100%;
            max-width: 1100px;
        }

        header {
            margin-bottom: 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--glass-bg);
            backdrop-filter: blur(12px);
            padding: 1.5rem 2rem;
            border-radius: 16px;
            border: 1px solid var(--glass-border);
        }

        header h1 {
            font-size: 1.8rem;
            font-weight: 800;
            background: linear-gradient(to right, #818cf8, #c084fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        header p {
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-top: 0.25rem;
        }

        .status-badge {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            border-radius: 50px;
            font-size: 0.9rem;
            font-weight: 600;
            border: 1px solid var(--glass-border);
        }

        .status-badge.connected {
            background: rgba(52, 211, 153, 0.15);
            color: var(--accent-green);
            border-color: rgba(52, 211, 153, 0.3);
        }

        .status-badge.disconnected {
            background: rgba(248, 113, 113, 0.15);
            color: var(--accent-red);
            border-color: rgba(248, 113, 113, 0.3);
        }

        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
        }

        @media (max-width: 768px) {
            .grid {
                grid-template-columns: 1fr;
            }
        }

        .card {
            background: var(--glass-bg);
            backdrop-filter: blur(16px);
            border-radius: 16px;
            border: 1px solid var(--glass-border);
            padding: 2rem;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        }

        .card h2 {
            font-size: 1.3rem;
            font-weight: 600;
            border-bottom: 1px solid var(--glass-border);
            padding-bottom: 0.75rem;
            color: var(--accent-purple);
        }

        .btn {
            background: var(--accent-purple);
            color: var(--text-primary);
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-align: center;
            text-decoration: none;
            display: inline-block;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(129, 140, 248, 0.4);
            filter: brightness(1.1);
        }

        .btn-outline {
            background: transparent;
            border: 1px solid var(--accent-purple);
            color: var(--accent-purple);
        }

        .btn-outline:hover {
            background: var(--accent-purple);
            color: var(--text-primary);
        }

        .btn-success {
            background: var(--accent-green);
            color: #0f172a;
        }

        .btn-success:hover {
            box-shadow: 0 4px 12px rgba(52, 211, 153, 0.4);
        }

        textarea {
            width: 100%;
            height: 180px;
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--glass-border);
            border-radius: 8px;
            color: var(--text-primary);
            padding: 1rem;
            resize: none;
            font-family: monospace;
            font-size: 0.9rem;
        }

        textarea:focus {
            outline: none;
            border-color: var(--accent-purple);
        }

        ul {
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            max-height: 250px;
            overflow-y: auto;
            padding-right: 0.5rem;
        }

        ul::-webkit-scrollbar { width: 6px; }
        ul::-webkit-scrollbar-track { background: rgba(0,0,0,0.1); }
        ul::-webkit-scrollbar-thumb { background: var(--glass-border); border-radius: 4px; }

        li {
            background: rgba(255,255,255,0.03);
            padding: 0.75rem 1rem;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.03);
            font-size: 0.95rem;
        }

        .form-group {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .form-group label {
            font-size: 0.9rem;
            color: var(--text-secondary);
        }

        .form-group input {
            padding: 0.75rem;
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--glass-border);
            border-radius: 8px;
            color: #fff;
            font-family: 'Outfit', sans-serif;
            font-size: 1rem;
        }

        .form-group input:focus {
            outline: none;
            border-color: var(--accent-purple);
        }

        .alert-info {
            padding: 0.75rem 1rem;
            border-radius: 8px;
            font-size: 0.9rem;
            background: rgba(129, 140, 248, 0.1);
            color: var(--accent-purple);
            border: 1px solid rgba(129, 140, 248, 0.2);
        }

        hr.divider {
            border: none;
            border-top: 1px solid var(--glass-border);
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>TubeFlow Dashboard</h1>
                <p>Autonomous Channel Engine for <b>$channel_name</b></p>
            </div>
            <div class="status-badge $badge_class">
                ● YouTube $status_text
            </div>
        </header>

        <div class="grid">
            <!-- Left Panel: Authorization & Manual Control -->
            <div class="card">
                <h2>Platform Connections</h2>

                <div style="margin-bottom: 1rem;">
                    <h3 style="color:#f8fafc; font-size:1.1rem; margin-bottom:0.5rem;">YouTube</h3>
                    $auth_section
                </div>

                <div style="margin-bottom: 1rem;">
                    <h3 style="color:#f8fafc; font-size:1.1rem; margin-bottom:0.5rem;">TikTok</h3>
                    $tiktok_auth_section
                </div>

                <hr class="divider">

                <h2>Trigger Pipeline Manually</h2>
                <form action="/api/pipeline/trigger" method="POST" class="form-group">
                    <label>Enter custom video topic:</label>
                    <input type="text" name="topic" placeholder="e.g. Why the F-35 Lightning II is a computer with wings" required>
                    <button type="submit" class="btn btn-success">&#x1F680; Generate &amp; Publish Video</button>
                </form>

                <div class="alert-info">
                    &#x1F4A1; <b>Automation Tip</b>: Edit your schedule in <code>config.yaml</code> and run the scheduler to post videos automatically.
                </div>
            </div>

            <!-- Right Panel: Queue Management & History -->
            <div class="card">
                <h2>Topics Queue (topics_queue.txt)</h2>
                <form action="/api/queue/save" method="POST" style="display:flex;flex-direction:column;gap:1rem;">
                    <textarea name="queue_content">$queue_content</textarea>
                    <button type="submit" class="btn btn-outline">Save Queue Changes</button>
                </form>

                <h2>Completed Videos History</h2>
                <ul>$history_items</ul>
            </div>
        </div>
    </div>
</body>
</html>""")


OAUTH_STATE = {"tiktok_verifier": ""}

def generate_pkce_pair():
    length = 64
    chars = string.ascii_letters + string.digits + "-._~"
    verifier = ''.join(random.choice(chars) for _ in range(length))
    digest = hashlib.sha256(verifier.encode('ascii')).digest()
    challenge = base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')
    return verifier, challenge

def update_env_var(key: str, value: str):
    env_file = ".env"
    if not os.path.exists(env_file):
        open(env_file, 'w').close()
    with open(env_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    key_found = False
    new_lines = []
    pattern = re.compile(rf"^{key}=")
    for line in lines:
        if pattern.match(line):
            new_lines.append(f"{key}={value}\n")
            key_found = True
        else:
            new_lines.append(line)
    if not key_found:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines.append("\n")
        new_lines.append(f"{key}={value}\n")
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    os.environ[key] = value


def get_channel_name():
    if os.path.exists("config.yaml"):
        try:
            with open("config.yaml", "r") as f:
                cfg = yaml.safe_load(f)
                return cfg.get("channel", {}).get("name", "MilitaryDeepOps")
        except Exception:
            pass
    return "MilitaryDeepOps"


@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    try:
        publisher = YouTubePublisher()
        authorized = publisher.is_authorized()
    except SystemExit:
        authorized = False
    channel_name = get_channel_name()

    # Load queue content
    queue_content = ""
    if os.path.exists("topics_queue.txt"):
        with open("topics_queue.txt", "r", encoding="utf-8") as f:
            queue_content = f.read()

    # Load history
    history_items = ""
    if os.path.exists("topics_done.txt"):
        with open("topics_done.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in reversed(lines):
            if line.strip():
                history_items += f"<li>{line.strip()}</li>"
    if not history_items:
        history_items = "<li>No videos generated yet.</li>"

    # Build auth section
    secrets_file = os.getenv("YOUTUBE_SECRETS_FILE", "client_secrets.json")
    if authorized:
        badge_class = "connected"
        status_text = "Authorized"
        auth_section = """
        <p style="color:var(--text-secondary);font-size:0.95rem;">
            Your YouTube channel is successfully connected. The automation pipeline has full upload permissions.
        </p>
        <button class="btn" style="background:rgba(52,211,153,0.2);color:var(--accent-green);cursor:default;border:1px solid var(--accent-green);">&#x2713; Channel Ready</button>
        """
    else:
        badge_class = "disconnected"
        status_text = "Not Connected"
        auth_section = f"""
        <p style="color:var(--text-secondary);font-size:0.95rem;">
            Before uploading videos, link your YouTube channel. Make sure <code>{secrets_file}</code> is in the project root folder.
        </p>
        <a href="/api/youtube/authorize" class="btn">&#x1F517; Link YouTube Channel</a>
        """

    # TikTok Auth Status
    tiktok_access_token = os.getenv("TIKTOK_ACCESS_TOKEN", "")
    tiktok_client_key = os.getenv("TIKTOK_CLIENT_KEY", "")
    if tiktok_access_token:
        tiktok_auth_section = """
        <p style="color:var(--text-secondary);font-size:0.95rem;">TikTok is connected.</p>
        <button class="btn" style="background:rgba(52,211,153,0.2);color:var(--accent-green);cursor:default;border:1px solid var(--accent-green);">&#x2713; Ready</button>
        """
    elif not tiktok_client_key:
        tiktok_auth_section = """
        <p style="color:#f87171;font-weight:bold;font-size:0.95rem;">⚠️ TIKTOK_CLIENT_KEY missing in .env!</p>
        <p style="color:var(--text-secondary);font-size:0.85rem;">Please paste your Client Key in the .env file first.</p>
        """
    else:
        verifier, challenge = generate_pkce_pair()
        OAUTH_STATE["tiktok_verifier"] = verifier
        redirect_uri_tiktok = f"{request.base_url}tiktok_callback"
        tiktok_url = f"https://www.tiktok.com/v2/auth/authorize/?client_key={tiktok_client_key}&response_type=code&scope=user.info.basic,video.upload&redirect_uri={redirect_uri_tiktok}&state=tiktok_auth&code_challenge={challenge}&code_challenge_method=S256"
        tiktok_auth_section = f"""
        <p style="color:var(--text-secondary);font-size:0.95rem;">Connect TikTok to auto-upload.</p>
        <a href="{tiktok_url}" class="btn" style="background:#00f2fe;color:#000;">&#x1F517; Link TikTok</a>
        """



    html = DASHBOARD_HTML.safe_substitute(
        channel_name=channel_name,
        badge_class=badge_class,
        status_text=status_text,
        auth_section=auth_section,
        tiktok_auth_section=tiktok_auth_section,
        queue_content=queue_content,
        history_items=history_items,
    )
    return html


@app.get("/api/youtube/authorize")
def authorize(request: Request):
    """Initiates the Google OAuth2 web flow."""
    publisher = YouTubePublisher()
    redirect_uri = f"{request.base_url}oauth2callback"
    try:
        auth_url, _ = publisher.get_auth_url(redirect_uri)
        return RedirectResponse(auth_url)
    except Exception as e:
        return HTMLResponse(
            content=(
                f"<h3 style='font-family:sans-serif;color:#f87171;'>Error initializing OAuth flow</h3>"
                f"<p style='font-family:sans-serif;'>{str(e)}</p>"
                f"<p style='font-family:sans-serif;'>Make sure you downloaded <b>client_secrets.json</b> "
                f"(Desktop App type) from Google Cloud Console and placed it in the project root.</p>"
            ),
            status_code=500,
        )


@app.get("/oauth2callback")
def oauth2callback(request: Request, code: str = None, error: str = None):
    """Callback from Google after user authorizes."""
    if error:
        return HTMLResponse(content=f"<h3>OAuth error</h3><p>{error}</p>", status_code=400)
    if not code:
        return HTMLResponse(content="<h3>Missing OAuth authorization code</h3>", status_code=400)

    publisher = YouTubePublisher()
    redirect_uri = f"{request.base_url}oauth2callback"
    try:
        publisher.fetch_token(redirect_uri, str(request.url))
        return HTMLResponse(content="""
        <div style="font-family:sans-serif;text-align:center;margin-top:100px;padding:2rem;">
            <h2 style="color:#34d399;">&#x2714; YouTube Authorization Successful!</h2>
            <p style="color:#64748b;margin-top:1rem;">
                Your channel is now linked. Go back to the
                <a href="/" style="color:#818cf8;">Dashboard</a>.
            </p>
        </div>
        """)
    except Exception as e:
        return HTMLResponse(
            content=f"<h3>Token exchange failed</h3><p>{str(e)}</p>", status_code=500
        )


@app.get("/tiktok_callback")
def tiktok_callback(request: Request, code: str = None, error: str = None):
    if error:
        return HTMLResponse(content=f"<h3>Errore TikTok: {error}</h3>", status_code=400)
    if not code:
        return HTMLResponse(content="<h3>Manca il codice di autorizzazione.</h3>", status_code=400)
        
    client_key = os.getenv("TIKTOK_CLIENT_KEY")
    client_secret = os.getenv("TIKTOK_CLIENT_SECRET")
    redirect_uri = f"{request.base_url}tiktok_callback"
    
    url = "https://open.tiktokapis.com/v2/oauth/token/"
    data = {
        "client_key": client_key,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
        "code_verifier": OAUTH_STATE.get("tiktok_verifier", "")
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded", "Cache-Control": "no-cache"}
    
    try:
        res = requests.post(url, data=data, headers=headers)
        res_json = res.json()
        if "access_token" in res_json:
            update_env_var("TIKTOK_ACCESS_TOKEN", res_json["access_token"])
            update_env_var("TIKTOK_OPENID", res_json.get("open_id", ""))
            return RedirectResponse(url="/", status_code=303)
        else:
            return HTMLResponse(content=f"<h3>Errore nello scambio del token:</h3><pre>{res_json}</pre>", status_code=500)
    except Exception as e:
        return HTMLResponse(content=f"<h3>Errore di connessione:</h3><pre>{str(e)}</pre>", status_code=500)





@app.post("/api/queue/save")
async def save_queue(request: Request):
    """Saves updated queue content to topics_queue.txt."""
    form = await request.form()
    content = form.get("queue_content", "")
    with open("topics_queue.txt", "w", encoding="utf-8") as f:
        f.write(content)
    return RedirectResponse(url="/", status_code=303)


def run_pipeline_task(topic: str):
    """Background task that runs the full video pipeline."""
    pipeline = Pipeline()
    pipeline.run(manual_topic=topic)


@app.post("/api/pipeline/trigger")
async def trigger_pipeline(request: Request, background_tasks: BackgroundTasks):
    """Triggers video generation pipeline in the background."""
    form = await request.form()
    topic = form.get("topic", "").strip()
    if not topic:
        return RedirectResponse(url="/", status_code=303)

    background_tasks.add_task(run_pipeline_task, topic)
    return HTMLResponse(content=f"""
    <div style="font-family:sans-serif;text-align:center;margin-top:100px;padding:2rem;background:#0f172a;min-height:100vh;color:#f8fafc;">
        <h2 style="color:#818cf8;">&#x1F680; Pipeline Started!</h2>
        <p style="color:#94a3b8;margin-top:1rem;">Topic: <b>"{topic}"</b></p>
        <p style="color:#94a3b8;margin-top:0.5rem;">The system is writing the script, downloading footage, rendering the video and uploading it to YouTube.</p>
        <p style="color:#94a3b8;margin-top:0.5rem;">This takes approximately 2-10 minutes.</p>
        <p style="margin-top:2rem;"><a href="/" style="color:#818cf8;font-weight:bold;">&#x2190; Back to Dashboard</a></p>
    </div>
    """)


if __name__ == "__main__":
    import uvicorn
    # Bind to 0.0.0.0 to support both IPv4 and IPv6 localhost addresses on Windows
    print("Starting TubeFlow Dashboard on http://localhost:8000 ...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

