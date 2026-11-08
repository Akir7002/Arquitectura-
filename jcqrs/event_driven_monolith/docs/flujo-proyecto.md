# Flujo y arquitectura de Event-Driven Monolith

## 1. Resumen

Este repositorio es una prueba de concepto (PoC) de un **monolito orientado a eventos**. No son microservicios independientes: FastAPI, los servicios de negocio, los consumidores de RabbitMQ y el simulador de pagos viven dentro del mismo código y se despliegan en el contenedor `app`. La separación se consigue mediante límites funcionales, bases lógicas independientes y mensajes pub/sub.

El diagrama navegable está en [event_driven_monolith_componentes.drawio](../event_driven_monolith_componentes.drawio). El archivo [analisis.drawio](../analisis.drawio) se conserva como ejemplo original.

## 2. Componentes desplegados

`docker-compose.yml` levanta tres servicios en la red `evt-drv-net`:

| Componente | Tecnología | Puerto | Responsabilidad |
|---|---|---:|---|
| `app` | Python 3.11, FastAPI, Uvicorn | `80` (API), `1984` (depuración) | API, negocio, consumidores, pagos simulados |
| `couchdb` | CouchDB 3.3 | `5984` | Persistencia documental |
| `rabbitmq` | RabbitMQ 3.12 Management | `5672` AMQP, `15672` UI | Transporte de eventos pub/sub |

El contenedor de aplicación espera a que CouchDB y RabbitMQ estén saludables. La configuración se inyecta por variables de entorno definidas a partir de [.env_template](../.env_template).

Los contenedores no tienen una política de reinicio automático. Para iniciarlos manualmente usa `docker compose up -d` o el botón **Start** del proyecto en Docker Desktop.

## 3. ¿Con qué base de datos funciona?

Funciona con **CouchDB 3.3**, no con PostgreSQL, MySQL ni una base relacional. La aplicación se conecta por HTTP mediante `httpx` a `http://couchdb:5984`. La clase `CouchDb` de [src/database.py](../src/database.py) encapsula:

- creación de bases y permisos;
- índices Mango mediante `POST /_index`;
- consultas por documento y por selector mediante `/_find`;
- lectura masiva;
- upsert con control de `_rev` y cabecera `If-Match`.

En ejecución normal se crean seis bases documentales:

| Base | Datos principales | Quién la usa |
|---|---|---|
| `user-credentials` | hash bcrypt, `validated`, `last_login` | registro, login y `enable_user` |
| `user-info` | nombre, teléfono, dirección | perfil y notificaciones |
| `email-confirmation` | JWT de confirmación y fecha confirmada | confirmación de correo |
| `recipe` | resumen, categoría, dificultad, precio, tags y receta | carga y consultas de recetas |
| `user-recipe` | recetas del usuario y estado `requested/purchased` | compra y consulta personalizada |
| `payment` | relación checkout/usuario, pago y estado | checkout y webhook |

Los nombres se prefijan con `test-` cuando se ejecutan pruebas (`IN_TEST`). CouchDB se configura como single-node y usa un usuario administrativo para crear bases y un usuario de aplicación con rol `app` para las operaciones normales.

## 4. Capas y módulos

- **Entrada HTTP/SSE:** [src/main.py](../src/main.py) define los endpoints FastAPI, transforma payloads y devuelve `JSONResponse` o `EventSourceResponse`.
- **Servicios de negocio:** [src/services.py](../src/services.py) implementa autenticación, confirmación, recetas, compras, pagos y callbacks de consumidores.
- **Inicialización:** [src/core.py](../src/core.py) crea bases/índices, crea el usuario administrador e inicia un hilo consumidor por suscripción.
- **Persistencia:** [src/database.py](../src/database.py) es el adaptador CouchDB.
- **Mensajería:** [src/pubsub.py](../src/pubsub.py) usa `pika`, exchanges `fanout`, colas exclusivas temporales y confirmación de publicación.
- **Contratos:** [src/schemas.py](../src/schemas.py) valida modelos con Pydantic.
- **Seguridad:** [src/utils.py](../src/utils.py) genera/valida JWT HS256, calcula hashes bcrypt y cifra datos de pago con Fernet.
- **Estados HTTP:** [src/output_status.py](../src/output_status.py) normaliza respuestas de los servicios.

## 5. Eventos y consumidores

Cada `Subscription` crea un exchange `fanout` y una cola temporal exclusiva. En consecuencia, un evento puede entregarse a varios consumidores:

