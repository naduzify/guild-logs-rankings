"""One-time user login (OAuth2 authorization code flow) for the /user API endpoint.

Archived reports (about 2 years after upload) are only readable through /user,
by a subscribed account. Run once, log in in the browser, and the token is saved
to .wcl_user_token.json (git-ignored).

The WCL client must list REDIRECT_URI among its redirect URLs.

Usage:
    python -m pipeline.auth
"""

import json
import secrets
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from pipeline.wcl import TOKEN_URL, USER_TOKEN_FILE, WCLClient

AUTHORIZE_URL = "https://www.warcraftlogs.com/oauth/authorize"
PORT = 8765
REDIRECT_URI = f"http://localhost:{PORT}/callback"


def main() -> None:
    client = WCLClient("classic", user=False)
    state = secrets.token_urlsafe(16)
    url = AUTHORIZE_URL + "?" + urlencode({
        "client_id": client.client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "state": state,
    })
    received = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            params = parse_qs(urlparse(self.path).query)
            if urlparse(self.path).path != "/callback":
                self.send_response(404)
                self.end_headers()
                return
            received.update({k: v[0] for k, v in params.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Login received, you can close this tab.")

        def log_message(self, *args):
            pass

    server = HTTPServer(("localhost", PORT), Handler)
    print("Opening the browser. If it does not open, visit:\n" + url)
    webbrowser.open(url)
    while "code" not in received and "error" not in received:
        server.handle_request()
    server.server_close()

    if received.get("state") != state or "code" not in received:
        raise SystemExit(f"login failed: {received}")

    resp = requests.post(
        TOKEN_URL,
        data={"grant_type": "authorization_code", "code": received["code"], "redirect_uri": REDIRECT_URI},
        auth=(client.client_id, client.client_secret),
        timeout=30,
    )
    resp.raise_for_status()
    token = resp.json()
    token["obtained_at"] = time.time()
    USER_TOKEN_FILE.write_text(json.dumps(token), encoding="utf-8")
    days = token.get("expires_in", 0) / 86400
    print(f"token saved to {USER_TOKEN_FILE.name} (valid ~{days:.0f} days)")


if __name__ == "__main__":
    main()
