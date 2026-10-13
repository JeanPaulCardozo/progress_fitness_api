# Progress Fit API

Backend de [ProgressFit](https://github.com/JeanPaulCardozo/progress_fitness), una app para registrar el progreso en el gimnasio. Cada usuario tiene su cuenta, su plan de entrenamiento en texto y el registro de sus series (peso, repeticiones y sensación).

Hecha con **FastAPI**, **PostgreSQL**, **SQLAlchemy 2**, **Alembic** y **uv**.

## Puesta en marcha

### Requisitos

- [uv](https://docs.astral.sh/uv/) (instala Python 3.13 por su cuenta si no lo tienes)
- PostgreSQL con una base de datos creada para el proyecto

### 1. Instalar dependencias

```bash
uv sync
```

### 2. Variables de entorno

Copia `src/progress_fitness_api/.env_example` a `src/progress_fitness_api/.env` y completa los valores:

| Variable | Para qué sirve | Ejemplo |
|----------|----------------|---------|
| `DATABASE_URL` | Conexión a PostgreSQL (driver psycopg 3) | `postgresql+psycopg://usuario:clave@localhost:5432/progress_fitness` |
| `SECRET_KEY` | Clave para firmar los tokens JWT. Debe ser larga y secreta | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ALGORITHM` | Algoritmo del JWT (por defecto `HS256`) | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duración del token (por defecto 120) | `120` |
| `FRONTEND_URL` | Dirección del frontend, sin barra final. Se usa para armar el enlace del correo de recuperación | `http://localhost:5174` |
| `RESET_MINUTES` | Minutos que vale el enlace de recuperación (por defecto 10). El correo muestra este mismo valor | `10` |
| `RESEND_API_KEY` | Clave de [Resend](https://resend.com) para enviar correos. Si está vacía, el enlace se imprime en la consola | `re_xxxxxxxx` |
| `EMAIL_FROM` | Remitente de los correos | `ProgressFit <onboarding@resend.dev>` |

Sin un dominio verificado en Resend, el remitente tiene que ser `onboarding@resend.dev`, y solo se pueden enviar correos a la dirección de tu propia cuenta de Resend. Para enviar a cualquier usuario hay que verificar un dominio.

Las variables `POSTGRESS_USER`, `POSTGRESS_PASS` y `POSTGRESS_DB` del ejemplo no las usa el código. La conexión sale solo de `DATABASE_URL`.

El `.env` está en el `.gitignore`. Nunca lo subas al repositorio.

### 3. Crear las tablas

```bash
uv run alembic upgrade head
```

### 4. Levantar el servidor

```bash
uv run fastapi dev src/progress_fitness_api/main.py
```

La API queda en `http://127.0.0.1:8000`, con documentación interactiva (Swagger) en `http://127.0.0.1:8000/docs`.

### Con Docker

La imagen no incluye el `.env`: las variables se pasan al ejecutar el contenedor.

```bash
docker build -t progress-fitness-api .

# Migraciones
docker run --rm --env-file src/progress_fitness_api/.env progress-fitness-api alembic upgrade head

# Servidor
docker run --rm -p 8000:8000 --env-file src/progress_fitness_api/.env progress-fitness-api
```

El puerto se puede cambiar con la variable `PORT` (por defecto 8000), que es la que usan servicios como Render o Railway.

Si PostgreSQL corre en tu máquina y no en otro contenedor, dentro de `DATABASE_URL` usa `host.docker.internal` en lugar de `localhost`. Dentro del contenedor, `localhost` es el propio contenedor.

## Cómo consumirla

### Convenciones

- Todo es JSON, salvo el login, que recibe un formulario (ver más abajo).
- Las rutas marcadas con 🔒 necesitan el token en la cabecera: `Authorization: Bearer <token>`.
- Con un token vencido o inválido, la API responde `401`. El cliente debe cerrar la sesión.
- Todos los errores tienen el mismo formato, con un texto listo para mostrar al usuario:
  ```json
  { "message": "Email or Password Incorrect" }
  ```
  Los errores de validación (`422`) indican el campo: `"day: Input should be less than or equal to 7"`.
- `/plan/` y `/sets/` llevan **barra final**. Sin ella, FastAPI responde con una redirección `307`.
- Desde el navegador, CORS solo permite dos orígenes: `https://jeanpaulcardozo.github.io` (la app publicada) y `http://localhost:5174` (el frontend en desarrollo). Para agregar otro, edita `allow_origins` en `main.py`. CORS no afecta a curl, Postman ni a otros servidores: lo que protege los datos es el token.

### Autenticación

| Método | Ruta | Cuerpo | Respuesta |
|--------|------|--------|-----------|
| POST | `/auth/register` | `{ name, email, password }` | `201` con el usuario. `400` si el correo ya existe |
| POST | `/auth/login` | formulario: `username` (el correo) y `password` | `200 { access_token, token_type }`. `401` si los datos no coinciden |
| GET | `/auth/me` 🔒 | | `200` con el usuario |
| POST | `/auth/forgot-password` | `{ email }` | `204` siempre, exista o no la cuenta |
| POST | `/auth/reset-password` | `{ token, password }` | `204`. `400` si el enlace no es válido, ya caducó o ya se usó |

- `password` necesita al menos 8 caracteres y `email` tiene que ser un correo válido.
- El registro **no** devuelve token: después de registrarse hay que hacer login.
- El login y `forgot-password` aceptan 5 peticiones por minuto desde una misma IP. Después responden `429`.
- El login usa el formato estándar de OAuth2 (`application/x-www-form-urlencoded`). Por eso el campo se llama `username` aunque contiene el correo, y por eso funciona el botón **Authorize** de `/docs`.

```bash
# Registro
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name": "Ana", "email": "ana@correo.com", "password": "secreta123"}'

# Login
curl -X POST http://127.0.0.1:8000/auth/login \
  -d "username=ana@correo.com&password=secreta123"
# → {"access_token": "eyJhbGciOi...", "token_type": "bearer"}
```

Usuario:

```json
{ "id": 1, "name": "Ana", "email": "ana@correo.com" }
```

### Recuperar la contraseña

1. El cliente llama a `POST /auth/forgot-password` con el correo.
2. Si la cuenta existe, la API envía un correo con el enlace `<FRONTEND_URL>/?reset=<token>`. La respuesta es la misma (`204`) exista o no la cuenta, para no revelar qué correos están registrados. El correo se envía en segundo plano, así que tampoco el tiempo de respuesta lo delata.
3. El frontend lee el `token` del enlace y llama a `POST /auth/reset-password` con la contraseña nueva.

Detalles de seguridad:
- El token es aleatorio (`secrets.token_urlsafe(32)`). En la base de datos solo se guarda su hash SHA-256 y la fecha en que caduca.
- Vale `RESET_MINUTES` minutos y se puede usar una sola vez. Si se pide un enlace nuevo, el anterior deja de funcionar.
- Las sesiones abiertas (tokens JWT emitidos antes del cambio) siguen siendo válidas hasta que vencen.

```bash
curl -X POST http://127.0.0.1:8000/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "ana@correo.com"}'

curl -X POST http://127.0.0.1:8000/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{"token": "<token del enlace>", "password": "nueva-clave"}'
```

En desarrollo, sin `RESEND_API_KEY`, el enlace aparece en la consola donde corre la API.

### Plan de entrenamiento

Cada usuario tiene **un solo plan**, guardado como texto libre. La API no lo interpreta: el frontend lo convierte en días y ejercicios.

| Método | Ruta | Cuerpo | Respuesta |
|--------|------|--------|-----------|
| GET | `/plan/` 🔒 | | `200 { id, user_id, text }`. `404` si el usuario aún no tiene plan |
| PUT | `/plan/` 🔒 | `{ text }` | `200 { id, user_id, text }` |

`PUT` crea el plan si no existe y lo reemplaza si ya existe (upsert). Llamarlo varias veces con el mismo texto deja el mismo resultado. `text` necesita al menos 5 caracteres.

El `404` de `GET /plan/` es un caso normal (un usuario nuevo todavía no tiene plan), no un fallo. Trátalo como "sin plan".

```bash
curl -X PUT http://127.0.0.1:8000/plan/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"text": "# Día 1: Pierna\n- Sentadilla: 4 x 6–8, descanso 2 min"}'
```

### Series

Cada fila es una serie de un ejercicio.

| Método | Ruta | Cuerpo | Respuesta |
|--------|------|--------|-----------|
| GET | `/sets/` 🔒 | | `200` con la lista de series del usuario |
| POST | `/sets/` 🔒 | serie (ver abajo) | `201` con la serie creada |
| DELETE | `/sets/{id}` 🔒 | | `204`. `404` si no existe, `403` si es de otro usuario |

Campos para crear una serie:

| Campo | Tipo | Reglas |
|-------|------|--------|
| `date` | `"YYYY-MM-DD"` | Fecha del entrenamiento. No puede ser futura (se permite un día de margen por la zona horaria) |
| `day` | entero | Posición del día en el plan del usuario, de 1 a 7 |
| `exercise` | texto | Nombre del ejercicio |
| `reps` | entero | Repeticiones |
| `weight` | número | Peso en kg, admite decimales |
| `feel` | texto | Uno de: `"Fácil"`, `"Moderado"`, `"Difícil"`, `"Al Fallo"` |
| `notes` | texto u omitido | Opcional |

La respuesta incluye además `id`, `user_id` y `created_at` (fecha y hora ISO 8601 en UTC). El volumen (`weight × reps`) se calcula y se guarda en la base de datos, pero todavía no se devuelve en la respuesta.

```bash
curl -X POST http://127.0.0.1:8000/sets/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"date": "2026-10-09", "day": 1, "exercise": "Sentadilla", "reps": 8, "weight": 60, "feel": "Moderado"}'
```

```json
{
  "id": 1,
  "user_id": 1,
  "date": "2026-10-09",
  "day": 1,
  "exercise": "Sentadilla",
  "reps": 8,
  "weight": 60.0,
  "feel": "Moderado",
  "notes": null,
  "created_at": "2026-10-09T17:20:29.518940Z"
}
```

### Otros

| Método | Ruta | Respuesta |
|--------|------|-----------|
| GET | `/` | `200 { "status": "ok" }`, para comprobar que el servidor está vivo |

## Estructura

```
alembic/                    migraciones de la base de datos
src/progress_fitness_api/
├── main.py                 app, CORS, routers y manejo de errores
├── database.py             conexión y sesión de SQLAlchemy
├── core/                   seguridad (JWT, bcrypt, tokens de recuperación), dependencias,
│   │                       límite de peticiones y envío de correos
│   └── templates/          plantilla HTML del correo de recuperación
├── models/                 tablas (SQLAlchemy)
├── schemas/                validación de entrada y salida (Pydantic)
├── routers/                endpoints
└── services/               lógica y consultas a la base de datos
tests/                      pruebas con pytest
```

## Migraciones

Después de cambiar un modelo:

```bash
uv run alembic revision --autogenerate -m "describe el cambio"
uv run alembic upgrade head
```

Revisa el archivo generado en `alembic/versions/` antes de aplicarlo, porque el autogenerate no detecta todos los cambios.

## Pruebas

Las pruebas necesitan un PostgreSQL **propio**: crean y borran las tablas en cada ejecución. Nunca uses la base de `DATABASE_URL`. La forma más rápida es un contenedor temporal:

```bash
docker run -d --rm --name pf-test-db -e POSTGRES_PASSWORD=test -e POSTGRES_DB=progress_fitness_test -p 55432:5432 postgres:16

TEST_DATABASE_URL=postgresql+psycopg://postgres:test@localhost:55432/progress_fitness_test uv run pytest

docker stop pf-test-db
```

En PowerShell, define la variable antes: `$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:test@localhost:55432/progress_fitness_test"`.

Sin `TEST_DATABASE_URL`, pytest se detiene sin importar la app. Los correos no se envían: las pruebas los capturan.

## Pendiente

- Cerrar las sesiones abiertas al cambiar la contraseña: guardar en el usuario la fecha del último cambio y rechazar los JWT emitidos antes.
- Leer los orígenes de CORS desde una variable de entorno, para agregar dominios sin cambiar el código.
