# Arquitectura de la aplicación

## 1. Resumen ejecutivo

Este proyecto implementa una combinación de **Clean Architecture**, **Domain-Driven Design (DDD)** y patrones de **Ports and Adapters**.

La aplicación es una API HTTP asíncrona construida con FastAPI para administrar usuarios y autenticarlos mediante OAuth2 Password Flow y JWT.

La regla principal es:

> Las políticas de negocio viven en `app/core`; los detalles externos viven en `app/infra`.

La dependencia conceptual fluye hacia el centro:

```text
Cliente HTTP
    -> API / FastAPI
    -> Casos de uso
    -> Entidades, value objects y puertos
    -> Adaptadores de infraestructura
    -> PostgreSQL / hashing / JWT
```

El dominio no debería conocer FastAPI, SQLModel, PostgreSQL, Passlib ni JWT. En cambio, la infraestructura conoce los contratos (`Protocol`) definidos por el núcleo y los implementa.

## 2. Capas presentes

### 2.1 Capa de entrada y entrega (`app/infra/api`)

Es la capa que recibe HTTP y convierte HTTP en llamadas a la aplicación.

Componentes principales:

- `app/infra/api/app.py`: crea la instancia FastAPI, registra routers, handlers y lifespan.
- `app/infra/api/routers/root.py`: endpoint `/health-check`.
- `app/infra/api/routers/v1/user.py`: endpoints CRUD de usuarios.
- `app/infra/api/routers/v1/auth.py`: emisión de tokens y consulta del usuario autenticado.
- `app/infra/api/dependencies/*`: composición de dependencias y adaptadores concretos.
- `app/infra/api/extensions.py`: conversión de errores de validación a respuestas HTTP.

Esta capa conoce HTTP, códigos de estado, headers, OAuth2 y FastAPI. No contiene la lógica de negocio principal; delega esa responsabilidad en los casos de uso.

### 2.2 Capa de aplicación (`app/core/usecases`)

Los casos de uso coordinan una operación completa del sistema. Reciben DTOs o valores simples, aplican reglas y usan puertos para acceder a recursos externos.

Casos existentes:

| Caso de uso | Responsabilidad | Dependencia principal |
|---|---|---|
| `CreateUserUsecase` | Validar, comprobar duplicado, hashear contraseña y guardar usuario | `UserUnitOfWork`, `Hasher` |
| `GetUserUsecase` | Buscar un usuario por UUID | `UserRepo` |
| `UpdateUserUsecase` | Leer, construir versión actualizada y persistir | `UserUnitOfWork` |
| `DeleteUserUsecase` | Convertir ID y eliminar | `UserRepo` |
| `AuthenticateUserUsecase` | Validar email, consultar usuario y verificar contraseña | `UserRepo`, `Hasher` |

Los casos de uso devuelven `UserResponse` o un resultado simple. No devuelven modelos SQLModel ni respuestas HTTP.

### 2.3 Núcleo de dominio (`app/core/entities`, `value_objects`, `exceptions`)

El dominio contiene conceptos y reglas que no dependen de la tecnología web o de la base de datos.

#### Entidad `User`

Archivo: `app/core/entities/user.py`.

`User` es una entidad porque tiene identidad propia (`ID`) y representa al usuario a lo largo del tiempo. Sus campos son:

- `id: ID`: identidad UUID.
- `name: str`: nombre obligatorio.
- `email: Email`: email validado.
- `password: Password`: contraseña o hash con la regla de longitud.

La entidad es inmutable (`dataclass(frozen=True)`) y rechaza un nombre vacío.

#### Value objects

Los value objects representan valores válidos, sin identidad independiente:

- `Email`: comprueba el patrón del correo.
- `Password`: exige entre 8 y 100 caracteres.
- `ID`: encapsula UUID, puede generarse o reconstruirse desde texto.

Al estar congelados, reducen estados inválidos y hacen explícita la validación del dominio.

#### Excepciones

`app/core/exceptions.py` define errores de negocio como `UserNotFoundError`, `UserAlreadyExistsError`, `AuthenticationFailedError` e `InvalidUserError`. Los routers traducen estos errores a HTTP 400, 401, 404 o 409.

### 2.4 Contratos o puertos (`app/core/ports`)

Los puertos son interfaces que expresan lo que el núcleo necesita, sin acoplarse a una implementación.

