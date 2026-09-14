# Análisis — Repositorio `python-clean-architecture` (FastAPI + Clean Architecture)
# MARIA FERNANDA PATIÑO CARRANZA - ARQUITECTURA DE SOFTWARE

## 1. Flujo de una petición en Clean Architecture

Clean Architecture (Uncle Bob) organiza el software en **capas concéntricas** donde la **Regla de Dependencia** establece que todas las dependencias del código fuente apuntan **hacia adentro** (hacia el dominio). El flujo de una petición es exactamente el inverso: **entra desde afuera y viaja hacia adentro**.

```
   ENTRADA HTTP                                       SALIDA HTTP
        │                                                  ▲
        ▼                                                  │
┌─────────────────────┐   ┌───────────────────── ┐   ┌──────┴──────────────┐
│ Frameworks &        │   │ Interface Adapters   │   │ Interface Adapters  │
│ Drivers (HTTP)      │──▶│ (Routers, DTOs,     │──▶│ (DTO de respuesta)  │──▶ Cliente
│ FastAPI/UVicorn     │   │  Inyección deps)     │   │                     │
└─────────────────────┘   └──────────┬──────────┘   └─────────────────────┘
                                     ▼                          ▲
                          ┌─────────────────────┐               │
                          │ Use Cases           │───────────────┘
                          │ (Reglas de aplic.)  │
                          └──────────┬──────────┘
                                     ▼
                          ┌─────────────────────────┐
                          │ Domain (Entidades,      │
                          │ Value Objects, Puertos) │
                          └─────────────────────────┘
                                     ▲
                                     │ Implementaciones concretas
                                     │ (Repositories, UoW, Crypto) ──▶ DB/FW
```

**Flujo genérico:**

1. **Frameworks & Drivers**: el servidor HTTP (Uvicorn/FastAPI) recibe la petición y la enruta.
2. **Interface Adapters**: el *router* (controlador) valida/parsea el cuerpo en un DTO, obtiene los componentes (usecase, repositorio, hasher) mediante **inyección de dependencias** y traduce datos externos a formatos del dominio.
3. **Use Cases**: el caso de uso orquesta la regla de negocio: valida value objects, consulta/usa puertos (interfaces), coordina la transacción (Unit of Work) y devuelve un DTO de salida.
4. **Domain**: entidades y value objects encapsulan las reglas de negocio puras, sin dependencia de nada externo.
5. **Retorno**: el caso de uso devuelve un DTO → el router lo serializa como respuesta HTTP, mapeando excepciones de dominio a códigos HTTP (400, 404, 409, 401, 422).

**Clave**: el dominio **no conoce** a FastAPI ni a la base de datos. La dependencia se invierte mediante **puertos** (`Protocol` en Python): el dominio define la interfaz, la infraestructura la implementa.

---

## 2. Capas presentes en el proyecto

| Capa (Clean Architecture) | ¿Presente? | Ubicación en el proyecto |
|---|---|---|
| **Entities / Domain** | ✅ Sí | `app/core/entities/user.py` (entidad `User`), `app/core/value_objects/` (`Email`, `Password`, `ID`), `app/core/exceptions.py` (excepciones de dominio) |
| **Use Cases / Application** | ✅ Sí | `app/core/usecases/user/` (`create_user`, `get_user`, `update_user`, `delete_user`, `authenticate_user`) |
| **Ports (interfaces, inversión de dependencias)** | ✅ Sí | `app/core/ports/` (`user.py`: `UserRepo`, `UserUnitOfWork`; `unit_of_work.py`: `UnitOfWork`; `crypto.py`: `Hasher`) |
| **Interface Adapters (controladores, presentadores)** | ✅ Sí | `app/infra/api/routers/v1/` (routers), `app/infra/api/dependencies/` (composición DI), `app/core/dtos/` (DTOs de entrada/salida), `app/infra/db/repositories/` (adaptadores de persistencia), `app/infra/db/unit_of_work/` (transacciones) |
| **Frameworks & Drivers** | ✅ Sí | FastAPI (HTTP), SQLModel/SQLAlchemy + Alembic (BD y migraciones), passlib/bcrypt (hashing), PyJWT (`app/infra/auth/jwt.py`), Docker |