| Exchange | Productor | Consumidor | Efecto |
|---|---|---|---|
| `user-signed-up` | `user_sign_up` | `email_confirmation` | crea token de confirmación, persiste el token y simula envío imprimiendo el correo |
| `email-confirmed` | `check_email_confirmation` | `enable_user` | marca `validated=True` en `user-credentials` |
| `recipe-purchase-requested` | `start_checkout` | `add_user_recipe` | agrega la receta del usuario con estado `requested` |
| `recipe-purchase-requested` | `start_checkout` | `send_purchase_notification` | coloca una notificación en la cola en memoria del usuario |
| `purchase-status-changed` | `update_payment_status` | `update_recipe_status` | convierte estado de pago a `requested` o `purchased` y actualiza `user-recipe` |
| `purchase-status-changed` | `update_payment_status` | `notify_recipe_state_change` | publica el cambio a la cola SSE del usuario |

Los consumidores se ejecutan en hilos daemon dentro del mismo proceso. La cola de notificaciones es `queue.SimpleQueue` en memoria; el propio código deja indicado que debería sustituirse por CouchDB u otro mecanismo durable si se necesitara escalar.

## 6. Flujo completo de alta y login

1. El cliente llama `POST /signup` con credenciales y datos del usuario.
2. `user_sign_up` comprueba si existe el correo en `user-credentials`.
3. Si es nuevo, calcula el hash bcrypt, guarda credenciales y perfil en `user-info`.
4. Publica `user-signed-up` con usuario, nombre y URL base.
5. `email_confirmation` consume el evento, crea un JWT de confirmación con vigencia de 24 horas, lo guarda en `email-confirmation` y escribe el mensaje de correo en stdout.
6. El usuario abre `GET /confirm-email?token=...` o usa `POST /confirm-email-api`.
7. `check_email_confirmation` valida firma/expiración, comprueba el documento, guarda `confirmed_datetime` y publica `email-confirmed`.
8. `enable_user` consume el evento y marca el usuario como validado.
9. `POST /login` verifica hash y `validated`, guarda `last_login` y devuelve un JWT HS256 de acceso con vigencia de 24 horas.
10. Los endpoints protegidos usan `OAuth2PasswordBearer` y `handle_token` para validar ese JWT.

El administrador de aplicación se crea durante el arranque con `APP_ADM_USER` y `APP_ADM_PASSWORD`; solo ese usuario puede usar `POST /load-recipes`.

## 7. Flujo de recetas

### Carga

`POST /load-recipes` requiere un JWT cuyo `sub` coincida con `APP_ADM_USER`. El archivo se lee como CSV tabulado (`\t`) con campos de nombre, descripción, categoría, dificultad, precio, tags, ingredientes y direcciones. [services.py](../src/services.py) valida cada fila con Pydantic, separa listas por `|`, genera un slug a partir del nombre y hace upsert en `recipe`.

### Consulta

- `GET /get-all-recipes` obtiene el catálogo desde `recipe` y el estado del usuario desde `user-recipe`. Para recetas compradas oculta el precio y marca el estado.
- `GET /get-recipe-details/{recipe_id}` combina el documento de `recipe` con el estado del usuario. Si está `requested`, oculta el detalle completo hasta finalizar la compra.

## 8. Flujo de compra y pago

1. El cliente llama `POST /buy-recipe/{recipe_id}` con JWT y datos de pago cifrados.
2. `start_checkout` llama internamente a `POST /create-checkout/{recipe_id}` con API key y payload Fernet.
3. El simulador valida la API key, descifra y valida la tarjeta, genera `checkout_id` y envía el procesamiento a un `ThreadPoolExecutor` de hasta cinco workers.
4. La aplicación guarda `checkout_id -> user_id` en `payment` y publica `recipe-purchase-requested`.
5. Los dos consumidores del evento agregan la receta como `requested` y notifican al usuario.
6. El endpoint de compra responde; el pago todavía es asíncrono.
7. El simulador espera aleatoriamente entre 1 y 5 minutos y genera un pago `PAID`.
8. Llama a `POST /payment-webhook/{checkout_id}` con `recipe_id`, `payment_id` y `payment_status`.
9. `update_payment_status` completa el documento `payment` y publica `purchase-status-changed`.
10. `update_recipe_status` cambia la receta del usuario a `purchased`.
11. `notify_recipe_state_change` agrega un evento a la `SimpleQueue` del usuario.
12. El cliente que mantiene `GET /notifications` abierto recibe ambos cambios mediante Server-Sent Events.

