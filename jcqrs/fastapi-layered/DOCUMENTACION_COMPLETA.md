# Que hace este proyecto y como fluye todo

## 1. Resumen

Este proyecto implementa una API REST para gestionar usuarios y sus tareas
con FastAPI. Permite registrar usuarios, iniciar sesion, emitir y validar JWT
Bearer, consultar el usuario actual, listar usuarios con paginacion y hacer
CRUD de tareas propias.

La arquitectura tiene una sola direccion de dependencias:

```text
Cliente HTTP
    -> Routers/API (HTTP, validacion y status codes)
    -> Services (reglas de negocio)
    -> Repositories (consultas SQLAlchemy)
    -> Models/DB (tablas, engine y sesiones)
```

`core` es transversal: contiene configuracion, seguridad y excepciones de
dominio. Las capas internas no conocen HTTP.

## 2. Implementacion real

La implementacion versionada esta en `fastapi-layered/`:

```text
fastapi-layered/
|-- app/
|   |-- main.py
|   |-- core/{config.py,exceptions.py,security.py}
|   |-- db/{base.py,session.py}
|   |-- models/{user.py,task.py}
|   |-- schemas/{auth.py,common.py,user.py,task.py}
|   |-- repositories/{user_repository.py,task_repository.py}
|   |-- services/{user_service.py,task_service.py}
|   `-- api/{deps.py,v1/api.py,v1/routers/{auth.py,users.py,tasks.py}}
|-- tests/{conftest.py,test_auth.py,test_users.py,test_tasks.py}
|-- requirements.txt
|-- Dockerfile
|-- pytest.ini
|-- .env.example
`-- README.md
```

Las carpetas `app/` y `tests/` de la raiz del workspace solo contienen
artefactos `__pycache__`; no son la fuente versionada que monta la aplicacion.
El `app.db` de la raiz es una base local, no codigo.

## 3. Arranque y ciclo de vida

El punto de entrada es `app/main.py` y el objeto ASGI final se llama `app`.
Desde `fastapi-layered/` se ejecuta:

```bash
uvicorn app.main:app --reload
```

El arranque ocurre asi:

1. `get_settings()` lee `.env` y variables de entorno; `lru_cache` evita
   reconstruir la configuracion en cada request.
2. Se crea el engine async de SQLAlchemy usando `DATABASE_URL`.
3. `create_application()` crea FastAPI con metadatos OpenAPI.
4. Se registra CORS si hay origenes configurados.
5. Se registra GZip para respuestas mayores de 1000 bytes.
6. Se registra el manejador global de `DomainError`.
7. Se agregan los routers bajo `/api/v1`.
8. Al entrar al `lifespan`, `Base.metadata.create_all` crea tablas faltantes.
9. La aplicacion atiende requests.
10. Al apagarse, `engine.dispose()` libera conexiones.

FastAPI expone automaticamente `/docs` (Swagger UI) y `/redoc` (ReDoc).

`GET /health` es publico y devuelve:

```json
{"status": "ok", "environment": "development"}
```

## 4. Configuracion

`app/core/config.py` define `Settings` con Pydantic Settings. Lee el entorno
y `.env`; las variables de entorno tienen prioridad.

| Variable | Default | Funcion |
|---|---|---|
| `APP_NAME` | `Users API` | Nombre en OpenAPI |
| `APP_VERSION` | `1.0.0` | Version publicada |
| `API_V1_PREFIX` | `/api/v1` | Prefijo de version |
| `ENVIRONMENT` | `development` | Valor mostrado por health |
| `DEBUG` | `false` | Activa `echo` SQL |
| `DATABASE_URL` | `sqlite+aiosqlite:///./app.db` | Conexion async |
| `SECRET_KEY` | obligatoria | Firma de JWT |
| `ALGORITHM` | `HS256` | Algoritmo JWT permitido |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Vida del access token |
| `BACKEND_CORS_ORIGINS` | `[]` | CSV de origenes permitidos |

El validador de CORS convierte una cadena separada por comas en una lista.
Los campos desconocidos del entorno se ignoran.

## 5. Base de datos y transacciones

`app/db/base.py` define la clase declarativa `Base`. El modelo ORM
`app/models/user.py` registra la tabla `users`:

| Columna | Reglas |
|---|---|
| `id` | entero, primary key e indice |
| `email` | requerido, unico e indexado |
| `full_name` | requerido |
| `hashed_password` | requerido; nunca sale por HTTP |
| `is_active` | booleano, default `true` |
| `is_superuser` | booleano, default `false` |
| `created_at` | fecha/hora generada por la BD |
| `updated_at` | fecha/hora con `onupdate` |

