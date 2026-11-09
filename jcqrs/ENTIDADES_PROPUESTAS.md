# Entidades adicionales propuestas

`Fecha: 04-11-2026`

Este documento revisa el estado actual del proyecto y propone entidades de negocio que se pueden desarrollar para ampliar el ejemplo de CQRS sin repetir lo que ya hace `Clientes`.

## 1. Diagnóstico del estado actual

- La aplicación `projectdev` tiene una sola entidad de ejemplo: `Clientes`.
- `Clientes` ya cubre el CRUD completo (listar, obtener, alta, baja y actualización) y sirve como plantilla de nombres: `XXXAllRequest`, `XXXByIdRequest`, `XXXAddRequest`, `XXXDeleteRequest`, `XXXUpdateRequest`, `XXXResponse` y sus handlers.
- Los handlers no persisten: las consultas generan datos fijos en memoria y los comandos solo imprimen el request.
- El `Mediator` de `projectlib` soporta despacho síncrono (`send`) y asíncrono (`sendAsync`), pero la aplicación demo solo usa el síncrono.
- No hay validación, manejo global de errores, paginación, autenticación ni separación real entre almacén de lectura y de escritura.

Por lo tanto, las entidades nuevas deberían aportar algo distinto: relaciones, agregados, comandos que no sean un CRUD plano, proyecciones de lectura o soporte técnico para la consistencia eventual.

## 2. Criterios de selección

1. **Aportar un caso nuevo**: no duplicar `Clientes` con otro nombre.
2. **Cubrir relaciones**: 1-N, N-N y composición dentro de un agregado.
3. **Separar lectura y escritura**: que las consultas devuelvan DTOs compuestos y los comandos apliquen reglas de negocio.
4. **Ser incremental**: poder implementarse por fases sin romper la demo existente.
5. **Ser reconocible**: usar un dominio de ventas/inventario fácil de explicar y de probar por API REST.

## 3. Catálogo de entidades candidatas

| Entidad | Rol | Prioridad | Complejidad | Qué aporta al ejemplo |
|---|---|---|---|---|
| `Categorias` | Catálogo | Alta | Baja | Relación 1-N simple y validación de existencia |
| `Productos` | Maestro | Alta | Media | CRUD completo, SKU único, filtros y paginación |
| `Proveedores` | Maestro | Alta | Media | Segundo maestro y relación con productos |
| `Pedidos` | Transaccional | Alta | Alta | Agregado con cabecera y detalle, estados y reglas |
| `DetallePedido` | Detalle | Alta | Media | Composición, cálculos y consistencia del agregado |
| `MovimientosStock` | Inventario | Media | Alta | Comandos de dominio que no son CRUD |
| `Facturas` | Facturación | Media | Alta | Numeración, estados y relación con pedidos |
| `Pagos` | Finanzas | Baja | Media | Aplicación de pagos, saldos y estados |
| `Usuarios` | Seguridad | Media | Media | Entidad transversal para autenticación y roles |
| `Roles` / `Permisos` | Seguridad | Baja | Baja | Relación N-N |
| `Direcciones` | Satélite | Baja | Baja | Composición de cliente y dirección principal |
| `Monedas` | Catálogo | Baja | Baja | Soporte multi-moneda |
| `Impuestos` | Catálogo | Baja | Baja | Cálculo de alícuotas y vigencias |
| `EventosDominio` | Técnica | Media | Media | Trazabilidad y base para un event store |
| `OutboxMessages` | Técnica | Baja | Alta | Consistencia eventual entre escritura y lectura |
| `IdempotencyKeys` | Técnica | Baja | Media | Evitar comandos duplicados |

## 4. Detalle de las entidades principales

### 4.1. Categorías

Catálogo mínimo para clasificar productos.

**Campos sugeridos**

| Campo | Tipo | Regla |
|---|---|---|
| `id` | `int` | Clave primaria |
| `nombre` | `String` | Obligatorio y único |
| `descripcion` | `String` | Opcional |
| `categoriaPadreId` | `Integer` | Opcional, permite jerarquía |
| `activo` | `boolean` | Baja lógica |

