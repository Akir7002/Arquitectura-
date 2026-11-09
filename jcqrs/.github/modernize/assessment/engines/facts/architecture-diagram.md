# Architecture Diagram

Este documento describe la arquitectura que existe actualmente en `projectdev`. La aplicación es una API REST monolítica basada en Spring Boot que aplica un mediador para enrutar comandos y consultas CQRS hacia sus handlers. La persistencia todavía no está implementada.

## Application Architecture

<!-- mermaid-checked: no \n, no em-dash/en-dash, no {} in labels, subgraphs are id["label"], arrows are -->|"label"|, all subgraphs closed by end, ids unique -->
~~~mermaid
flowchart TD
    subgraph ClientLayer["Cliente"]
        HttpClient["Cliente HTTP"]
    end
    subgraph AppLayer["Aplicacion - Spring Boot 3.5.3"]
        RestApi["ClientesController REST"]
        Mediator["Mediator CQRS"]
        Commands["Command handlers"]
        Queries["Query handlers"]
        Contracts["Requests y Responses"]
    end
    subgraph RuntimeLayer["Runtime"]
        Spring["Spring ApplicationContext"]
        Tomcat["Tomcat embebido"]
        Config["application.properties"]
    end
    subgraph StorageLayer["Persistencia actual"]
        Memory["Datos en memoria"]
        Console["Salida de consola"]
    end
    subgraph LibraryLayer["Biblioteca reutilizable"]
        JcqrsLib["projectlib JCQRS"]
    end

    HttpClient -->|"HTTP en puerto 9898"| Tomcat
    Tomcat -->|"entrega solicitudes"| RestApi
    RestApi -->|"crea request"| Contracts
    RestApi -->|"envia request"| Mediator
    Mediator -->|"busca beans"| Spring
    Mediator -->|"despacha por tipo"| Commands
    Mediator -->|"despacha por tipo"| Queries
    Commands -->|"procesa comandos"| Contracts
    Queries -->|"construye respuestas"| Memory
    Commands -->|"registra request"| Console
    Config -->|"configura runtime"| Spring
    JcqrsLib -.->|"define contratos CQRS"| Mediator
~~~

### Technology Stack Summary

| Capa | Tecnología | Versión | Propósito |
|---|---|---:|---|
| Lenguaje | Java | 17 | Código de la aplicación y la biblioteca |
| Framework | Spring Boot | 3.5.3 | Arranque, configuración y ciclo de vida |
| API | Spring Web MVC | Incluida en Boot 3.5.3 | Controlador REST y serialización JSON |
| Servidor | Tomcat embebido | Gestionada por Spring Boot | Atención HTTP |
| Patrón | CQRS + Mediator | Implementación propia | Separar comandos, consultas y despacho |
| Construcción | Maven Wrapper | Proyecto Maven | Compilación, pruebas y empaquetado |
| Biblioteca | JCQRS | 1.0.3 | Interfaces y mediador reutilizables |
| Pruebas | Spring Boot Test + JUnit | Gestionada por Boot | Verificación de carga del contexto |

### Data Storage & External Services

La aplicación no usa una base de datos: `InMemoryStore` mantiene productos y pedidos mientras vive el proceso. Los pedidos validan clientes y productos, copian el precio vigente a sus líneas y calculan el total; al reiniciar se pierde el estado. No se observan caché, colas, APIs externas, autenticación ni servicios de mensajería.

### Key Architectural Decisions

- El `ClientesController` delega todas las operaciones al `Mediator`, evitando seleccionar handlers directamente.
- `Mediator` descubre beans `IRequestHandler` mediante `ApplicationContext` y elige el handler cuyo `getRequestType()` acepta el request.
- La separación CQRS es estructural y todas las entidades se enrutan mediante `Mediator`, con un almacén efímero compartido para integrar productos y pedidos.

## Component Relationships

