# Auditoría API — fastapi-layered-api (RMM + PNM/PM + OWASP Top 10)

> Alcance: `fastapi-layered/app/` (routers, servicios, repositorios, schemas, core, db).
> Fecha: 2026-09-23. 
> Veredicto: **buena base de ejemplo, no apta para producción sin los 4 HIGH.**

---

## 1. Nivel de Madurez de Richardson (RMM): Nivel 2 (sin HATEOAS)

| Nivel | Veredicto | Evidencia |
|---|---|---|
| 0 — POX/RPC | Superado | No hay endpoint único genérico. Recursos separados (`auth`, `users`, `tasks`). |
| 1 — Recursos | Parcial (incumple) | `/users`, `/tasks`, `/users/{id}`, `/tasks/{id}` OK (sustantivos plural). Pero `POST /auth/register` y `POST /auth/login` son RPC con verbos en la URI. REST puro: `POST /users` + `POST /auth/token`. |
| 2 — Verbos + Status | En su mayoría | GET/POST/PUT/DELETE bien usados; `201` al crear, `204` al borrar, `401/403/404/409` presentes. Peros: PUT para update parcial + `responses={...}` inconsistente en OpenAPI. |
| 3 — HATEOAS | Ausente | Ninguna respuesta incluye `_links`. Esperable. No agregar salvo que un cliente lo exija. |

**Calificación: Nivel 2 con dos violaciones de Nivel 1 (verbos en URI).**

---

## 2. Incumplimientos PNM/PM y OWASP (por archivo)

### HIGH 1 — Lectura de tareas pública (exposición excesiva) — `app/api/v1/routers/tasks.py:40-68`
`GET /tasks` y `GET /tasks/{id}` no exigen autenticación. Cualquiera enumera todas las tareas (`description`, `owner_id`, fechas). Sostenido por `list_public` / `get_public_by_id` en `app/repositories/task_repository.py:35-45` y `app/services/task_service.py:22-42`.

### HIGH 2 — Enumeración de usuarios + PII — `app/api/v1/routers/users.py:45-62`
`list_users` solo pide login: cualquier cuenta activa lista todos los usuarios (email + nombre + flags). Cosecha de correos para phishing/stuffing. Debe ser solo-superusuario.

### HIGH 3 — Sin rate limiting / brute-force — todo el proyecto
Sin `slowapi`/limiter ni límite de intentos en `POST /auth/login` (`app/api/v1/routers/auth.py:43-66`). Solo GZip como middleware. Diccionario de credenciales ilimitado.

### HIGH 4 — `is_active` tocable por usuarios — `app/schemas/user.py:37-42` + `app/api/v1/routers/users.py:90-101`
`UserUpdate` incluye `is_active` y el endpoint solo exige self-o-superuser. Un usuario normal se auto-desactiva (y no hay barrera admin). `is_active` debe ir en schema solo-admin.

### MEDIUM 5 — Excepción de dominio equivocada — `app/services/task_service.py:16-26`, `app/api/v1/routers/tasks.py:60-94`
Tareas lanza `UserNotFoundError("Tarea con id=...")` cuando no existe **o es de otro dueño** (`WHERE id+owner_id` retorna None en ambos casos). Devuelve 404 en ambos (OK para no revelar existencia) pero accidental; confunde logs y choca con el handler `DomainError → 400` de `app/main.py:82-93`. Crear `TaskNotFoundError`.

### MEDIUM 6 — PUT usado como PATCH — `app/api/v1/routers/users.py:84`, `app/api/v1/routers/tasks.py:71`
`UserUpdate` y `TaskUpdate` son 100% opcionales → semántica PATCH, no PUT (representación completa idempotente).

### MEDIUM 7 — Enumeración de emails en registro — `app/services/user_service.py:27-31` + `app/api/v1/routers/auth.py:32-40`
`POST /auth/register` responde `409 "El email 'x' ya está registrado"`: oráculo de existencia. El login sí está mitigado (error genérico + hash dummy en `app/core/security.py:47-58`).

### MEDIUM 8 — Error no estándar — `app/schemas/common.py:6-14`
`ErrorResponse { detail: str }` sin `code/status/timestamp/instance`, no RFC 9457. Varios endpoints sin `responses={401,403,404,422}` en OpenAPI.

### LOW 9–12 (higiene)
- Path params sin validar: `user_id: int`, `task_id: int` sin `Path(ge=1)` (`users.py:73`, `tasks.py:61`).
- Código muerto: `LoginRequest`, `TokenPayload` (`app/schemas/auth.py:6-17`); login usa `OAuth2PasswordRequestForm.username` como email.
- Secretos/debug: `.env` commiteado con `SECRET_KEY="CHANGE_ME_..."`, `DEBUG=true` (activa `echo=DEBUG` → SQL en logs, `app/db/session.py:27-31`). Sin validador en `app/core/config.py:36`.
- Sin revocación: JWT solo `sub/iat/exp` (`app/core/security.py:61-79`), sin `jti`/refresh → sin logout. `health` expone `environment` (`app/main.py:97-100`). CORS `allow_methods/headers=["*"]` amplio.

### Lo que SÍ está bien
Argon2 + dummy anti-timing, HS256 fijado (anti alg-confusion), `WWW-Authenticate: Bearer`, `response_model=UserPublic` (nunca `hashed_password`), BOLA en users (`_ensure_self_or_superuser`), ownership en tasks (`WHERE id+owner_id`), commit-on-success con rollback, Pydantic estricta (`EmailStr`, min/max, `Query(ge/le)`), ORM parametrizado.