**Endpoints**

- `GET /categorias`
- `GET /categorias/{id}`
- `POST /categorias/add`
- `PUT /categorias/update`
- `DELETE /categorias/delete/{id}`

**Artefactos CQRS**

- `CategoriasAllRequest` → `CategoriasAllHandler`
- `CategoriasByIdRequest` → `CategoriasByIdHandler`
- `CategoriasAddRequest` → `CategoriasAddHandler`
- `CategoriasUpdateRequest` → `CategoriasUpdateHandler`
- `CategoriasDeleteRequest` → `CategoriasDeleteHandler`
- `CategoriasResponse`

**Reglas**

- No eliminar una categoría con productos activos.
- No permitir dos categorías con el mismo nombre dentro del mismo padre.
- Evitar ciclos si se implementa la jerarquía.

**Por qué conviene**: es la entidad más simple para validar que el patrón se replica con relaciones y reglas antes de encarar un agregado complejo.

### 4.2. Productos

Entidad central del catálogo y base para pedidos y stock.

**Campos sugeridos**

| Campo | Tipo | Regla |
|---|---|---|
| `id` | `int` | Clave primaria |
| `sku` | `String` | Obligatorio y único |
| `nombre` | `String` | Obligatorio |
| `descripcion` | `String` | Opcional |
| `categoriaId` | `int` | Debe existir |
| `precioVenta` | `BigDecimal` | Mayor que cero |
| `costo` | `BigDecimal` | Mayor o igual que cero |
| `stockMinimo` | `int` | Mayor o igual que cero |
| `activo` | `boolean` | Baja lógica |
| `fechaAlta` | `LocalDateTime` | Generada por el servidor |

**Endpoints**

- `GET /productos?page=0&size=20`
- `GET /productos/{id}`
- `GET /productos/categoria/{categoriaId}`
- `POST /productos/add`
- `PUT /productos/update`
- `DELETE /productos/delete/{id}`
- `PATCH /productos/{id}/activar` y `/desactivar` (opcional)

**Artefactos CQRS**

- Consultas: `ProductosAllRequest`, `ProductosByIdRequest`, `ProductosByCategoriaRequest`.
- Comandos: `ProductosAddRequest`, `ProductosUpdateRequest`, `ProductosDeleteRequest`.
- `ProductosResponse` y, si se pagina, `PaginaResponse<T>` reutilizable.

**Reglas**

- `sku` único (comparación sin distinguir mayúsculas).
- La categoría debe existir y estar activa.
- No eliminar físicamente un producto con movimientos o pedidos; desactivarlo.
- El precio de venta no puede ser menor que el costo sin una autorización explícita (regla opcional).

**Por qué conviene**: replica el CRUD conocido, pero agrega validación cruzada, búsqueda por relación y paginación, tres cosas que `Clientes` no tiene.

### 4.3. Proveedores

Maestro secundario para compras y reposición de stock.

**Campos sugeridos**: `id`, `razonSocial`, `cuit`, `email`, `telefono`, `direccion`, `activo`.

**Endpoints**: los mismos cinco del CRUD, más `GET /proveedores?activo=true`.

**Reglas**

- `cuit` único y validado.
- No eliminar un proveedor con productos asociados.
- El alta y la modificación deben validar el formato de email y teléfono.

**Relación opcional N-N**: `ProductoProveedor` (`productoId`, `proveedorId`, `codigoProveedor`, `precioCompra`). Es un buen ejercicio para una tabla intermedia y para consultas que devuelven datos combinados.

### 4.4. Pedidos y DetallePedido

Es la entidad que mejor muestra la separación entre escritura y lectura.

**Cabecera `Pedidos`**