La tabla `tasks` representa el segundo recurso:

| Columna | Reglas |
|---|---|
| `id` | entero, primary key e indice |
| `title` | requerido, maximo 255 caracteres |
| `description` | opcional, texto de hasta 5000 caracteres |
| `completed` | booleano, default `false` |
| `owner_id` | FK requerida a `users.id`, con borrado en cascada |
| `created_at`, `updated_at` | fechas de auditoria |

La relacion es `User 1 -> N Task`. El cliente nunca envia `owner_id`: el
servidor lo obtiene del JWT. El repositorio filtra siempre por el propietario,
por lo que un usuario no puede acceder a la tarea de otro aunque conozca su id.

`db/session.py` crea un engine compartido y una sesion `AsyncSession` por
request. Usa `aiosqlite`; se puede cambiar el driver mediante
`DATABASE_URL`.

La dependencia `get_db()` implementa una unidad de trabajo por request:

1. Abre la sesion.
2. La entrega a repositorio, servicio y router mediante `Depends`.
3. Si todo termina bien, hace un unico `commit`.
4. Si ocurre cualquier excepcion, hace `rollback` y relanza el error.
5. Cierra la sesion al salir del contexto.

Los repositorios solo hacen `flush()` para obtener ids o sincronizar cambios;
no hacen `commit`.

## 6. Schemas: entradas y salidas

- `UserBase`: email valido y `full_name` entre 1 y 255 caracteres.
- `UserCreate`: agrega password entre 8 y 128 caracteres.
- `UserUpdate`: `full_name`, `password` e `is_active` opcionales; permite
  actualizacion parcial aunque la ruta se llame `PUT`.
- `UserPublic`: id, email, nombre, flags y fechas; excluye passwords.
- `UserListResponse`: items y metadatos `total`, `page`, `page_size`.
- `Token`: `access_token` y `token_type` (`bearer`).
- `ErrorResponse`: `{ "detail": "..." }`.

`UserPublic` usa `from_attributes=True` para construirse desde ORM.

`LoginRequest` y `TokenPayload` existen en `schemas/auth.py`, pero el flujo
actual no los usa: login usa `OAuth2PasswordRequestForm` y el JWT se maneja
como diccionario.

## 7. Cadena de dependencias

Para una ruta con servicio y BD, FastAPI resuelve:

```text
get_db()
  -> get_user_repository(db)
      -> get_user_service(repository)
          -> router
```

Para una ruta protegida se suma:

```text
Authorization: Bearer <jwt>
  -> oauth2_scheme
      -> get_current_user
          -> decode_access_token
          -> service.get_by_id(sub)
              -> get_current_active_user
                  -> router
```

`OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")` extrae el Bearer y
configura el boton Authorize de Swagger.

## 8. Todos los endpoints y sus flujos

### `POST /api/v1/auth/register`

Es publico y recibe JSON `UserCreate`.

1. FastAPI valida email, nombre y longitud de password.
2. El router llama a `UserService.register`.
3. El servicio busca el email con `UserRepository.get_by_email`.
4. Si existe, lanza `UserAlreadyExistsError` y el router devuelve `409`.
5. Si no existe, `hash_password` genera un hash Argon2.
6. El repositorio crea `User`, hace `flush`, refresca el objeto y lo devuelve.
7. `get_db()` hace el `commit` al terminar el request.
8. El router transforma el ORM a `UserPublic`.

Respuesta: `201 Created`, sin password ni hash.

### `POST /api/v1/auth/login`

Es publico y recibe `application/x-www-form-urlencoded`, no JSON:

```text
username=ada@example.com&password=ClaveSegura123
```

Aunque OAuth2 llama `username` al campo, el valor esperado es un email.

1. `OAuth2PasswordRequestForm` parsea el formulario.
2. El servicio busca el email.
3. Verifica la password contra Argon2.
4. Si el usuario no existe, verifica contra `_DUMMY_HASH` para igualar el
   coste aproximado y dificultar la enumeracion de usuarios.
5. Si email o password fallan, devuelve `401` con mensaje generico.
6. Si existe pero esta inactivo, devuelve `401`.
7. Si todo es correcto, `create_access_token` firma un JWT HS256.
8. El JWT contiene `sub` con el id, `iat` de emision y `exp` de expiracion.

Respuesta exitosa: `200 OK`:

```json
{"access_token": "...", "token_type": "bearer"}
```

### `GET /api/v1/users/me`

