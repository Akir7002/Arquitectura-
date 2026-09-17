"""
Dependencias compartidas de la capa API.

Centralizar las dependencias (siguiendo bigger-applications de FastAPI:
https://fastapi.tiangolo.com/tutorial/bigger-applications/) evita
duplicar lógica de "obtener el repositorio", "obtener el servicio" o
"obtener el usuario actual" en cada router.
"""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UserNotFoundError
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService

# `tokenUrl` apunta al endpoint de login; esto es lo que hace que
# Swagger UI (/docs) muestre el botón "Authorize" con usuario/contraseña.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_user_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> UserRepository:
    return UserRepository(db)


def get_user_service(
    repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserService:
    return UserService(repository)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    """
    Dependencia de autenticación: decodifica el JWT del header
    `Authorization: Bearer <token>` y resuelve el usuario correspondiente.

    Reutilizable en cualquier endpoint protegido con:
        current_user: Annotated[User, Depends(get_current_user)]
    """
    from app.core.security import decode_access_token  # import local: evita ciclos

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    try:
        return await service.get_by_id(int(user_id))
    except (UserNotFoundError, ValueError):
        raise credentials_exception


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Igual que `get_current_user` pero además exige que la cuenta esté activa."""
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo.")
    return current_user
