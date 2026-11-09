# Guía de arranque y sustentación del flujo

`Fecha: 04-11-2026`

Esta guía responde tres preguntas concretas:

1. Cómo se inicia la API normalmente.
2. Cómo comprobar que está funcionando.
3. Cómo explicar y defender el flujo del proyecto frente a otra persona.

## 1. Requisitos

| Requisito | Detalle |
|---|---|
| JDK | Java 17 (el `pom.xml` declara `<java.version>17</java.version>`) |
| Maven | No hace falta instalarlo: el proyecto trae el wrapper `mvnw` / `mvnw.cmd` |
| Puerto | `9898` libre |
| Base de datos | Ninguna. La demo funciona en memoria |
| Sistema | Los ejemplos están pensados para Windows, con notas para Linux/macOS |

Comprobación rápida:

```powershell
java -version
```

Debe responder con una versión `17.x`. Si el comando no existe, hay que instalar un JDK 17 y configurar `JAVA_HOME`.

## 2. Cómo iniciar la API

### Opción A: desde la terminal (recomendada para demostrar)

Hay que ubicarse **dentro de `projectdev`**, no en la raíz del repositorio:

```powershell
cd C:\Users\maria\Documents\GitHub\jcqrs\projectdev
```

Luego, según la terminal:

| Terminal | Comando |
|---|---|
| PowerShell | `.\mvnw.cmd spring-boot:run` |
| CMD | `mvnw.cmd spring-boot:run` |
| Git Bash | `./mvnw spring-boot:run` |
| Linux / macOS | `./mvnw spring-boot:run` |

La primera ejecución descarga Maven 3.9.11 y las dependencias de Spring Boot, por lo que puede tardar varios minutos. Las siguientes son mucho más rápidas.

La aplicación está lista cuando aparece un log similar a este:

```text
Tomcat started on port 9898 (http) with context path ''
Started JcqrsApplication in X.XXX seconds
```

No hay que cerrar esa terminal: mientras esté abierta, la API está corriendo. Para detenerla se usa `Ctrl + C`.

### Opción B: desde el IDE

**IntelliJ IDEA**

1. `File > Open` y seleccionar `projectdev/pom.xml` (abrir como proyecto Maven).
2. Verificar que el SDK del proyecto sea JDK 17.
3. Abrir `JcqrsApplication.java`.
4. Ejecutar el método `main` con el botón Run.

**Eclipse**

1. `File > Import > Maven > Existing Maven Projects`.
2. Seleccionar la carpeta `projectdev`.
3. Clic derecho sobre `JcqrsApplication.java > Run As > Java Application`.

**VS Code**

1. Instalar el Extension Pack for Java.
2. Abrir la carpeta `projectdev`.
3. Ejecutar `JcqrsApplication` desde el panel de ejecución.

### Opción C: compilar y ejecutar el JAR

```powershell
cd C:\Users\maria\Documents\GitHub\jcqrs\projectdev
.\mvnw.cmd clean package
java -jar target\jcqrs-0.0.1-SNAPSHOT.jar
```

El resultado del build queda en `projectdev/target/`. Esta opción es útil para demostrar que la aplicación se empaqueta y se ejecuta fuera del IDE.

### Verificación inmediata

Abrir en el navegador:

```text
http://localhost:9898/clientes
```

Si devuelve un JSON con tres clientes, la API está operativa.

## 3. Pruebas rápidas de la API

### 3.1. Endpoints disponibles

| Método | Endpoint | Request | Respuesta esperada |
|---|---|---|---|
| `GET` | `/clientes` | `ClientesAllRequest` | `200` con los tres clientes fijos |
| `GET` | `/clientes/{id}` | `ClientesByIdRequest` | `200` con el cliente o `404` si no existe |
| `POST` | `/clientes/add` | `ClientesAddRequest` | `201` con el cuerpo `1` |
| `PUT` | `/clientes/update` | `ClientesUpdateRequest` | `201` con el cuerpo `1` |
| `DELETE` | `/clientes/delete/{id}` | `ClientesDeleteRequest` | `204` |

Los comandos devuelven `1` cuando simulan éxito y `0` cuando simulan error. El controlador traduce `0` a `400`.

### 3.2. Con PowerShell