- `UserRepo`: guardar, buscar por ID, buscar por email, actualizar y eliminar.
- `UserUnitOfWork`: exponer `user_repo` y controlar commit/rollback.
- `Hasher`: hashear y verificar contraseñas.

Estos contratos son `Protocol`. La infraestructura los implementa de forma estructural: no necesita heredar explícitamente para ser compatible.

### 2.5 Infraestructura (`app/infra`)

Contiene adaptadores concretos y detalles externos:

- `infra/db/models/user.py`: tabla SQLModel `users`.
- `infra/db/repositories/user.py`: convierte entre `User` y `DBUser` y ejecuta consultas.
- `infra/db/unit_of_work/*`: administra sesión y transacción.
- `infra/security/crypto.py`: implementa `Hasher` con Passlib/bcrypt.
- `infra/auth/jwt.py`: crea y decodifica JWT.
- `infra/db/migrations`: evolución del esquema mediante Alembic.

## 3. DTO, entidad y modelo de persistencia

Son objetos diferentes y cumplen responsabilidades diferentes.

### DTO (`app/core/dtos`)

Transporta datos entre límites:

- `CreateUserRequest`: `name`, `email`, `password` de entrada.
- `UpdateUser`: campos opcionales `name` y `email`; exige al menos uno.
- `UserResponse`: representación pública de un usuario, sin exponer la contraseña.
- `TokenResponse`: `expire`, `access_token` y `token_type`.

Un DTO no debería decidir cómo se guarda un usuario. Solo define la forma del dato que cruza una frontera.

### Entidad (`app/core/entities/user.py`)

Representa al usuario en el dominio. Contiene identidad y reglas de negocio. No sabe que existe una tabla, una sesión o un endpoint.

### Modelo de base de datos (`app/infra/db/models/user.py`)

`DBUser` es la representación SQLModel de la tabla. Usa `UUID`, `name`, `email` y `password_hash` para persistencia. No debe circular por los casos de uso.

La conversión ocurre en el repositorio:

```text
DTO de entrada -> Entidad User -> DBUser -> PostgreSQL
PostgreSQL -> DBUser -> Entidad User -> UserResponse
```

## 4. Cómo se conectan los componentes

### Composición de dependencias

FastAPI construye los objetos desde `app/infra/api/dependencies`:

1. `get_user_repo()` abre una sesión y entrega `UserRepo`.
2. `get_user_uow()` abre una sesión y crea `UserUnitOfWork` con un repositorio.
3. `get_hasher()` entrega el adaptador Passlib.
4. `get_token_provider()` crea `JWTProvider` desde `Settings`.
5. `get_*_usecase()` ensambla el caso de uso con los puertos concretos.

Por ejemplo, crear usuario queda ensamblado así:

```text
FastAPI
  -> get_create_user_usecase
      -> CreateUserUsecase(
           uow=get_user_uow(),
           hasher=get_hasher()
         )
```

El router solo recibe una abstracción ya construida mediante `Depends`.

### Repositorio y Unit of Work

Las operaciones de lectura y eliminación usan directamente `UserRepo` con una sesión abierta por la dependencia. Las operaciones de creación y actualización usan `UserUnitOfWork`:

```text
async with uow:
    operaciones del repositorio

si no hay excepción -> commit
si hay excepción     -> rollback
al salir             -> cerrar sesión
```

`BaseUnitOfWork.__aexit__` implementa commit o rollback y cierra la sesión asíncrona.

## 5. Flujo general de una petición

1. El cliente envía una petición HTTP.
2. Uvicorn entrega la petición a FastAPI.
3. FastAPI encuentra el router por método y ruta.
4. FastAPI valida path, query, JSON o formulario.
5. FastAPI resuelve `Depends`: sesión, repositorio, UoW, hasher, JWT o usuario actual.
6. El router llama a `usecase.execute(...)`.
7. El caso de uso construye value objects y entidades.
8. El caso de uso invoca un puerto.
9. El adaptador de infraestructura ejecuta la operación externa.
10. El resultado vuelve como entidad o dato del dominio.
11. El caso de uso construye un DTO de salida.
12. El router traduce excepciones de dominio a códigos HTTP.
13. FastAPI serializa la respuesta.

## 6. Flujo detallado por endpoint

### 6.1 `POST /api/v1/users`: crear usuario

