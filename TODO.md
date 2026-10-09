# Pendientes

## 1. Recuperar contraseña

El frontend ya tiene las pantallas. Solo faltan estas dos rutas (detalles en `API.md` del frontend):

- [ ] `POST /auth/forgot-password` con `{ email }` → `204` siempre, exista o no la cuenta (así no se revela qué correos están registrados).
- [ ] Generar un token aleatorio de un solo uso (`secrets.token_urlsafe(32)`), guardar su hash y la fecha de expiración (por ejemplo, 30 minutos).
- [ ] Enviar el correo con Resend con el enlace `<URL del frontend>/?reset=<token>`. La URL del frontend va en el `.env`.
- [ ] `POST /auth/reset-password` con `{ token, password }` → `204`. Si el token no existe, expiró o ya se usó: `400` con `message`.
- [ ] Al usarlo, cambiar la contraseña (con hash) e invalidar el token.
- [ ] Limitar `forgot-password` con slowapi, igual que el login.

## 2. README.md

- [ ] Qué es el proyecto y con qué está hecho (FastAPI, PostgreSQL, SQLAlchemy, Alembic, uv).
- [ ] Requisitos e instalación: `uv sync`.
- [ ] Variables de entorno (copiar `.env_example` a `.env`).
- [ ] Migraciones: `uv run alembic upgrade head`.
- [ ] Cómo levantarla: `uv run fastapi dev src/progress_fitness_api/main.py`, y que la documentación está en `/docs`.
- [ ] Lista de endpoints o enlace al contrato del frontend.