```powershell
# Listar
Invoke-RestMethod http://localhost:9898/clientes | ConvertTo-Json

# Obtener uno
Invoke-RestMethod http://localhost:9898/clientes/2 | ConvertTo-Json

# Alta simulada
$body = @{
  razon     = "ACME SA"
  direccion = "Av. Siempre Viva 742"
  email     = "contacto@acme.com"
  movil     = "11-5555-1234"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri http://localhost:9898/clientes/add `
  -ContentType "application/json" -Body $body

# Actualización simulada
$bodyUpdate = @{
  id        = 2
  razon     = "GRUPO TEXTIL SA"
  direccion = "Rosario 7788"
  email     = "info@grupo-textil.com.ar"
  movil     = "11-3344-9911"
} | ConvertTo-Json

Invoke-RestMethod -Method Put -Uri http://localhost:9898/clientes/update `
  -ContentType "application/json" -Body $bodyUpdate

# Baja simulada
Invoke-RestMethod -Method Delete -Uri http://localhost:9898/clientes/delete/2
```

### 3.3. Con curl

```bash
curl -i http://localhost:9898/clientes
curl -i http://localhost:9898/clientes/2
curl -i http://localhost:9898/clientes/99

curl -i -X POST http://localhost:9898/clientes/add \
  -H "Content-Type: application/json" \
  -d '{"razon":"ACME SA","direccion":"Av. Siempre Viva 742","email":"contacto@acme.com","movil":"11-5555-1234"}'

curl -i -X PUT http://localhost:9898/clientes/update \
  -H "Content-Type: application/json" \
  -d '{"id":2,"razon":"GRUPO TEXTIL SA","direccion":"Rosario 7788","email":"info@grupo-textil.com.ar","movil":"11-3344-9911"}'

curl -i -X DELETE http://localhost:9898/clientes/delete/2
```

### 3.4. Qué demuestra cada prueba

- `GET /clientes` demuestra el **lado de lectura**: no modifica nada y devuelve un DTO.
- `GET /clientes/99` demuestra el **manejo de un caso no encontrado**: el handler devuelve `null` y el controlador responde `404`.
- `POST`, `PUT` y `DELETE` demuestran el **lado de escritura**: el controlador crea un request de comando y el Mediator lo despacha.
- Después de un `POST`, un nuevo `GET /clientes` sigue mostrando los mismos tres clientes. Eso no es un error de la prueba: es la prueba de que la demo **no persiste**. Los comandos solo simulan la operación.

## 4. Sustentación del flujo del proyecto

### 4.1. Idea central para explicar

> El controlador no contiene lógica de negocio. Solo transforma una petición HTTP en un objeto `Request` y se lo entrega al `Mediator`. El `Mediator` busca el `Handler` que sabe procesar ese tipo de request y lo ejecuta. El `Handler` devuelve un `Response`, y el controlador lo traduce a una respuesta HTTP.

Esa frase resume el proyecto y demuestra que se entiende la separación de responsabilidades.

### 4.2. Diagrama del flujo

```text
Cliente HTTP
    |
    v
Tomcat embebido :9898
    |
    v
ClientesController                 (adaptador HTTP)
    |
    v
Request (Command o Query)          (contrato de entrada)
    |
    v
Mediator.send(request)             (despachador)
    |
    v
ApplicationContext.getBeansOfType(IRequestHandler)
    |
    v
canHandle(request) == true         (selección por tipo)
    |
    v
Handler.handle(request)            (caso de uso)
    |
    v
Response                           (DTO de salida)
    |
    v
ResponseEntity                     (traducción a HTTP)
```

### 4.3. Recorrido paso a paso de `GET /clientes/2`

Este es el ejemplo más claro para explicar en una exposición:

1. El navegador o `curl` llama a `GET http://localhost:9898/clientes/2`.
2. Tomcat recibe la petición y Spring la enruta a `ClientesController.getById(2)`.
3. El controlador crea `new ClientesByIdRequest(2)`.
4. Llama a `_mediator.send(request)`.
5. `Mediator` pide al `ApplicationContext` todos los beans que implementan `IRequestHandler`.
6. Recorre esos handlers y ejecuta `canHandle(request)`.
7. `canHandle` compara el tipo del request con lo que devuelve `getRequestType()`. Solo `ClientesByIdHandler` declara `ClientesByIdRequest.class`.
8. El Mediator ejecuta `ClientesByIdHandler.handle(request)`.
9. El handler arma la lista fija de clientes, filtra por el id recibido y devuelve un `ClientesResponse`.
10. Si el id no existe, la búsqueda falla, el `catch` devuelve `null` y el controlador responde `404`.
11. Si existe, el controlador responde `200` con el JSON del cliente.