1. El cliente envía JSON con `name`, `email` y `password`.
2. FastAPI lo convierte en `CreateUserRequest`.
3. Se resuelven `UserUnitOfWork` y `Hasher`.
4. `CreateUserUsecase` crea `Email` y `Password`.
5. Si email o contraseña son inválidos, lanza `InvalidUserError`; el router responde 400.
6. Dentro del UoW, busca el email mediante `user_repo.get_by_email`.
7. Si existe, lanza `UserAlreadyExistsError`; el contexto revierte y el router responde 409.
8. El hasher convierte la contraseña plana en hash.
9. Se crea `User` con `ID.generate()`.
10. `user_repo.save(user)` transforma la entidad en `DBUser` y la añade a la sesión.
11. Al salir correctamente del UoW se ejecuta `commit`.
12. El caso de uso devuelve `UserResponse` sin contraseña.
13. FastAPI responde 201.

### 6.2 `GET /api/v1/users/{user_id}`: consultar usuario

1. FastAPI valida `{user_id}` como `UUID`.
2. Si no es UUID, rechaza la petición con 422 antes de entrar al router.
3. Se crea `GetUserUsecase` con `UserRepo`.
4. El caso de uso convierte el texto en `ID`.
5. El repositorio hace `session.get(DBUser, id)`.
6. Si no existe, el caso de uso lanza `UserNotFoundError` y el router responde 404.
7. Si existe, el repositorio convierte `DBUser` en `User` y el caso de uso en `UserResponse`.
8. FastAPI responde 200.

### 6.3 `PATCH /api/v1/users/{user_id}`: actualizar usuario

1. FastAPI valida UUID y crea `UpdateUser`.
2. `UpdateUser` exige que llegue `name` o `email`.
3. Se crea un `UserUnitOfWork`.
4. El caso de uso convierte el ID y busca la entidad actual.
5. Si no existe, lanza `UserNotFoundError`; el contexto hace rollback y responde 404.
6. Construye una nueva entidad conservando los valores no enviados.
7. `Email` valida el nuevo email, si existe.
8. El repositorio actualiza `DBUser` y devuelve la entidad actualizada.
9. El UoW hace commit.
10. Se devuelve `UserResponse` con 200.

### 6.4 `DELETE /api/v1/users/{user_id}`: eliminar usuario

1. FastAPI valida UUID.
2. Se crea `DeleteUserUsecase` con `UserRepo`.
3. El caso de uso convierte el ID a `ID`.
4. El repositorio busca el registro y, si existe, lo marca para eliminar.
5. La dependencia cierra la sesión; el flujo actual no usa un `UnitOfWork` explícito para este caso.
6. Si devuelve `False`, el router responde 404; si devuelve `True`, responde 204.

### 6.5 `POST /api/v1/auth/token`: autenticación

1. El cliente envía formulario OAuth2 con `username` y `password`. En este proyecto `username` contiene el email.
2. FastAPI crea `OAuth2PasswordRequestForm`.
3. Se resuelven `AuthenticateUserUsecase` y `JWTProvider`.
4. El caso de uso valida el email con `Email`.
5. Consulta `UserRepo.get_by_email`.
6. Passlib verifica la contraseña recibida contra `user.password.value`.
7. Si falla cualquiera de los pasos, se lanza `AuthenticationFailedError` y el router responde 401.
8. Si es correcta, el router pide a `JWTProvider` un token con `sub=user_id:<id>` y expiración.
9. Se devuelve `TokenResponse` con 200.

### 6.6 `GET /api/v1/auth/me`: usuario autenticado

1. El cliente envía `Authorization: Bearer <token>`.
2. `OAuth2PasswordBearer` extrae el token.
3. `JWTProvider.get_sub` decodifica el JWT y extrae el ID desde `sub`.
4. Si el token es inválido, la dependencia responde 401.
5. `get_current_user` usa `GetUserUsecase` para consultar el usuario.
6. Si el usuario no existe, responde 401.
7. Si existe, `CurrentUser` entrega `UserResponse` al router.
8. El router devuelve ese DTO con 200.

## 7. Endpoints y componentes involucrados

