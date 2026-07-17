"""
Standalone YouTube OAuth authentication.
Run this ONCE from terminal: python auth_youtube.py
It opens browser, you login, token.json is saved.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from pathlib import Path

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

CLIENT_SECRET = Path(__file__).parent / "config" / "client_secret.json"
TOKEN_PATH = Path(__file__).parent / "token.json"

def main():
    if not CLIENT_SECRET.exists():
        print("ERROR: config/client_secret.json not found!")
        return

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
    creds = flow.run_local_server(port=8090, open_browser=True)

    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())

    print(f"\nToken saved to {TOKEN_PATH}")
    print("You can now use YouTube upload in the app.")

if __name__ == "__main__":
    main()