La misma secuencia se repite para todos los endpoints; solo cambian el request y el handler.

### 4.4. Por qué esto es CQRS en el código

| Lado | Paquete | Qué hace | Ejemplos |
|---|---|---|---|
| Consultas | `application/Query` | Solo lee y devuelve DTOs | `ClientesAllHandler`, `ClientesByIdHandler` |
| Comandos | `application/Command` | Representa una intención de cambio | `ClientesAddHandler`, `ClientesUpdateHandler`, `ClientesDeleteHandler` |
| Contratos | `application/Request` | Define la forma de la entrada | `ClientesAddRequest`, `ClientesByIdRequest` |
| Salida | `application/Response` | Define la forma de la salida | `ClientesResponse` |
| Infraestructura | `cqrs` | Mediator, interfaces y alias | `Mediator`, `IRequest`, `IRequestHandler` |

Puntos importantes para mencionar:

- **`IRequest<TResponse>`** es el contrato base de toda solicitud. El genérico indica qué tipo de respuesta produce.
- **`IRequestHandler<TRequest, TResponse>`** es el contrato de los casos de uso. Tiene `handle`, `getRequestType` y `canHandle`.
- **`Mediator`** no conoce ningún handler concreto: los descubre por tipo en el contexto de Spring.
- **`RequestHandlerAliasConfig`** registra alias predecibles para los beans. No participa en el despacho; es una comodidad de infraestructura.
- **`ClientesController`** es un adaptador: no decide reglas de negocio ni accede a datos.

### 4.5. Comandos y consultas: la diferencia concreta

Una consulta se puede repetir sin efectos secundarios:

```text
GET /clientes -> devuelve datos, no cambia nada
```

Un comando expresa una intención de cambio:

```text
POST   /clientes/add
PUT    /clientes/update
DELETE /clientes/delete/{id}
```

En este proyecto la separación es **lógica**, no física: no hay dos bases de datos ni dos servicios. Esa es la forma correcta y honesta de describirlo. La estructura ya está preparada para que, más adelante, los handlers de escritura usen un repositorio y los de lectura usen otro.

### 4.6. Guion corto para una demostración (5 a 7 minutos)

1. **Mostrar la estructura** de `projectdev/src/main/java/com/jcqrslib/jcqrs`: `controller`, `application/Command`, `application/Query`, `application/Request`, `application/Response` y `cqrs`.
2. **Explicar la regla de nombres**: `XXXAllRequest`, `XXXByIdRequest`, `XXXAddRequest`, etc., y un handler por request.
3. **Arrancar la API** con `.\mvnw.cmd spring-boot:run` y señalar el log `Tomcat started on port 9898`.
4. **Abrir** `http://localhost:9898/` para ver el panel web.
5. **Abrir** `http://localhost:9898/swagger-ui.html` para explorar y probar la API.
6. Las rutas `/clientes`, `/productos` y `/pedidos` siguen disponibles como respuestas JSON.
5. **Probar** `GET /clientes/2` y luego `GET /clientes/99` para mostrar el `200` y el `404`.
6. **Ejecutar un POST** y mostrar el `201` con `1`.
7. **Volver a listar** y explicar que los datos no cambiaron porque la demo no persiste.
8. **Abrir `Mediator.java`** y mostrar las tres líneas clave: obtener handlers, preguntar `canHandle` y ejecutar `handle`.
9. **Abrir un handler** y mostrar que implementa el contrato y declara su request.
10. **Cerrar con las limitaciones y el roadmap**: persistencia, validación, errores globales, separación real de almacenes y entidades nuevas.

### 4.7. Preguntas probables y respuestas

**¿Esto es CQRS de verdad?**
Es CQRS a nivel de estructura: comandos y consultas están separados en paquetes, contratos y handlers distintos. Todavía no hay separación física de almacenes; eso queda como evolución.

