# Arquitectura de Role

## 1. Objetivo

La entidad `Role` representa un perfil funcional que puede asociarse a un usuario. La implementación sigue la misma arquitectura que ya utiliza `User`: dominio independiente, casos de uso, puertos, adaptadores de infraestructura, API FastAPI, persistencia SQLModel/PostgreSQL y pruebas.

La relación principal es:

```text
User.role_id -> Role.id
users.role_id -> roles.id
```

El rol es opcional para conservar compatibilidad con usuarios creados antes de introducir esta funcionalidad.

## 2. Vista general del flujo

```text
Cliente HTTP
    |
    v
FastAPI Router
    |
    v
DTO CreateRoleRequest / UpdateRole
    |
    v
Dependency Injection
    |
    v
RoleUsecase
    |
    v
RoleRepo / RoleUnitOfWork
    |
    v
DBRole <-> PostgreSQL roles
```

Para un usuario asociado a un rol:

```text
CreateUserRequest.role_id
    -> CreateUserUsecase
    -> User.role_id: ID
    -> UserRepo
    -> DBUser.role_id
    -> users.role_id FK roles.id
```

## 3. Capas involucradas

### 3.1 Entrada y entrega

Ubicación: `app/infra/api`.

La API recibe peticiones HTTP, valida sus datos y convierte errores de dominio en respuestas HTTP.

Archivos principales:

- `app/infra/api/routers/v1/role.py`: endpoints CRUD de roles.
- `app/infra/api/routers/v1/user.py`: acepta y devuelve `role_id` durante operaciones de usuario.
- `app/infra/api/dependencies/role.py`: crea repositorios y unidades de trabajo de roles.
- `app/infra/api/dependencies/usecases/role.py`: construye los casos de uso con `Depends`.
- `app/infra/api/routers/v1/__init__.py`: registra `/roles` junto a `/users` y `/auth`.

### 3.2 Dominio

Ubicación: `app/core`.

El dominio no conoce FastAPI, SQLModel ni PostgreSQL.

Archivos principales:

- `app/core/entities/role.py`: entidad `Role`.
- `app/core/entities/user.py`: entidad `User` con `role_id` opcional.
- `app/core/dtos/role.py`: contratos de entrada y salida para roles.
- `app/core/dtos/user.py`: DTOs de usuario con `role_id` opcional.
- `app/core/ports/role.py`: contratos `RoleRepo` y `RoleUnitOfWork`.
- `app/core/exceptions.py`: errores de rol.
- `app/core/usecases/role/*`: operaciones de aplicación para roles.

### 3.3 Persistencia

Ubicación: `app/infra/db`.

- `app/infra/db/models/role.py`: modelo SQLModel de `roles`.
- `app/infra/db/models/user.py`: columna `role_id` con clave foránea.
- `app/infra/db/repositories/role.py`: implementación concreta de `RoleRepo`.
- `app/infra/db/repositories/user.py`: persiste y recupera `role_id`.
- `app/infra/db/unit_of_work/role.py`: transacciones de roles.
- `app/infra/db/migrations/versions/9b3d4f7a1c2e_add_roles_and_user_role.py`: evolución del esquema.

## 4. Entidad Role

La entidad se define conceptualmente así:

```python
@dataclass(frozen=True, kw_only=True)
class Role:
    id: ID
    name: str
    description: str = ""
```

### Identidad

`id` utiliza el value object `ID`, igual que `User`. Esto evita manejar UUIDs arbitrarios dentro del dominio y centraliza la conversión y validación.

### Nombre

`name` es obligatorio. La entidad rechaza nombres vacíos o compuestos únicamente por espacios mediante `InvalidRoleError`.

### Descripción

`description` es opcional y sirve para explicar el propósito del rol sin introducir reglas innecesarias en esta primera versión.

### Inmutabilidad

La entidad usa `dataclass(frozen=True)`. Para actualizarla se crea una nueva instancia y el repositorio reemplaza los valores persistidos. Esto mantiene el mismo estilo de `User`.

