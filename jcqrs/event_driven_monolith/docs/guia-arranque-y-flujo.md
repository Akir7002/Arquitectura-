# Guía de arranque, demo y sustentación

Esta guía explica cómo levantar el proyecto en modo normal (Docker), cómo recorrer el flujo completo con peticiones reales y cómo sustentar la arquitectura sin quedarse en la superficie.

> Documento complementario: [flujo-proyecto.md](flujo-proyecto.md), donde está el detalle de componentes, bases de datos, eventos y limitaciones.

---

## 0. Resumen para decir en 30 segundos

> "Es un **monolito orientado a eventos**: se despliega como un solo contenedor de aplicación, pero internamente está separado en servicios lógicos. Cada servicio tiene su base CouchDB y se comunica con los demás por eventos en RabbitMQ con exchanges `fanout`. FastAPI atiende las peticiones HTTP, los consumidores corren en hilos dentro del mismo proceso, el pago se procesa de forma asíncrona en un `ThreadPoolExecutor` y el usuario recibe los cambios por Server-Sent Events. La separación es lógica, no de infraestructura; por eso es un monolito, pero con el desacoplamiento de una arquitectura orientada a eventos."

---

## 1. Requisitos

| Requisito | Detalle |
|---|---|
| Docker Desktop | Con el daemon o servicio corriendo |
| Docker Compose v2 | En este equipo está disponible como `docker compose` |
| Python local | Solo para generar claves y el token de pago de la demo |
| Puertos libres | `80`, `5984`, `5672`, `15672` |
| `make` | **No es necesario en Windows**; se usa en Linux/macOS |

Comprueba Docker:

```powershell
docker --version
docker compose version
docker info
```

Si `docker info` falla, abre Docker Desktop y espera a que termine de arrancar.

---

## 2. Configurar `.env`

En la raíz del proyecto:

```powershell
Copy-Item .env_template .env
notepad .env
```

Variables que debes completar:

| Variable | Uso | Formato |
|---|---|---|
| `COUCHDB_USER` | Usuario administrador de CouchDB | Texto |
| `COUCHDB_PASSWORD` | Contraseña del administrador | Texto |
| `COUCHDB_APP_USER` | Usuario de aplicación | Texto |
| `COUCHDB_APP_PASSWORD` | Contraseña del usuario de aplicación | Texto |
| `APP_ADM_USER` | Administrador de la aplicación | **Debe parecer un email** |
| `APP_ADM_PASSWORD` | Contraseña del administrador | Texto |
| `ACCESS_TOKEN_SECRET_KEY` | Firma de los JWT HS256 | 64 caracteres hex recomendados |
| `PAYMENT_PROVIDER_API_KEY` | API key del simulador de pagos | **Exactamente 64 caracteres** |
| `PAYMENT_PROVIDER_ENCRYPTION_KEY` | Cifrado Fernet de la tarjeta | Base64 urlsafe de 32 bytes (44 caracteres) |

Genera los valores con Python:

```powershell
# 64 caracteres hex: sirve para ACCESS_TOKEN_SECRET_KEY y PAYMENT_PROVIDER_API_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# Clave Fernet de 32 bytes en base64 urlsafe
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Si el segundo comando falla porque falta `cryptography`:

```powershell
python -m pip install cryptography
```

### Advertencia importante sobre la configuración actual

Al revisar el `.env` de este equipo, `PAYMENT_PROVIDER_API_KEY` tiene **26 caracteres**. El esquema `PaymentCheckoutInfo` exige **exactamente 64**:

```python
api_key: str = Field(min_length=64, max_length=64)
```

Si no se corrige, `/buy-recipe` fallará al construir `PaymentCheckoutInfo` y la compra no llegará al simulador. Genera una nueva con:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

y reemplaza el valor en `.env`.

`APP_ADM_USER` también debe tener formato de email porque el login lo valida con `EmailStr`.

---

## 3. Primer arranque

El orden importa: CouchDB debe estar sano y el usuario de aplicación debe existir **antes** de que arranque la app. Si la app arranca antes, falla al crear los índices con el usuario `app`.

```powershell
# 1. Construir las imágenes
docker compose build

# 2. Levantar solamente CouchDB
docker compose up -d couchdb

# 3. Esperar a que esté "healthy"
docker compose ps

# 4. Crear el usuario de aplicación y habilitar el nodo único
docker compose exec -d couchdb ./init_couchdb
Start-Sleep -Seconds 2