El simulador no es un proveedor externo real: vive en la propia API y siempre termina simulando `PAID` si la validación inicial es correcta.

## 9. Seguridad y configuración

- Contraseñas: bcrypt con salt.
- Tokens: JWT HS256 con `ACCESS_TOKEN_SECRET_KEY`.
- Datos de pago: Fernet con `PAYMENT_PROVIDER_ENCRYPTION_KEY`.
- Proveedor simulado: `PAYMENT_PROVIDER_API_KEY`.
- CouchDB: credenciales administrativas y de aplicación separadas.
- Las claves y contraseñas deben permanecer en `.env`; no deben versionarse.

## 10. Arranque y límites conocidos

```text
make build
make start
```

La documentación interactiva queda en `http://127.0.0.1/docs`. Las pruebas se ejecutan con `make test`.

Limitaciones explícitas de la PoC:

- HTTP sin TLS para CouchDB y RabbitMQ.
- RabbitMQ sin autenticación y con `BlockingConnection`.
- CouchDB y RabbitMQ en single-node.
- Sin recuperación completa de conexiones de RabbitMQ.
- Notificaciones en memoria, por lo que se pierden al reiniciar el proceso.
- El monolito comparte proceso y despliegue; los límites de servicio son lógicos, no de infraestructura.

Estas decisiones sirven para estudiar el patrón, pero requieren endurecimiento antes de un uso productivo.

## 11. Propuesta de entidades extras a desarrollar

Las entidades actuales cubren el mínimo del negocio: identidad, catálogo, compra y notificación. Las siguientes ampliaciones mantienen el mismo criterio del proyecto: **una base lógica por contexto**, servicios con responsabilidad única y comunicación por eventos cuando el efecto cruza contextos.

La prioridad indicada es orientativa: **P1** son ampliaciones pequeñas que reutilizan los flujos existentes; **P2** requieren un agregado o un cambio de flujo; **P3** abren contextos nuevos.

### 11.1 Resumen

| Entidad | Contexto | Datos clave | Eventos principales | Prioridad |
|---|---|---|---|---|
| `Favorite` | Descubrimiento | `user_id`, `recipe_id`, `created_at` | `favorite-added`, `favorite-removed` | P1 |
| `Review` / `Rating` | Reputación | `review_id`, `user_id`, `recipe_id`, `order_id`, `rating`, `comment`, `status` | `review-created`, `review-moderated` | P1 |
| `Category` | Catálogo | `category_id`, `name`, `slug`, `parent_id` | `category-created`, `category-updated` | P1 |
| `Tag` | Catálogo | `tag_id`, `name`, `slug`, `synonyms` | `tag-created`, `tag-merged` | P1 |
| `PasswordResetToken` | Identidad | `user_id`, `token_hash`, `expires_at`, `used_at` | `password-reset-requested`, `password-reset-completed` | P1 |
| `Session` / `RefreshToken` | Identidad | `session_id`, `user_id`, `device`, `expires_at`, `revoked_at` | `session-created`, `session-revoked` | P1 |
| `Notification` | Notificaciones | `notification_id`, `user_id`, `channel`, `payload`, `status`, `attempts` | `notification-requested`, `notification-sent`, `notification-read` | P1 |
| `Cart` / `CartItem` | Compra | `user_id`, `items[]`, `updated_at` | `cart-updated`, `cart-checked-out` | P2 |
| `Order` / `OrderItem` | Compra | `order_id`, `user_id`, `items[]`, `total`, `status` | `order-created`, `order-paid`, `order-cancelled` | P2 |
| `Coupon` / `Promotion` | Monetización | `code`, `kind`, `value`, `valid_from`, `valid_to`, `max_uses` | `coupon-redeemed`, `coupon-exhausted` | P2 |
| `Invoice` / `Refund` | Pagos | `invoice_id`, `order_id`, `amount`, `status`, `refund_reason` | `invoice-issued`, `refund-requested`, `refund-completed` | P2 |
| `IdempotencyKey` | Plataforma | `key`, `user_id`, `endpoint`, `request_hash`, `response`, `expires_at` | — | P2 |
| `OutboxEvent` | Plataforma | `event_id`, `aggregate_id`, `event_name`, `payload`, `status`, `retries` | — | P2 |
| `Subscription` / `Plan` | Monetización | `subscription_id`, `user_id`, `plan_id`, `status`, `next_billing_at` | `subscription-started`, `subscription-renewed`, `subscription-cancelled` | P3 |
| `Ingredient` / `RecipeIngredient` | Catálogo | `ingredient_id`, `name`, `unit`, `allergens`, `nutrition` | `ingredient-created`, `recipe-ingredients-updated` | P3 |
| `RecipeMedia` | Catálogo | `media_id`, `recipe_id`, `url`, `kind`, `order` | `media-uploaded`, `media-removed` | P3 |
| `Author` / `Chef` | Catálogo | `author_id`, `name`, `bio`, `user_id` | `author-created`, `recipe-published` | P3 |
| `RecipeCollection` | Catálogo | `collection_id`, `name`, `recipe_ids[]`, `price` | `collection-published`, `collection-purchased` | P3 |
| `MealPlan` / `ShoppingList` | Planificación | `user_id`, `week`, `entries[]`, `items[]` | `meal-plan-created`, `shopping-list-generated` | P3 |
| `AuditLog` | Operación | `actor_id`, `action`, `entity`, `before`, `after`, `when` | consume todos los eventos | P3 |
| `Report` / `SupportTicket` | Operación | `report_id`, `user_id`, `target`, `reason`, `status` | `report-created`, `report-resolved` | P3 |