| Endpoint | Router | DTO entrada | Caso de uso | Adaptadores | Salida |
|---|---|---|---|---|---|
| `GET /health-check` | `root.py` | ninguno | ninguno | `Settings` | `HealthCheck` |
| `POST /api/v1/users` | `v1/user.py` | `CreateUserRequest` | `CreateUserUsecase` | UoW, repositorio, hasher | `UserResponse` |
| `GET /api/v1/users/{id}` | `v1/user.py` | path UUID | `GetUserUsecase` | repositorio | `UserResponse` |
| `PATCH /api/v1/users/{id}` | `v1/user.py` | `UpdateUser` | `UpdateUserUsecase` | UoW, repositorio | `UserResponse` |
| `DELETE /api/v1/users/{id}` | `v1/user.py` | path UUID | `DeleteUserUsecase` | repositorio | `204` |
| `POST /api/v1/auth/token` | `v1/auth.py` | OAuth2 form | `AuthenticateUserUsecase` | repositorio, hasher, JWT | `TokenResponse` |
| `GET /api/v1/auth/me` | `v1/auth.py` | Bearer token | `GetUserUsecase` | JWT, repositorio | `UserResponse` |

## 8. Evaluación de la arquitectura

| Elemento de Clean Architecture | Presente | Evidencia |
|---|---:|---|
| Entidades de dominio | Sí | `app/core/entities/user.py` |
| Value objects | Sí | `Email`, `Password`, `ID` |
| Casos de uso | Sí | `app/core/usecases/user/*` |
| DTOs | Sí | `app/core/dtos/*` |
| Puertos/interfaces | Sí | `app/core/ports/*` con `Protocol` |
| Adaptadores de persistencia | Sí | repositorio SQLModel y modelo `DBUser` |
| Unit of Work | Sí | protocolos y `BaseUnitOfWork` |
| Adaptador de seguridad | Sí | Passlib detrás de `Hasher` |
| Adaptador de autenticación | Sí | `JWTProvider` |
| Capa HTTP | Sí | FastAPI routers y dependencies |
| Migraciones | Sí | Alembic |
| Pruebas unitarias | Sí | `tests/unit` |
| Pruebas de integración | Sí | `tests/integration` |
| Independencia completa del framework en `core` | Parcial | `core` es mayormente independiente, pero `core/dtos` también funciona como contrato HTTP |

## 9. Entidad Role y relación con User

La entidad `Role` representa un perfil funcional que puede asignarse a un usuario.

### Dominio

- `app/core/entities/role.py`: entidad inmutable con `id`, `name` y `description`.
- `app/core/dtos/role.py`: `CreateRoleRequest`, `UpdateRole` y `RoleResponse`.
- `app/core/ports/role.py`: contratos `RoleRepo` y `RoleUnitOfWork`.
- `app/core/usecases/role/*`: crear, consultar, actualizar y eliminar roles.

`Role` valida que el nombre no sea vacío y utiliza `ID` para identidad, igual que `User`.

### Persistencia

- `app/infra/db/models/role.py`: tabla `roles`, con nombre único.
- `app/infra/db/repositories/role.py`: conversión entre `Role` y `DBRole`.
- `app/infra/db/unit_of_work/role.py`: transacciones de roles.
- `users.role_id`: clave foránea opcional hacia `roles.id`.
- `app/infra/db/migrations/versions/9b3d4f7a1c2e_add_roles_and_user_role.py`: crea la tabla y la relación.

La relación es opcional para conservar usuarios existentes y permitir una migración progresiva. Cuando se envía `role_id` al crear o actualizar un usuario, el caso de uso lo convierte en `ID` y el repositorio lo guarda como UUID.

### API

El router `app/infra/api/routers/v1/role.py` expone:

- `POST /api/v1/roles`: crear un rol.
- `GET /api/v1/roles/{role_id}`: consultar un rol.
- `PATCH /api/v1/roles/{role_id}`: modificar un rol.
- `DELETE /api/v1/roles/{role_id}`: eliminar un rol.

Los endpoints de usuario aceptan `role_id` en `CreateUserRequest` y `UpdateUser`, y `UserResponse` lo devuelve. Por tanto, el flujo queda:

```text
Cliente -> Router de roles -> Caso de uso Role -> RoleRepo -> roles
Cliente -> Router de usuarios -> Caso de uso User -> UserRepo -> users.role_id -> roles.id
```

La autenticación también conserva `role_id` en el `UserResponse`, por lo que `/api/v1/auth/token` y `/api/v1/auth/me` pueden entregar el rol asociado sin exponer la contraseña.

### Orden recomendado de uso

1. Crear un rol con `POST /api/v1/roles`.
2. Tomar el `id` devuelto.
3. Enviar ese UUID como `role_id` al crear o actualizar un usuario.
4. Consultar el usuario o autenticarse para comprobar el `role_id` en la respuesta.

