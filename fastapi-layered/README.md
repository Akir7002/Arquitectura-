# Users API — API REST en capas con FastAPI

API REST de ejemplo, **documentada paso a paso**, que implementa una
**arquitectura en capas** (layered architecture) con [FastAPI](https://fastapi.tiangolo.com/),
siguiendo la documentación oficial de FastAPI, el estándar OAuth2/JWT
(RFC 6749 / RFC 7519) y el **OWASP API Security Top 10 (2023)**.

Caso de uso: gestión de usuarios con registro, login y autenticación JWT.

> Este proyecto es el material de acompañamiento de la presentación
> `FastAPI - API REST en capas.pptx`. El código es funcional: fue instalado,
> arrancado y probado end-to-end (registro, login, CRUD y errores) antes
> de esta entrega.

---

## 1. Por qué una arquitectura en capas

Separar responsabilidades en capas con una única dirección de dependencia
(API → Servicios → Repositorios → Modelos) es una práctica estándar de
la industria (equivalente a *Clean/Hexagonal Architecture* aplicada a un
proyecto FastAPI). Objetivos:

- **Testabilidad**: los servicios se pueden probar sin levantar HTTP;
  los repositorios se pueden sustituir por dobles de prueba.
- **Mantenibilidad**: cambiar de SQLite a PostgreSQL, o de JWT a sesiones,
  afecta solo a una capa.
- **Separación de responsabilidades (SRP)**: cada capa tiene un único
  motivo de cambio.

```
Cliente HTTP
     │
     ▼
┌─────────────────────┐  Recibe/valida HTTP, traduce excepciones
│   API (routers)      │  de dominio a códigos de estado HTTP.
└─────────┬────────────┘
          ▼
┌─────────────────────┐  Reglas de negocio: unicidad de email,
│   Services            │  autenticación, emisión de JWT.
└─────────┬────────────┘
          ▼
┌─────────────────────┐  Traduce operaciones de negocio a
│   Repositories         │  consultas SQLAlchemy (patrón Repository).
└─────────┬────────────┘
          ▼
┌─────────────────────┐  Modelos ORM + engine/sesión async.
│   Models / DB          │
└─────────────────────┘
```

Capa transversal **Core**: configuración (`pydantic-settings`), seguridad
(hash de contraseñas + JWT) y excepciones de dominio, usadas por varias capas.

---

## 2. Estructura del proyecto

```
fastapi-layered-api/
├── app/
│   ├── main.py                     # Application factory, middlewares, lifespan
│   ├── core/
│   │   ├── config.py               # Settings (pydantic-settings) + .env
│   │   ├── security.py             # Hash Argon2 (pwdlib) + JWT (pyjwt)
│   │   └── exceptions.py           # Excepciones de dominio (sin HTTP)
│   ├── db/
│   │   ├── base.py                 # Declarative Base de SQLAlchemy
│   │   └── session.py              # engine async + get_db() con commit-on-success
│   ├── models/
│   │   └── user.py                 # Modelo ORM (tabla `users`)
│   ├── schemas/
│   │   ├── user.py                 # UserCreate / UserUpdate / UserPublic
│   │   ├── auth.py                 # Token, LoginRequest
│   │   └── common.py               # ErrorResponse
│   ├── repositories/
│   │   └── user_repository.py      # CRUD puro contra la base de datos
│   ├── services/
│   │   └── user_service.py         # Reglas de negocio + orquestación
│   └── api/
│       ├── deps.py                 # Dependencias compartidas (DB, auth)
│       └── v1/
│           ├── api.py              # Agregador de routers v1
│           └── routers/
│               ├── auth.py         # POST /auth/register, /auth/login
│               └── users.py        # /users/me, /users, /users/{id}
├── tests/                          # pytest + httpx.AsyncClient
│   ├── conftest.py
│   ├── test_auth.py
│   └── test_users.py
├── requirements.txt
├── .env.example
├── .gitignore
├── Dockerfile
└── pytest.ini
```

---

## 3. Guía paso a paso: cómo se construyó (y cómo ejecutarlo)

### Paso 1 — Entorno virtual y dependencias

```bash
python3 -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Librerías clave y por qué se eligieron:

| Librería | Uso | Referencia |
|---|---|---|
| `fastapi` | Framework web ASGI | https://fastapi.tiangolo.com |
| `uvicorn[standard]` | Servidor ASGI de producción | Recomendado en docs oficiales de FastAPI |
| `pydantic` / `pydantic-settings` | Validación de datos y configuración tipada | https://fastapi.tiangolo.com/advanced/settings/ |
| `sqlalchemy` (async) + `aiosqlite` | ORM y acceso a datos no bloqueante | https://fastapi.tiangolo.com/tutorial/sql-databases/ |
| `pwdlib[argon2]` | Hash de contraseñas (Argon2) | Recomendación oficial actual de FastAPI para OAuth2+JWT |
| `pyjwt` | Firma/verificación de JWT (RFC 7519) | Recomendación oficial actual de FastAPI |
| `pytest`, `httpx`, `pytest-asyncio` | Testing automatizado | https://fastapi.tiangolo.com/tutorial/testing/ |

### Paso 2 — Configuración (`app/core/config.py`)

Se define una clase `Settings(BaseSettings)` que lee variables de entorno
y un archivo `.env`, con `lru_cache` para no releerlo en cada request.
Esto sigue el factor **"Config"** de la metodología
[12-Factor App](https://12factor.net/config): la configuración vive en
el entorno, nunca hardcodeada.

```bash
cp .env.example .env
# Generar una clave fuerte para SECRET_KEY:
openssl rand -hex 32
```

Edita `.env` y reemplaza `SECRET_KEY` con el valor generado.

### Paso 3 — Modelo de datos (`app/models/user.py`)

Se define la entidad `User` como modelo SQLAlchemy 2.0 (`Mapped[...]`,
tipado moderno). **Nunca** se expone este modelo directamente en las
respuestas HTTP.

### Paso 4 — Schemas Pydantic (`app/schemas/user.py`)

Se separan los contratos por propósito: `UserCreate` (entrada, incluye
password), `UserUpdate` (entrada parcial), `UserPublic` (salida, sin
password). Esta separación evita fugas accidentales de datos sensibles
y es el patrón documentado oficialmente por FastAPI.

### Paso 5 — Repositorio (`app/repositories/user_repository.py`)

Encapsula todas las consultas SQL (`select`, `get`, `count`, etc.). No
conoce reglas de negocio ni HTTP.

### Paso 6 — Seguridad (`app/core/security.py`)

- Hash de contraseñas con **Argon2** vía `pwdlib` (ganador de la Password
  Hashing Competition; resistente a ataques por GPU/ASIC).
- Emisión y verificación de **JWT** vía `pyjwt`, con `exp` (expiración) e
  `iat` obligatorios, y el algoritmo fijado explícitamente (`algorithms=[...]`)
  para evitar el ataque de "alg confusion".
- Verificación contra un hash señuelo cuando el usuario no existe, para
  no filtrar por tiempo de respuesta si un email está registrado.

### Paso 7 — Servicio (`app/services/user_service.py`)

Contiene las reglas de negocio: registrar (valida email único), autenticar
(valida credenciales + estado activo), emitir tokens, actualizar y borrar.
Lanza excepciones de dominio (`app/core/exceptions.py`), nunca `HTTPException`.

### Paso 8 — Dependencias de API (`app/api/deps.py`)

Se define `OAuth2PasswordBearer` (para que `/docs` muestre el botón
"Authorize") y las dependencias encadenadas `get_user_repository` →
`get_user_service` → `get_current_user` → `get_current_active_user`.

### Paso 9 — Routers (`app/api/v1/routers/`)

Cada router recibe la petición, la valida con un schema, invoca al
servicio y traduce las excepciones de dominio a códigos HTTP (`401`,
`403`, `404`, `409`). Aplica autorización a nivel de objeto: un usuario
solo puede leer/editar su propio recurso (mitigación de OWASP
**API1:2023 Broken Object Level Authorization**).

### Paso 10 — Aplicación principal (`app/main.py`)

Ensambla todo: crea la app, agrega middlewares (CORS, GZip), registra un
manejador global de excepciones de dominio, incluye los routers bajo el
prefijo `/api/v1` (versionado por URL) y expone `/health`.

### Paso 11 — Levantar el servidor

```bash
uvicorn app.main:app --reload
```

Documentación interactiva autogenerada por FastAPI (OpenAPI 3.1):

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

### Paso 12 — Probar el flujo completo

```bash
# 1) Registro
curl -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"ada@example.com","full_name":"Ada Lovelace","password":"ClaveSegura123"}'