Requiere `Authorization: Bearer <token>`.

1. `oauth2_scheme` extrae el token.
2. `decode_access_token` verifica firma, secreto, algoritmo y expiracion.
3. Se lee `sub` y se convierte a entero.
4. Se busca ese usuario en la base de datos.
5. Token invalido, sin `sub`, con id no entero o usuario inexistente produce
   `401`.
6. Usuario inactivo produce `403` mediante `get_current_active_user`.
7. El router devuelve `UserPublic` con `200 OK`.

### `GET /api/v1/users`

Requiere un usuario activo autenticado. Cualquier usuario activo puede listar.

Query params:

- `page`: minimo 1, default `1`.
- `page_size`: entre 1 y 100, default `20`.

El servicio calcula `offset = (page - 1) * page_size`. El repositorio ejecuta
una consulta ordenada por `id` con `offset` y `limit`, y otra con `count(*)`.

Respuesta `200 OK`:

```json
{"items": [], "total": 0, "page": 1, "page_size": 20}
```

### `GET /api/v1/users/{user_id}`

Requiere usuario activo y autorizacion por objeto.

1. `_ensure_self_or_superuser` permite el propio id o cualquier id a un
   superusuario.
2. Si no coincide, devuelve `403` sin consultar el recurso objetivo.
3. Si coincide pero no existe, devuelve `404`.
4. Si existe, devuelve `200` con `UserPublic`.

### `PUT /api/v1/users/{user_id}`

Requiere propietario o superusuario y recibe `UserUpdate`.

1. Verifica autorizacion.
2. Busca el usuario; si no existe, devuelve `404`.
3. Actualiza `full_name` si fue enviado.
4. Actualiza `is_active` si fue enviado.
5. Hashea y reemplaza la password si fue enviada.
6. Hace `flush` y refresca el ORM.
7. `get_db()` confirma con `commit`.
8. Devuelve `UserPublic`.

No permite cambiar `email` ni `is_superuser`, porque no existen en
`UserUpdate`.

### `DELETE /api/v1/users/{user_id}`

Requiere propietario o superusuario.

1. Verifica autorizacion.
2. Busca el usuario; si no existe, devuelve `404`.
3. El repositorio marca el objeto para borrado y hace `flush`.
4. `get_db()` hace `commit`.

Respuesta exitosa: `204 No Content`, sin cuerpo.

### `POST /api/v1/tasks`

Requiere un usuario activo autenticado. Recibe:

```json
{"title": "Aprender FastAPI", "description": "Crear un CRUD"}
```

El servicio toma el id del usuario autenticado y crea la tarea con
`completed=false`. El cliente no puede asignar la tarea a otro usuario.
Devuelve `201 Created`.

### `GET /api/v1/tasks`

Requiere autenticacion. Acepta `page` (minimo 1, default 1) y `page_size`
(1-100, default 20). Devuelve unicamente las tareas del usuario autenticado,
ordenadas por id, junto con `total`, `page` y `page_size`.

### `GET /api/v1/tasks/{task_id}`

Requiere autenticacion. Busca por `task_id` y por el id del usuario actual.
Devuelve `200` si la tarea es propia y `404` si no existe o pertenece a otro
usuario. Esta respuesta evita revelar recursos de otros propietarios.

### `PUT /api/v1/tasks/{task_id}`

Requiere autenticacion. Acepta parcialmente `title`, `description` y
`completed`. Solo actualiza una tarea propia y devuelve `404` para tareas
ajenas o inexistentes.

### `DELETE /api/v1/tasks/{task_id}`

Requiere autenticacion. Elimina una tarea propia y devuelve `204`. Al eliminar
un usuario, la relacion ORM elimina sus tareas asociadas.

## 9. Manejo de errores

Las excepciones de negocio no dependen de FastAPI:

- `UserAlreadyExistsError` -> `409 Conflict` en registro.
- `UserNotFoundError` -> `404 Not Found` en get/update/delete.
- `InvalidCredentialsError` -> `401 Unauthorized` en login.
- `InactiveUserError` -> `401 Unauthorized` en login.
- Token invalido o usuario no resoluble -> `401 Unauthorized`.
- Usuario inactivo en rutas protegidas -> `403 Forbidden`.
- Acceso de un usuario al recurso de otro -> `403 Forbidden`.

Si un `DomainError` escapa de un router, el manejador global devuelve `400`
con `detail`. Las validaciones de Pydantic/FastAPI ocurren antes de entrar
al endpoint y generan los errores automaticos de validacion.

## 10. Seguridad implementada