La base actual no valida todavía que el UUID enviado pertenezca a un rol existente antes de guardar el usuario; la FK de PostgreSQL lo garantiza al hacer commit. Puede añadirse una validación de aplicación con un puerto combinado si el caso de uso necesita mensajes de negocio más específicos.

## 10. Observaciones y oportunidades de mejora

1. El puerto `UserRepo` define `save`, mientras el adaptador también tiene `create`. El flujo usado por `CreateUserUsecase` es `save`; conviene eliminar `create` o formalizarlo en el puerto para evitar dos contratos.
2. `DELETE` recibe un repositorio directo y no un UoW explícito. Conviene decidir si el commit debe quedar siempre bajo una abstracción transaccional uniforme.
3. `DBUser` y la entidad `User` tienen nombres iguales en módulos diferentes. Los alias actuales funcionan, pero nombres como `UserModel` y `User` harían más clara la frontera.
4. `UserResponse` vive en `core`, aunque representa también la respuesta HTTP. Si el dominio debe ser completamente independiente del transporte, puede moverse a una capa de aplicación/entrega.
5. El router captura algunas excepciones manualmente. Un handler centralizado para excepciones de dominio reduciría repetición y haría más uniforme el contrato de errores.
6. La creación de usuario valida la longitud del hash al reconstruir `Password` después del hashing. Actualmente el hash bcrypt cumple esa restricción, pero conceptualmente conviene separar `PlainPassword` de `PasswordHash` si el dominio crece.

## 11. Arranque, configuración, persistencia y calidad

### Arranque de la aplicación

El proceso comienza en `app/__main__.py`, que llama a `start_server()` desde `app/__init__.py`. Ese método inicia Uvicorn y carga la aplicación mediante `create_app(Settings)`.

Durante la creación:

1. `get_settings()` lee y valida la configuración con Pydantic Settings.
2. `create_instance()` crea la instancia FastAPI.
3. `register_extensions()` registra el handler global de `RequestValidationError`.
4. `register_routers()` monta `/health-check`, `/api/v1/users` y `/api/v1/auth`.
5. `lifespan()` registra el motor de base de datos en `app.state`.
6. Al apagar la aplicación, el lifespan libera el engine asíncrono.

### Configuración

`app/config.py` centraliza `DB_URL`, claves JWT, algoritmo, expiración, host, puerto, logging y modo de ejecución. Los valores se pueden cargar desde `.env` y `get_settings()` usa `lru_cache`, por lo que la instancia se reutiliza durante el proceso.

### Persistencia y migraciones

La conexión usa `create_async_engine`, `async_sessionmaker` y `AsyncSession`. El repositorio traduce entre la entidad `User` y el modelo SQLModel `DBUser`; la tabla persistida es `users` y el email tiene restricción única.

Alembic mantiene la evolución del esquema en `app/infra/db/migrations`. La configuración de `alembic.ini` apunta a esa carpeta y las revisiones existentes crean la tabla inicial y agregan cambios posteriores. El despliegue debe aplicar `alembic upgrade head` antes de atender tráfico contra una base nueva.

### Estrategia de pruebas y calidad

- `tests/unit/core` prueba entidades, value objects y casos de uso con `MagicMock` y `AsyncMock`, sin depender de PostgreSQL.
- `tests/integration` prueba routers, autenticación, health check y persistencia mediante `AsyncClient`, `ASGITransport` y `LifespanManager`.
- `pytest` ejecuta la suite.
- `ruff check .` comprueba estilo y errores de lint.
- `mypy app tests` comprueba tipos.
- `ruff format` y pre-commit mantienen el formato y validaciones automáticas.

## 12. Cómo leer el diagrama

El archivo `docs/architecture.drawio` puede abrirse directamente en diagrams.net/draw.io mediante **File > Open From > Device**. El archivo original contiene seis páginas. La variante `docs/architecture-role.drawio` contiene esas vistas ampliadas con `Role` y una página adicional dedicada a la relación User-Role:

1. Vista general de las capas.
2. Capas y carpetas concretas del proyecto.
3. Componentes, DTOs, entidad, puertos y adaptadores.
4. Ciclo completo de una petición HTTP.
5. Flujos de creación, autenticación, `/me` y CRUD.
6. Arranque, configuración, persistencia, migraciones y pruebas.

- Las flechas sólidas representan llamadas de ejecución.
- Las flechas discontinuas representan dependencias de contrato o composición.
- Las capas amarilla, azul y verde separan entrada, núcleo y adaptadores.
- Las secuencias inferiores muestran creación de usuario, autenticación y `/me`.