| Campo | Tipo | Regla |
|---|---|---|
| `id` | `int` | Clave primaria |
| `numero` | `String` | Único, generado por el servidor |
| `clienteId` | `int` | Debe existir |
| `fecha` | `LocalDateTime` | Generada al confirmar |
| `estado` | `enum` | `BORRADOR`, `CONFIRMADO`, `FACTURADO`, `ANULADO` |
| `subtotal` | `BigDecimal` | Calculado |
| `descuento` | `BigDecimal` | Mayor o igual que cero |
| `impuestos` | `BigDecimal` | Calculado |
| `total` | `BigDecimal` | Calculado |
| `monedaId` | `int` | Debe existir |
| `usuarioId` | `int` | Responsable del pedido |

**Detalle `DetallePedido`**

| Campo | Tipo | Regla |
|---|---|---|
| `id` | `int` | Clave primaria |
| `pedidoId` | `int` | Parte del agregado |
| `productoId` | `int` | Debe existir |
| `cantidad` | `int` | Mayor que cero |
| `precioUnitario` | `BigDecimal` | Se copia al momento de agregar |
| `descuento` | `BigDecimal` | Mayor o igual que cero |
| `subtotal` | `BigDecimal` | `cantidad * precioUnitario - descuento` |

**Endpoints**

- `GET /pedidos?estado=CONFIRMADO&page=0&size=20`
- `GET /pedidos/{id}` (cabecera con detalle)
- `GET /pedidos/cliente/{clienteId}`
- `POST /pedidos/add` (crea el pedido en `BORRADOR` con sus líneas)
- `POST /pedidos/{id}/lineas` (agrega línea)
- `DELETE /pedidos/{id}/lineas/{lineaId}` (quita línea)
- `PATCH /pedidos/{id}/confirmar`
- `PATCH /pedidos/{id}/anular`
- `DELETE /pedidos/delete/{id}` (solo si está en `BORRADOR`)

**Artefactos CQRS**

- Consultas: `PedidosAllRequest`, `PedidosByIdRequest`, `PedidosByClienteRequest`, `PedidosByEstadoRequest`.
- Comandos: `PedidosAddRequest`, `PedidosAgregarLineaRequest`, `PedidosQuitarLineaRequest`, `PedidosConfirmarRequest`, `PedidosAnularRequest`, `PedidosDeleteRequest`.
- Respuestas: `PedidoResponse` (cabecera), `PedidoDetalleResponse` (línea) y `PedidoCompletoResponse` (cabecera + líneas).

**Reglas**

- No modificar líneas si el pedido no está en `BORRADOR`.
- Confirmar recalcula totales y reserva stock.
- Anular un pedido confirmado libera el stock reservado.
- El precio unitario se congela al agregar la línea; no se recalcula si cambia el producto.
- El detalle no se modifica por fuera del agregado `Pedido`.

**Por qué conviene**: introduce un agregado real, transiciones de estado, cálculos y la necesidad de coordinar pedidos con stock. Es el mejor candidato para justificar CQRS.

### 4.5. MovimientosStock

No es un CRUD: es un registro de eventos de inventario.

**Campos sugeridos**: `id`, `productoId`, `tipo` (`ENTRADA`, `SALIDA`, `AJUSTE`, `RESERVA`, `LIBERACION`), `cantidad`, `motivo`, `referenciaTipo`, `referenciaId`, `fecha`, `usuarioId`.

**Endpoints**

- `GET /stock/{productoId}` (saldo actual, consulta de lectura)
- `GET /stock/{productoId}/movimientos`
- `POST /stock/entradas`
- `POST /stock/salidas`
- `POST /stock/ajustes`

**Reglas**

- El saldo no se edita directamente: se obtiene de la suma de movimientos o de una proyección `stockActual`.
- Una salida no puede dejar el saldo en negativo (salvo ajuste autorizado).
- Cada movimiento debe referenciar su origen (`PEDIDO`, `COMPRA`, `AJUSTE`).
- Las operaciones son idempotentes por `referenciaTipo` + `referenciaId`.

**Por qué conviene**: demuestra comandos con intención de negocio, idempotencia y una proyección de lectura distinta del modelo de escritura.

### 4.6. Facturas

