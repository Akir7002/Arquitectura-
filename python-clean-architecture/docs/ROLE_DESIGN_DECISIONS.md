# Decisiones de diseño: integración de Role

## 1. Qué se quería resolver

El proyecto ya tenía una entidad `User` con flujo completo de creación, consulta, actualización, eliminación y autenticación. La nueva necesidad era agregar una entidad `Role` sin romper esa arquitectura ni convertir el rol en una tabla aislada.

La decisión central fue integrar `Role` como una entidad de dominio relacionada con `User` mediante `role_id`.

```text
User.role_id -> Role.id
users.role_id -> roles.id
```

## 2. Por qué se creó una entidad y no un campo simple

Un rol no es solo un texto como `"admin"`. Tiene identidad, nombre, descripción y reglas futuras. Si se guardara directamente como texto dentro de `User`, aparecerían problemas:

- Nombres duplicados escritos de distintas maneras.
- Imposibilidad de actualizar la descripción de un rol en un solo lugar.
- Falta de integridad referencial.
- Dificultad para agregar permisos después.
- Mezcla entre datos del usuario y catálogo de roles.

Por eso se creó una entidad independiente:

```python
Role(id: ID, name: str, description: str)
```

## 3. Por qué sigue el mismo flujo de User

El proyecto usa una arquitectura repetible:

```text
Entity
    -> DTO
    -> Port
    -> Use case
    -> Repository
    -> Unit of Work
    -> API Router
```

Usar el mismo flujo para `Role` tiene estas ventajas:

- El código es predecible.
- Las dependencias se resuelven igual con FastAPI.
- Las pruebas pueden reutilizar mocks.
- La infraestructura mantiene una sola convención.
- La documentación y los diagramas son consistentes.

Por eso `Role` tiene sus propios DTOs, puertos, casos de uso, repositorio, unidad de trabajo y router.

## 4. Decisión sobre la identidad

Se reutilizó el value object `ID` en lugar de usar UUID directamente en el dominio.

Razones:

1. `User` ya utiliza `ID`.
2. La validación de UUID queda centralizada.
3. Las entidades comparten la misma forma de identificarse.
4. La conversión a UUID de PostgreSQL se realiza en el adaptador.

El dominio trabaja con `ID`; el modelo SQL trabaja con `UUID`.

```text
texto HTTP -> ID -> UUID SQLModel -> PostgreSQL
```

## 5. Decisión sobre la validación del nombre

`Role` rechaza nombres vacíos o compuestos por espacios.

Se colocó esta regla en la entidad porque es una regla propia del dominio, no de HTTP ni de PostgreSQL. De esta forma, cualquier entrada que cree un `Role` queda protegida, incluso si mañana llega desde un script, un mensaje o una tarea interna.

La excepción usada es `InvalidRoleError`, siguiendo el patrón de `InvalidUserError`.

## 6. Decisión sobre los DTOs

Se crearon tres DTOs:

- `CreateRoleRequest`: datos necesarios para crear.
- `UpdateRole`: campos modificables.
- `RoleResponse`: representación pública.

No se expone directamente `DBRole` porque ese objeto pertenece a la persistencia. Tampoco se devuelve la sesión ni el repositorio.

La separación evita que un cambio en SQLModel cambie automáticamente el contrato HTTP.

## 7. Decisión sobre los casos de uso

Se crearon cuatro casos de uso:

- `CreateRoleUsecase`.
- `GetRoleUsecase`.
- `UpdateRoleUsecase`.
- `DeleteRoleUsecase`.

Se eligió CRUD completo porque un rol necesita ser administrable, no solo creado durante una migración.

### Crear

Comprueba duplicados por nombre antes de guardar.

### Consultar

Permite recuperar el rol por UUID y devuelve un DTO.

### Actualizar

Construye una nueva entidad y conserva los campos que no llegaron en el PATCH.

### Eliminar

Devuelve un booleano para que el router pueda decidir entre `204` y `404`.

## 8. Decisión sobre el repositorio

El puerto `RoleRepo` está en `app/core/ports`, mientras que `RoleRepo` concreto está en `app/infra/db/repositories`.

Esto aplica inversión de dependencias:

```text
Caso de uso -> RoleRepo Protocol <- RoleRepo SQLModel
```

El caso de uso sabe qué operación necesita, pero no cómo se ejecuta en PostgreSQL.

## 9. Decisión sobre Unit of Work

Crear y actualizar roles usan `RoleUnitOfWork` porque modifican datos y necesitan una transacción.

El flujo es:

```python
async with self.uow:
    comprobar
    guardar o actualizar

sin excepción -> commit
con excepción -> rollback
```

Esto es importante para el caso duplicado: si el nombre ya existe, no se guarda una segunda entidad y la transacción termina en rollback.

## 10. Decisión sobre la relación con User

Se agregó `role_id` a `User`, no un objeto `Role` completo dentro de la entidad.

### Motivos

- Evita cargar siempre el rol completo.
- Mantiene la entidad User sencilla.
- Sigue el estilo actual de persistencia.
- Permite que el repositorio controle la conversión.
- Deja abierta una futura carga de permisos o detalles del rol.

La relación es opcional:

```python
role_id: ID | None = None
```

Esto fue deliberado para no invalidar usuarios existentes ni obligar a todos los clientes actuales a enviar un nuevo campo.

## 11. Por qué `role_id` también está en los DTOs de User

