"""
Punto de entrada de la aplicación.

Responsabilidades de este archivo (y solo estas):
1. Crear la instancia de `FastAPI` con metadatos para OpenAPI.
2. Registrar middlewares (CORS, GZip).
3. Registrar manejadores globales de excepciones.
4. Incluir los routers versionados.
5. Definir el ciclo de vida (`lifespan`) y endpoints transversales
   (health check).

Toda la lógica de negocio vive en las capas inferiores (services,
repositories, models) -- este archivo es intencionalmente "delgado".
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.core.config import get_settings
from app.core.exceptions import DomainError
from app.db.base import Base
from app.db.session import engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Ciclo de vida de la aplicación (reemplaza a los deprecados
    `@app.on_event("startup"/"shutdown")`).

    En este ejemplo se crean las tablas automáticamente al arrancar para
    simplificar la puesta en marcha. En un proyecto real de producción,
    el esquema se gestiona con migraciones versionadas (Alembic) y esta
    línea se elimina -- ver README, sección "De este ejemplo a producción".
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield  # <- la aplicación atiende requests durante este punto

    await engine.dispose()


def create_application() -> FastAPI:
    """Application Factory: facilita crear instancias distintas para tests."""
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "API REST de ejemplo con arquitectura en capas (routers -> "
            "services -> repositories -> models), construida con FastAPI "
            "siguiendo las guías oficiales y estándares de la industria "
            "(OWASP API Security Top 10, OAuth2/JWT, 12-Factor App)."
        ),
        lifespan=lifespan,
        # Estandarización de documentación: Swagger UI y ReDoc quedan
        # expuestos automáticamente por FastAPI en /docs y /redoc.
        contact={"name": "Equipo de Plataforma", "email": "platform@example.com"},
        license_info={"name": "MIT"},
    )

    if settings.BACKEND_CORS_ORIGINS:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=settings.BACKEND_CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Comprime respuestas > 1KB; mejora rendimiento sin cambiar el contrato.
    application.add_middleware(GZipMiddleware, minimum_size=1000)

    @application.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        """
        Red de seguridad: si algún router olvida capturar una excepción
        de dominio explícitamente, esta responde con un 400 genérico en
        vez de devolver un 500 con detalles internos (evita filtrar
        información -- OWASP API8:2023 Security Misconfiguration).
        """
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    application.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @application.get("/health", tags=["health"], summary="Chequeo de salud del servicio")
    async def health_check() -> dict[str, str]:
        """Endpoint estándar de liveness/readiness para orquestadores (k8s, ECS, etc.)."""
        return {"status": "ok", "environment": settings.ENVIRONMENT}

    return application


app = create_application()