**¿Para qué sirve el Mediator si podría llamar al handler directamente?**
Para desacoplar el controlador de los casos de uso. El controlador solo conoce `Request` y `Mediator`; agregar un caso de uso nuevo no obliga a modificarlo.

**¿Qué pasa si ningún handler puede procesar el request?**
El Mediator lanza `RuntimeException` con el nombre del request. Hoy el controlador no la captura, así que se traduce en un error `500`.

**¿Qué pasa si dos handlers declaran el mismo request?**
Se ejecuta el primero que aparezca en el mapa de beans. Es una limitación de diseño a tener en cuenta; la convención es un handler por request.

**¿Dónde está la base de datos?**
No hay. Los handlers generan datos en memoria. La explicación está en `FLUJO_PROYECTO.md`, sección 5.

**¿Por qué los comandos devuelven `Integer`?**
Es una simplificación de la demo: `1` significa éxito y `0`, error. En un caso real convendría devolver el id generado o un objeto de resultado.

**¿Por qué hay dos copias de las clases CQRS?**
`projectdev` tiene su copia local en `com.jcqrslib.jcqrs.cqrs`. `projectlib` contiene la versión reutilizable y publicable en `com.jqrslib.cqrs`. La demo no depende del JAR de la librería; por eso los paquetes y nombres no coinciden exactamente.

**¿Se usa la parte asíncrona?**
La librería de `projectlib` incluye `IAsyncRequest` y `sendAsync`, pero la aplicación demo no los usa. Es una capacidad disponible, no un flujo activo.

**¿Hay seguridad?**
No. No hay autenticación ni autorización. Es una de las mejoras pendientes.

### 4.8. Limitaciones que conviene reconocer

Reconocerlas suma credibilidad; ocultarlas resta:

- No hay persistencia: los datos se regeneran en cada consulta.
- Los comandos no modifican el estado que leen las consultas.
- No hay validación de payloads ni manejo global de errores.
- Los `catch (Exception)` devuelven `null` o `0` y ocultan la causa real.
- No hay paginación.
- Los identificadores mezclan `int` y `long` (`ClientesByIdRequest` usa `int`; `ClientesUpdateRequest` usa `long`).
- No hay autenticación, autorización, caché, colas ni réplica de lectura.
- La separación de almacenes es conceptual; no está implementada.

### 4.9. Cómo cerrar la presentación

> La demo muestra la columna vertebral de CQRS: el controlador delega, el Mediator despacha y cada caso de uso tiene su propio contrato. Lo que falta es la infraestructura de persistencia y la separación física de lectura y escritura. El siguiente paso natural es incorporar `Categorias` y `Productos`, y después `Pedidos`, para demostrar relaciones y agregados.

## 5. Problemas comunes al iniciar

| Síntoma | Causa probable | Solución |
|---|---|---|
| `java` no se reconoce | JDK no instalado o fuera del `PATH` | Instalar JDK 17 y configurar `JAVA_HOME` |
| `Port 9898 was already in use` | Otra instancia sigue corriendo | Cerrar la otra terminal o cambiar `server.port` en `application.properties` |
| La primera ejecución tarda mucho | Maven descarga dependencias | Esperar; las siguientes son más rápidas |
| `404` en `/clientes` | Se arrancó otro proyecto o el puerto es distinto | Verificar el log y la URL `http://localhost:9898` |
| El comando `mvnw` no se reconoce | Se usó el nombre incorrecto según la terminal | PowerShell: `.\mvnw.cmd`; Git Bash: `./mvnw` |
| No aparece el log de Tomcat | El build falló | Leer el error de Maven antes de asumir que la API está arriba |

## 6. Referencia rápida

```powershell
# Ubicación
cd C:\Users\maria\Documents\GitHub\jcqrs\projectdev

# Arranque
.\mvnw.cmd spring-boot:run

# Build
.\mvnw.cmd clean package

# Ejecución del JAR
java -jar target\jcqrs-0.0.1-SNAPSHOT.jar

# API
http://localhost:9898/clientes
```

Para el detalle de cada endpoint y del flujo interno, ver [`FLUJO_PROYECTO.md`](./FLUJO_PROYECTO.md). Para las próximas entidades, ver [`ENTIDADES_PROPUESTAS.md`](./ENTIDADES_PROPUESTAS.md).
