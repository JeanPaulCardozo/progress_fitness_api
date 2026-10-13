from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from conftest import login, register
from progress_fitness_api.core.limiter import Limit
from progress_fitness_api.models.users import User


# ── Registro y login ──

def test_register_returns_user_without_password(client):
    res = register(client)
    assert res.status_code == 201
    assert res.json() == {"id": 1, "name": "Ana", "email": "ana@correo.com"}


def test_register_duplicate_email(client):
    register(client)
    res = register(client)
    assert res.status_code == 400
    assert res.json() == {"message": "User Already Registered"}


def test_validation_errors_use_message_format(client):
    res = register(client, password="corta")
    assert res.status_code == 422
    assert res.json()["message"].startswith("password:")


def test_password_is_stored_hashed(client, db):
    register(client)
    user = db.query(User).one()
    assert user.hashed_password != "secreta123"
    assert user.hashed_password.startswith("$2b$")  # bcrypt


def test_login_ok_and_me(client):
    register(client)
    res = login(client)
    assert res.status_code == 200
    assert res.json()["token_type"] == "bearer"

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {res.json()['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "ana@correo.com"


def test_login_wrong_password(client):
    register(client)
    res = login(client, password="otra-clave")
    assert res.status_code == 401
    assert res.json() == {"message": "Email or Password Incorrect"}


def test_me_rejects_missing_or_invalid_token(client):
    assert client.get("/auth/me").status_code == 401
    res = client.get("/auth/me", headers={"Authorization": "Bearer basura"})
    assert res.status_code == 401
    assert "message" in res.json()


def test_login_rate_limit(client):
    register(client)
    Limit.enabled = True
    Limit.reset()
    codes = [login(client, password="mala-clave").status_code for _ in range(6)]
    assert codes == [401] * 5 + [429]
    assert login(client).json()["message"].startswith("Rate Limit Exceeded")


# ── Recuperar contraseña ──

def reset_token_from(link):
    return parse_qs(urlparse(link).query)["reset"][0]


def test_forgot_password_unknown_email_sends_nothing(client, sent_emails):
    res = client.post("/auth/forgot-password", json={"email": "nadie@correo.com"})
    assert res.status_code == 204
    assert sent_emails == []


def test_forgot_password_sends_link_and_stores_only_the_hash(client, db, sent_emails):
    register(client)
    res = client.post("/auth/forgot-password", json={"email": "ana@correo.com"})
    assert res.status_code == 204

    [(to, link)] = sent_emails
    assert to == "ana@correo.com"
    assert link.startswith("http://front.test/?reset=")

    token = reset_token_from(link)
    user = db.query(User).one()
    assert user.reset_token_hash and user.reset_token_hash != token
    assert user.reset_token_expires > datetime.now(timezone.utc)


def test_reset_password_changes_it_once(client, sent_emails):
    register(client)
    client.post("/auth/forgot-password", json={"email": "ana@correo.com"})
    token = reset_token_from(sent_emails[0][1])

    res = client.post("/auth/reset-password", json={"token": token, "password": "nueva-clave"})
    assert res.status_code == 204
    assert login(client, password="nueva-clave").status_code == 200
    assert login(client, password="secreta123").status_code == 401

    # El mismo enlace no sirve dos veces
    again = client.post("/auth/reset-password", json={"token": token, "password": "otra-clave1"})
    assert again.status_code == 400
    assert again.json() == {"message": "El enlace no es válido o ya caducó"}


def test_reset_password_rejects_expired_token(client, db, sent_emails):
    register(client)
    client.post("/auth/forgot-password", json={"email": "ana@correo.com"})
    token = reset_token_from(sent_emails[0][1])

    user = db.query(User).one()
    user.reset_token_expires = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    res = client.post("/auth/reset-password", json={"token": token, "password": "nueva-clave"})
    assert res.status_code == 400
    assert login(client).status_code == 200  # la contraseña no cambió


def test_reset_password_rejects_unknown_token_and_short_password(client):
    assert client.post("/auth/reset-password", json={"token": "inventado", "password": "nueva-clave"}).status_code == 400
    assert client.post("/auth/reset-password", json={"token": "inventado", "password": "corta"}).status_code == 422


def test_new_reset_request_invalidates_the_previous_link(client, sent_emails):
    register(client)
    client.post("/auth/forgot-password", json={"email": "ana@correo.com"})
    client.post("/auth/forgot-password", json={"email": "ana@correo.com"})
    first, second = (reset_token_from(link) for _, link in sent_emails)

    assert client.post("/auth/reset-password", json={"token": first, "password": "nueva-clave"}).status_code == 400
    assert client.post("/auth/reset-password", json={"token": second, "password": "nueva-clave"}).status_code == 204


# ── CORS ──

def test_cors_allows_only_known_origins(client):
    preflight = {"Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "authorization"}
    ok = client.options("/auth/me", headers={"Origin": "https://jeanpaulcardozo.github.io", **preflight})
    assert ok.headers.get("access-control-allow-origin") == "https://jeanpaulcardozo.github.io"

    blocked = client.options("/auth/me", headers={"Origin": "https://otra-web.com", **preflight})
    assert "access-control-allow-origin" not in blocked.headers