### Estructura del código

```
app/
├── core/                        ← DOMINIO + APLICACIÓN (capas internas)
│   ├── entities/                 ← Entidades de negocio (User)
│   ├── value_objects/            ← Email, Password, ID (invariantes autovalidadas)
│   ├── exceptions.py             ← Excepciones del dominio
│   ├── ports/                    ← Interfaces (Protocol) que el dominio define
│   │   ├── user.py              ← UserRepo, UserUnitOfWork
│   │   ├── unit_of_work.py      ← UnitOfWork (commit/rollback)
│   │   └── crypto.py            ← Hasher (hash/verify)
│   ├── usecases/user/            ← Casos de uso (lógica de aplicación)
│   └── dtos/                     ← DTOs de entrada/salida de casos de uso
├── infra/                        ← INFRAESTRUCTURA (capas externas)
│   ├── api/                      ← Interface adapters HTTP
│   │   ├── app.py               ← Factory de la app FastAPI
│   │   ├── routers/v1/          ← Controladores (user, auth)
│   │   ├── dependencies/        ← Inyección de dependencias (composición)
│   │   └── extensions.py, lifespan.py
│   ├── db/                       ← Persistencia
│   │   ├── models/user.py       ← Modelo SQLModel (tabla BD)
│   │   ├── repositories/user.py ← Implementación de UserRepo
│   │   ├── unit_of_work/        ← Implementación del UnitOfWork
│   │   └── migrations/           ← Alembic
│   ├── security/crypto.py        ← Implementación de Hasher (bcrypt)
│   └── auth/jwt.py               ← Proveedor JWT
└── config.py, logger.py          ← Configuración transversal
```

### Verificación de la Regla de Dependencia

- `app/core` **no importa nada de `app/infra`** ni de FastAPI/SQLModel → ✅ dependencias apuntan hacia adentro.
- El dominio define **puertos** con `typing.Protocol` y la infraestructura los implementa: `app/infra/db/repositories/user.py` implementa el puerto `UserRepo`, `app/infra/db/unit_of_work/base.py` implementa el puerto `UnitOfWork`, `app/infra/security/crypto.py` implementa el puerto `Hasher` → ✅ **inversión de dependencias (DIP)**.
- Los casos de uso solo dependen de abstracciones y de entidades del dominio → ✅ testeables sin infraestructura (los tests unitarios en `tests/unit/core/` lo confirman).
- Única dependencia "hacia afuera" tolerada: los DTOs viven en `core/dtos`, pero son objetos planos sin dependencias de framework → aceptable como contrato de entrada/salida de los use cases.

**Conclusión: el proyecto sí implementa las capas de Clean Architecture** (Entities, Use Cases, Interface Adapters, Frameworks & Drivers), con puertos/adaptadores y DI como mecanismo de inversión de dependencias.

---

## 3. Flujo de una petición concreta: `POST /api/v1/users` (crear usuario)

### Cadena de componentes involucrados

```
Cliente HTTP
  └─▶ Uvicorn/FastAPI (app/infra/api/app.py: create_app, register_routers)
        └─▶ Router (app/infra/api/routers/v1/user.py:29 → create())
              ├─ DTO entrada: CreateUserRequest (app/core/dtos/user.py)
              ├─ DI: CreateUserUsecase (app/infra/api/dependencies/usecases/user.py:16)
              │     ├─ UnitOfWork (dependencies/user.py:16 → user_uow_factory)
              │     │     └─ UserRepo (app/infra/db/repositories/user.py)
              │     └─ Hasher (dependencies/crypto.py:9 → app/infra/security/crypto.py)
              └─▶ UseCase (app/core/usecases/user/create_user.py:21 → execute())
                    ├─ Value Objects: Email, Password (validación de invariantes)
                    ├─ Puerto: UserUnitOfWork (app/core/ports/user.py:65)
                    │     ├─ user_repo.get_by_email(email)  ← ¿existe?
                    │     ├─ hasher.hash(password)          ← puerto Hasher
                    │     └─ user_repo.save(User)           ← persistencia
                    ├─ Entidad: User (app/core/entities/user.py)
                    └─ DTO salida: UserResponse (app/core/dtos/user.py)
                          └─▶ HTTP 201 {id, name, email}
```

