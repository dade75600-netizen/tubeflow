import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
from pyngrok import ngrok

# Directory to serve
web_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'tiktok_verify'))
os.makedirs(web_dir, exist_ok=True)
os.chdir(web_dir)

port = 8081

class CORSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

server = HTTPServer(('127.0.0.1', port), CORSRequestHandler)

print("Starting ngrok tunnel...")
# Start ngrok
try:
    public_url = ngrok.connect(port, bind_tls=True)
    print("\n" + "="*50)
    print("SUCCESS! NGROK TUNNEL IS ACTIVE.")
    print("NGROK_URL:", public_url.public_url)
    print("="*50 + "\n")
except Exception as e:
    print("\nNgrok Error:", str(e))
    print("If it requires an auth token, you may need to run: pyngrok config add-authtoken <TOKEN>\n")
    sys.exit(1)

# Run server
try:
    print(f"Serving HTTP on 127.0.0.1 port {port} (http://127.0.0.1:{port}/) ...")
    server.serve_forever()
except KeyboardInterrupt:
    print("\nShutting down...")
    server.server_close()