# 2) Login (form-urlencoded, estándar OAuth2 Password Flow)
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -d "username=ada@example.com&password=ClaveSegura123"
# => {"access_token": "...", "token_type": "bearer"}

# 3) Usar el token
curl http://127.0.0.1:8000/api/v1/users/me \
  -H "Authorization: Bearer <access_token>"
```

### Paso 13 — Tests automatizados

```bash
pytest -v
```

Los tests usan SQLite **en memoria** e inyectan la sesión de prueba con
`app.dependency_overrides[get_db]` (mecanismo oficial de testing de
FastAPI: https://fastapi.tiangolo.com/tutorial/testing/), sin depender
de la base de datos real ni de un servidor HTTP levantado.

---

## 4. Buenas prácticas aplicadas (resumen)

- **Arquitectura en capas** con dirección de dependencia única.
- **`response_model` explícito** en cada endpoint (nunca se serializa el
  modelo ORM directamente).
- **Versionado de API** por prefijo de URL (`/api/v1`), facilita introducir
  `/api/v2` sin romper clientes existentes.
- **Paginación** en endpoints de colección (`page`, `page_size`, `total`).
- **Inyección de dependencias** (`Depends`) para DB, servicios y usuario
  autenticado — facilita el testing y evita acoplamiento.
- **Manejo consistente de errores**: excepciones de dominio traducidas a
  códigos HTTP correctos (`401/403/404/409`), formato de error uniforme.
- **Seguridad (OWASP API Security Top 10 2023)**:
  - API1 *Broken Object Level Authorization* → verificación de propiedad
    del recurso en cada endpoint de `/users/{id}`.
  - API2 *Broken Authentication* → JWT firmado, expiración corta,
    hashing Argon2, mitigación de timing attacks.
  - API8 *Security Misconfiguration* → manejador global que evita fugar
    detalles internos ante errores no controlados.
- **Transacciones**: patrón *Unit of Work por request* (`commit` al
  final si todo sale bien, `rollback` ante cualquier excepción).
- **Configuración externalizada** (12-Factor App): nada de secretos en
  el código fuente.
- **Contenedores**: `Dockerfile` con usuario no-root e imagen `slim`.
- **Testing automatizado** con base de datos aislada por test.

## 5. De este ejemplo a producción

Este proyecto es un ejemplo educativo. Antes de usarlo en producción,
considera:

1. **Migraciones versionadas** con [Alembic](https://alembic.sqlalchemy.org/)
   en lugar de `Base.metadata.create_all` en el `lifespan`.
2. **PostgreSQL** (`postgresql+asyncpg://...`) en vez de SQLite.
3. **Rate limiting** (p. ej. `slowapi`) para mitigar OWASP
   **API4:2023 Unrestricted Resource Consumption**.