### Paso a paso

| # | Etapa | Archivo / método | Responsabilidad |
|---|---|---|---|
| 1 | **Arranque** | `app/infra/api/app.py:31` `create_app()` | Crea la app FastAPI, registra routers (`/api/v1`) y el handler de excepciones de validación |
| 2 | **Recepción** | `app/infra/api/routers/v1/user.py:29` `create()` | FastAPI recibe `POST /api/v1/users`, parsea el JSON al DTO `CreateUserRequest` |
| 3 | **Inyección de dependencias** | `dependencies/usecases/user.py:16` `get_create_user_usecase(uow, hasher)` | Compone el caso de uso: abre una sesión async de BD, construye `UserUnitOfWork` (con su `UserRepo`) y el `Hasher` (bcrypt). El router **no conoce** implementaciones concretas |
| 4 | **Ejecución del caso de uso** | `usecases/user/create_user.py:21` `execute()` | Orquesta la creación; el router solo llama `await usecase.execute(dto)` |
| 5 | **Validación de dominio (VO)** | `value_objects/email.py`, `password.py` | `Email` y `Password` se autovalidan; si fallan → `InvalidUserError` (→ HTTP 400) |
| 6 | **Transacción** | `ports/unit_of_work.py:11` `async with self.uow:` | Abre la transacción; `__aexit__` hace **commit** si todo salió bien o **rollback** si hubo excepción (`infra/db/unit_of_work/base.py`) |
| 7 | **Regla de negocio** | `create_user.py:41` `uow.user_repo.get_by_email(email)` | Consulta por el puerto `UserRepo`; si ya existe → `UserAlreadyExistsError` (→ HTTP 409) |
| 8 | **Encriptación** | `ports/crypto.py` → `infra/security/crypto.py:12` | El use case llama `hasher.hash()` por el **puerto**; la implementación real (bcrypt) vive en infra |
| 9 | **Creación de entidad** | `entities/user.py:10` `User(...)` | Se construye la entidad con `ID.generate()`, VO validados y password hasheado |
| 10 | **Persistencia** | `infra/db/repositories/user.py:48` `save()` | El adaptador traduce la entidad al modelo SQLModel `DBUser` y lo agrega a la sesión |
| 11 | **Commit** | `infra/db/unit_of_work/base.py:13` | Al salir del `async with` sin errores → `session.commit()` + `session.close()` |
| 12 | **Respuesta** | `create_user.py:54` → `routers/v1/user.py:29` | El use case devuelve `UserResponse`; el router lo serializa a JSON con **201 Created**. Excepciones de dominio se mapean a HTTP (400/409) |

### Flujo de error (ejemplo)

```
Email inválido ("no-email") en el body
  └─▶ Email(...) lanza InvalidEmailError        (value_objects/email.py:18)
        └─▶ UseCase la convierte en InvalidUserError (create_user.py:38)
              └─▶ Router la captura             (routers/v1/user.py:32)
                    └─▶ HTTP 400 {"detail": "Invalid email address no-email"}
```

---

## 4. Otros flujos del proyecto (resumen)