**Campos sugeridos**: `id`, `numero`, `puntoVenta`, `pedidoId`, `clienteId`, `fecha`, `estado` (`EMITIDA`, `PAGADA`, `ANULADA`), `neto`, `iva`, `total`, `monedaId`.

**Endpoints**

- `GET /facturas`
- `GET /facturas/{id}`
- `GET /facturas/cliente/{clienteId}`
- `POST /facturas/add` (emitir desde un pedido confirmado)
- `PATCH /facturas/{id}/anular`
- `PATCH /facturas/{id}/pagar`

**Reglas**

- Solo se factura un pedido `CONFIRMADO`.
- El número es único por punto de venta y se genera de forma atómica.
- Una factura anulada no admite pagos.
- No se puede modificar una factura emitida; se anula y se emite otra.

### 4.7. Pagos

**Campos sugeridos**: `id`, `facturaId`, `fecha`, `medio` (`EFECTIVO`, `TRANSFERENCIA`, `TARJETA`), `importe`, `referencia`, `estado` (`REGISTRADO`, `APLICADO`, `RECHAZADO`).

**Endpoints**

- `GET /pagos/factura/{facturaId}`
- `POST /pagos/add`
- `PATCH /pagos/{id}/aplicar`
- `PATCH /pagos/{id}/rechazar`

**Reglas**

- La suma de pagos aplicados no puede superar el total de la factura.
- Aplicar el pago actualiza el estado de la factura a `PAGADA` si corresponde.

### 4.8. Usuarios, Roles y Permisos

Entidad transversal necesaria para dejar de tener una API abierta.

**Usuarios**: `id`, `username`, `email`, `passwordHash`, `nombre`, `activo`, `fechaAlta`.

**Roles**: `id`, `nombre`, `descripcion`.

**Permisos**: `id`, `codigo`, `descripcion`.

**Relaciones**: `UsuarioRol` (N-N) y `RolPermiso` (N-N).

**Endpoints**

- `GET /usuarios`, `GET /usuarios/{id}`
- `POST /usuarios/add`
- `PUT /usuarios/update`
- `PATCH /usuarios/{id}/activar` y `/desactivar`
- `PUT /usuarios/{id}/roles`
- `GET /roles`, `POST /roles/add`

**Reglas**

- El `username` y el `email` son únicos.
- Nunca devolver `passwordHash` en un `Response`.
- La baja es lógica.
- La autorización por rol se resuelve en infraestructura (filtro o interceptor), no dentro de cada handler.

### 4.9. Entidades satélite de bajo costo

- **Direcciones**: `id`, `clienteId`, `calle`, `numero`, `piso`, `ciudad`, `provincia`, `codigoPostal`, `pais`, `principal`. Aporta composición y una regla clara: solo una dirección principal por cliente.
- **Monedas**: `id`, `codigoIso`, `nombre`, `simbolo`, `decimales`. Aporta datos de referencia para pedidos y facturas.
- **Impuestos**: `id`, `nombre`, `alicuota`, `vigenciaDesde`, `vigenciaHasta`. Aporta cálculo con vigencias y valores históricos.

### 4.10. Entidades técnicas para CQRS

Estas no son de negocio, pero son las que permiten pasar de una demo en memoria a un CQRS real.

- **`EventosDominio`** (event store): `id`, `aggregateId`, `aggregateType`, `eventType`, `payload`, `version`, `occurredAt`, `usuarioId`. Permite reconstruir estado y auditar cambios.
- **`OutboxMessages`**: `id`, `aggregateId`, `eventType`, `payload`, `status`, `createdAt`, `processedAt`, `retries`. Garantiza que un comando y su evento se guarden en la misma transacción.
- **`IdempotencyKeys`**: `key`, `requestHash`, `response`, `createdAt`. Evita duplicar altas o pagos cuando el cliente reintenta.
- **`Proyecciones` de lectura**: tablas o documentos como `PedidoResumenView`, `StockView` o `ClienteResumenView`, mantenidos por los eventos. Son el equivalente práctico a la base de lectura separada.

## 5. Orden de implementación recomendado

