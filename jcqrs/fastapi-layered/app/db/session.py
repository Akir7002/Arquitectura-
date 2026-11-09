"""
Capa de acceso a datos: engine y sesiones (Core/DB).

Patrón oficial de FastAPI para SQLAlchemy: un único `engine` compartido
por toda la aplicación y una sesión (`AsyncSession`) por request, inyectada
mediante Depends() con `yield` para garantizar que se cierre siempre
(incluso si la vista lanza una excepción).
Referencia: https://fastapi.tiangolo.com/tutorial/sql-databases/

Se usa el driver async `aiosqlite` para no bloquear el event loop, lo que
en producción se traduce 1:1 a un motor como `asyncpg` (PostgreSQL) o
`aiomysql` (MySQL) solo cambiando `DATABASE_URL`.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

# `connect_args` con `check_same_thread=False` es específico de SQLite y
# permite reutilizar la conexión entre distintos workers async.
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=connect_args,
)

# `expire_on_commit=False` evita una recarga (round-trip) extra a la BD
# tras cada commit, útil cuando luego serializamos el objeto a un schema.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependencia de FastAPI que entrega una sesión de BD por request.

    Implementa el patrón "Unit of Work a nivel de request" (commit-on-success):
    - Si el endpoint (y los servicios/repositorios que invoca) terminan sin
      excepciones, se hace COMMIT una sola vez al final del request.
    - Si se lanza cualquier excepción (de dominio o HTTPException), se hace
      ROLLBACK antes de propagarla, para no dejar cambios parciales a medias.

    Las capas de repositorio solo hacen `flush()` (para obtener IDs
    autogenerados dentro de la transacción); el `commit()` real está
    centralizado aquí, en el límite de la petición, evitando compromisos
    parciales cuando un router encadena varias operaciones.

    El uso de `yield` además garantiza el cierre de la sesión al finalizar
    la petición (patrón "dependencias con yield" de FastAPI), liberando la
    conexión de vuelta al pool incluso ante errores.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