4. **Logging estructurado** y correlación de requests (request id).
5. **Refresh tokens** y una estrategia de revocación de tokens (deny-list
   o tokens de corta duración + refresh).
6. **CI/CD** ejecutando `pytest` y linters (`ruff`, `mypy`) en cada PR.
7. **Gestión de secretos** con un vault (AWS Secrets Manager, Vault, etc.)
   en vez de un archivo `.env` en el servidor.

---

## Fuentes y estándares consultados

- FastAPI — Bigger Applications: https://fastapi.tiangolo.com/tutorial/bigger-applications/
- FastAPI — OAuth2 with Password and JWT: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
- FastAPI — SQL Databases: https://fastapi.tiangolo.com/tutorial/sql-databases/
- FastAPI — Settings and Environment Variables: https://fastapi.tiangolo.com/advanced/settings/
- FastAPI — Testing: https://fastapi.tiangolo.com/tutorial/testing/
- OWASP API Security Top 10 (2023): https://owasp.org/API-Security/editions/2023/en/0x11-t10/
- The Twelve-Factor App: https://12factor.net/
- RFC 6749 (OAuth 2.0): https://www.rfc-editor.org/rfc/rfc6749
- RFC 7519 (JSON Web Token): https://www.rfc-editor.org/rfc/rfc7519