- **`GET /api/v1/users/{id}`**: router → `GetUserUsecase` (inyectado solo con `Repo`) → `ID.from_string()` valida el UUID → `repo.get_by_id()` → `UserResponse` o `UserNotFoundError` (HTTP 404).
- **`POST /api/v1/auth/token`** (login): router recibe `OAuth2PasswordRequestForm` → `AuthenticateUserUsecase(repo, hasher)` → valida `Email` → busca usuario por email → `hasher.verify(password, hash)` (puerto) → si falla `AuthenticationFailedError` (HTTP 401) → el router usa `JWTProvider` para emitir el token.
- **`GET /api/v1/auth/me`** (protegida): dependencia `CurrentUser` (`dependencies/auth.py:33`) → valida el JWT → `GetUserUsecase.execute(sub)` → devuelve el usuario autenticado. Ejemplo de cómo la seguridad también entra por la capa de adaptadores.

---

## 5. Conclusión

1. **El flujo de petición respeta Clean Architecture**: HTTP → Router (adapter) → DI → Use Case → Domain/Ports → adapters de infraestructura (repo, UoW, crypto) → respuesta DTO → HTTP.
2. **Todas las capas están presentes**: Domain (entities, value objects, exceptions), Application (use cases), Ports (inversión de dependencias), Interface Adapters (routers, DTOs, repositorios, UoW) y Frameworks & Drivers (FastAPI, SQLModel, Alembic, bcrypt, JWT, Docker).
3. **La Regla de Dependencia se cumple**: `core` no importa nada de `infra`; los casos de uso solo conocen puertos (`Protocol`), lo que permite probarlos de forma unitaria sin BD ni framework, como demuestran los tests en `tests/unit/core/`.

---

## 6. Diagrama para draw.io (código listo para pegar)

El siguiente XML genera un diagrama con **dos paneles**:
1. **Capas de Clean Architecture presentes** en el proyecto (Frameworks & Drivers, Interface Adapters, Use Cases, Domain) con sus componentes reales.
2. **Flujo de la petición `POST /api/v1/users`** (crear usuario) recorriendo los componentes concretos del repositorio.

