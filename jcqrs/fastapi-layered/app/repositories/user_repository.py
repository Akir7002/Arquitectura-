"""
Repositorio de Usuario (patrón Repository).

Responsabilidad única: traducir operaciones de negocio a consultas
SQLAlchemy. Esta capa NO conoce reglas de negocio (por ejemplo, no decide
si un email ya está en uso o cómo hashear una contraseña) ni conoce HTTP;
solo sabe hablar con la base de datos.

Beneficios de aislar esta capa:
- La capa de servicios puede testearse con un repositorio falso/mock.
- Si se cambia de SQLAlchemy a otro ORM, o de SQLite a PostgreSQL, solo
  se toca este archivo.
"""

from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: int) -> Optional[User]:
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def list(self, *, offset: int = 0, limit: int = 20) -> tuple[Sequence[User], int]:
        items_result = await self._session.execute(
            select(User).order_by(User.id).offset(offset).limit(limit)
        )
        total_result = await self._session.execute(select(func.count()).select_from(User))
        total = total_result.scalar_one()
        return items_result.scalars().all(), total

    async def create(self, *, email: str, full_name: str, hashed_password: str) -> User:
        user = User(email=email, full_name=full_name, hashed_password=hashed_password)
        self._session.add(user)
        await self._session.flush()  # asigna el `id` sin cerrar la transacción
        await self._session.refresh(user)
        return user

    async def update(self, user: User, data: UserUpdate, hashed_password: Optional[str]) -> User:
        if data.full_name is not None:
            user.full_name = data.full_name
        if data.is_active is not None:
            user.is_active = data.is_active
        if hashed_password is not None:
            user.hashed_password = hashed_password
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        await self._session.delete(user)
        await self._session.flush()