Si solo se agregara la tabla `roles`, no existiría una forma de asignar un rol mediante la API.

Por eso se integró en:

- `CreateUserRequest`.
- `UpdateUser`.
- `UserResponse`.
- `CreateUserUsecase`.
- `UpdateUserUsecase`.
- `GetUserUsecase`.
- `AuthenticateUserUsecase`.
- `UserRepo`.
- Modelo `DBUser`.

Así, el dato recorre todo el sistema de forma consistente.

## 12. Por qué el JWT no cambió todavía

El JWT actual identifica al usuario mediante:

```text
sub=user_id:<id>
```

No se agregó el rol como claim todavía porque la primera integración solo necesitaba relacionar las entidades y devolver el rol. Agregar claims implicaría decidir:

- Qué roles son confiables dentro del token.
- Cuándo expira o se revoca un cambio de rol.
- Si los permisos se consultan desde el token o desde la base.
- Cómo invalidar tokens después de modificar un rol.

Por ahora, `/auth/me` devuelve `role_id` y deja preparado el camino para autorización futura sin introducir una política incompleta.

## 13. Decisión sobre la migración

La migración crea:

1. `roles`.
2. Índice y restricción única para `roles.name`.
3. `users.role_id` nullable.
4. Foreign key `users.role_id -> roles.id`.

La columna nullable es necesaria porque ya pueden existir usuarios sin rol. Hacerla obligatoria habría obligado a crear un rol por defecto y actualizar todos los registros históricos durante la migración.

## 14. Consideración sobre eliminar roles

La relación introduce una decisión importante: qué ocurre cuando se elimina un rol usado por usuarios.

La implementación actual deja la FK como protección de PostgreSQL. Antes de usar eliminación de roles en producción hay tres opciones:

1. Impedir la eliminación si hay usuarios asignados.
2. Reasignar usuarios a un rol por defecto.
3. Usar borrado lógico con `active` o `deleted_at`.

Se dejó esta política abierta porque no estaba definida en los requisitos originales.

## 15. Decisión sobre el router

Se agregó:

```text
/api/v1/roles
```

El router es responsable de:

- Recibir DTOs.
- Recibir casos de uso mediante `Depends`.
- Convertir excepciones a códigos HTTP.
- Devolver DTOs.

No crea sesiones ni accede directamente a SQLModel.

## 16. Prueba realizada

### Limitación del entorno

No se pudo ejecutar una petición HTTP real porque la terminal no tenía instalados:

- Uvicorn.
- FastAPI.
- SQLModel.
- HTTPX.
- pytest.
- Poetry.

Por eso no se simuló falsamente una respuesta HTTP completa. Se probó el caso de uso real, que es la parte donde se toman las decisiones de negocio.

### Prueba exitosa

Se ejecutó:

```python
CreateRoleRequest(
    name="admin",
    description="Acceso administrativo",
)
```

Se usaron un `RoleRepo` y un `RoleUnitOfWork` controlados para imprimir cada paso.

Resultado:

```text
[1] Cliente prepara POST /api/v1/roles
[2] DTO recibido
[3] FastAPI validaria el body y resolveria Depends
[4] get_create_role_usecase recibe RoleUnitOfWork
[5] Router llama CreateRoleUsecase.execute
[6] RoleUnitOfWork abre transaccion
[7] RoleRepo.get_by_name consulta duplicado
[10] RoleRepo.save guarda Role con UUID
[11] RoleUnitOfWork hace commit
[12] Se produce RoleResponse
[13] El router responderia HTTP 201
```

La prueba confirmó que el caso de uso crea el rol, pasa por el puerto del repositorio y finaliza con commit.

### Prueba de duplicado

Se ejecutó dos veces el mismo nombre: `admin`.

Resultado:

```text
UoW enter -> abre transaccion
RoleRepo.get_by_name -> consulta duplicado
RoleRepo.save -> guarda entidad
UoW exit -> commit
UoW enter -> abre transaccion
RoleRepo.get_by_name -> consulta duplicado
UoW exit -> rollback
Resultado esperado -> RoleAlreadyExistsError
Entidades guardadas -> 1
```

Esto confirma:

- El primer rol se guarda.
- El segundo se detecta como duplicado.
- No se ejecuta un segundo guardado válido.
- Se lanza `RoleAlreadyExistsError`.
- Se hace rollback.
- El repositorio termina con una sola entidad.

## 17. Qué falta para una prueba HTTP completa

La prueba completa debe ejecutarse con el entorno de desarrollo o Docker:

```sh
docker compose up tests
```

Debe verificar como mínimo:

1. Crear un rol.
2. Repetir el nombre y esperar `409`.
3. Consultar el rol.
4. Actualizarlo.
5. Crear un usuario con `role_id`.
6. Consultar el usuario y confirmar `role_id`.
7. Obtener un token.
8. Consultar `/api/v1/auth/me`.
9. Confirmar que el usuario autenticado conserva `role_id`.
10. Intentar eliminar un rol asignado y validar la política elegida.

## 18. Resumen de la decisión

`Role` se agregó como entidad completa porque representa un concepto del dominio y debe crecer hacia permisos y autorización. Se relacionó con `User` mediante `role_id` para mantener el modelo simple, compatible y preparado para futuras reglas. Se reutilizaron los mismos patrones del proyecto para evitar una segunda arquitectura dentro de la aplicación.