# 5. Levantar el resto
docker compose up -d

# 6. Verificar
docker compose ps
docker compose logs --tail=100 app
```

En los logs de `app` deberías ver seis líneas `Starting consumer thread` y ningún `traceback`.

### Si prefieres usar el Makefile

En Linux, macOS o Git Bash con `make` instalado:

```bash
make build
make start
make status
```

`make build` hace exactamente la secuencia anterior: construye, levanta CouchDB, espera 10 segundos, ejecuta `init_couchdb` y levanta todo.

---

## 4. URLs del sistema

| Servicio | URL | Notas |
|---|---|---|
| Documentación interactiva | http://127.0.0.1/docs | Swagger UI de FastAPI |
| OpenAPI | http://127.0.0.1/openapi.json | Contrato de la API |
| CouchDB Fauxton | http://127.0.0.1:5984/_utils/ | Usa `COUCHDB_USER` / `COUCHDB_PASSWORD` |
| RabbitMQ Management | http://127.0.0.1:15672 | Por defecto `guest` / `guest` |
| API | http://127.0.0.1 | Puerto 80 del contenedor |

Si el puerto 80 está ocupado en Windows, cambia en `docker-compose.yml`:

```yaml
ports:
  - "8000:80"
```

y usa `http://127.0.0.1:8000`. No hace falta tocar el código: las llamadas internas del simulador usan `http://localhost/...` dentro del contenedor, donde Uvicorn sigue escuchando en el puerto 80.

### Arranque y parada del día a día

```powershell
docker compose up -d      # arrancar
docker compose stop       # detener sin borrar
docker compose down       # borrar contenedores, conservar datos
docker compose down -v    # borrar contenedores y datos (¡cuidado!)
docker compose logs -f app
```

No uses `docker compose restart app` como primera opción si cambiaste `.env`: para recrear variables de entorno hace falta `docker compose up -d --force-recreate app`.

### ¿Y si quiero ejecutar `uvicorn` directamente?

No es la forma normal del proyecto. `src/config.py` fija los hosts `couchdb` y `rabbitmq`, que solo resuelven dentro de la red de Docker. Para correrlo fuera de Docker tendrías que:

1. Levantar solo las dependencias: `docker compose up -d couchdb rabbitmq`.
2. Ejecutar `init_couchdb`.
3. Añadir `127.0.0.1 couchdb` y `127.0.0.1 rabbitmq` al archivo `hosts` de Windows.
4. Exportar todas las variables del `.env` en la sesión.
5. Ejecutar `uvicorn main:app --reload --port 80` desde `src/`.

Para la sustentación y la demo, usa Docker: es el modo para el que está diseñado el proyecto y evita diferencias de entorno.

---

## 5. Demo completa con peticiones reales

Abre dos terminales:

- **Terminal A:** logs de la app y SSE.
- **Terminal B:** peticiones HTTP.

### 5.1 Preparar variables en PowerShell

```powershell
$base = 'http://127.0.0.1'
$email = "demo+$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())@example.com"
$password = 'DemoPass123!'
```

### 5.2 Registro

`/signup` recibe dos objetos: `credentials` y `user_info`.

```powershell
$signupBody = @{
    credentials = @{
        id       = $email
        password = $password
    }
    user_info = @{
        id           = $email
        name         = 'Demo User'
        phone_number = '1234567890'
        address      = 'Demo Street 123'
    }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Method Post -Uri "$base/signup" `
    -ContentType 'application/json' -Body $signupBody
```

Respuesta esperada: `status = successful_sign_up`.

El correo no se envía: se imprime en los logs del contenedor. Búscalo con:

```powershell
docker compose logs app --no-color | Select-String 'confirm-email\?token='
```

Verás algo así:

```text
To confirm you subscription, please access the following link:
http://127.0.0.1/confirm-email?token=eyJhbGciOi...
```

### 5.3 Confirmar el correo

Copia el token de la URL y confírmalo por API:

```powershell
$confirmToken = Read-Host 'Pega el token de confirmación'
Invoke-RestMethod -Method Post -Uri "$base/confirm-email-api" `
    -ContentType 'application/json' `
    -Body (@{ token = $confirmToken } | ConvertTo-Json)