| Fase | Entidades | Objetivo |
|---|---|---|
| 0 | Base técnica | Persistencia, validación, manejo global de errores, paginación |
| 1 | `Categorias` + `Productos` | Replicar el patrón con relación 1-N y reglas |
| 2 | `Proveedores` + `Direcciones` | Maestros secundarios y composición |
| 3 | `Pedidos` + `DetallePedido` + `MovimientosStock` | Agregado, estados y dominio real |
| 4 | `Facturas` + `Pagos` + `Impuestos` + `Monedas` | Procesos transaccionales encadenados |
| 5 | `Usuarios` + `Roles` + `Permisos` | Seguridad transversal |
| 6 | `EventosDominio` + `Outbox` + proyecciones | Consistencia eventual y lectura separada |

La fase 1 es la recomendada para empezar: permite comprobar el scaffolding completo con dos entidades relacionadas y sin la complejidad de un agregado.

## 6. Scaffolding sugerido por entidad

Cada entidad nueva puede seguir la misma estructura que `Clientes`:

```text
Productos
  |__ Command
  |   |__ ProductosAddHandler.java
  |   |__ ProductosUpdateHandler.java
  |   |__ ProductosDeleteHandler.java
  |__ Query
  |   |__ ProductosAllHandler.java
  |   |__ ProductosByIdHandler.java
  |   |__ ProductosByCategoriaHandler.java
  |__ Request
  |   |__ ProductosAllRequest.java
  |   |__ ProductosByIdRequest.java
  |   |__ ProductosByCategoriaRequest.java
  |   |__ ProductosAddRequest.java
  |   |__ ProductosUpdateRequest.java
  |   |__ ProductosDeleteRequest.java
  |__ Response
      |__ ProductosResponse.java
```

Además, por entidad:

- Un `ProductosController` con `@RequestMapping("/productos")`.
- Un handler por cada request; no un handler genérico que resuelva todo el CRUD.
- Un `Response` propio; no reutilizar `ClientesResponse` ni devolver la entidad de persistencia.
- Un repositorio o adaptador de persistencia inyectado en los handlers.

## 7. Reglas de diseño a respetar

1. **Request y Response no son entidades de persistencia.** Son contratos de entrada y salida.
2. **Un request, un handler.** El `Mediator` busca por tipo; un handler que atienda varios comandos rompe la convención.
3. **Los comandos devuelven el identificador o un resultado**, no el objeto completo.
4. **Las consultas devuelven DTOs**, aunque internamente lean de una entidad o de una vista.
5. **Validar en el handler del comando**, no en el controlador, para que la regla se aplique también fuera de HTTP.
6. **No compartir el mismo request entre alta y actualización.** `id` obligatorio en update, ausente en add.
7. **Un agregado se modifica a través de su raíz.** `DetallePedido` se cambia con comandos de `Pedidos`.
8. **Baja lógica antes que borrado físico** cuando existan referencias.
9. **Paginación obligatoria en los listados** que puedan crecer (`Productos`, `Pedidos`, `Facturas`, `MovimientosStock`).
10. **Unificar el tipo de los identificadores.** Hoy `Clientes` mezcla `int` y `long`; conviene elegir `long` o `int` para todas las entidades.
11. **Errores explícitos.** Reemplazar `catch (Exception) { return 0; }` por excepciones de dominio y un `@RestControllerAdvice` que traduzca a códigos HTTP.

## 8. Recomendación final

Si el objetivo es ampliar la demo sin perder claridad, el orden más útil es:

1. `Categorias` y `Productos`, para demostrar relaciones y validaciones.
2. `Pedidos` con `DetallePedido`, para demostrar un agregado y comandos con estados.
3. `MovimientosStock`, para demostrar que CQRS no es solo CRUD.
4. `Usuarios` y `Roles`, para cerrar la API con seguridad.
5. `EventosDominio` y `Outbox`, para explicar la consistencia eventual entre escritura y lectura.

Con esas cinco incorporaciones el repositorio deja de ser un CRUD de clientes y pasa a mostrar los problemas que CQRS realmente resuelve.