- Passwords almacenadas con Argon2; nunca se guarda texto plano.
- JWT firmado con secreto configurable y algoritmo restringido explicitamente.
- Claims `iat` y `exp` en los tokens emitidos.
- Tokens Bearer en el header `Authorization`.
- Mensaje generico para no revelar si existe un email.
- Hash senal cuando el usuario no existe para mitigar diferencias de tiempo.
- `UserPublic` impide devolver hashes por accidente.
- Autorizacion a nivel de objeto contra acceso horizontal entre usuarios.
- Limite de `page_size` a 100.
- Contenedor ejecutado como usuario no-root.
- CORS configurable.
- Manejador global que evita filtrar detalles internos de errores de dominio.

Es un ejemplo educativo, no una configuracion completa de produccion.
Faltan rate limiting, refresh y revocacion de tokens, logging estructurado,
migraciones Alembic, gestion externa de secretos y controles operativos.

## 11. Tests y flujo de prueba

Los tests usan `pytest`, `pytest-asyncio` y `httpx`. No levantan un servidor
TCP: `httpx.ASGITransport` llama directamente a la aplicacion ASGI.

`conftest.py` fija una clave y una SQLite en memoria antes de importar la app.
La fixture `db_session` crea tablas en una base aislada con `StaticPool`.
La fixture `client` reemplaza `get_db` usando
`app.dependency_overrides`, por lo que no toca el `app.db` real; al terminar
limpia los overrides.

Se comprueba:

- Registro devuelve `201` y no filtra password/hash.
- Email duplicado devuelve `409`.
- Login correcto devuelve JWT Bearer.
- Password incorrecta devuelve `401`.
- `/users/me` rechaza peticiones sin autenticacion.
- `/users/me` devuelve el usuario autenticado.
- Un usuario no puede leer el recurso de otro (`403`).
- El listado devuelve metadatos de paginacion.
- Las tareas requieren autenticacion.
- Un usuario puede crear, listar, actualizar y eliminar sus tareas.
- Un usuario no puede consultar la tarea de otro (`404`).

Comando desde `fastapi-layered/`:

```powershell
..\.venv\Scripts\python.exe -m pytest -q
```

## 12. Ejecucion manual completa

Desde `fastapi-layered/`:

```powershell
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Registro:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"ada@example.com","full_name":"Ada Lovelace","password":"ClaveSegura123"}'
```

Login:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=ada@example.com&password=ClaveSegura123"
```

Consulta autenticada:

```bash
curl http://127.0.0.1:8000/api/v1/users/me \
  -H "Authorization: Bearer <access_token>"
```

## 13. Docker

El `Dockerfile` usa `python:3.12-slim`, desactiva bytecode, fuerza logs sin
buffer, instala `requirements.txt`, copia `app`, crea el usuario no-root
`appuser`, expone 8000 y arranca Uvicorn en `0.0.0.0:8000`.

```bash
docker build -t fastapi-layered .
docker run --rm -p 8000:8000 --env-file .env fastapi-layered
```

En produccion hay que apuntar `DATABASE_URL` a una BD adecuada, quitar
`--reload` si se agrega, y reemplazar `create_all` por migraciones.

## 14. Dependencias principales

- `fastapi`: framework ASGI y OpenAPI.
- `uvicorn`: servidor ASGI.
- `pydantic` y `pydantic-settings`: schemas y configuracion.
- `sqlalchemy`, `aiosqlite`, `greenlet`: ORM y SQLite async.
- `pwdlib[argon2]`: hashing de contrasenas.
- `pyjwt`: creacion y validacion JWT.
- `python-multipart`: formularios OAuth2.
- `pytest`, `pytest-asyncio`, `httpx`: pruebas async contra ASGI.

## 15. Detalles que no hay que asumir

- El registro no inicia sesion automaticamente; hay que hacer login despues.
- Las tareas pertenecen al usuario del token y no aceptan `owner_id` desde el
  cliente.
- El JWT solo contiene el id (`sub`), no el email ni roles detallados.
- `is_superuser` existe y se consulta, pero no hay endpoint para concederlo.
- Todo usuario activo puede listar `/users`; la regla de propietario se aplica
  a `/{user_id}`, no al listado.
- El login recibe `username`, aunque semanticamente es un email.
- La ruta es `PUT`, pero el payload permite actualizacion parcial.
- `create_all` crea tablas faltantes, pero no migra cambios de esquema.
- La SQLite por defecto es relativa al directorio actual del proceso.
- El commit ocurre despues del endpoint, dentro de `get_db`; si falla, hay
  rollback.
