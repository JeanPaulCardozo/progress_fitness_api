import os

import pytest

# Las pruebas usan su propia base de datos de Postgres, nunca la de DATABASE_URL.
# Ejemplo con Docker:
#   docker run -d --rm --name pf-test-db -e POSTGRES_PASSWORD=test -e POSTGRES_DB=progress_fitness_test -p 55432:5432 postgres:16
#   TEST_DATABASE_URL=postgresql+psycopg://postgres:test@localhost:55432/progress_fitness_test uv run pytest
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    # Se detiene antes de importar la app, así nunca toca la base real
    pytest.exit(
        "Define TEST_DATABASE_URL para ejecutar las pruebas (ver tests/conftest.py)",
        returncode=4,
    )

# Antes de importar la app: así ningún módulo llega a apuntar a la base real ni usa los secretos del .env
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["SECRET_KEY"] = "test-secret"
os.environ["RESET_MINUTES"] = "30"
os.environ["FRONTEND_URL"] = "http://front.test"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from progress_fitness_api.core.limiter import Limit  # noqa: E402
from progress_fitness_api.database import Base, get_db  # noqa: E402
from progress_fitness_api.main import app  # noqa: E402
from progress_fitness_api.models import plan, sets, users  # noqa: E402, F401  (registra las tablas)
from progress_fitness_api.routers import users as users_router  # noqa: E402

engine = create_engine(TEST_DATABASE_URL)
TestSession = sessionmaker(bind=engine, autoflush=False)


@pytest.fixture(scope="session", autouse=True)
def tables():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db():
    session = TestSession()
    yield session
    session.close()
    with engine.begin() as conn:
        conn.execute(text('TRUNCATE "Sets", "Plans", "Users" RESTART IDENTITY CASCADE'))


@pytest.fixture
def sent_emails(monkeypatch):
    """Guarda los correos en una lista en lugar de enviarlos con Resend."""
    sent = []
    monkeypatch.setattr(
        users_router, "send_reset_email", lambda to, link: sent.append((to, link))
    )
    return sent


@pytest.fixture
def client(db, sent_emails):
    def override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    Limit.enabled = False  # el límite de peticiones se prueba aparte
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Limit.enabled = True


def register(client, email="ana@correo.com", password="secreta123", name="Ana"):
    return client.post(
        "/auth/register", json={"name": name, "email": email, "password": password}
    )


def login(client, email="ana@correo.com", password="secreta123"):
    return client.post("/auth/login", data={"username": email, "password": password})


@pytest.fixture
def auth(client):
    """Registra a un usuario y devuelve la cabecera con su token."""
    register(client)
    token = login(client).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_auth(client):
    register(client, email="luis@correo.com", name="Luis")
    token = login(client, email="luis@correo.com").json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
