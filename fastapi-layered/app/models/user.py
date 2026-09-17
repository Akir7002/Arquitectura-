"""
Modelo ORM de Usuario (capa de persistencia).

Importante: este modelo NUNCA se expone directamente en las respuestas
de la API. Para eso existen los schemas Pydantic (app/schemas/user.py),
que definen explícitamente qué campos viajan hacia/desde el cliente
(por ejemplo, `hashed_password` jamás debe serializarse en una respuesta).
Esta separación Modelo <-> Schema es una de las prácticas recomendadas
por la documentación oficial de FastAPI.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:  # pragma: no cover - solo utilidad de debug
        return f"<User id={self.id} email={self.email!r}>"
