import os
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = f"{os.getenv('API_URL')}/auth/google/callback"


def google_login_url(state: str) -> str:
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }

    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


def fetch_google_user(code: str) -> dict:
    tokens = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )

    tokens.raise_for_status()

    user = httpx.get(
        "https://openidconnect.googleapis.com/v1/userinfo",
        headers={"Authorization": f"Bearer {tokens.json()['access_token']}"},
        timeout=10,
    )

    user.raise_for_status()

    return user.json()