### 11.2 Ampliaciones P1 (bajo coste, alto valor)

**`Favorite`.** Permite guardar recetas sin comprarlas. Base `favorite` con `_id` compuesto por usuario y receta para evitar duplicados. Al publicar `favorite-added` o `favorite-removed`, un consumidor puede mantener un contador en `recipe` y otro puede alimentar recomendaciones. Endpoints: `POST /favorites/{recipe_id}`, `DELETE /favorites/{recipe_id}` y `GET /favorites`.

**`Review` / `Rating`.** Solo debería permitirse una reseña por usuario y receta, y opcionalmente exigir que exista una compra (`order_id` o el `payment` actual). Campos: `rating` de 1 a 5, `title`, `comment`, `status` (`pending`, `approved`, `rejected`) y `moderated_by`. Eventos: `review-created` actualiza la media y el número de reseñas en `recipe`; `review-moderated` decide si se publica. La media agregada evita que el catálogo tenga que leer todas las reseñas.

**`Category` y `Tag`.** Hoy `category` es texto libre y `tags` son cadenas dentro de `Recipe`. Normalizarlos permite filtros consistentes, sinónimos y conteos. `Category` puede ser jerárquica con `parent_id`; `Tag` puede absorber sinónimos y aliases. La receta guardaría referencias (`category_id`, `tag_ids`) y un consumidor mantendría el catálogo de solo lectura actualizado.

**`PasswordResetToken`.** Cierra el hueco funcional más visible de la autenticación. Flujo: `POST /forgot-password` publica `password-reset-requested`; el consumidor de correo genera un JWT de un solo uso, guarda su hash y caduca en poco tiempo; `POST /reset-password` valida, cambia el hash bcrypt y publica `password-reset-completed` para invalidar sesiones.

**`Session` / `RefreshToken`.** El JWT actual no se puede revocar. Una entidad de sesión permite logout real, rotación de refresh tokens, detección de reutilización y listado de dispositivos. El access token seguiría siendo JWT corto; el refresh token se guardaría hasheado y asociado a `session_id`.

**`Notification` durable.** Sustituye la `SimpleQueue` en memoria descrita en la sección 5. Cada notificación tendría `status` (`pending`, `sent`, `read`, `failed`), canal (`sse`, `email`), reintentos y fecha de lectura. Eventos: `notification-requested` la persiste, `notification-sent` la marca entregada y `notification-read` la cierra. Con esto las notificaciones sobreviven a reinicios y el SSE puede hacer replay de las no leídas.

### 11.3 Ampliaciones P2 (agregados y consistencia)

**`Cart` / `CartItem` y `Order` / `OrderItem`.** El flujo actual compra una receta por checkout. Un agregado `Order` permitiría varias recetas, totales, moneda e historial. `Cart` sería el estado editable previo; `Order` el estado inmutable que se envía a pago. Eventos: `cart-updated`, `cart-checked-out`, `order-created`, `order-paid`, `order-cancelled`. El `checkout_id` pasaría a pertenecer al pedido, no a una única receta. Es el cambio con mayor impacto en `payment`, `user-recipe` y el simulador.