## 5. DTOs de Role

### `CreateRoleRequest`

Entrada de `POST /api/v1/roles`:

```json
{
  "name": "admin",
  "description": "Acceso administrativo"
}
```

### `UpdateRole`

Entrada de `PATCH /api/v1/roles/{role_id}`. Permite actualizar `name`, `description` o ambos. Exige que llegue al menos un campo.

### `RoleResponse`

Salida pública del sistema:

```json
{
  "id": "uuid",
  "name": "admin",
  "description": "Acceso administrativo"
}
```

Los DTOs evitan exponer directamente modelos SQLModel o sesiones de base de datos.

## 6. Puertos

`RoleRepo` define lo que los casos de uso necesitan:

- `save(role)`: guardar un rol.
- `get_by_id(id)`: buscar por identidad.
- `get_by_name(name)`: comprobar duplicados.
- `update(role)`: modificar un rol existente.
- `delete(id)`: eliminar un rol.

`RoleUnitOfWork` expone `role_repo` y controla commit, rollback y cierre de sesión.

El caso de uso depende del puerto, no de `RoleRepo` SQLModel. Esto permite usar mocks en pruebas y cambiar PostgreSQL por otra implementación sin modificar el dominio.

## 7. Casos de uso

### 7.1 Crear Role

Archivo: `app/core/usecases/role/create_role.py`.

Flujo:

1. Recibe `CreateRoleRequest`.
2. Abre `RoleUnitOfWork`.
3. Consulta `role_repo.get_by_name()`.
4. Si ya existe, lanza `RoleAlreadyExistsError`.
5. Genera `ID.generate()`.
6. Construye la entidad `Role`.
7. Ejecuta `role_repo.save(role)`.
8. Si no hay excepción, el UoW hace commit.
9. Devuelve `RoleResponse`.

### 7.2 Consultar Role

Archivo: `app/core/usecases/role/get_role.py`.

1. Recibe el UUID como texto.
2. Lo convierte a `ID`.
3. Llama a `RoleRepo.get_by_id()`.
4. Si no existe, lanza `RoleNotFoundError`.
5. Convierte la entidad a `RoleResponse`.

### 7.3 Actualizar Role

Archivo: `app/core/usecases/role/update_role.py`.

1. Convierte el UUID a `ID`.
2. Abre la unidad de trabajo.
3. Busca el rol actual.
4. Conserva los campos no enviados.
5. Construye una nueva entidad `Role`.
6. Ejecuta `RoleRepo.update()`.
7. Hace commit.
8. Devuelve el rol actualizado.

### 7.4 Eliminar Role

Archivo: `app/core/usecases/role/delete_role.py`.

1. Convierte el UUID recibido.
2. Llama a `RoleRepo.delete()`.
3. Devuelve `True` o `False`.
4. El router convierte el resultado en `204` o `404`.

Si existen usuarios asociados, la clave foránea debe considerarse antes de eliminar el rol. La política de borrado puede evolucionar a impedir la eliminación, reasignar usuarios o usar borrado lógico.

## 8. Endpoints

### Crear

```http
POST /api/v1/roles
```

Éxito: `201 Created`.

Errores:

- `400`: nombre inválido.
- `409`: nombre duplicado.

### Consultar

```http
GET /api/v1/roles/{role_id}
```

Éxito: `200 OK`.

Errores:

- `404`: rol inexistente o UUID inválido según la validación aplicada.

### Actualizar

```http
PATCH /api/v1/roles/{role_id}
```

Éxito: `200 OK`.

Errores:

- `400`: datos o UUID inválidos.
- `404`: rol inexistente.

### Eliminar

```http
DELETE /api/v1/roles/{role_id}
```

Éxito: `204 No Content`.

Error:

- `404`: rol inexistente.

## 9. Relación con User

`User` ahora puede contener:

```python
role_id: ID | None = None
```

La relación se propaga por todo el flujo.

### Creación de usuario con rol