<!-- mermaid-checked: no \n, no em-dash/en-dash, no {} in labels, subgraphs are id["label"], arrows are -->|"label"|, all subgraphs closed by end, ids unique -->
~~~mermaid
flowchart LR
    subgraph cPresentation["Presentation"]
        cController["ClientesController"]
        cCatalogController["ProductosController"]
        cOrderController["PedidosController"]
        cEndpoints["GET POST PUT DELETE"]
    end
    subgraph cBusiness["Business Logic"]
        cMediator["Mediator"]
        cCommandHandlers["Command handlers"]
        cQueryHandlers["Query handlers"]
    end
    subgraph cContracts["Contracts"]
        cRequests["Clientes Productos Pedidos requests"]
        cResponse["Clientes Producto Pedido responses"]
        cInterfaces["IRequest and IRequestHandler"]
    end
    subgraph cInfrastructure["Infrastructure"]
        cContext["ApplicationContext"]
        cAlias["RequestHandlerAliasConfig"]
        cTomcat["Embedded Tomcat"]
    end
    subgraph     cStorage["In memory storage"]
    cStore["InMemoryStore"]
    end

    cTomcat -->|"receives HTTP"| cController
    cEndpoints -->|"maps routes"| cController
    cController -->|"injects and calls"| cMediator
    cCatalogController -->|"injects and calls"| cMediator
    cOrderController -->|"injects and calls"| cMediator
    cController -->|"creates requests"| cRequests
    cMediator -->|"resolves handlers"| cContext
    cMediator -->|"checks canHandle"| cInterfaces
    cMediator -->|"dispatches commands"| cCommandHandlers
    cMediator -->|"dispatches queries"| cQueryHandlers
    cCommandHandlers -->|"implements"| cInterfaces
    cQueryHandlers -->|"implements"| cInterfaces
    cQueryHandlers -->|"reads data"| cStore
    cCommandHandlers -->|"writes data"| cStore
    cStore -.->|"orders validate products"| cResponse
    cAlias -.->|"registers aliases"| cContext
    cQueryHandlers -->|"returns DTO"| cResponse
    cController -->|"serializes response"| cResponse
~~~

### Component Inventory

| Componente | Capa | Tipo | Responsabilidad |
|---|---|---|---|
| `ClientesController` | Presentation | `@RestController` | Expone `/clientes`, convierte HTTP a requests y respuestas |
| `ProductosController` | Presentation | `@RestController` | Expone el CRUD de productos y delega al mediador |
| `PedidosController` | Presentation | `@RestController` | Expone consultas y alta/baja de pedidos |
| `Mediator` | Business Logic | `@Component` | Busca el handler compatible y ejecuta `handle` |
| `ClientesAddHandler` | Business Logic | `@Service` command | Simula el alta y devuelve `1` o `0` |
| `ClientesUpdateHandler` | Business Logic | `@Service` command | Simula la actualización y devuelve `1` o `0` |
| `ClientesDeleteHandler` | Business Logic | `@Service` command | Simula el borrado y devuelve `1` o `0` |
| `ClientesAllHandler` | Business Logic | `@Service` query | Construye y devuelve tres clientes |
| `ClientesByIdHandler` | Business Logic | `@Service` query | Busca un cliente en la lista fija |
| `Productos*Handler` | Business Logic | `@Service` query y command | Gestiona el catálogo y valida SKU, nombre y precio |
| `Pedidos*Handler` | Business Logic | `@Service` query y command | Valida cliente y productos, compone líneas y calcula totales |
| `InMemoryStore` | Infrastructure | `@Component` | Comparte productos y pedidos durante la ejecución |
| `IRequest` | Contracts | Interface | Marca un request y su tipo de respuesta |
| `IRequestHandler` | Contracts | Interface | Define `handle`, `getRequestType` y `canHandle` |
| `Clientes*Request` | Contracts | DTO de entrada | Transporta datos de cada operación |
| `ClientesResponse` | Contracts | DTO de salida | Representa los datos de un cliente |
| `ApplicationContext` | Infrastructure | Spring container | Mantiene y entrega los beans handler |
| `RequestHandlerAliasConfig` | Infrastructure | `@Configuration` | Intenta registrar aliases para handlers |
| `InMemoryStore` | Current storage | Estado efímero | Datos de productos y pedidos sin persistencia |