**`Coupon` / `Promotion`.** Código, tipo (`percent`, `fixed`), valor, vigencia, mínimo de compra, límite global y límite por usuario. El canje debe ser atómico para no superar `max_uses`; en CouchDB conviene un documento de contador con `_rev` o una reserva con estado. Eventos: `coupon-redeemed`, `coupon-exhausted`. Al cancelar un pedido se publicaría `coupon-released`.

**`Invoice` / `Refund`.** El pago actual no tiene comprobante ni devolución. `Invoice` guardaría número, importe, impuestos y estado; `Refund` referenciaría el pago original, el motivo y el importe devuelto. Eventos: `invoice-issued`, `refund-requested`, `refund-completed`. Un `refund-completed` debería revertir el acceso a la receta mediante `purchase-status-changed`, reutilizando el consumidor existente.

**`IdempotencyKey`.** Necesaria para `buy-recipe`, `payment-webhook` y futuros endpoints de pedido. Guarda la clave enviada por el cliente, el hash del cuerpo, el usuario, la respuesta y una expiración. Si llega una petición repetida con la misma clave y cuerpo, se devuelve la respuesta original; si el cuerpo cambia, se responde conflicto. Evita cobros y altas duplicadas.

**`OutboxEvent`.** Resuelve el doble escritura entre CouchDB y RabbitMQ: primero se guarda el evento en la misma operación lógica que el dato de negocio y un publicador lo envía después, con reintentos. Campos: `event_id`, `aggregate_id`, `event_name`, `payload`, `status` (`pending`, `published`, `failed`), `created_at`, `published_at` y `retries`. Es la mejora de consistencia más importante antes de escalar el PoC.

### 11.4 Ampliaciones P3 (contextos nuevos)

**`Subscription` / `Plan`.** Cambia el modelo de venta de recetas sueltas a acceso recurrente. `Plan` define periodicidad, precio y colecciones incluidas; `Subscription` guarda estado, periodo y fecha de próximo cobro. Eventos: `subscription-started`, `subscription-renewed`, `subscription-cancelled`, `subscription-expired`. La comprobación de acceso deja de mirar solo `user-recipe` y consulta también la suscripción activa.

**`Ingredient` / `RecipeIngredient`.** Normaliza ingredientes, unidades, alérgenos y nutrición. Habilita filtros dietéticos, listas de la compra y cálculo de costes. La receta mantendría una lista de referencias con cantidad y unidad; un consumidor recalcularía alérgenos y valores nutricionales.

**`RecipeMedia`.** Metadatos de imágenes o vídeos: `recipe_id`, URL, tipo, orden y texto alternativo. El almacenamiento real podría ser un objeto S3-compatible; CouchDB solo guardaría la referencia.

**`Author` / `Chef`.** Separa quién crea la receta del usuario comprador. Campos: nombre, biografía, usuario asociado y estado. Eventos: `author-created`, `recipe-published`. Permite perfiles públicos y atribución.

**`RecipeCollection`.** Agrupa recetas en packs o menús con un precio conjunto. Es un paso intermedio entre la receta individual y la suscripción.

**`MealPlan` / `ShoppingList`.** Planificación semanal que referencia recetas y genera una lista de la compra agregando ingredientes. Eventos: `meal-plan-created`, `shopping-list-generated`. Depende de `Ingredient` y de `RecipeIngredient`.

**`AuditLog`.** Entidad de solo lectura alimentada por un consumidor que escuche todos los exchanges. Guarda actor, acción, entidad, estado anterior y posterior. Es útil para depurar el propio modelo de eventos y para cumplimiento.

**`Report` / `SupportTicket`.** Permite denunciar recetas o reseñas y abrir incidencias. Estados: `open`, `in_review`, `resolved`, `dismissed`. Eventos: `report-created`, `report-resolved`.

### 11.5 Orden de implementación sugerido

1. **Semana 1:** `Favorite`, `Review`, `Category`/`Tag`, `PasswordResetToken`.
2. **Semana 2:** `Session`/`RefreshToken`, `Notification` durable, `IdempotencyKey`.
3. **Semana 3:** `OutboxEvent`, `Order`/`Cart`, `Coupon`.
4. **Después:** `Invoice`/`Refund`, `Subscription`, `Ingredient`, `MealPlan`.

Cada entidad debería seguir el patrón ya existente: esquema Pydantic en `schemas.py`, base lógica propia, servicio con una única responsabilidad y, si el efecto cruza contextos, un exchange `fanout` con su consumidor. Las entidades de plataforma (`IdempotencyKey`, `OutboxEvent`, `AuditLog`) no pertenecen a un contexto de negocio y conviene agruparlas en un módulo transversal.