```

También puedes abrir la URL en el navegador: `GET /confirm-email?token=...`.

Espera un segundo: el consumidor `enable_user` marca `validated=True` de forma asíncrona. Si intentas hacer login inmediatamente y recibes `email_not_validated`, espera y reintenta.

### 5.4 Login

```powershell
$login = Invoke-RestMethod -Method Post -Uri "$base/login" `
    -Body @{ username = $email; password = $password }

$token = $login.details.data.token
if (-not $token) { $token = $login.details.data.new_token }
$headers = @{ Authorization = "Bearer $token" }
```

El token es un JWT HS256 con `sub = email` y 24 horas de vigencia.

### 5.5 Login del administrador y carga de recetas

Lee las credenciales del `.env` sin imprimirlas:

```powershell
$envMap = @{}
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([A-Za-z_]+)\s*=\s*(.*)$') {
        $value = $matches[2].Trim().Trim("'")
        $envMap[$matches[1]] = $value
    }
}

$adminLogin = Invoke-RestMethod -Method Post -Uri "$base/login" `
    -Body @{
        username = $envMap['APP_ADM_USER']
        password = $envMap['APP_ADM_PASSWORD']
    }
$adminToken = $adminLogin.details.data.token
if (-not $adminToken) { $adminToken = $adminLogin.details.data.new_token }
```

Carga el CSV de ejemplo. Es tabulado, **sin cabecera**, y el campo del formulario se llama `recipes_csv`:

```powershell
curl.exe -s -X POST "$base/load-recipes" `
    -H "Authorization: Bearer $adminToken" `
    -F "recipes_csv=@src/recipes.csv"
```

Respuesta esperada: `status = api_recipes_loaded`, HTTP 201.

### 5.6 Consultar el catálogo

```powershell
$recipes = Invoke-RestMethod -Uri "$base/get-all-recipes" -Headers $headers
$recipes.details.data.all_recipes | Select-Object -First 3 | Format-List
```

Cada receta trae `id` (slug generado desde el nombre), `summary`, `category`, `easiness`, `tags`, `price` y `status`. Detalle real del código: aunque el esquema declara el alias `recipe_id`, la serialización por defecto devuelve la clave `id`; los tests lo confirman.

Guarda una receta para la compra:

```powershell
$recipe = $recipes.details.data.all_recipes[0]
$recipeId = $recipe.id
$recipeId
```

Detalle de una receta:

```powershell
Invoke-RestMethod -Uri "$base/get-recipe-details/$recipeId" -Headers $headers |
    ConvertTo-Json -Depth 6
```

### 5.7 Generar el pago cifrado

El endpoint `/buy-recipe/{recipe_id}` espera `{ "encr_info": "<token Fernet>" }`. Ese token se genera con la misma clave `PAYMENT_PROVIDER_ENCRYPTION_KEY` y contiene un JSON con los datos de la tarjeta.

Crea `payment_token.py` en la raíz del proyecto:

```python
import json
import os
from datetime import datetime

from cryptography.fernet import Fernet

key = os.environ["PAYMENT_PROVIDER_ENCRYPTION_KEY"].encode()
payload = {
    "card_holder_name": "Demo User",
    "card_number": "4242424242424242",
    "expiration_month": 12,
    "expiration_year": datetime.now().year + 2,
    "cvv": 123,
    "number_installments": 1,
}
print(Fernet(key).encrypt(json.dumps(payload).encode()).decode())
```

Ejecútalo con las variables del `.env` cargadas en PowerShell:

```powershell
$env:PAYMENT_PROVIDER_ENCRYPTION_KEY = $envMap['PAYMENT_PROVIDER_ENCRYPTION_KEY']
$encrInfo = python payment_token.py
$encrInfo
```

### 5.8 Comprar la receta

```powershell
$buyBody = @{ encr_info = $encrInfo } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$base/buy-recipe/$recipeId" `
    -Headers $headers -ContentType 'application/json' -Body $buyBody