```http
POST /api/v1/users
Content-Type: application/json

{
  "name": "Maria",
  "email": "maria@example.com",
  "password": "password",
  "role_id": "uuid-del-rol"
}
```

Recorrido:

1. FastAPI crea `CreateUserRequest`.
2. `CreateUserUsecase` convierte el `role_id` en `ID`.
3. Se construye `User` con `role_id`.
4. `UserRepo.save()` copia el valor a `DBUser.role_id`.
5. PostgreSQL valida la FK contra `roles.id`.
6. `UserResponse` devuelve el `role_id`.

### Actualización de usuario

`PATCH /api/v1/users/{user_id}` también acepta `role_id`. El caso de uso conserva el rol actual si no se envía uno nuevo.

### Autenticación

`AuthenticateUserUsecase` y `GetUserUsecase` incluyen `role_id` en `UserResponse`. Por eso el dato está disponible en:

- La respuesta de autenticación lógica.
- `GET /api/v1/auth/me`.
- El contenido que puede utilizar una autorización futura.

El JWT actual continúa identificando al usuario con `sub=user_id:<id>`. El rol se entrega en la respuesta del usuario, pero todavía no se agrega como claim ni se usa para bloquear endpoints.

## 10. Persistencia y migración

La migración `9b3d4f7a1c2e_add_roles_and_user_role.py` realiza estas operaciones:

1. Crea la tabla `roles`.
2. Crea `roles.id` como clave primaria.
3. Crea `roles.name` como único.
4. Crea el índice de búsqueda por nombre.
5. Crea `roles.description`.
6. Agrega `users.role_id` como columna nullable.
7. Crea la FK `users.role_id -> roles.id`.

Comando recomendado:

```sh
alembic upgrade head
```

La columna nullable permite que registros de usuarios anteriores sigan siendo válidos.

## 11. Prueba trazable ejecutada

El entorno local no tenía instalados Uvicorn, FastAPI, SQLModel, HTTPX, pytest ni Poetry. Por eso no se pudo levantar una petición HTTP real ni ejecutar PostgreSQL desde esta terminal.

Se ejecutó el caso de uso real de creación de roles con un `RoleRepo` y un `RoleUnitOfWork` controlados. Se aisló el paquete `app` para no arrancar la capa web y poder verificar el núcleo.

Entrada usada:

```python
CreateRoleRequest(
    name="admin",
    description="Acceso administrativo",
)
```

Salida observada:

```text
[1] Cliente prepara POST /api/v1/roles
[2] DTO recibido: CreateRoleRequest(name='admin', description='Acceso administrativo')
[3] FastAPI validaria el body y resolveria Depends(get_create_role_usecase)
[4] get_create_role_usecase() recibe RoleUnitOfWork
[5] Router llama CreateRoleUsecase.execute(dto)
[6] RoleUnitOfWork.__aenter__() -> transaccion iniciada
[7] RoleRepo.get_by_name(name)
[10] RoleRepo.save(Role id=<UUID>, name='admin')
[11] RoleUnitOfWork.__aexit__() -> commit
[12] RoleResponse producido
[13] Router responderia HTTP 201 con JSON del rol
```

También se repitió la operación con el mismo nombre:

```text
UoW enter -> abre transaccion
RoleRepo.get_by_name -> consulta duplicado
UoW exit -> rollback
Resultado esperado -> RoleAlreadyExistsError
Entidades guardadas -> 1 (esperado: 1)
```

Esto verifica el camino exitoso y el camino de error de negocio.

## 12. Prueba HTTP completa recomendada

Con dependencias instaladas y PostgreSQL disponible:

```sh
docker compose up tests
```

El flujo HTTP completo esperado sería:

```text
HTTP POST /api/v1/roles
    -> FastAPI
    -> router role.create
    -> Depends(get_create_role_usecase)
    -> CreateRoleUsecase.execute
    -> RoleUnitOfWork
    -> RoleRepo
    -> SQLModel AsyncSession
    -> PostgreSQL roles
    -> commit
    -> RoleResponse
    -> HTTP 201
```
