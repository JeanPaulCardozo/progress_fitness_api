from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from conftest import login, register
from progress_fitness_api.models.users import User
from progress_fitness_api.routers import users as users_router

GOOGLE_USER = {
    "sub": "109876543210",
    "email": "ana@gmail.com",
    "email_verified": True,
    "name": "Ana Google",
}


@pytest.fixture
def google(monkeypatch):
    """Simula a Google: devuelve `user` y anota cada code que se canjea."""

    class FakeGoogle:
        user = dict(GOOGLE_USER)
        error = None
        codes = []

    def fetch(code):
        FakeGoogle.codes.append(code)
        if FakeGoogle.error:
            raise FakeGoogle.error
        return FakeGoogle.user

    monkeypatch.setattr(users_router, "fetch_google_user", fetch)
    return FakeGoogle


def start_login(client):
    """Paso 1: la API redirige a Google y deja la cookie del state. Devuelve el state."""
    res = client.get("/auth/google/login", follow_redirects=False)
    return parse_qs(urlparse(res.headers["location"]).query)["state"][0]


def callback(client, **params):
    res = client.get("/auth/google/callback", params=params, follow_redirects=False)
    assert res.status_code == 307
    return res.headers["location"]


def google_login(client):
    """Flujo completo con la respuesta simulada. Devuelve la URL de vuelta al frontend."""
    state = start_login(client)
    return callback(client, code="code-de-google", state=state)


def token_from(location):
    assert location.startswith("http://front.test/#token=")
    return location.split("#token=")[1]


def me(client, token):
    return client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})


# ── Paso 1: ir a Google ──

def test_login_redirects_to_google_with_state_cookie(client):
    res = client.get("/auth/google/login", follow_redirects=False)
    assert res.status_code == 307

    url = urlparse(res.headers["location"])
    query = parse_qs(url.query)
    assert url.netloc == "accounts.google.com"
    assert query["client_id"] == ["test-client-id"]
    assert query["redirect_uri"] == ["http://api.test/auth/google/callback"]
    assert query["response_type"] == ["code"]
    assert query["scope"] == ["openid email profile"]

    cookie = res.headers["set-cookie"]
    assert f"oauth_state={query['state'][0]}" in cookie
    assert "HttpOnly" in cookie
    assert "Secure" not in cookie  # API_URL es http en las pruebas


def test_each_login_gets_a_new_state(client):
    assert start_login(client) != start_login(client)


# ── Paso 2: la vuelta de Google ──

def test_new_google_user_is_created_without_password(client, db, google):
    location = google_login(client)

    assert google.codes == ["code-de-google"]
    assert me(client, token_from(location)).json()["email"] == "ana@gmail.com"

    user = db.query(User).one()
    assert user.google_id == "109876543210"
    assert user.name == "Ana Google"
    assert user.hashed_password is None


def test_callback_clears_the_state_cookie(client, google):
    state = start_login(client)
    res = client.get(
        "/auth/google/callback",
        params={"code": "c", "state": state},
        follow_redirects=False,
    )
    assert 'oauth_state=""' in res.headers["set-cookie"]


def test_second_login_finds_the_same_user(client, db, google):
    first = me(client, token_from(google_login(client))).json()
    google.user = {**GOOGLE_USER, "email": "nuevo-correo@gmail.com"}  # cambió su Gmail
    second = me(client, token_from(google_login(client))).json()

    assert second["id"] == first["id"]  # se encuentra por google_id, no por correo
    assert db.query(User).count() == 1


def test_links_existing_account_with_same_email(client, db, google):
    register(client, email="ana@gmail.com")
    location = google_login(client)

    assert me(client, token_from(location)).json()["id"] == 1
    assert db.query(User).count() == 1
    assert db.query(User).one().google_id == "109876543210"
    # Sigue pudiendo entrar con su contraseña
    assert login(client, email="ana@gmail.com").status_code == 200


def test_name_falls_back_to_the_email(client, db, google):
    google.user = {k: v for k, v in GOOGLE_USER.items() if k != "name"}
    google_login(client)
    assert db.query(User).one().name == "ana"


def test_unverified_email_is_rejected(client, db, google):
    google.user = {**GOOGLE_USER, "email_verified": False}
    assert google_login(client) == "http://front.test/#error=google_email"
    assert db.query(User).count() == 0


def test_google_user_cannot_use_password_login(client, google):
    google_login(client)
    res = login(client, email="ana@gmail.com", password="cualquier-cosa")
    assert res.status_code == 401


# ── Errores: siempre vuelve a la app con #error=google ──

def test_wrong_state_is_rejected_before_calling_google(client, google):
    start_login(client)
    assert callback(client, code="c", state="otro-state") == "http://front.test/#error=google"
    assert google.codes == []


def test_missing_cookie_is_rejected(client, google):
    # Sin pasar por /auth/google/login: no hay cookie
    assert callback(client, code="c", state="x") == "http://front.test/#error=google"
    assert google.codes == []


def test_user_cancelled_in_google(client, google):
    state = start_login(client)
    location = callback(client, error="access_denied", state=state)
    assert location == "http://front.test/#error=google"


def test_google_error_returns_to_app(client, db, google):
    google.error = httpx.ConnectError("Google no responde")
    assert google_login(client) == "http://front.test/#error=google"
    assert db.query(User).count() == 0