```

Respuesta esperada: HTTP 201 con `status = api_recipe_purchase_started`.

En este punto ya se publicó `recipe-purchase-requested`. Los consumidores:

1. `add_user_recipe` guarda la receta con estado `requested`.
2. `send_purchase_notification` encola una notificación SSE.

### 5.9 Ver las notificaciones en vivo

En la terminal A:

```powershell
curl.exe -N -H "Authorization: Bearer $token" "$base/notifications"
```

Verás primero el evento `recipe-purchase-requested`. El pago tarda entre **1 y 5 minutos** porque el simulador hace `time.sleep(minutos * 60)`. Cuando termina, el webhook publica `purchase-status-changed` y verás el segundo evento con `payment_status = 1` (`PAID`).

Mientras esperas, puedes comprobar el estado en CouchDB:

- Base `payment`: documento con `_id = checkout_id`, `user_id`, `recipe_id`, `payment_id` y `payment_status`.
- Base `user-recipe`: documento con `_id = email`, lista `recipes` con la receta en `requested` y luego `purchased`.

Cuando llegue el webhook, `update_recipe_status` cambia el estado a `purchased` y `notify_recipe_state_change` publica el cambio por SSE.

---

## 6. Cómo explicar el flujo interno

### 6.1 Qué se despliega

| Contenedor | Tecnología | Función |
|---|---|---|
| `evt-drv-app` | FastAPI + Uvicorn | API, servicios, consumidores y simulador de pagos |
| `evt-drv-couchdb` | CouchDB 3.3 | Persistencia documental |
| `evt-drv-rabbitmq` | RabbitMQ 3.12 | Transporte de eventos pub/sub |

No son microservicios: los servicios de negocio, los consumidores y el simulador viven en el mismo proceso y en el mismo despliegue. La separación es por **límites funcionales**: cada servicio tiene su base lógica y se comunica por eventos.

### 6.2 Capas del código

| Archivo | Responsabilidad |
|---|---|
| `src/main.py` | Endpoints HTTP/SSE y traducción a `JSONResponse` |
| `src/services.py` | Lógica de negocio y callbacks de consumidores |
| `src/core.py` | Creación de bases, usuario admin e hilos consumidores |
| `src/database.py` | Adaptador CouchDB: bases, índices, `_find`, upsert |
| `src/pubsub.py` | RabbitMQ: exchanges `fanout`, colas exclusivas y publicación |
| `src/schemas.py` | Validación con Pydantic |
| `src/utils.py` | JWT, bcrypt, Fernet, slugs y utilidades |
| `src/output_status.py` | Normalización de estados de respuesta |

La regla de diseño es: el endpoint no contiene reglas de negocio; el servicio no conoce detalles HTTP; la base no se comparte entre contextos.

### 6.3 Las seis bases

| Base | Contenido |
|---|---|
| `user-credentials` | Hash bcrypt, `validated`, `last_login` |
| `user-info` | Nombre, teléfono, dirección |
| `email-confirmation` | Token JWT de confirmación y fecha de confirmación |
| `recipe` | Catálogo: resumen, categoría, dificultad, precio, tags y receta |
| `user-recipe` | Recetas del usuario y estado `requested` / `purchased` |
| `payment` | Relación `checkout_id -> user_id`, datos del pago y estado |

En tests se prefijan con `test-` gracias a `IN_TEST`.

### 6.4 Los cuatro exchanges

| Exchange | Productor | Consumidores | Efecto |
|---|---|---|---|
| `user-signed-up` | `user_sign_up` | `email_confirmation` | Genera token y simula el correo |
| `email-confirmed` | `check_email_confirmation` | `enable_user` | Marca `validated=True` |
| `recipe-purchase-requested` | `start_checkout` | `add_user_recipe`, `send_purchase_notification` | Agrega la receta y notifica |
| `purchase-status-changed` | `update_payment_status` | `update_recipe_status`, `notify_recipe_state_change` | Cambia el estado y notifica |

Cada `Subscription` crea una cola temporal exclusiva. Por eso un mismo evento puede llegar a varios consumidores: es un patrón **fanout**, no una cola de trabajo compartida.

### 6.5 Flujo de alta y login

1. `POST /signup` valida y guarda credenciales y perfil.
2. Publica `user-signed-up`.
3. El consumidor `email_confirmation` genera un JWT de 24 horas, lo guarda y escribe el correo en stdout.
4. El usuario confirma con `GET /confirm-email` o `POST /confirm-email-api`.
5. Se guarda `confirmed_datetime` y se publica `email-confirmed`.
6. El consumidor `enable_user` marca `validated=True`.
7. `POST /login` verifica bcrypt, exige `validated`, guarda `last_login` y devuelve un JWT.

### 6.6 Flujo de compra y pago

1. `POST /buy-recipe/{recipe_id}` recibe el pago cifrado con Fernet.
2. `start_checkout` llama al simulador `POST /create-checkout/{recipe_id}` con API key.
3. El simulador valida la API key, descifra la tarjeta, genera `checkout_id` y envía el procesamiento a un `ThreadPoolExecutor` de hasta cinco workers.
4. La app guarda `checkout_id -> user_id` en `payment` y publica `recipe-purchase-requested`.
5. Los consumidores agregan la receta como `requested` y encolan la notificación.
6. El endpoint responde 201; el pago sigue en segundo plano.
7. El simulador espera de 1 a 5 minutos y llama a `POST /payment-webhook/{checkout_id}` con `PAID`.
8. `update_payment_status` completa el documento `payment` y publica `purchase-status-changed`.
9. `update_recipe_status` cambia a `purchased`; `notify_recipe_state_change` publica por SSE.
10. El cliente que mantiene `GET /notifications` abierto recibe ambos eventos.

La clave para sustentarlo: **hay dos velocidades**. La petición HTTP termina rápido; el pago y la actualización de estado son eventualmente consistentes.

### 6.7 Decisiones que conviene defender

- **Monolito y no microservicios:** menos latencia de red, menos complejidad operativa, reutilización de código y un solo despliegue. Los límites lógicos permiten extraer servicios después si hiciera falta.
- **RabbitMQ con `fanout`:** desacopla productor y consumidores y permite añadir consumidores sin tocar al productor.
- **CouchDB:** modelo documental, API HTTP y una base por contexto. El coste es que no hay transacciones entre bases.
- **Hilos consumidores:** suficientes para una PoC; en producción se separarían en workers.
- **ThreadPoolExecutor:** libera el endpoint de checkout mientras el simulador espera.
- **SSE:** canal unidireccional suficiente para notificaciones y más simple que WebSockets.
- **Consistencia eventual:** el usuario ve `requested` y después `purchased`; no se promete consistencia fuerte.

### 6.8 Limitaciones que debes reconocer sin que te las pregunten

- HTTP sin TLS en CouchDB y RabbitMQ.
- RabbitMQ sin autenticación y con `BlockingConnection`.
- CouchDB y RabbitMQ en un solo nodo.
- Sin recuperación completa de conexiones de RabbitMQ.
- Notificaciones en `queue.SimpleQueue` en memoria: se pierden al reiniciar y no sirven para escalar.
- Sin `outbox`: se escribe en CouchDB y se publica en RabbitMQ en dos pasos; si falla el segundo, queda inconsistente.
- Sin idempotencia en compras ni webhooks: una petición repetida podría duplicar efectos.
- El simulador siempre termina en `PAID` si la validación inicial es correcta.

---

## 7. Guion de sustentación (5 a 7 minutos)

### 7.1 Apertura (30 segundos)

> "El proyecto es una plataforma de venta de recetas. Lo que quiero demostrar no es la tienda, sino la viabilidad de un monolito orientado a eventos: un solo despliegue, pero con servicios lógicos separados por bases de datos y comunicación asíncrona. La pregunta que responde la PoC es si se puede tener el desacoplamiento de los microservicios sin pagar el coste operativo de coordinarlos."

### 7.2 Arquitectura (1,5 minutos)

> "Hay tres contenedores: la app FastAPI, CouchDB y RabbitMQ. La app contiene los endpoints, los servicios de negocio, los consumidores y el simulador de pagos. Cada servicio tiene su propia base: credenciales, perfil, confirmación, recetas, recetas del usuario y pagos. La comunicación entre contextos no es por llamadas directas, sino por eventos publicados en exchanges `fanout`. Eso permite que un mismo evento tenga varios consumidores: por ejemplo, cuando se solicita una compra, un consumidor agrega la receta y otro envía la notificación."

### 7.3 Recorrido del flujo (3 minutos)

> "Hago el registro, el sistema publica `user-signed-up`, el consumidor de confirmación genera un JWT y lo imprime en los logs porque el correo está simulado. Confirmo el correo, se publica `email-confirmed` y el consumidor habilita al usuario. Hago login y obtengo un JWT. Como administrador cargo el CSV de recetas. Consulto el catálogo y compro una receta con un pago cifrado con Fernet. La compra responde 201 antes de que el pago termine: el simulador procesa en un hilo aparte y espera entre uno y cinco minutos. Mientras tanto, la receta aparece como `requested`. Cuando llega el webhook, se publica `purchase-status-changed`, la receta pasa a `purchased` y el cliente que está suscrito a `/notifications` recibe el cambio por SSE."

### 7.4 Cierre (1 minuto)

> "La PoC demuestra que el patrón funciona y que el acoplamiento baja. También deja claras las deudas: notificaciones en memoria, falta de outbox e idempotencia, RabbitMQ sin autenticación y todo en un solo nodo. Esas son precisamente las mejoras que plantearía antes de llevar esto a producción: outbox, idempotencia, notificaciones durables y separación de consumidores en workers."

---

## 8. Preguntas probables y respuestas

**¿Por qué es un monolito si usa eventos?**
Porque hay un solo despliegue y un solo proceso de aplicación. La arquitectura orientada a eventos describe la comunicación, no la topología de despliegue. Los límites son lógicos.

**¿Por qué no microservicios?**
Porque el objetivo es evitar la complejidad operativa y la latencia de red, manteniendo la posibilidad de extraer servicios. Para el volumen de una PoC, un monolito es más simple de desplegar y depurar.

**¿Qué pasa si RabbitMQ se cae?**
La publicación falla y se registra el error. No hay outbox ni reintentos durables, así que el evento puede perderse. Es una limitación consciente de la PoC.

**¿Cómo se garantiza que no se cobre dos veces?**
Hoy no se garantiza: no hay clave de idempotencia. El webhook actualiza por `checkout_id`, pero una repetición o una compra duplicada no está protegida. La mejora está propuesta en la sección 11 del documento de flujo.

**¿Cómo se escala?**
Los consumidores son hilos dentro del proceso. Para escalar de verdad habría que sacarlos a workers y cambiar las colas exclusivas por colas compartidas si se quiere repartir carga. Ojo: con `fanout` y colas exclusivas, cada instancia recibe una copia del evento, no una parte del trabajo.

**¿La consistencia es fuerte?**
No. Es eventual. La compra responde antes de que el pago termine y el estado pasa por `requested` y luego `purchased`. Eso es intencional.

**¿Dónde está el correo de confirmación?**
No se envía. El servicio de entrega imprime el mensaje en los logs del contenedor. Es una simulación para la PoC.

**¿Qué protege los datos de la tarjeta?**
Se cifran con Fernet antes de enviarse y se descifran en el simulador. En producción faltaría TLS, tokenización real y no persistir datos sensibles.

**¿Por qué CouchDB y no PostgreSQL?**
Porque el modelo es documental y cada contexto tiene documentos simples. CouchDB ofrece API HTTP y despliegue sencillo. El trade-off es que no hay transacciones entre bases.

---

## 9. Problemas frecuentes

| Síntoma | Causa probable | Solución |
|---|---|---|
| La app reinicia en bucle | No se ejecutó `init_couchdb` | `docker compose exec -d couchdb ./init_couchdb` y recrear la app |
| `InvalidAppAdminCredentialsError` | Faltan `APP_ADM_USER` o `APP_ADM_PASSWORD` | Completar `.env` y recrear |
| `/buy-recipe` falla con error de validación | `PAYMENT_PROVIDER_API_KEY` no tiene 64 caracteres | Generar una nueva y recrear |
| Login devuelve `email_not_validated` | El consumidor `enable_user` aún no procesó el evento | Esperar un segundo y reintentar |
| No aparece el correo | Es simulado | `docker compose logs app \| Select-String 'confirm-email'` |
| No llegan notificaciones SSE | El pago tarda de 1 a 5 minutos | Esperar; revisar logs y el documento `payment` |
| Puerto 80 ocupado | Otro servicio en Windows | Cambiar a `"8000:80"` en `docker-compose.yml` |
| `docker compose` no encuentra `.env` | Falta el archivo | `Copy-Item .env_template .env` |
| Los datos desaparecen | Se ejecutó `docker compose down -v` | Volver a cargar recetas y registrarse |

---

## 10. Chuleta de comandos

```powershell
# Arranque inicial
docker compose build
docker compose up -d couchdb
docker compose ps
docker compose exec -d couchdb ./init_couchdb
docker compose up -d
docker compose ps

# Operación
docker compose logs -f app
docker compose stop
docker compose up -d

# Documentación
Start-Process http://127.0.0.1/docs
Start-Process http://127.0.0.1:5984/_utils/
Start-Process http://127.0.0.1:15672

# Tests dentro del contenedor
docker compose exec app pytest
docker compose exec app pytest tests/test_services.py
```