```xml
<mxfile host="app.diagrams.net" agent="5.0" version="24.7.5" type="device">
  <diagram id="cleanarch-flujo" name="Clean Architecture - Flujo de peticion">
    <mxGraphModel dx="1400" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1400" pageHeight="1000" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />

        <!-- ================= PANEL 1: CAPAS ================= -->
        <mxCell id="t1" value="1. Capas de Clean Architecture presentes en el proyecto" style="text;html=1;align=left;verticalAlign=middle;fontSize=14;fontStyle=1;strokeColor=none;fillColor=none;" vertex="1" parent="1">
          <mxGeometry x="40" y="45" width="560" height="30" as="geometry" />
        </mxCell>

        <mxCell id="leg1" value="Frameworks &amp; Drivers" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;fontSize=10;" vertex="1" parent="1">
          <mxGeometry x="40" y="120" width="120" height="26" as="geometry" />
        </mxCell>
        <mxCell id="leg2" value="Interface Adapters" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;fontSize=10;" vertex="1" parent="1">
          <mxGeometry x="40" y="152" width="120" height="26" as="geometry" />
        </mxCell>
        <mxCell id="leg3" value="Use Cases / Aplicacion" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=10;" vertex="1" parent="1">
          <mxGeometry x="40" y="184" width="120" height="26" as="geometry" />
        </mxCell>
        <mxCell id="leg4" value="Dominio / Entidades" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=10;" vertex="1" parent="1">
          <mxGeometry x="40" y="216" width="120" height="26" as="geometry" />
        </mxCell>

        <mxCell id="b1" value="&#10003; PRESENTE — FRAMEWORKS &amp; DRIVERS&lt;br&gt;&lt;font style=&quot;font-size:10px&quot;&gt;Uvicorn + FastAPI (app/infra/api/app.py) &#183; SQLModel / SQLAlchemy + Alembic &#183; bcrypt &#183; PyJWT &#183; Docker&lt;/font&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;fontSize=12;align=center;verticalAlign=middle;spacing=6;" vertex="1" parent="1">
          <mxGeometry x="220" y="120" width="380" height="90" as="geometry" />
        </mxCell>
        <mxCell id="b2" value="&#10003; PRESENTE — INTERFACE ADAPTERS&lt;br&gt;&lt;font style=&quot;font-size:10px&quot;&gt;Routers (api/routers/v1) &#183; DTOs (core/dtos) &#183; Inyeccion de dependencias (api/dependencies) &#183; Repositorios (db/repositories) &#183; Unit of Work (db/unit_of_work)&lt;/font&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;fontSize=12;align=center;verticalAlign=middle;spacing=6;" vertex="1" parent="1">
          <mxGeometry x="220" y="225" width="380" height="90" as="geometry" />
        </mxCell>
        <mxCell id="b3" value="&#10003; PRESENTE — USE CASES / APLICACION&lt;br&gt;&lt;font style=&quot;font-size:10px&quot;&gt;app/core/usecases/user: create_user &#183; get_user &#183; update_user &#183; delete_user &#183; authenticate_user&lt;/font&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=12;align=center;verticalAlign=middle;spacing=6;" vertex="1" parent="1">
          <mxGeometry x="220" y="330" width="380" height="80" as="geometry" />
        </mxCell>
        <mxCell id="b4" value="&#10003; PRESENTE — DOMINIO / ENTIDADES&lt;br&gt;&lt;font style=&quot;font-size:10px&quot;&gt;app/core: entities (User) &#183; value_objects (Email, Password, ID) &#183; exceptions &#183; ports (Protocol)&lt;/font&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=12;align=center;verticalAlign=middle;spacing=6;" vertex="1" parent="1">
          <mxGeometry x="220" y="425" width="380" height="90" as="geometry" />
        </mxCell>

        <mxCell id="inA" value="" style="rounded=0;html=1;fillColor=none;strokeColor=none;pointerEvents=0;" vertex="1" parent="1">
          <mxGeometry x="170" y="140" width="8" height="8" as="geometry" />
        </mxCell>
        <mxCell id="inB" value="" style="rounded=0;html=1;fillColor=none;strokeColor=none;pointerEvents=0;" vertex="1" parent="1">
          <mxGeometry x="170" y="490" width="8" height="8" as="geometry" />
        </mxCell>
        <mxCell id="outA" value="" style="rounded=0;html=1;fillColor=none;strokeColor=none;pointerEvents=0;" vertex="1" parent="1">
          <mxGeometry x="615" y="140" width="8" height="8" as="geometry" />
        </mxCell>
        <mxCell id="outB" value="" style="rounded=0;html=1;fillColor=none;strokeColor=none;pointerEvents=0;" vertex="1" parent="1">
          <mxGeometry x="615" y="490" width="8" height="8" as="geometry" />
        </mxCell>

        <mxCell id="egIn" value="Peticion HTTP" style="html=1;endArrow=classic;endFill=1;strokeColor=#82b366;strokeWidth=3;" edge="1" parent="1" source="inA" target="inB">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
        <mxCell id="egOut" value="Respuesta HTTP" style="html=1;endArrow=classic;endFill=1;strokeColor=#e81414;strokeWidth=3;" edge="1" parent="1" source="outB" target="outA">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>

        <mxCell id="note1" value="Regla de Dependencia cumplida: app/core NO importa app/infra; los casos de uso solo conocen puertos (Protocol). El dominio no conoce FastAPI ni la BD; la infraestructura implementa los puertos (DIP)." style="whiteSpace=wrap;html=1;rounded=0;fillColor=#f5f5f5;strokeColor=#666666;dashed=1;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="220" y="545" width="380" height="80" as="geometry" />
        </mxCell>

        <!-- ================= PANEL 2: FLUJO POST /api/v1/users ================= -->
        <mxCell id="t2" value="2. Flujo de una peticion segun los componentes:  POST /api/v1/users (CREAR USUARIO)" style="text;html=1;align=left;verticalAlign=middle;fontSize=14;fontStyle=1;strokeColor=none;fillColor=none;" vertex="1" parent="1">
          <mxGeometry x="680" y="45" width="680" height="30" as="geometry" />
        </mxCell>

        <mxCell id="n1" value="1 &#183; CLIENTE HTTP&lt;br&gt;&lt;font style=&quot;font-size:10px&quot;&gt;POST /api/v1/users &#8594; JSON {name, email, password}&lt;/font&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;fontSize=12;" vertex="1" parent="1">
          <mxGeometry x="700" y="110" width="600" height="60" as="geometry" />
        </mxCell>
        <mxCell id="n2" value="2 &#183; FRAMEWORKS &amp; DRIVERS&lt;br&gt;&lt;font style=&quot;font-size:10px&quot;&gt;Uvicorn + FastAPI &#183; app/infra/api/app.py create_app() &#8594; registra routers y handlers&lt;/font&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;fontSize=12;" vertex="1" parent="1">
          <mxGeometry x="700" y="190" width="600" height="60" as="geometry" />
        </mxCell>
        <mxCell id="n3" value="3 &#183; INTERFACE ADAPTER &#8212; Router&lt;br&gt;&lt;font style=&quot;font-size:10px&quot;&gt;app/infra/api/routers/v1/user.py:29 create(dto) &#183; FastAPI parsea JSON &#8594; DTO CreateUserRequest (core/dtos/user.py)&lt;/font&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;fontSize=12;" vertex="1" parent="1">
          <mxGeometry x="700" y="270" width="600" height="60" as="geometry" />
        </mxCell>
        <mxCell id="n4" value="4 &#183; INTERFACE ADAPTER &#8212; Inyeccion de dependencias&lt;br&gt;&lt;font style=&quot;font-size:10px&quot;&gt;app/infra/api/dependencies/usecases/user.py:16 get_create_user_usecase(uow, hasher) &#8594; CreateUserUsecase con UnitOfWork + Hasher&lt;/font&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;fontSize=12;" vertex="1" parent="1">
          <mxGeometry x="700" y="350" width="600" height="60" as="geometry" />
        </mxCell>
        <mxCell id="n5" value="5 &#183; USE CASE &#8212; Regla de negocio&lt;br&gt;&lt;font style=&quot;font-size:10px&quot;&gt;core/usecases/user/create_user.py:21 execute(dto) &#183; valida Email y Password &#183; uow.user_repo.get_by_email? &#183; hasher.hash()&lt;/font&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=12;" vertex="1" parent="1">
          <mxGeometry x="700" y="430" width="600" height="60" as="geometry" />
        </mxCell>
        <mxCell id="n6" value="6 &#183; DOMINIO &#8212; Entidades y Value Objects&lt;br&gt;&lt;font style=&quot;font-size:10px&quot;&gt;User (entities/user.py) &#183; Email &#183; Password &#183; ID &#8212; invariantes autovalidadas (core/value_objects)&lt;/font&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=12;" vertex="1" parent="1">
          <mxGeometry x="700" y="510" width="600" height="60" as="geometry" />
        </mxCell>
        <mxCell id="n7" value="7 &#183; PUERTOS (Protocol) &#8212; interfaces del dominio&lt;br&gt;&lt;font style=&quot;font-size:10px&quot;&gt;core/ports: UserRepo &#183; UserUnitOfWork &#183; Hasher &#8212; las dependencias apuntan hacia adentro&lt;/font&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=12;" vertex="1" parent="1">
          <mxGeometry x="700" y="590" width="600" height="60" as="geometry" />
        </mxCell>
        <mxCell id="n8" value="8 &#183; INTERFACE ADAPTER &#8212; Implementaciones&lt;br&gt;&lt;font style=&quot;font-size:10px&quot;&gt;db/repositories/user.py:48 save() &#8594; DBUser &#183; db/unit_of_work/base.py commit/rollback &#183; security/crypto.py bcrypt&lt;/font&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;fontSize=12;" vertex="1" parent="1">
          <mxGeometry x="700" y="670" width="600" height="60" as="geometry" />
        </mxCell>
        <mxCell id="n9" value="9 &#183; BASE DE DATOS&lt;br&gt;&lt;font style=&quot;font-size:10px&quot;&gt;SQLModel / SQLAlchemy &#183; tabla users (Alembic) &#183; session.add() + commit()&lt;/font&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;fontSize=12;" vertex="1" parent="1">
          <mxGeometry x="700" y="750" width="600" height="60" as="geometry" />
        </mxCell>
        <mxCell id="resp" value="10 &#183; RESPUESTA (DTO de salida)&lt;br&gt;&lt;font style=&quot;font-size:10px&quot;&gt;UserResponse(id, name, email) &#8594; Router serializa &#8594; HTTP 201 Created&lt;/font&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;fontSize=12;" vertex="1" parent="1">
          <mxGeometry x="700" y="850" width="600" height="60" as="geometry" />
        </mxCell>

        <mxCell id="rA" value="" style="rounded=0;html=1;fillColor=none;strokeColor=none;pointerEvents=0;" vertex="1" parent="1">
          <mxGeometry x="1325" y="865" width="8" height="8" as="geometry" />
        </mxCell>
        <mxCell id="rB" value="" style="rounded=0;html=1;fillColor=none;strokeColor=none;pointerEvents=0;" vertex="1" parent="1">
          <mxGeometry x="1325" y="140" width="8" height="8" as="geometry" />
        </mxCell>

        <mxCell id="e1" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;endArrow=classic;endFill=1;strokeColor=#6c8ebf;strokeWidth=2;" edge="1" parent="1" source="n1" target="n2">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
        <mxCell id="e2" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;endArrow=classic;endFill=1;strokeColor=#6c8ebf;strokeWidth=2;" edge="1" parent="1" source="n2" target="n3">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
        <mxCell id="e3" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;endArrow=classic;endFill=1;strokeColor=#6c8ebf;strokeWidth=2;" edge="1" parent="1" source="n3" target="n4">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
        <mxCell id="e4" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;endArrow=classic;endFill=1;strokeColor=#6c8ebf;strokeWidth=2;" edge="1" parent="1" source="n4" target="n5">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
        <mxCell id="e5" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;endArrow=classic;endFill=1;strokeColor=#6c8ebf;strokeWidth=2;" edge="1" parent="1" source="n5" target="n6">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
        <mxCell id="e6" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;endArrow=classic;endFill=1;strokeColor=#6c8ebf;strokeWidth=2;" edge="1" parent="1" source="n6" target="n7">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
        <mxCell id="e7" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;endArrow=classic;endFill=1;strokeColor=#6c8ebf;strokeWidth=2;" edge="1" parent="1" source="n7" target="n8">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
        <mxCell id="e8" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;endArrow=classic;endFill=1;strokeColor=#6c8ebf;strokeWidth=2;" edge="1" parent="1" source="n8" target="n9">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
        <mxCell id="e9" value="commit() OK &#8212; async with uow" style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;endArrow=classic;endFill=1;dashed=1;strokeColor=#82b366;strokeWidth=2;fontSize=10;" edge="1" parent="1" source="n9" target="resp">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
        <mxCell id="eR" value="Respuesta HTTP 201 &#8594;" style="html=1;endArrow=classic;endFill=1;strokeColor=#e81414;strokeWidth=3;" edge="1" parent="1" source="rA" target="rB">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>

        <mxCell id="note2" value="Mapeo de excepciones de dominio &#8594; HTTP:  InvalidUserError (400) &#183; UserAlreadyExistsError (409) &#183; InvalidIDError (422) &#183; UserNotFoundError (404) &#183; AuthenticationFailedError (401)" style="whiteSpace=wrap;html=1;rounded=0;fillColor=#f5f5f5;strokeColor=#666666;dashed=1;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="700" y="935" width="600" height="50" as="geometry" />
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```


