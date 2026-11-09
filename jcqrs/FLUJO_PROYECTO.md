# Flujo del proyecto JCQRS

## 1. Qué contiene el repositorio

El repositorio tiene dos partes:

- [`projectdev`](./projectdev): aplicación demostrativa Spring Boot que expone la API REST de clientes.
- [`projectlib/jcqrslib`](./projectlib/jcqrslib): biblioteca reutilizable con los contratos CQRS y el `Mediator`.

El archivo [`analisis.drawio`](./analisis.drawio) se tomó como referencia visual. El diagrama específico de este proyecto está en [`analisis-jcqrs.drawio`](./analisis-jcqrs.drawio), con páginas de vista general, capas, componentes y flujo de endpoints.

Las entidades de negocio que se pueden incorporar más adelante, con campos, endpoints, reglas y orden de implementación, se detallan en [`ENTIDADES_PROPUESTAS.md`](./ENTIDADES_PROPUESTAS.md).

La implementación ampliada y su diagrama actualizado están en [`analisis-jcqrs nuevas entidades.drawio`](./analisis-jcqrs%20nuevas%20entidades.drawio). Incluyen los flujos de `Productos` y `Pedidos` integrados al mismo `Mediator`.

## 2. Arranque de la aplicación

1. Maven carga [`projectdev/pom.xml`](./projectdev/pom.xml).
2. Spring Boot inicia desde `JcqrsApplication`.
3. El escaneo de componentes registra `ClientesController`, `Mediator`, `RequestHandlerAliasConfig` y los seis handlers como beans.
4. Tomcat embebido atiende en el puerto `9898`, definido en [`application.properties`](./projectdev/src/main/resources/application.properties).

No se necesita una base de datos para iniciar la aplicación. No hay un driver JDBC, JPA, Spring Data, migraciones ni una URL de conexión configurada.

La guía completa de arranque (terminal, IDE y JAR), las pruebas de humo y el guion para explicar el flujo están en [`GUIA_ARRANQUE_Y_FLUJO.md`](./GUIA_ARRANQUE_Y_FLUJO.md).

## 3. Flujo común de una solicitud

```text
Cliente HTTP
  -> Tomcat embebido:9898
  -> ClientesController
  -> request CQRS
  -> Mediator.send(request)
  -> ApplicationContext.getBeansOfType(IRequestHandler.class)
  -> handler compatible mediante canHandle()
  -> handle(request)
  -> ResponseEntity HTTP
```

`IRequestHandler.canHandle` compara el tipo concreto del request con el valor que devuelve `getRequestType()`. Si ningún handler coincide, `Mediator` lanza una excepción de ejecución.

### Flujo integrado de Productos y Pedidos

- `ProductosController` traduce las operaciones REST a `Productos*Request`; sus handlers leen y escriben en `InMemoryStore`.
- `PedidosController` crea y consulta pedidos mediante `Pedidos*Request`.
- `PedidosAddHandler` valida que exista el cliente, que cada producto esté activo y que la cantidad sea positiva. Copia el precio vigente a cada línea y calcula el total.
- Un producto utilizado por un pedido no se elimina, y un pedido solo puede eliminarse mientras está en estado `BORRADOR`.
- El almacén sigue siendo de demostración: los cambios viven mientras el proceso Spring Boot está activo y se pierden al reiniciar.

| Operación | Endpoint | Request | Handler |
|---|---|---|---|
| Listar productos | `GET /productos` | `ProductosAllRequest` | `ProductosAllHandler` |
| Obtener producto | `GET /productos/{id}` | `ProductosByIdRequest` | `ProductosByIdHandler` |
| Crear producto | `POST /productos/add` | `ProductosAddRequest` | `ProductosAddHandler` |
| Actualizar producto | `PUT /productos/update` | `ProductosUpdateRequest` | `ProductosUpdateHandler` |
| Eliminar producto | `DELETE /productos/delete/{id}` | `ProductosDeleteRequest` | `ProductosDeleteHandler` |
| Listar pedidos | `GET /pedidos` | `PedidosAllRequest` | `PedidosAllHandler` |
| Obtener pedido | `GET /pedidos/{id}` | `PedidosByIdRequest` | `PedidosByIdHandler` |
| Crear pedido | `POST /pedidos/add` | `PedidosAddRequest` | `PedidosAddHandler` |
| Eliminar borrador | `DELETE /pedidos/delete/{id}` | `PedidosDeleteRequest` | `PedidosDeleteHandler` |