---

## 3. Código refactorizado

### Fix A — Excepción propia + lecturas protegidas (`core/exceptions.py`, `services/task_service.py`, `routers/tasks.py`)
```python
# app/core/exceptions.py — agregar
class TaskNotFoundError(DomainError):
    """La tarea solicitada no existe."""
```

```python
# app/services/task_service.py — reemplazar get_by_id
async def get_by_id(self, task_id: int, owner_id: int) -> Task:
    task = await self._repository.get_by_id(task_id, owner_id)
    if task is None:
        # No se distingue "no existe" de "es de otro": anti-enumeración.
        raise TaskNotFoundError(f"Tarea con id={task_id} no encontrada.")
    return task
```

```python
# app/api/v1/routers/tasks.py — proteger lecturas + Path + docs de errores
from fastapi import Path
from app.core.exceptions import TaskNotFoundError

@router.get("", response_model=TaskListResponse,
            responses={401: {"model": ErrorResponse}})
async def list_tasks(
    service: Annotated[TaskService, Depends(get_task_service)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> TaskListResponse:
    tasks, total = await service.list_tasks(
        owner_id=current_user.id, page=page, page_size=page_size)
    return TaskListResponse(
        items=[TaskPublic.model_validate(t) for t in tasks],
        total=total, page=page, page_size=page_size)

@router.get("/{task_id}", response_model=TaskPublic,
            responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
async def get_task(
    task_id: Annotated[int, Path(ge=1)],
    service: Annotated[TaskService, Depends(get_task_service)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> TaskPublic:
    try:
        task = await service.get_by_id(task_id, current_user.id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return TaskPublic.model_validate(task)

@router.patch("/{task_id}", response_model=TaskPublic,  # era PUT parcial
              responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
async def update_task(task_id: Annotated[int, Path(ge=1)], ...):
    try:
        task = await service.update_task(task_id, current_user.id, payload)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return TaskPublic.model_validate(task)
```

### Fix B — Cerrar enumeración masiva e `is_active` admin-only (`routers/users.py`, `schemas/user.py`)
```python
# app/schemas/user.py — dividir schemas
class UserUpdate(BaseModel):  # usuario normal
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    password: Optional[str] = Field(None, min_length=8, max_length=128)

class AdminUserUpdate(UserUpdate):  # solo superusuario
    is_active: Optional[bool] = None
```

```python
# app/api/v1/routers/users.py
def _ensure_superuser(u: User) -> None:
    if not u.is_superuser:
        raise HTTPException(status_code=403, detail="Solo administradores.")

@router.get("", response_model=UserListResponse,
            responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
async def list_users(..., current_user: Annotated[User, Depends(get_current_active_user)], ...):
    _ensure_superuser(current_user)
    ...

@router.patch("/{user_id}", ...)  # era PUT parcial
async def update_user(user_id: Annotated[int, Path(ge=1)], payload: UserUpdate, ...):
    _ensure_self_or_superuser(current_user, user_id)
    # is_active solo vía endpoint/schema admin separado
    ...
```

### Fix C — Error estándar RFC 9457 (`schemas/common.py` + `main.py`)
```python
# app/schemas/common.py
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class ProblemDetail(BaseModel):  # RFC 9457
    title: str = Field(examples=["Recurso no encontrado"])
    status: int = Field(examples=[404])
    detail: str = Field(examples=["Tarea con id=41 no encontrada."])
    instance: str = Field(examples=["/api/v1/tasks/41"])
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    code: str = Field(examples=["TASK_NOT_FOUND"])
```

```python
# app/main.py — sumar al handler existente
@app.exception_handler(TaskNotFoundError)
async def task_not_found(request: Request, exc: TaskNotFoundError):
    return JSONResponse(status_code=404, content=ProblemDetail(
        title="Recurso no encontrado", status=404, detail=str(exc),
        instance=request.url.path, code="TASK_NOT_FOUND").model_dump(mode="json"))
```

### Fix D — Rate limiting en login + secreto obligatorio (`routers/auth.py`, `core/config.py`)
```python
# pip install slowapi — app/api/v1/routers/auth.py
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)

@router.post("/login", response_model=Token, responses={401: {"model": ErrorResponse}})
@limiter.limit("5/minute")
async def login(request: Request, form_data: ..., service: ...): ...
```

```python
# app/core/config.py
from pydantic import field_validator
@field_validator("SECRET_KEY")
@classmethod
def _strong_secret(cls, v: str) -> str:
    if len(v) < 32 or "CHANGE_ME" in v:
        raise ValueError("SECRET_KEY insegura: genera con `openssl rand -hex 32`.")
    return v
```

Adicional: registro con mensaje genérico (`"No se pudo completar el registro."`, código `EMAIL_TAKEN` solo en logs), `DEBUG=false` en `.env` commiteado, `jti` en `create_access_token` si se necesita revocación.

### Orden sugerido
1. Fix A + B (BOLA/exposición — hoy). 2. Fix D (rate limit + secret — hoy). 3. Fix C + PUT→PATCH + `Path(ge=1)` (esta semana). 4. HATEOAS: no hacer. 5. Renombrar `/auth/*` solo en v2 (compat v1).