## 4. Flujos por endpoint

| Operación | Endpoint | Request | Handler | Comportamiento actual |
|---|---|---|---|---|
| Listar | `GET /clientes` | `ClientesAllRequest` | `ClientesAllHandler` | Crea una lista fija de tres clientes y devuelve `200`; ante `null`, devuelve `404` |
| Obtener | `GET /clientes/{id}` | `ClientesByIdRequest` | `ClientesByIdHandler` | Filtra la lista fija; si no encuentra el id, la excepción se convierte en `null` y devuelve `404` |
| Alta | `POST /clientes/add` | `ClientesAddRequest` | `ClientesAddHandler` | Imprime el request y devuelve `1`; no crea datos |
| Baja | `DELETE /clientes/delete/{id}` | `ClientesDeleteRequest` | `ClientesDeleteHandler` | Imprime el request y devuelve `1`; no elimina datos |
| Actualizar | `PUT /clientes/update` | `ClientesUpdateRequest` | `ClientesUpdateHandler` | Imprime el request y devuelve `1`; no modifica datos |

Para comandos, el controlador interpreta `0` como error y responde `400`. En los casos exitosos usa `201` para alta y actualización, y `204` para baja.

## 5. Base de datos y persistencia

### Respuesta directa

**Actualmente no funciona con ninguna base de datos.**

La separación CQRS del proyecto es una estructura de código, no una separación de almacenes. Las consultas regeneran objetos en memoria y los comandos no escriben en ningún almacenamiento. Al reiniciar la aplicación no existe información persistida y, además, los cambios simulados por `POST`, `PUT` o `DELETE` no afectan las respuestas de `GET`.

### Qué haría falta para persistir

Para conectar una base de datos habría que añadir un adaptador de persistencia, por ejemplo repositorios JDBC/JPA, una entidad o modelo de cliente, configuración externa de la URL/credenciales y migraciones. Los handlers deberían delegar en esos repositorios en lugar de crear listas o escribir en consola. La base concreta no está definida por el código actual.

## 6. Reglas y límites observados

- No hay autenticación, autorización, validación explícita de payloads ni manejo global de errores.
- No hay colas, eventos, caché, réplicas de lectura ni base de escritura separada.
- `RequestHandlerAliasConfig` recorre handlers para registrar aliases, pero su método de registro de definiciones no implementa lógica adicional.
- Los `catch (Exception)` de los handlers convierten cualquier error en `0` o `null`, por lo que el controlador solo puede inferir un error genérico.
- La biblioteca `projectlib` define la abstracción; la aplicación `projectdev` aporta los requests, responses, controller y handlers de clientes.

## 7. Archivos principales

| Archivo | Función |
|---|---|
| [`JcqrsApplication.java`](./projectdev/src/main/java/com/jcqrslib/jcqrs/JcqrsApplication.java) | Punto de entrada Spring Boot |
| [`ClientesController.java`](./projectdev/src/main/java/com/jcqrslib/jcqrs/controller/ClientesController.java) | API REST |
| [`Mediator.java`](./projectdev/src/main/java/com/jcqrslib/jcqrs/cqrs/Mediator.java) | Despacho CQRS |
| [`IRequestHandler.java`](./projectdev/src/main/java/com/jcqrslib/jcqrs/cqrs/IRequestHandler.java) | Contrato de handlers |
| [`ClientesAllHandler.java`](./projectdev/src/main/java/com/jcqrslib/jcqrs/application/Query/ClientesAllHandler.java) | Consulta de todos |
| [`ClientesByIdHandler.java`](./projectdev/src/main/java/com/jcqrslib/jcqrs/application/Query/ClientesByIdHandler.java) | Consulta por id |
| [`ClientesAddHandler.java`](./projectdev/src/main/java/com/jcqrslib/jcqrs/application/Command/ClientesAddHandler.java) | Comando de alta simulado |
| [`ClientesUpdateHandler.java`](./projectdev/src/main/java/com/jcqrslib/jcqrs/application/Command/ClientesUpdateHandler.java) | Comando de actualización simulado |
| [`ClientesDeleteHandler.java`](./projectdev/src/main/java/com/jcqrslib/jcqrs/application/Command/ClientesDeleteHandler.java) | Comando de baja simulado |
